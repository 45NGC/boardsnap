"""Measure classifier sensitivity independently of detection, on validation only."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
from PIL import Image

from tools.bounds_tolerance import SCENARIOS, case_name, labels_for, perturbed_squares
from tools.build_square_dataset import raster_bounds
from tools.evaluate_neural import score
from tools.neural_data import child, digest, read_index

ROOT = Path(__file__).resolve().parents[1]


def compare_records(records):
    """Do not let gains on other boards hide losses on working examples."""
    reference = {r['image']: r for r in records if r['scenario'] == 'reference'}
    output = {}
    for scenario in sorted({r['scenario'] for r in records}):
        rows = [r for r in records if r['scenario'] == scenario]
        lost = [r['image'] for r in rows if not r.get('error') and
                reference[r['image']]['predictions'] == r['expected'] and r['predictions'] != r['expected']]
        output[scenario] = {
            'all': score(rows),
            'applicable': score([r for r in rows if not r.get('error')]),
            'cases': {case: score([r for r in rows if r['case'] == case and not r.get('error')])
                      for case in sorted({r['case'] for r in rows})},
            'previouslyCorrectBoardsLost': lost,
            'invalidCrops': [r['image'] for r in rows if r.get('error')],
        }
    return output


def validation_gate(results, paired):
    """Fixed development gate, not release acceptance or an independent test."""
    baseline, candidate = list(results.values())
    reference_preserved = not paired['reference']['baselineCorrectCandidateWrong']
    reference_preserved &= (candidate['reference']['all']['correctSquares'] >=
                            baseline['reference']['all']['correctSquares'])
    cases = sorted({c for s in baseline.values() for c in s['cases']})
    deltas = {}
    for case in cases:
        deltas[case] = {field: sum(s['cases'][case][field] for s in candidate.values()) -
                             sum(s['cases'][case][field] for s in baseline.values())
                       for field in ('exactBoards', 'correctSquares')}
    perturbation_gain = sum(candidate[s]['applicable']['exactBoards'] - baseline[s]['applicable']['exactBoards']
                            for s in baseline if s != 'reference')
    applicable_same = all(candidate[s]['invalidCrops'] == baseline[s]['invalidCrops'] for s in baseline)
    passed = reference_preserved and applicable_same and perturbation_gain > 0 and all(
        value >= 0 for case in deltas.values() for value in case.values())
    return {'passed': bool(passed), 'referencePreserved': bool(reference_preserved),
            'sameApplicableInputs': applicable_same, 'perturbedExactBoardsGain': perturbation_gain,
            'caseDeltas': deltas, 'consultedRegressionsStillRequired': True,
            'policy': 'no loss of correct original boards or total original squares; strictly more exact perturbed boards; '
                      'no aggregate board/square losses within any overlay case; identical applicable inputs'}


def evaluate(dataset, model_paths, output, threads=4):
    import torch
    from boardsnap.neural import NeuralClassifier
    torch.set_num_threads(threads)
    metadata, rows = read_index(dataset)
    selected = [r for r in rows if r['split'] == 'validation']
    if not selected:
        raise ValueError('No validation boards.')
    models = {str(p): NeuralClassifier(p) for p in model_paths}
    records = {name: [] for name in models}
    for number, row in enumerate(selected, 1):
        path = child(Path(metadata['sourceRoot']), row['image'])
        if digest(path) != row['sha256']:
            raise ValueError('Source screenshot changed.')
        base = {k: row[k] for k in ('image', 'positionId', 'groupId')}
        base.update(expected=labels_for(row).tolist(), case=case_name(row))
        with Image.open(path) as source, source.convert('RGB') as image:
            for scenario in SCENARIOS:
                try:
                    pixels, _ = perturbed_squares(image, raster_bounds(row['boardBounds']), row['orientation'], scenario)
                except ValueError as error:
                    for name in models:
                        records[name].append(dict(base, scenario=scenario.name, predictions=[-1]*64, error=str(error)))
                    continue
                for name, model in models.items():
                    records[name].append(dict(base, scenario=scenario.name,
                                             predictions=model.predict_ids(pixels).tolist()))
        if number % 100 == 0:
            print(f'Measured {number}/{len(selected)} validation boards', flush=True)
    report = {
        'schemaVersion': 1, 'dataRole': 'validation', 'independentFinalEvaluation': False,
        'scope': 'classifier only; reviewed bounds plus fixed perturbations; no detector; no real-use cases',
        'datasetSha256': digest(dataset/'dataset.json'),
        'indexSha256': metadata['indexes']['verified']['sha256'],
        'models': {name: digest(name) for name in models},
        'scenarios': [asdict(s) for s in SCENARIOS],
        'sourceBoards': len(selected), 'sourcePositions': len({r['positionId'] for r in selected}),
        'sourceGroups': sorted({r['groupId'] for r in selected}),
        'environment': {'torch': str(torch.__version__), 'numpy': np.__version__, 'threads': threads},
        'codeSha256': {str(p.relative_to(ROOT)): digest(p) for p in
                       [Path(__file__).resolve(), ROOT/'tools/bounds_tolerance.py', ROOT/'tools/evaluate_neural.py',
                        ROOT/'tools/neural_data.py', ROOT/'tools/build_square_dataset.py',
                        *sorted((ROOT/'src/boardsnap').rglob('*.py'))]},
        'results': {name: compare_records(data) for name, data in records.items()},
    }
    if len(models) == 2:
        names = list(models)
        report['pairedModelComparison'] = {}
        for scenario in SCENARIOS:
            a = [r for r in records[names[0]] if r['scenario'] == scenario.name]
            b = [r for r in records[names[1]] if r['scenario'] == scenario.name]
            report['pairedModelComparison'][scenario.name] = {
                'baselineCorrectCandidateWrong': [x['image'] for x,y in zip(a,b,strict=True)
                    if x['predictions'] == x['expected'] and y['predictions'] != y['expected']],
                'baselineWrongCandidateCorrect': [x['image'] for x,y in zip(a,b,strict=True)
                    if x['predictions'] != x['expected'] and y['predictions'] == y['expected']],
            }
        report['validationGate'] = validation_gate(report['results'], report['pairedModelComparison'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--model', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args(argv)
    if len(args.model) > 2 or len(set(args.model)) != len(args.model) or args.threads < 1:
        parser.error('Choose one model or a distinct baseline and candidate, and positive threads.')
    report = evaluate(args.dataset, args.model, args.output, args.threads)
    return 0 if report.get('validationGate', {}).get('passed', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
