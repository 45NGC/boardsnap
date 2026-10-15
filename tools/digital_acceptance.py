"""Fail-closed digital release gates; consulted corpora remain regression data."""

import argparse
import json
import math
from pathlib import Path

from tools.neural_data import digest
from tools.position_dataset import ROOT


def check_frozen(policy, model):
    if digest(model) != policy['modelSha256']:
        raise ValueError('Model differs from the frozen acceptance candidate.')
    actual = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))}
    if actual != policy['runtimeSha256']:
        raise ValueError('Runtime differs from the frozen acceptance candidate.')


def metric_gate(name, actual, threshold, *, minimum=True):
    valid = isinstance(actual, (float, int)) and not isinstance(actual, bool) and math.isfinite(actual)
    return {'name': name, 'actual': actual, 'threshold': threshold,
            'comparison': '>=' if minimum else '<=',
            'passed': bool(valid and (actual >= threshold if minimum else actual <= threshold))}


def performance_gates(policy, benchmark):
    t = policy['thresholds']
    return [metric_gate('cpu-warm-samples', benchmark.get('warm', {}).get('samples'), policy['cpu']['minimumWarmSamples']),
            metric_gate('cpu-warm-p95-ms', benchmark.get('warm', {}).get('p95Milliseconds'), t['maximumWarmP95Milliseconds'], minimum=False),
            metric_gate('cpu-cold-ms', benchmark.get('coldMilliseconds'), t['maximumColdMilliseconds'], minimum=False),
            metric_gate('cpu-peak-rss-mib', benchmark.get('peakRssMiB'), t['maximumPeakRssMiB'], minimum=False)]


def readiness(policy, regression, benchmark, installation):
    if regression['models']['styleCandidate'] != policy['modelSha256']:
        raise ValueError('Regression report belongs to another model.')
    if benchmark['modelSha256'] != policy['modelSha256'] or benchmark.get('dataRole') != 'validation':
        raise ValueError('CPU evidence must use this model and validation data.')
    before = regression['results']['arrowBaseline']['detected']['strata']['cohort']['previous']
    after = regression['results']['styleCandidate']['detected']['strata']['cohort']['previous']
    if before['images'] != after['images']:
        raise ValueError('Regression denominators disagree.')
    missed = sum(r['images']-r['withinTwoPixels'] for r in regression['detection'].values())
    requirements = policy['prerequisites']
    before_errors={r['image'] for r in regression['results']['arrowBaseline']['detected']['errors']}
    after_errors={r['image'] for r in regression['results']['styleCandidate']['detected']['errors']}
    gates = [metric_gate('new-regression-board-errors', len(after_errors-before_errors),
                         requirements['maximumNewRegressionErrors'], minimum=False),
             metric_gate('unresolved-detection-misses', missed, requirements['maximumUnresolvedDetectionMisses'], minimum=False),
             {'name': 'clean-install', 'passed': installation.get('passed') is True and
              installation.get('modelSha256') == policy['modelSha256']}]
    gates += performance_gates(policy, benchmark)
    return {'status': 'ready' if all(g['passed'] for g in gates) else 'blocked',
            'ready': all(g['passed'] for g in gates), 'gates': gates,
            'finalEvaluationExecuted': False,
            'reason': 'Existing consulted images are regression evidence, never a fresh acceptance test.'}


def acceptance_gates(policy, summary):
    """Every required stratum/class must exist; averages cannot hide missing data."""
    thresholds = policy['thresholds']
    gates = [metric_gate('positive-images', summary['all']['images'], thresholds['minimumImages']),
             metric_gate('negative-images', summary['negatives']['images'], thresholds['minimumNegatives']),
             metric_gate('whole-board-rate', summary['all']['exactBoardRate'], thresholds['exactBoardRate']),
             metric_gate('detection-miss-rate', summary['detection']['missRate'], thresholds['maximumDetectionMissRate'], minimum=False),
             metric_gate('bounds-within-two-pixels', summary['detection']['withinTwoPixelsRate'], thresholds['minimumBoundsWithinTwoPixelsRate']),
             metric_gate('false-detection-rate', summary['negatives']['falseDetectionRate'], thresholds['maximumFalseDetectionRate'], minimum=False),
             metric_gate('explicit-orientation-mapping', summary['orientationMappingRate'], thresholds['explicitOrientationMappingRate'])]
    groups = {'combination': ([c['id'] for c in policy['configurations']], 'minimumImagesPerCombination'),
              'condition': (policy['conditions'], 'minimumImagesPerCondition'),
              'layout': (policy['layouts'], 'minimumImagesPerLayout'),
              'orientation': (['white-bottom', 'black-bottom'], None),
              'platform': (['lichess', 'chesscom'], None)}
    for dimension, (names, minimum) in groups.items():
        for name in names:
            entry = summary['strata'].get(dimension, {}).get(name, {})
            gates.append(metric_gate(f'{dimension}/{name}/exact', entry.get('exactBoardRate'), thresholds['stratumExactBoardRate']))
            gates.append(metric_gate(f'{dimension}/{name}/images', entry.get('images'), thresholds[minimum] if minimum else 1))
    from tools.position_dataset import LABELS
    for label in LABELS:
        entry = summary['all']['classes'].get(label, {})
        for metric, threshold in [('total', 'minimumClassSquares'), ('precision', 'classPrecision'), ('recall', 'classRecall')]:
            gates.append(metric_gate(f'class/{label}/{metric}', entry.get(metric), thresholds[threshold]))
    return gates


def require_ready(policy, policy_hash, path):
    """Recompute readiness from pinned evidence before accessing reserved pixels."""
    report=json.loads(path.read_text())
    if report.get('policySha256')!=policy_hash:
        raise ValueError('Readiness belongs to another policy.')
    evidence=[]
    for name in ('regression','benchmark','installation'):
        entry=report['evidence'][name]
        source=ROOT/entry['path']
        if digest(source)!=entry['sha256']:raise ValueError('Readiness evidence changed.')
        evidence.append(json.loads(source.read_text()))
    actual=readiness(policy,*evidence)
    if not actual['ready']:
        failed=', '.join(g['name'] for g in actual['gates'] if not g['passed'])
        raise ValueError(f'Final acceptance remains reserved; readiness failed: {failed}')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--regression', type=Path, required=True)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--installation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    check_frozen(policy, args.model)
    report = readiness(policy, *[json.loads(p.read_text()) for p in (args.regression,args.benchmark,args.installation)])
    report.update(policySha256=digest(args.policy), modelSha256=digest(args.model),
                  evidence={name:{'path':str(p),'sha256':digest(p)} for name,p in zip(
                      ('regression','benchmark','installation'),(args.regression,args.benchmark,args.installation),strict=True)},
                  readinessCodeSha256=digest(Path(__file__)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
