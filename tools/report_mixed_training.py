"""Summarize saved mixed-run predictions; never run inference or choose an unsafe epoch."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from tools.analyze_targeted_regressions import changes
from tools.evaluate_neural import score
from tools.mixed_training_policy import DEFAULT_PLAN, reference_records, strata
from tools.neural_data import digest
from tools.prepare_phone_photos import ROOT, write_json


def summarize(plan_path=DEFAULT_PLAN,root=ROOT):
    plan=json.loads(plan_path.read_text());run=root/plan['runDirectory']
    training=json.loads((run/'training.json').read_text())
    signature=json.loads((run/'execution.json').read_text())
    if signature['planSha256']!=digest(plan_path) or not training['complete']:
        raise ValueError('Expected the completed frozen run.')
    selected=training['selected']
    epoch=selected['epoch'] if selected else training['completedEpochs']
    item=training['history'][epoch-1];path=run/item['predictions']
    if digest(path)!=item['predictionsSha256']:raise ValueError('Saved predictions changed.')
    predictions=json.loads(path.read_text());baseline=reference_records(plan,root)
    model_path=run/('best.pt' if selected else 'last.pt')
    expected_hash=training['weightsSha256'] if selected else training['lastCheckpointSha256']
    if digest(model_path)!=expected_hash:raise ValueError('Saved model changed.')
    domains={}
    for domain,old in baseline.items():
        new=predictions['records'][domain]
        groups=defaultdict(list)
        for i,row in enumerate(old):
            for key in strata(row,domain):groups[key].append(i)
        delta=[];gained=[];lost=[]
        for a,b in zip(old,new,strict=True):
            if a['image']!=b['image'] or a['expected']!=b['expected']:raise ValueError('Unaligned predictions.')
            edits=changes(a['expected'],a['predictions'],b['predictions'])
            if edits:delta.append({'image':a['image'],'changes':edits})
            before=a['expected']==a['predictions'];after=b['expected']==b['predictions']
            if before and not after:lost.append(a['image'])
            if after and not before:gained.append(a['image'])
        domains[domain]={'baseline':score(old),'candidate':score(new),'gainedExactBoards':gained,
            'lostExactBoards':lost,'changedBoards':delta,
            'strata':[{'key':list(key),'baseline':score([old[i] for i in ids]),
                      'candidate':score([new[i] for i in ids])} for key,ids in sorted(groups.items())]}
    quality=bool(selected and selected['assessment']['accuracyAccepted'])
    return {'schemaVersion':1,'planId':plan['planId'],'planSha256':digest(plan_path),
        'run':str(run.relative_to(root)),'trainingSha256':digest(run/'training.json'),
        'runnerSha256':signature['runnerSha256'],'baseline':plan['baseline'],
        'complete':True,'completedEpochs':training['completedEpochs'],'selectedEpoch':selected['epoch'] if selected else None,
        'diagnosticEpoch':epoch,'diagnosticModel':{'path':str(model_path.relative_to(root)),'sha256':digest(model_path),
            'scope':'selected safe checkpoint' if selected else 'last epoch for diagnosis only, not selected or accepted'},
        'safeEpochs':[h['epoch'] for h in training['history'] if h['assessment']['safeCheckpoint']],
        'accuracyAcceptedEpochs':[h['epoch'] for h in training['history'] if h['assessment']['accuracyAccepted']],
        'history':[{'epoch':h['epoch'],'seconds':h['seconds'],'assessment':h['assessment']} for h in training['history']],
        'assessment':predictions['assessment'],'domains':domains,'qualityGatePassed':quality,
        'cpuCheck':{'status':'pending' if quality else 'not-run-no-qualifying-candidate'},
        'cliCheck':{'status':'pending' if quality else 'not-run-no-qualifying-candidate'},
        'promoted':False,'recommendedModel':plan['baseline']['path'],
        'decision':'Further CPU and CLI checks required before promotion.' if quality else 'Reject this bounded attempt; keep phone-v1. Do not extend epochs or relax criteria.',
        'trainingDiagnostics':'No additional inference on training photos: frozen validation already determines eligibility.',
        'finalEvaluationAccessed':False,'validationRole':'previously consulted development/model-selection data',
        'inputsUnchanged':all(digest(root/e['path'])==e['sha256'] for e in plan['frozenInputs'])}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=DEFAULT_PLAN)
    parser.add_argument('--report',type=Path,default=ROOT/'data/reports/neural-mixed-v1.json')
    args=parser.parse_args(argv)
    result=summarize(args.plan)
    if not result['inputsUnchanged']:raise ValueError('Frozen input changed.')
    write_json(args.report,result)
    print(json.dumps({'selectedEpoch':result['selectedEpoch'],'qualityGatePassed':result['qualityGatePassed']}))


if __name__=='__main__':main()
