"""Report the frozen weight ablation, with paired controls and thin-piece diagnostics."""

import json
from pathlib import Path

from tools.mixed_training_policy import metrics, reference_records
from tools.neural_data import digest
from tools.prepare_phone_photos import ROOT, write_json
from tools.report_mixed_empty_guard import compare, read_epoch
from tools.report_mixed_training import summarize
from tools.train_mixed_sqrt import DEFAULT_PLAN


def omission_metrics(records):
    result = metrics(records)
    result['pawnSquares'] = sum(e in (1, 7) for row in records for e in row['expected'])
    result['missedPawns'] = sum(e in (1, 7) and p == 0 for row in records
                                for e, p in zip(row['expected'], row['predictions'], strict=True))
    result['wrongPawnTypeOrColor'] = sum(e in (1, 7) and p not in (0, e) for row in records
                                        for e, p in zip(row['expected'], row['predictions'], strict=True))
    return result


def build_report(plan_path=DEFAULT_PLAN):
    plan = json.loads(plan_path.read_text())
    report = summarize(plan_path)
    if not report['inputsUnchanged']:
        raise ValueError('Frozen inputs changed.')
    control_plan = json.loads((ROOT / plan['weightExperiment']['controlPlan']).read_text())
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
        'plan': plan['weightExperiment']['controlPlan'], 'run': str(control_run.relative_to(ROOT)),
        'method': 'Same-epoch saved predictions; final epoch for diagnosis only, never unsafe selection.',
        'history': history, 'lastEpoch': history[-1],
    }
    # ca/cb refer to the last epoch even when selection chose an earlier safe epoch.
    baseline = reference_records(plan)['phone']
    photo_sets = {'baseline': baseline, 'controlLast': ca['phone'], 'candidateLast': cb['phone']}
    if report['selectedEpoch'] is not None:
        chosen = read_epoch(run, new['history'][report['selectedEpoch'] - 1])
        photo_sets['selectedCandidate'] = chosen['phone']
    appearances = sorted({r['appearance'] for r in baseline})
    report['photoDiagnostics'] = {
        name: {'all': omission_metrics(rows), 'byAppearance': {
            appearance: omission_metrics([r for r in rows if r['appearance'] == appearance])
            for appearance in appearances}} for name, rows in photo_sets.items()}
    report['weightAudit'] = {
        'controlWeights': control_plan['loss']['classWeights'], 'candidateWeights': plan['loss']['classWeights'],
        'classOrder': plan['classOrder'], 'classCounts': plan['loss']['classCounts'],
        'formula': plan['weightExperiment']['formula'],
        'controlBlackQueenToEmptyRatio': control_plan['loss']['classWeights'][11] / control_plan['loss']['classWeights'][0],
        'candidateBlackQueenToEmptyRatio': plan['loss']['classWeights'][11] / plan['loss']['classWeights'][0],
    }
    report['maskAudit'] = json.loads((run / 'mask-audit.json').read_text())
    report['reportCodeSha256'] = digest(Path(__file__))
    report['reportInferenceRun'] = False
    return report


def main():
    report = build_report()
    write_json(ROOT / 'data/reports/neural-mixed-sqrt-v1.json', report)
    print(json.dumps({'qualityGatePassed': report['qualityGatePassed'], 'selectedEpoch': report['selectedEpoch'],
                      'lastPhoto': report['photoDiagnostics']['candidateLast']['all'],
                      'lastDigital': report['controlComparison']['lastEpoch']['domains']['digital']['candidate']}))


if __name__ == '__main__':
    main()
