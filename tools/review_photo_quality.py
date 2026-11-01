"""Consolidate consulted photo/digital evidence and reject unsafe replacements."""

import argparse
from collections import Counter
import json
from pathlib import Path

from boardsnap.neural import CLASSES
from tools.evaluate_photo_detection import ROOT, digest
from tools.evaluate_photo_pipeline import placement_ids


def review():
    paths = {
        'pipeline': ROOT/'data/reports/photo-pipeline-validation-v1.json',
        'resampling': ROOT/'data/reports/photo-resampling-validation-v1.json',
        'training': ROOT/'.cache/neural-phone-robustness-v2/training.json',
        'comparison': ROOT/'.cache/neural-phone-robustness-v2/validation.json',
        'digital': ROOT/'data/reports/neural-phone-v1.json',
        'realUse': ROOT/'data/reports/real-use-geometry-after.json',
        'manifest': ROOT/'data/manifests/phone-validation-v1.json',
        'appearances': ROOT/'data/manifests/phone-validation-appearance-v1.json',
        'styleAudit': ROOT/'data/reports/photo-training-style-audit-v1.json',
    }
    data = {key: json.loads(path.read_text()) for key, path in paths.items()}
    pipeline, comparison = data['pipeline'], data['comparison']
    if pipeline['manifestSha256'] != digest(paths['manifest']):
        raise ValueError('Annotation version changed.')
    for model in comparison['models'].values():
        if digest(ROOT/model['path']) != model['sha256']:
            raise ValueError('Compared model changed.')
    if pipeline['modelSha256'] != comparison['models']['baseline']['sha256']:
        raise ValueError('Comparison baseline differs from photo CLI reference.')
    rows = {r['id']: r for r in data['manifest']['samples']}
    if data['manifest']['independentFinalEvaluation'] is not False or any(r['split'] != 'validation' for r in rows.values()):
        raise ValueError('Only consulted validation is allowed.')
    appearances = {r['photoId']: r['pieceAppearance'] for r in data['appearances']['samples']}
    failures, confusions = [], Counter()
    for r in pipeline['records']:
        expected = placement_ids(r['expected'])
        actual = placement_ids(r['cliResult']['piecePlacement']) if r['cliExitCode'] == 0 else None
        wrong = []
        if actual is not None:
            for index, (a, b) in enumerate(zip(expected, actual, strict=True)):
                if a != b:
                    confusions[(CLASSES[a], CLASSES[b])] += 1
                    wrong.append({'square': f"{'abcdefgh'[index%8]}{8-index//8}", 'expected': CLASSES[a], 'predicted': CLASSES[b]})
        if wrong or actual is None:
            failures.append({'id': r['id'], 'stage': 'detection' if actual is None else 'classification',
                             'appearance': appearances[r['id']], 'conditions': rows[r['id']]['conditions'], 'wrongSquares': wrong})
    conditions = {}
    for condition in sorted({c for r in rows.values() for c in r['conditions']}):
        group = [r for r in pipeline['records'] if condition in rows[r['id']]['conditions']]
        conditions[condition] = {'images': len(group), 'detected': sum(r['cliExitCode'] == 0 for r in group),
                                 'exactBoards': sum(r['automaticExact'] for r in group)}
    baseline, candidate = (comparison['results'][k]['all'] for k in ('baseline', 'candidate'))
    accepted = (not comparison['paired']['lostExactBoards'] and candidate['exactBoards'] > baseline['exactBoards']
                and candidate['correctSquares'] >= baseline['correctSquares'])
    if accepted or any(value['accepted'] for value in data['resampling']['summary'].values()):
        raise ValueError('Evidence changed: review replacement decisions explicitly instead of reusing this rejected-candidate conclusion.')
    def brief(metrics):
        return {k: metrics[k] for k in ('images', 'exactBoards', 'correctSquares', 'totalSquares', 'squareAccuracy')}
    digital = data['digital']['validation']['digital']
    return {'schemaVersion': 1, 'scope': 'Consulted validation and development; not independent release acceptance.',
            'reviewCodeSha256': digest(Path(__file__)),
            'finalEvaluationAccessed': False, 'runtimeChanged': False, 'modelPromoted': False,
            'inputs': {key: {'path': str(path.relative_to(ROOT)), 'sha256': digest(path)} for key, path in paths.items()},
            'photoAutomatic': pipeline['summary'], 'photoConditions': conditions, 'photoFailures': failures,
            'confusions': [{'expected': a, 'predicted': b, 'count': count} for (a, b), count in confusions.most_common()],
            'resamplingAccepted': {key: value['accepted'] for key, value in data['resampling']['summary'].items()},
            'trainingExperiment': {'model': comparison['models']['candidate'], 'baseline': brief(baseline), 'candidate': brief(candidate),
                                   'paired': comparison['paired'], 'accepted': accepted, 'training': data['training']},
            'digitalReference': {'model': digital['models']['baseline'], 'measured': brief(digital['results']['baseline']['all']),
                                 'photoModelOnDigital': brief(digital['results']['candidate']['all']),
                                 'scope': 'Reused existing measured crops; no rerun, no change to digital runtime or weights.'},
            'realUseScreenshots': data['realUse']['summary'],
            'decision': 'Keep digital conservative and photo-v1. Reject all three resampling variants and photo robustness v2: baseline-correct boards are lost. Obtain targeted style examples before further training.',
            'remainingEvidence': ['No isolated validation of defocus or glare; do not declare tolerance.',
                                  'Three photo detection rejections remain; classifier changes cannot recover them.',
                                  'Frozen final evaluation remains untouched.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Choose a new report path.')
    result = review()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['decision'])


if __name__ == '__main__':
    main()
