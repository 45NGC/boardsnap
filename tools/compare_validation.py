"""Compare two classifiers on existing validation crops, without running detection."""

import argparse
import json
from pathlib import Path
import resource
import time

import torch

from boardsnap.neural import NeuralClassifier
from tools.evaluate_neural import score, timing
from tools.neural_data import digest, load_board, read_index


def paired_changes(baseline, candidate):
    if [r['image'] for r in baseline] != [r['image'] for r in candidate]:
        raise ValueError('Comparison requires the same ordered validation images.')
    gained, lost = [], []
    for a, b in zip(baseline, candidate, strict=True):
        if a['expected'] != b['expected']:
            raise ValueError('Comparison labels differ.')
        old = a['expected'] == a['predictions']
        new = b['expected'] == b['predictions']
        if new and not old:
            gained.append(a['image'])
        if old and not new:
            lost.append(a['image'])
    return {'gainedExactBoards': gained, 'lostExactBoards': lost}


def compare(dataset, baseline, candidate, threads=4):
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    metadata, rows = read_index(dataset)
    rows = [r for r in rows if r['split'] == 'validation']
    if not rows:
        raise ValueError('No validation boards.')
    paths = {'baseline': baseline, 'candidate': candidate}
    hashes = {key: digest(path) for key, path in paths.items()}
    models = {key: NeuralClassifier(path) for key, path in paths.items()}
    records = {key: [] for key in models}
    warmup, _ = load_board(dataset, rows[0])
    for model in models.values():
        for _ in range(3):
            model.predict_ids(warmup)
    for number, row in enumerate(rows, 1):
        images, labels = load_board(dataset, row)
        base = {key: row[key] for key in ('image', 'positionId', 'groupId', 'orientation', 'configurationId')}
        base.update(expected=labels.tolist(), conditions=row.get('conditions', []),
                    category=row.get('source', {}).get('category', row.get('style', {}).get('platform', 'unknown')))
        for key, model in models.items():
            start = time.perf_counter()
            predictions = model.predict_ids(images).tolist()
            seconds = time.perf_counter() - start
            records[key].append(dict(base, predictions=predictions, seconds=seconds))
        if number % 250 == 0:
            print(f'Compared {number}/{len(rows)} validation boards', flush=True)
    results = {}
    for key, values in records.items():
        strata = {}
        for field in ('category', 'orientation', 'configurationId'):
            strata[field] = {value: score([r for r in values if r[field] == value])
                             for value in sorted({r[field] for r in values})}
        strata['conditions'] = {value: score([r for r in values if value in r['conditions']])
                                for value in sorted({c for r in values for c in r['conditions']})}
        results[key] = {'all': score(values), 'strata': strata,
                        'latency': timing([r['seconds'] for r in values])}
    if hashes != {key: digest(path) for key, path in paths.items()}:
        raise ValueError('Model changed during comparison.')
    return {'schemaVersion': 1, 'split': 'validation', 'datasetId': metadata['datasetId'],
            'datasetSha256': digest(dataset / 'dataset.json'),
            'indexSha256': metadata['indexes']['verified']['sha256'],
            'models': {key: {'path': str(path), 'sha256': hashes[key]} for key, path in paths.items()},
            'codeSha256': digest(Path(__file__)), 'torchVersion': str(torch.__version__), 'threads': threads,
            'scope': 'Classification of verified crops only; no automatic detection or final evaluation.',
            'latencyScope': '64 squares including preprocessing; warm models; excludes file I/O and rectification.',
            'peakProcessRssMiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            'memoryScope': 'Comparison process including both models, imports, indexes and records; not model-only.',
            'results': results, 'paired': paired_changes(records['baseline'], records['candidate']),
            'records': records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = compare(args.dataset, args.baseline, args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    for key, result in report['results'].items():
        metrics = result['all']
        print(f"{key}: {metrics['exactBoards']}/{metrics['images']} boards; {metrics['squareAccuracy']:.4%} squares")


if __name__ == '__main__':
    main()
