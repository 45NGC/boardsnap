"""Compare fixed models through the real CLI on consulted development cases."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from tools.evaluate_photo_pipeline import placement_ids
from tools.evaluate_neural import score
from tools.mixed_training_policy import metrics
from tools.neural_data import digest
from tools.prepare_phone_photos import ROOT, write_json

BASELINE = '.cache/neural-phone-v1/best.pt'
CANDIDATE = '.cache/neural-mixed-sqrt-v1/last.pt'
RUN = ROOT / '.cache/mixed-sqrt-cli-v1'


def check_contract(process):
    result = json.loads(process.stdout)
    if process.stderr or process.stdout != json.dumps(result) + '\n':
        raise ValueError('Diagnostics or noncanonical JSON output.')
    if set(result) == {'piecePlacement'}:
        if process.returncode != 0 or len(placement_ids(result['piecePlacement'])) != 64:
            raise ValueError('Invalid success contract.')
    elif set(result) == {'error'}:
        if (process.returncode != 1 or set(result['error']) != {'code', 'message'}
                or not all(isinstance(v, str) and v for v in result['error'].values())):
            raise ValueError('Invalid error contract.')
    else:
        raise ValueError('Unexpected JSON fields.')
    return result


def invoke(case, model, runtime):
    image = ROOT / case['path']
    if digest(image) != case['sha256']:
        raise ValueError('Development image changed.')
    key = {'imageSha256': case['sha256'], 'modelSha256': digest(ROOT / model),
           'orientation': case['orientation'], 'inputType': case.get('inputType', 'digital'),
           'runtime': runtime, 'python': sys.version}
    import hashlib
    cache = RUN / (hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest() + '.json')
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved['signature'] != key:
            raise ValueError('CLI cache signature differs.')
        check_contract(subprocess.CompletedProcess([], saved['exitCode'], saved['stdout'], saved['stderr']))
        return saved
    command = [sys.executable, '-m', 'boardsnap', str(image), '--model', str(ROOT / model),
               '--orientation', case['orientation'], '--input-type', case.get('inputType', 'digital')]
    began = time.perf_counter()
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120,
                             env={**os.environ, 'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4'})
    result = check_contract(process)
    saved = {'signature': key, 'command': command, 'result': result, 'exitCode': process.returncode,
             'stdout': process.stdout, 'stderr': process.stderr, 'seconds': time.perf_counter()-began}
    write_json(cache, saved)
    return saved


def paired_summary(records):
    summary = {}
    for model in ('baseline', 'candidate'):
        detected = [r for r in records if 'piecePlacement' in r[model]]
        labels = [{'positionId':r['expected'], 'expected': placement_ids(r['expected']),
                   'predictions': placement_ids(r[model]['piecePlacement'])} for r in detected]
        summary[model] = {'images': len(records), 'detected': len(detected),
                          'exactBoards': sum(r[model].get('piecePlacement') == r['expected'] for r in records),
                          'classificationOnDetectedOnly': score(labels) if labels else None,
                          'errorCountsOnDetectedOnly': metrics([dict(r,image=str(i)) for i,r in enumerate(labels)]) if labels else None}
    summary['gainedExactBoards'] = [r['id'] for r in records if r['candidate'].get('piecePlacement') == r['expected']
                                   and r['baseline'].get('piecePlacement') != r['expected']]
    summary['lostExactBoards'] = [r['id'] for r in records if r['baseline'].get('piecePlacement') == r['expected']
                                 and r['candidate'].get('piecePlacement') != r['expected']]
    summary['changedResults'] = [r['id'] for r in records if r['baseline'] != r['candidate']]
    return summary


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    runtime = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))}
    inputs = {}
    cases = []
    for name in ('real-use-development-v1', 'video-development-v2'):
        path = ROOT / f'data/manifests/{name}.json'
        data = json.loads(path.read_text())
        if data['independentFinalEvaluation'] is not False:
            raise ValueError('Development data only.')
        inputs[str(path.relative_to(ROOT))] = digest(path)
        for row in data['samples']:
            case = dict(row)
            if not (ROOT / case['path']).exists():
                moved = ROOT / '.cache/real-use-tests/computer-screenshots' / Path(case['path']).name
                if not moved.exists() or digest(moved) != case['sha256']:
                    raise ValueError('Missing or changed development screenshot: ' + case['path'])
                case['manifestPath'] = case['path']
                case['path'] = str(moved.relative_to(ROOT))
            cases.append(case)
    path = ROOT/'data/reports/digital-regressions-v8.json'
    data = json.loads(path.read_text());inputs[str(path.relative_to(ROOT))] = digest(path)
    for i, r in enumerate(data['images']):
        cases.append(dict(id=f'original-{i+1}',path=r['image'],sha256=r['sha256'],
                          orientation=r['orientation'],piecePlacement=r['expected']['piecePlacement'],
                          conditions=['consulted-original-regression']))
    # Preserve all aliases while executing an identical image/view only once.
    unique = {}
    for c in cases:
        key = (c['sha256'], c['orientation'])
        if key in unique:
            if unique[key]['piecePlacement'] != c['piecePlacement']:
                raise ValueError('Duplicate pixels have contradictory labels.')
            unique[key]['aliases'].append(c['id'])
        else:
            unique[key] = dict(c, aliases=[c['id']])
    digital = []
    for c in unique.values():
        outputs = {name: invoke(c, model, runtime) for name, model in [('baseline',BASELINE),('candidate',CANDIDATE)]}
        digital.append({'id': c['id'], 'aliases': c['aliases'], 'image':c['path'],'sha256':c['sha256'],
                        'orientation':c['orientation'],'expected':c['piecePlacement'],
                        'originalManifestPath':c.get('manifestPath',c['path']),
                        'conditions':c.get('conditions',[]), **{name:r['result'] for name,r in outputs.items()},
                        'cli':outputs})
        print(f'Digital {len(digital)}/{len(unique)}: {c["id"]}',flush=True)
    old_path=ROOT/'data/reports/photo-pipeline-validation-v2.json'
    new_path=ROOT/'.cache/neural-mixed-sqrt-v1/photo-cli-validation.json'
    old,new=(json.loads(p.read_text()) for p in (old_path,new_path))
    for report,path,model in [(old,old_path,BASELINE),(new,new_path,CANDIDATE)]:
        if (report['modelSha256'] != digest(ROOT/model) or report['finalEvaluationAccessed'] is not False
                or any(digest(ROOT/p)!=h for p,h in report['codeSha256'].items())
                or digest(Path(report['manifest']))!=report['manifestSha256']
                or digest(Path(report['detectionReport']))!=report['detectionReportSha256']):
            raise ValueError('Photo CLI report is stale.')
        inputs[str(path.relative_to(ROOT))]=digest(path)
    photos=[]
    for a,b in zip(old['records'],new['records'],strict=True):
        if any(a[k]!=b[k] for k in ('id','imageSha256','orientation','expected')):
            raise ValueError('Unaligned photo reports.')
        if digest(ROOT/a['image'])!=a['imageSha256']:raise ValueError('Photo changed.')
        photos.append({'id':a['id'],'image':a['image'],'sha256':a['imageSha256'],
                       'expected':a['expected'],'orientation':a['orientation'],'category':a['category'],
                       'baseline':a['cliResult'],'candidate':b['cliResult'],
                       'baselineAnnotated':a['annotatedPlacement'],'candidateAnnotated':b['annotatedPlacement'],
                       'candidateChangedSquaresVsAnnotated':b.get('changedSquaresVsAnnotated'),
                       'candidateGeometry':b.get('geometryMetrics')})
    error_checks=[]
    from PIL import Image
    blank=RUN/'no-board.png'
    if not blank.exists():
        with Image.new('RGB',(400,400),'white') as image:image.save(blank)
    for input_type in ('digital','photo'):
        case={'path':str(blank.relative_to(ROOT)),'sha256':digest(blank),
              'orientation':'white-bottom','inputType':input_type}
        outputs={name:invoke(case,model,runtime)['result'] for name,model in [('baseline',BASELINE),('candidate',CANDIDATE)]}
        if any(r.get('error',{}).get('code')!='BOARD_NOT_FOUND' for r in outputs.values()):
            raise ValueError('Blank-image negative control did not reject the image.')
        error_checks.append({'inputType':input_type,'expectedCode':'BOARD_NOT_FOUND',**outputs})
    report={'schemaVersion':1,'dataRole':'consulted-development-regression','finalEvaluationAccessed':False,
            'trainingRun':False,'negativeControls':error_checks,'baseline':{'path':BASELINE,'sha256':digest(ROOT/BASELINE)},
            'candidate':{'path':CANDIDATE,'sha256':digest(ROOT/CANDIDATE),'status':'experimental-not-promoted'},
            'runtimeSha256':runtime,'analysisCodeSha256':digest(Path(__file__)),'inputs':inputs,
            'photoBaselineReused':str(old_path.relative_to(ROOT)),
            'scope':'30 consulted photo validation cases; deduplicated annotated real screenshots and six exposed digital regressions. Not the full 3132-board validation corpus or final acceptance.',
            'timingScope':'CLI process including startup; no isolated CPU benchmark.',
            'photos':{'summary':paired_summary(photos),'records':photos,
                      'annotated':{'baseline':old['summary']['annotatedExactBoards'],'candidate':new['summary']['annotatedExactBoards']},
                      'byCategory':{c:paired_summary([r for r in photos if r['category']==c]) for c in sorted({r['category'] for r in photos})}},
            'digital':{'summary':paired_summary(digital),'records':digital,'manifestRowsBeforeDeduplication':len(cases)}}
    if runtime != {str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))}:
        raise ValueError('Runtime changed during comparison.')
    write_json(ROOT/'data/reports/mixed-sqrt-cli-v1.json',report)
    print(json.dumps({d:{m:{k:report[d]['summary'][m][k] for k in ('images','detected','exactBoards')} for m in ('baseline','candidate')} for d in ('photos','digital')}))


if __name__=='__main__':main()
