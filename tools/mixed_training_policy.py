"""Check the frozen mixed-training recipe and paired quality gates without training."""

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from tools.neural_data import digest
from tools.position_dataset import LABELS
from tools.prepare_phone_photos import ROOT, write_json

DEFAULT_PLAN = ROOT/'data/manifests/neural-mixed-v1-plan.json'


def metrics(records):
    if not records or len({r['image'] for r in records}) != len(records):
        raise ValueError('Expected nonempty unique prediction records.')
    for row in records:
        for key in ('expected', 'predictions'):
            if len(row[key]) != 64 or any(type(v) is not int or not 0 <= v < 13 for v in row[key]):
                raise ValueError('Expected 64 integer class IDs per board.')
    expected=np.asarray([r['expected'] for r in records])
    predictions=np.asarray([r['predictions'] for r in records])
    counts=np.bincount(expected.ravel(),minlength=13)
    correct=np.bincount(expected[expected==predictions],minlength=13)
    return {'boards':len(records),'squares':expected.size,
        'exactBoards':int((expected==predictions).all(1).sum()),
        'correctSquares':int((expected==predictions).sum()),
        'falsePieces':int(((expected==0)&(predictions!=0)).sum()),
        'missedPieces':int(((expected!=0)&(predictions==0)).sum()),
        'classTotals':counts.tolist(),'classCorrect':correct.tolist(),
        'macroRecall':float(np.mean(correct[counts>0]/counts[counts>0]))}


def strata(row, domain):
    keys=[('category',row.get('category','unknown')),('orientation',row.get('orientation','unknown'))]
    keys += [('condition',c) for c in row.get('conditions',[])]
    fields=('configurationId',) if domain=='digital' else ('appearance','background')
    keys += [(field,row.get(field,'unknown')) for field in fields]
    return keys


def assess_accuracy(baseline, candidate, *, minimum_photo_gain=1):
    """Separate checkpoint safety from improvement; counts cannot hide lost controls."""
    if type(minimum_photo_gain) is not int or minimum_photo_gain < 1:
        raise ValueError('Require at least one additional correct photo board.')
    if set(baseline) != {'phone','digital'} or set(candidate) != set(baseline):
        raise ValueError('Both complete validation domains are required.')
    reasons=[]; summaries={}
    for domain, old in baseline.items():
        new=candidate[domain]
        a,b=metrics(old),metrics(new)
        if [r['image'] for r in old] != [r['image'] for r in new] or any(
                x['expected']!=y['expected'] for x,y in zip(old,new)):
            raise ValueError('Validation image order or labels changed.')
        lost=[x['image'] for x,y in zip(old,new) if x['predictions']==x['expected'] and y['predictions']!=y['expected']]
        if lost:reasons.append(domain+': lost baseline-correct boards')
        if b['correctSquares'] < a['correctSquares']:reasons.append(domain+': fewer correct squares')
        for key in ('falsePieces','missedPieces'):
            if b[key]>a[key]:reasons.append(domain+': increased '+key)
        lost_classes=[LABELS[i] for i,(x,y) in enumerate(zip(a['classCorrect'],b['classCorrect'])) if y<x]
        if lost_classes:reasons.append(domain+': decreased class recall '+','.join(lost_classes))
        # Stratify using frozen reference metadata, never candidate-provided grouping.
        groups={key:[] for row in old for key in strata(row,domain)}
        for i,row in enumerate(old):
            for key in strata(row,domain):groups[key].append(i)
        stratum_losses=[]
        for key,indices in sorted(groups.items()):
            before=metrics([old[i] for i in indices]);after=metrics([new[i] for i in indices])
            worse=[k for k in ('exactBoards','correctSquares') if after[k]<before[k]]
            worse += [k for k in ('falsePieces','missedPieces') if after[k]>before[k]]
            if worse:stratum_losses.append({'stratum':list(key),'metrics':worse})
        if stratum_losses:reasons.append(domain+': worsened validation strata')
        summaries[domain]={'baseline':a,'candidate':b,'lostExactBoards':lost,'stratumRegressions':stratum_losses}
    safe=not reasons
    improved=summaries['phone']['candidate']['exactBoards'] >= summaries['phone']['baseline']['exactBoards']+minimum_photo_gain
    if not improved:reasons.append('phone: insufficient exact-board improvement')
    p=summaries['phone']['candidate'];d=summaries['digital']['candidate']
    return {'safeCheckpoint':safe,'accuracyAccepted':safe and improved,
            'rankingKey':[p['exactBoards'],p['macroRecall'],p['correctSquares'],d['exactBoards'],d['correctSquares']] if safe else None,
            'reasons':reasons,'domains':summaries,
            'promotionAllowed':False,'pending':['isolated CPU benchmark','full CLI regression checks']}


