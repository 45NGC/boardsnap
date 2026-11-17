"""Compare the completed empty-label ablation with its frozen control; no inference."""

import json
from pathlib import Path

from tools.analyze_targeted_regressions import changes
from tools.mixed_training_policy import metrics
from tools.neural_data import digest
from tools.prepare_phone_photos import ROOT, write_json
from tools.report_mixed_training import summarize
from tools.train_mixed_empty_guard import DEFAULT_PLAN


def compare(old, new):
    if len({r['image'] for r in old}) != len(old) or len(old) != len(new):
        raise ValueError('Duplicate or incomplete prediction records.')
    edits, gained, lost = [], [], []
    for a, b in zip(old, new, strict=True):
        if a['image'] != b['image'] or a['expected'] != b['expected']:
            raise ValueError('Unaligned control and candidate predictions.')
        delta = changes(a['expected'], a['predictions'], b['predictions'])
        if delta:
            edits.append({'image': a['image'], 'changes': delta})
        if a['expected'] == a['predictions'] and b['expected'] != b['predictions']:
            lost.append(a['image'])
        if b['expected'] == b['predictions'] and a['expected'] != a['predictions']:
            gained.append(a['image'])
    return {'control': metrics(old), 'candidate': metrics(new), 'changedBoards': edits,
            'gainedExactBoards': gained, 'lostExactBoards': lost}


def read_epoch(run, item):
    path = run / item['predictions']
    if digest(path) != item['predictionsSha256']:
        raise ValueError('Epoch predictions changed.')
    return json.loads(path.read_text())['records']


def build_report(plan_path=DEFAULT_PLAN):
    plan = json.loads(plan_path.read_text())
    report = summarize(plan_path)
    if not report['inputsUnchanged']:
        raise ValueError('Frozen inputs changed.')
    control_plan = json.loads((ROOT / plan['intervention']['controlPlan']).read_text())
    control_run, run = ROOT / control_plan['runDirectory'], ROOT / plan['runDirectory']
    old = json.loads((control_run / 'training.json').read_text())
    new = json.loads((run / 'training.json').read_text())
    if not old['complete'] or not new['complete'] or len(old['history']) != len(new['history']):
        raise ValueError('Expected completed paired attempts.')
    history = []
    for a, b in zip(old['history'], new['history'], strict=True):
        if a['epoch'] != b['epoch']:
            raise ValueError('Epochs differ.')
        ca, cb = read_epoch(control_run, a), read_epoch(run, b)
        history.append({'epoch': a['epoch'], 'domains': {d: compare(ca[d], cb[d]) for d in ca}})
    report['controlComparison'] = {
        'plan': plan['intervention']['controlPlan'], 'run': str(control_run.relative_to(ROOT)),
        'method': 'Same-epoch saved predictions; final epoch used for diagnosis only, not unsafe model selection.',
        'history': history, 'lastEpoch': history[-1],
    }
    report['maskAudit'] = json.loads((run / 'mask-audit.json').read_text())
    report['reportCodeSha256'] = digest(Path(__file__))
    report['reportInferenceRun'] = False
    return report


def main():
    report = build_report()
    write_json(ROOT / 'data/reports/neural-mixed-empty-guard-v1.json', report)
    final = report['controlComparison']['lastEpoch']['domains']
    print(json.dumps({'qualityGatePassed': report['qualityGatePassed'], 'selectedEpoch': report['selectedEpoch'],
                      'lastEpoch': {d: {'control': r['control'], 'candidate': r['candidate'],
                                       'changedBoards': len(r['changedBoards'])} for d, r in final.items()}}))


if __name__ == '__main__':
    main()
