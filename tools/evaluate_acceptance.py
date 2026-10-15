"""One-shot reserved evaluation, guarded by frozen policy and release readiness."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import resource
import time

from tools.digital_acceptance import acceptance_gates, check_frozen, performance_gates, require_ready
from tools.neural_data import child, digest


def start_attempt(root, policy_hash, model_hash, plan=None, history=None):
    """A crash also consumes the set; do not silently retry a consulted holdout."""
    with (root/'acceptance-attempt.json').open('x') as stream:
        if plan is not None:
            from tools.acceptance_history import consume, HISTORY
            consume(plan, policy_hash, model_hash, HISTORY if history is None else history)
        stream.write(json.dumps({'policySha256':policy_hash,'modelSha256':model_hash,
                                 'status':'started; reserved data is now considered consulted'},indent=2)+'\n')


def summarize(records, negatives, bounds_ok, misses):
    from tools.evaluate_neural import score
    from boardsnap.orientation import to_canonical
    def metrics(rows):
        result=score(rows)
        result['exactBoardRate']=result['exactBoards']/result['images'] if result['images'] else None
        return result
    strata={}
    for field in ('combination','condition','layout','orientation','platform'):
        groups=defaultdict(list)
        for row in records:groups[row[field]].append(row)
        strata[field]={key:metrics(group) for key,group in groups.items()}
    canonical=[[f'{chr(97+c)}{8-r}' for c in range(8)] for r in range(8)]
    mapping=sum(to_canonical(view,orientation)==canonical for view,orientation in (
        (canonical,'white-bottom'),([row[::-1] for row in canonical[::-1]],'black-bottom')))/2
    return {'all':metrics(records),'strata':strata,
            'detection':{'images':len(records),'misses':misses,'missRate':misses/len(records),
                         'withinTwoPixels':bounds_ok,'withinTwoPixelsRate':bounds_ok/len(records)},
            'negatives':{'images':len(negatives),'falseDetections':sum(r['falseDetection'] for r in negatives),
                         'falseDetectionRate':sum(r['falseDetection'] for r in negatives)/len(negatives)},
            'orientationMappingRate':mapping}


def evaluate(policy_path, plan_path, model_path, readiness_path, corpus_root, output):
    policy=json.loads(policy_path.read_text())
    check_frozen(policy,model_path)
    require_ready(policy,digest(policy_path),readiness_path)  # Must precede even opening corpus.json.
    if output.exists():raise ValueError('Never overwrite a final acceptance result.')
    from tools.acceptance_corpus import validate_plan
    plan=json.loads(plan_path.read_text())
    if digest(plan_path)!=policy['planSha256']:raise ValueError('Frozen plan changed.')
    validate_plan(plan)
    corpus=json.loads((corpus_root/'corpus.json').read_text())
    if corpus['policySha256']!=digest(policy_path) or corpus['planSha256']!=digest(plan_path):
        raise ValueError('Corpus belongs to another frozen protocol.')
    if len(corpus['positives'])!=4560 or len(corpus['negatives'])<policy['thresholds']['minimumNegatives']:
        raise ValueError('Incomplete acceptance corpus.')
    identities={p['positionId']:p for p in plan['positions']}
    unique=set()
    for row in corpus['positives']:
        position=identities[row['positionId']]
        if row['groupId']!=position['groupId'] or row['piecePlacement']!=position['piecePlacement'] or row['split']!='acceptance':
            raise ValueError('Acceptance source identity changed.')
        key=tuple(row[k] for k in ('positionId','combination','orientation','layout','condition'))
        if key in unique:raise ValueError('Duplicate acceptance variant.')
        unique.add(key)
    import cv2
    import torch
    from boardsnap.neural import NeuralClassifier
    from boardsnap.detection import BoardDetectionError, detect_board
    from boardsnap.image_input import ImageInputError, read_image
    from boardsnap.classification import ClassificationError
    from tools.build_square_dataset import raster_bounds
    from tools.evaluate_detection import rectangle_metrics
    from tools.evaluate_neural import placement_ids, timing
    torch.set_num_threads(policy['cpu']['torchThreads']); cv2.setNumThreads(policy['cpu']['opencvThreads'])
    classifier=NeuralClassifier(model_path)
    start_attempt(corpus_root,digest(policy_path),digest(model_path),plan)
    records,negative_results,latencies=[],[],[]
    within=missed=0
    for row in corpus['positives']:
        path=child(corpus_root,row['image'])
        if digest(path)!=row['sha256']:raise ValueError('Reserved image changed.')
        record={k:row[k] for k in ('image','positionId','groupId','combination','condition','layout','orientation','platform')}
        record['expected']=placement_ids(row['piecePlacement']).tolist()
        start=time.perf_counter()
        try:
            result=classifier.recognize_image(path,orientation=row['orientation'])
            if set(result)!={'piecePlacement'}:raise ValueError('Public JSON contract changed.')
            record['predictions']=placement_ids(result['piecePlacement']).tolist()
        except (ImageInputError,BoardDetectionError,ClassificationError) as error:
            record.update(predictions=[-1]*64,error=error.to_dict())
        latencies.append(time.perf_counter()-start)
        with read_image(path) as image:
            try:
                box=detect_board(image)
                geometry=rectangle_metrics(box.as_box(),raster_bounds(row['boardBounds']).as_box())
                within+=geometry['maxEdgeErrorPixels']<=2
            except BoardDetectionError:missed+=1
        records.append(record)
        if len(records)%100==0:print(f'Acceptance {len(records)}/{len(corpus["positives"])}',flush=True)
    for row in corpus['negatives']:
        path=child(corpus_root,row['image'])
        if digest(path)!=row['sha256']:raise ValueError('Negative image changed.')
        with read_image(path) as image:
            try:
                detect_board(image); false=True
            except BoardDetectionError as error:false=error.code!='BOARD_NOT_FOUND'
        negative_results.append(dict(row,falseDetection=false))
    summary=summarize(records,negative_results,within,missed)
    readiness_report=json.loads(readiness_path.read_text())
    benchmark=json.loads((Path(__file__).resolve().parents[1]/readiness_report['evidence']['benchmark']['path']).read_text())
    performance=dict(benchmark,warm=timing(latencies),peakRssMiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    gates=acceptance_gates(policy,summary)+performance_gates(policy,performance)
    report={'status':'accepted' if all(g['passed'] for g in gates) else 'rejected',
            'policySha256':digest(policy_path),'modelSha256':digest(model_path),
            'corpusSha256':digest(corpus_root/'corpus.json'),'planSha256':digest(plan_path),
            'readinessSha256':digest(readiness_path),
            'evaluationCodeSha256':digest(Path(__file__)),'summary':summary,'gates':gates,
            'environment':{'torch':str(torch.__version__),'opencv':cv2.__version__,
                           'torchThreads':policy['cpu']['torchThreads'],'opencvThreads':policy['cpu']['opencvThreads']},
            'warmLatency':performance['warm'],'peakRssMiB':performance['peakRssMiB'],
            'performance':{k:performance[k] for k in ('warm','coldMilliseconds','peakRssMiB')},
            'coldScope':'fresh-process validation benchmark pinned in readiness report',
            'records':records,'negatives':negative_results,
            'warning':'This set is now consulted. Do not tune on it and claim a new independent final test.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('policy','plan','model','readiness','corpus','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:
        report=evaluate(args.policy,args.plan,args.model,args.readiness,args.corpus,args.output)
    except (ValueError,FileExistsError) as error:
        parser.exit(2,str(error)+'\n')
    print(report['status'])
    return 0 if report['status']=='accepted' else 1


if __name__=='__main__':raise SystemExit(main())