def reference_records(plan, root=ROOT):
    appearances={r['photoId']:r for r in json.loads((root/plan['appearanceManifest']).read_text())['samples']}
    result={}
    for domain,entry in plan['baselineReports'].items():
        report=json.loads((root/entry['path']).read_text())
        if report['split']!='validation' or report['models']['baseline']['sha256']!=plan['baseline']['sha256']:
            raise ValueError('Wrong reference model or split.')
        records=report['records']['baseline']
        if domain=='phone':
            records=[dict(r,appearance=appearances[Path(r['image']).stem]['pieceAppearance'],
                          background=appearances[Path(r['image']).stem]['boardAppearance']) for r in records]
        result[domain]=records
    return result


def preflight(plan, root=ROOT):
    for entry in plan['frozenInputs']:
        if digest(root/entry['path'])!=entry['sha256']:
            raise ValueError('Changed frozen input: '+entry['path'])
    dataset=root/plan['dataset']
    metadata=json.loads((dataset/'dataset.json').read_text())
    if not metadata['complete'] or metadata['audit']['observedConflicts']:
        raise ValueError('Mixed dataset is incomplete or conflicting.')
    for name,entry in metadata['artifacts'].items():
        if digest(dataset/name)!=entry['sha256']:raise ValueError('Changed prepared artifact.')
    for entry in metadata['inputs']:
        if digest(root/entry['path'])!=entry['sha256']:raise ValueError('Changed source data.')
    labels=np.load(dataset/'training-labels.npy',mmap_mode='r',allow_pickle=False)
    counts=np.bincount(labels,minlength=13)
    if counts.tolist()!=plan['loss']['classCounts']:raise ValueError('Class frequencies changed.')
    weights=(len(labels)/(13*counts)).astype(np.float32).tolist()
    if weights!=plan['loss']['classWeights']:raise ValueError('Class weighting differs from the recipe.')
    with np.load(dataset/'sampling-epoch-000.npz',allow_pickle=False) as draws:
        refs=[json.loads(line) for line in (dataset/'training-boards.jsonl').read_text().splitlines()]
        pools=Counter(refs[int(i)]['pool'] for i in draws['board_indices'])
    if pools!=plan['poolQuotas']:raise ValueError('Sampling quotas changed.')
    baseline=reference_records(plan,root)
    validation=[json.loads(line) for line in (dataset/'validation.jsonl').read_text().splitlines()]
    appearance_rows={r['photoId']:r for r in json.loads((root/plan['appearanceManifest']).read_text())['samples']}
    for domain,records in baseline.items():
        expected={r['row']['image']:r['row'] for r in validation
                  if r['sourceDataset']==plan['validationDatasets'][domain]}
        if len(expected)!=len(records) or set(expected)!={r['image'] for r in records}:
            raise ValueError('Reference validation membership differs.')
        for record in records:
            row=expected[record['image']]
            if record['expected']!=[c['classId'] for c in row['cells']]:raise ValueError('Reference labels changed.')
            if domain=='phone' and appearance_rows[row['photoId']]['imageSha256']!=row['sha256']:
                raise ValueError('Appearance review refers to another photo.')
        if metrics(records)!=plan['baselineMetrics'][domain]:raise ValueError('Baseline metrics changed.')
    return {'planId':plan['planId'],'status':'configuration-frozen-training-not-started',
            'baselineMetrics':plan['baselineMetrics'],'classCounts':counts.tolist(),
            'teacherSamples':sum(n for pool,n in pools.items() if pool!='photo-targeted'),
            'supervisedOnlySamples':pools['photo-targeted'],
            'artifactsVerified':len(metadata['artifacts']),'trainingRun':False,'inferenceRun':False,
            'finalEvaluationAccessed':False,
            'remainingImplementation':['Wire the mixed checked loader, masked training teacher, per-epoch dual-domain safety gate and resumable checkpoint selection into the runner before launching.']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=DEFAULT_PLAN)
    parser.add_argument('--report',type=Path,default=ROOT/'data/reports/neural-mixed-v1-preflight.json')
    args=parser.parse_args(argv)
    result=preflight(json.loads(args.plan.read_text()))
    result['planSha256']=digest(args.plan)
    write_json(args.report,result)
    print(json.dumps({'status':result['status'],'trainingRun':False}))


if __name__=='__main__':main()
