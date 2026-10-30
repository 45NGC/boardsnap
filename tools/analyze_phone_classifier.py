"""Analyze cached validation predictions and reviewed appearances; never run a model."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from tools.capture_lichess import expand_placement
from tools.position_dataset import LABELS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows):
    matrix = [[0] * 13 for _ in LABELS]
    for row in rows:
        for expected, predicted in zip(row['expected'], row['predictions'], strict=True):
            matrix[expected][predicted] += 1
    classes = {}
    for i, label in enumerate(LABELS):
        support, predicted, correct = sum(matrix[i]), sum(r[i] for r in matrix), matrix[i][i]
        classes[label] = {'support': support, 'correct': correct, 'predicted': predicted,
                          'precision': correct / predicted if predicted else None,
                          'recall': correct / support if support else None}
    total = sum(map(sum, matrix))
    correct = sum(matrix[i][i] for i in range(13))
    return {'boards': len(rows), 'positions': len({r['positionId'] for r in rows}),
            'exactBoards': sum(r['expected'] == r['predictions'] for r in rows),
            'squares': total, 'correctSquares': correct,
            'squareAccuracy': correct / total if total else None, 'classes': classes,
            'confusions': [{'expected': LABELS[i], 'predicted': LABELS[j], 'count': matrix[i][j]}
                           for i in range(13) for j in range(13) if i != j and matrix[i][j]]}


def checked_records(report, manifest, appearances):
    """Require exact sample membership and unchanged identities, views and targets."""
    if report.get('split') != 'validation' or manifest.get('independentFinalEvaluation') is not False:
        raise ValueError('Only the consulted validation batch is supported.')
    samples = {r['imagePath']: r for r in manifest['samples']}
    annotations = {r['photoId']: r for r in appearances['samples']}
    if (len(samples) != len(manifest['samples']) or len(annotations) != len(appearances['samples'])
            or set(annotations) != {r['id'] for r in samples.values()}):
        raise ValueError('Appearance membership must match every validation photo exactly once.')
    joined = {}
    for name in ('baseline', 'candidate'):
        records = report['records'][name]
        if len(records) != len(samples) or {r['image'] for r in records} != set(samples):
            raise ValueError('Prediction membership must match every validation photo exactly once.')
        joined[name] = []
        for row in records:
            photo = samples[row['image']]
            annotation = annotations[photo['id']]
            expected = [LABELS.index('empty' if p == '.' else p)
                        for rank in expand_placement(photo['label']['piecePlacement']) for p in rank]
            if (photo['split'] != 'validation' or row['expected'] != expected
                    or row['orientation'] != photo['label']['orientation']
                    or row['groupId'] != photo['groupId'] or row['conditions'] != photo['conditions']
                    or row['category'] != photo['source']['category']
                    or annotation['imageSha256'] != photo['imageSha256']):
                raise ValueError('Prediction identity, target, view or review is stale.')
            if (len(row['predictions']) != 64 or any(type(p) is not int or not 0 <= p < 13
                                                   for p in row['predictions'])):
                raise ValueError('Require exactly 64 valid class predictions.')
            if annotation['pieceAppearance'] not in appearances['pieceAppearances']:
                raise ValueError('Unknown piece appearance.')
            corners = photo['boardCorners']
            edges = [math.dist(corners[i], corners[(i + 1) % 4]) for i in range(4)]
            ratio = max(edges[0] / edges[2], edges[2] / edges[0], edges[1] / edges[3], edges[3] / edges[1])
            joined[name].append(dict(row, photoId=photo['id'],
                **{key: annotation[key] for key in ('pieceAppearance', 'boardAppearance', 'displayedPlatform', 'interface')},
                observedGameId=photo['source'].get('gameId'),
                geometry={'shortestEdgePixels': min(edges), 'shortestEdgePerCellPixels': min(edges) / 8,
                          'oppositeEdgeRatio': ratio},
                geometryBand='opposite-edge-ratio-under-1.2' if ratio < 1.2 else 'opposite-edge-ratio-at-least-1.2'))
        joined[name].sort(key=lambda r: r['image'])
    a, b = joined['baseline'], joined['candidate']
    if any(x['positionId'] != y['positionId'] for x, y in zip(a, b, strict=True)):
        raise ValueError('Model comparison position identities differ.')
    return joined


def summarize(report, manifest, appearances):
    records = checked_records(report, manifest, appearances)
    output = {'overall': {key: metrics(rows) for key, rows in records.items()}, 'strata': {}, 'photos': []}
    for field in ('category', 'displayedPlatform', 'interface', 'pieceAppearance', 'boardAppearance', 'orientation', 'geometryBand'):
        output['strata'][field] = {value: {key: metrics([r for r in rows if r[field] == value])
                                               for key, rows in records.items()}
                                   for value in sorted({r[field] for r in records['candidate']})}
    output['strata']['conditions'] = {value: {key: metrics([r for r in rows if value in r['conditions']])
                                             for key, rows in records.items()}
                                     for value in sorted({v for r in records['candidate'] for v in r['conditions']})}
    output['byClassAndSquareColor'] = {}
    for color, parity in [('light', 0), ('dark', 1)]:
        # Canonical a8 is light. Highlights/textures do not change this geometric color.
        selected = [i for i in range(64) if (i // 8 + i % 8) % 2 == parity]
        output['byClassAndSquareColor'][color] = {key: metrics([
            dict(r, expected=[r['expected'][i] for i in selected], predictions=[r['predictions'][i] for i in selected])
            for r in rows])['classes'] for key, rows in records.items()}
    gains, losses = 0, 0
    for a, b in zip(records['baseline'], records['candidate'], strict=True):
        errors = []
        for i, (target, old, new) in enumerate(zip(a['expected'], a['predictions'], b['predictions'], strict=True)):
            gains += old != target and new == target
            losses += old == target and new != target
            if old != target or new != target:
                errors.append({'square': f"{'abcdefgh'[i % 8]}{8 - i // 8}",
                    'squareColor': 'light' if (i // 8 + i % 8) % 2 == 0 else 'dark',
                    'expected': LABELS[target], 'baseline': LABELS[old], 'candidate': LABELS[new]})
        output['photos'].append({key: b[key] for key in ('photoId', 'image', 'groupId', 'observedGameId',
            'pieceAppearance', 'boardAppearance', 'displayedPlatform', 'conditions', 'geometry')} |
            {'baselineErrors': sum(x != y for x, y in zip(a['expected'], a['predictions'])),
             'candidateErrors': sum(x != y for x, y in zip(b['expected'], b['predictions'])), 'errors': errors})
    output['squareChanges'] = {'recovered': gains, 'regressed': losses, 'netRecovered': gains - losses}
    output['appearanceCoverage'] = {key: {
        'status': 'all-observed-boards-correct' if values['candidate']['exactBoards'] == values['candidate']['boards']
                  else 'observed-failures',
        'officialThemeVerified': False, 'generalCompatibilityEstablished': False,
        'photos': [r['photoId'] for r in records['candidate'] if r['pieceAppearance'] == key],
    } for key, values in output['strata']['pieceAppearance'].items()}
    output['scope'] = {'measured': 'Classification with reviewed corners and unchanged cached predictions',
        'automaticDetection': 'not measured', 'officialThemeCompatibility': 'not established',
        'photoSources': dict(Counter(r['category'] for r in records['candidate'])),
        'partitionGroups': sorted({r['groupId'] for r in records['candidate']}),
        'cameras': dict(Counter(r['captureMetadata']['cameraModel'] for r in manifest['samples'])),
        'limitations': ['30 photos are correlated within games/videos, not 30 independent sources.',
                       'Conditions overlap and covary with style/background; these slices do not establish causality.',
                       'All photos include perspective and moire; no clean-camera control group.',
                       'Opposite-edge ratio and edge length describe annotated geometry, not camera angle or optical resolution.',
                       'One observed camera; no evidence of cross-device or native-mobile-app compatibility.']}
    return output


def build(report_path, manifest_path, appearance_path, provenance_path):
    report, manifest, appearances, provenance = [json.loads(p.read_text()) for p in
                                                (report_path, manifest_path, appearance_path, provenance_path)]
    if (digest(report_path) != appearances['predictionReportSha256']
            or digest(manifest_path) != appearances['manifestSha256']
            or digest(report_path) != provenance['validation']['phone']['rawReport']['sha256']
            or report['models'] != provenance['validation']['phone']['models']):
        raise ValueError('Pinned prediction report, model identities or manifest changed.')
    analysis = summarize(report, manifest, appearances)
    for name in ('baseline', 'candidate'):
        cached = report['results'][name]['all']
        actual = analysis['overall'][name]
        if (actual['exactBoards'], actual['correctSquares'], actual['squares']) != (
                cached['exactBoards'], cached['correctSquares'], cached['totalSquares']):
            raise ValueError('Recomputed totals disagree with cached evaluation.')
    return {'schemaVersion': 1, 'dataRole': 'consulted-validation-analysis', 'inferenceRun': False,
            'trainingRun': False, 'finalEvaluationAccessed': False,
            'inputs': {str(p): digest(p) for p in (report_path, manifest_path, appearance_path, provenance_path)},
            'analysisCodeSha256': digest(Path(__file__)), 'models': report['models'],
            'appearanceDefinitions': appearances['pieceAppearances'], **analysis,
            'digitalRegression': {'paired': provenance['validation']['digital']['paired'],
                'overall': {key: value['all'] for key, value in provenance['validation']['digital']['results'].items()}}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, default=Path('.cache/neural-phone-v1/phone-validation.json'))
    parser.add_argument('--manifest', type=Path, default=Path('data/manifests/phone-validation-v1.json'))
    parser.add_argument('--appearances', type=Path, default=Path('data/manifests/phone-validation-appearance-v1.json'))
    parser.add_argument('--provenance', type=Path, default=Path('data/reports/neural-phone-v1.json'))
    parser.add_argument('--output', type=Path, default=Path('data/reports/phone-classifier-analysis-v1.json'))
    args = parser.parse_args(argv)
    result = build(args.predictions, args.manifest, args.appearances, args.provenance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Saved {args.output}; reused predictions, no inference or training.")


if __name__ == '__main__':
    main()
