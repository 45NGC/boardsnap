"""Join existing photographic predictions and geometry; no image decoding or inference."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from tools.capture_lichess import expand_placement

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    'pipeline': 'data/reports/photo-pipeline-validation-v2.json',
    'detection': 'data/reports/photo-detection-validation-v2.json',
    'manifest': 'data/manifests/phone-validation-v1.json',
    'appearances': 'data/manifests/phone-validation-appearance-v1.json',
    'previousExperiments': 'data/reports/photo-quality-review-v1.json',
    'developmentDetection': 'data/reports/photo-detection-development-v2.json',
    'developmentManifest': 'data/manifests/phone-photos-v1.json',
    'candidatePolicy': 'data/manifests/screen-preview-v1.json',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index(rows, key='id'):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate photo identity.')
    return result


def cells(placement):
    return ['empty' if symbol == '.' else symbol for rank in expand_placement(placement) for symbol in rank]


def compare_cells(expected, annotated, automatic):
    """Canonical chess coordinates: never rotate predictions a second time."""
    target, manual = cells(expected), cells(annotated)
    auto = cells(automatic) if automatic is not None else None
    wrong = []
    for i, (truth, prediction) in enumerate(zip(target, manual, strict=True)):
        other = auto[i] if auto is not None else None
        if truth == prediction and (auto is None or truth == other):
            continue
        wrong.append({'square': f"{'abcdefgh'[i % 8]}{8-i//8}",
                      'squareColor': 'light' if (i//8+i%8) % 2 == 0 else 'dark',
                      'expected': truth, 'annotated': prediction, 'automatic': other,
                      'annotatedWrong': truth != prediction,
                      'automaticWrong': truth != other if auto is not None else None})
    return wrong


def identity(row, sample):
    for key in ('imageSha256', 'groupId', 'split'):
        if row[key] != sample[key]:
            raise ValueError(f'Changed image identity/partition: {key}')
    if row['image'] != sample['imagePath']:
        raise ValueError('Changed image path.')


def consolidate(data):
    pipeline, manifest = data['pipeline'], data['manifest']
    if (manifest.get('independentFinalEvaluation') is not False
            or pipeline.get('finalEvaluationAccessed') is not False
            or data['detection'].get('finalEvaluationAccessed') is not False):
        raise ValueError('Only previously consulted photos are supported.')
    samples = index(manifest['samples'])
    predictions = index(pipeline['records'])
    geometry = index(data['detection']['records'])
    styles = index(data['appearances']['samples'], 'photoId')
    if not (set(samples) == set(predictions) == set(geometry) == set(styles)):
        raise ValueError('All inputs must describe exactly the same photos.')
    if pipeline['modelSha256'] != data['candidatePolicy']['models']['photo']['sha256']:
        raise ValueError('Pipeline results belong to another model.')
    photos = []
    for photo_id, sample in sorted(samples.items()):
        row, detection, style = predictions[photo_id], geometry[photo_id], styles[photo_id]
        identity(row, sample)
        identity(detection, sample)
        if sample['split'] != 'validation' or style['imageSha256'] != sample['imageSha256']:
            raise ValueError('Only unchanged consulted validation is supported.')
        if (row['expected'] != sample['label']['piecePlacement']
                or row['orientation'] != sample['label']['orientation']
                or detection['expectedCorners'] != sample['boardCorners']
                or row['category'] != sample['source']['category']
                or detection['category'] != row['category']):
            raise ValueError('Target, orientation, category or annotated corners changed.')
        if style['pieceAppearance'] not in data['appearances']['pieceAppearances']:
            raise ValueError('Unknown appearance group.')
        if row['cliExitCode'] == 0:
            if set(row['cliResult']) != {'piecePlacement'}:
                raise ValueError('Invalid success contract.')
            automatic = row['cliResult']['piecePlacement']
            if (row.get('automaticCorners') != detection.get('detectedCorners')
                    or not row.get('automaticCorners') or row.get('geometryMetrics') != detection.get('metrics')):
                raise ValueError('Automatic geometry evidence disagrees.')
            stage = 'detected'
        else:
            if (row['cliExitCode'] != 1 or row['cliResult'].get('error') != detection.get('error')
                    or row['cliResult']['error']['code'] != 'BOARD_NOT_FOUND' or 'detectedCorners' in detection):
                raise ValueError('Unexpected failure: do not silently label it as missing detection.')
            automatic, stage = None, 'detection-failed'
        wrong = compare_cells(row['expected'], row['annotatedPlacement'], automatic)
        manual_wrong = [r for r in wrong if r['annotatedWrong']]
        auto_wrong = [r for r in wrong if r['automaticWrong']] if automatic is not None else None
        if row['annotatedExact'] != (not manual_wrong) or row['automaticExact'] != (auto_wrong == []):
            raise ValueError('Cached exact-board flags disagree with placements.')
        if stage == 'detected':
            if auto_wrong and not manual_wrong:
                stage = 'crop-sensitive-failure'
            elif auto_wrong:
                stage = 'classification-fails-with-both-geometries'
            elif manual_wrong:
                stage = 'automatic-crop-recovers-position'
            else:
                stage = 'both-correct'
        recovered = [r['square'] for r in wrong if r['annotatedWrong'] and r['automaticWrong'] is False]
        introduced = [r['square'] for r in wrong if not r['annotatedWrong'] and r['automaticWrong'] is True]
        persistent = [r['square'] for r in wrong if r['annotatedWrong'] and r['automaticWrong'] is True]
        photos.append({'id': photo_id, 'image': row['image'], 'imageSha256': row['imageSha256'],
            'originalPath': sample['originalPath'], 'groupId': row['groupId'], 'split': row['split'],
            'source': sample['source'], 'orientation': row['orientation'],
            'pieceAppearance': style['pieceAppearance'], 'boardAppearance': style['boardAppearance'],
            'displayedPlatform': style['displayedPlatform'], 'interface': style['interface'],
            'conditions': sample['conditions'], 'expected': row['expected'],
            'annotatedPlacement': row['annotatedPlacement'], 'automaticPlacement': automatic,
            'annotatedCorners': sample['boardCorners'], 'automaticCorners': row.get('automaticCorners'),
            'geometryMetrics': row.get('geometryMetrics'),
            'cropMeanAbsoluteRgbDifference': row.get('cropMeanAbsoluteRgbDifference'),
            'annotatedErrorCount': len(manual_wrong), 'automaticErrorCount': len(auto_wrong) if auto_wrong is not None else None,
            'stage': stage, 'classifierFailsWithReviewedCorners': bool(manual_wrong),
            'recoveredSquares': recovered, 'introducedSquares': introduced, 'persistentWrongSquares': persistent,
            'wrongSquares': wrong, 'error': row['cliResult'].get('error')})
    summary = {'images': len(photos), 'detected': sum(p['automaticPlacement'] is not None for p in photos),
               'annotatedExactBoards': sum(p['annotatedErrorCount'] == 0 for p in photos),
               'automaticExactBoards': sum(p['automaticErrorCount'] == 0 for p in photos)}
    if summary != pipeline['summary']:
        raise ValueError('Recomputed totals differ from the source report.')
    summary.update(annotatedSquareErrors=sum(p['annotatedErrorCount'] for p in photos),
                   automaticSquareErrorsOnDetectedOnly=sum(p['automaticErrorCount'] or 0 for p in photos),
                   failureTableRows=sum(p['stage'] != 'both-correct' for p in photos),
                   stages=dict(Counter(p['stage'] for p in photos)),
                   introducedSquares=sum(len(p['introducedSquares']) for p in photos),
                   recoveredSquares=sum(len(p['recoveredSquares']) for p in photos))
    conditions = {}
    for name in sorted({c for p in photos for c in p['conditions']}):
        subset = [p for p in photos if name in p['conditions']]
        conditions[name] = {'images': len(subset), 'detected': sum(p['automaticPlacement'] is not None for p in subset),
                            'annotatedExact': sum(p['annotatedErrorCount'] == 0 for p in subset),
                            'automaticExact': sum(p['automaticErrorCount'] == 0 for p in subset)}
    detected = [p for p in photos if p['automaticPlacement'] is not None]
    paired = {'images': len(detected), 'squares': 64*len(detected),
              'annotatedSquareErrors': sum(p['annotatedErrorCount'] for p in detected),
              'automaticSquareErrors': sum(p['automaticErrorCount'] for p in detected)}
    appearances = {}
    for name in sorted({p['pieceAppearance'] for p in photos}):
        subset = [p for p in photos if p['pieceAppearance'] == name]
        appearances[name] = {'images': len(subset), 'detected': sum(p['automaticPlacement'] is not None for p in subset),
                             'annotatedExact': sum(p['annotatedErrorCount'] == 0 for p in subset),
                             'automaticExact': sum(p['automaticErrorCount'] == 0 for p in subset),
                             'automaticSquareErrorsOnDetectedOnly': sum(p['automaticErrorCount'] or 0 for p in subset)}
    return {'schemaVersion': 1, 'scope': 'Paired consulted validation only; development detection gaps listed separately.',
            'inferenceRun': False, 'trainingRun': False, 'finalEvaluationAccessed': False,
            'modelSha256': pipeline['modelSha256'], 'summary': summary, 'pairedDetectedMetrics': paired,
            'byCondition': conditions, 'byAppearance': appearances,
            'pieceAppearances': data['appearances']['pieceAppearances'], 'photos': photos,
            'limitations': ['Observed appearance IDs are not verified official themes.',
                           'Crop-dependent changes do not prove inaccurate corners; manual annotations also have limited precision.',
                           'Co-occurring marks/moire/styles do not establish causation. No isolated blur/glare experiment.',
                           'Detection failure has no automatic square predictions; null is not zero errors.']}


def development_gaps(data):
    manifest, report = data['developmentManifest'], data['developmentDetection']
    if manifest['independentFinalEvaluation'] is not False or report['finalEvaluationAccessed'] is not False:
        raise ValueError('Reserved data cannot enter this inventory.')
    samples, records = index(manifest['samples']), index(report['records'])
    if set(samples) != set(records):
        raise ValueError('Development geometry membership changed.')
    gaps = []
    for photo_id, row in sorted(records.items()):
        sample = samples[photo_id]
        identity(row, sample)
        if row['split'] != 'development' or row['expectedCorners'] != sample['boardCorners']:
            raise ValueError('Development geometry identity changed.')
        if 'detectedCorners' not in row or not row['metrics']['withinPolicy']:
            gaps.append({'id': photo_id, 'originalPath': sample['originalPath'], 'image': row['image'],
                         'imageSha256': row['imageSha256'], 'groupId': row['groupId'], 'split': row['split'],
                         'category': row['category'], 'conditions': sample['conditions'],
                         'geometryError': row.get('error'), 'metrics': row.get('metrics'),
                         'classificationComparisonAvailable': False, 'pieceAppearance': None})
    return {'summary': report['summary'], 'gaps': gaps,
            'scope': 'No paired full-pipeline recognition report for this development cohort; do not infer piece errors or styles.'}


def generate(root=ROOT):
    paths = {key: root/name for key, name in INPUTS.items()}
    data = {key: json.loads(path.read_text()) for key, path in paths.items()}
    for key in ('pipeline', 'detection', 'appearances'):
        if data[key]['manifestSha256'] != digest(paths['manifest']):
            raise ValueError('Validation annotation hash changed.')
    if data['pipeline']['detectionReportSha256'] != digest(paths['detection']):
        raise ValueError('Detection report changed.')
    if data['developmentDetection']['manifestSha256'] != digest(paths['developmentManifest']):
        raise ValueError('Development annotation hash changed.')
    for name, expected in data['pipeline']['codeSha256'].items():
        if digest(root/name) != expected:
            raise ValueError('Cached pipeline predictions no longer describe current code.')
    for key in ('detection', 'developmentDetection'):
        if data[key]['detectorSha256'] != digest(root/'src/boardsnap/photo_detection.py'):
            raise ValueError('Geometry report is stale.')
    output = consolidate(data)
    output['developmentGeometryOnly'] = development_gaps(data)
    previous = data['previousExperiments']
    output['previousExperimentsNotRepeated'] = {
        'scope': 'Historical v1 geometry; preserve rejected conclusions, do not substitute for current v2 metrics.',
        'resamplingAccepted': previous['resamplingAccepted'],
        'trainingExperiment': {k: previous['trainingExperiment'][k] for k in ('model', 'baseline', 'candidate', 'paired', 'accepted')},
        'decision': previous['decision']}
    output['inputs'] = {k: {'path': INPUTS[k], 'sha256': digest(p)} for k, p in paths.items()}
    output['toolSha256'] = digest(Path(__file__))
    return output


def error_text(photo, mode):
    if mode == 'automatic' and photo['automaticPlacement'] is None:
        return 'NOT_DETECTED'
    items = [f"{r['square']}:{r['expected']}->{r[mode]}" for r in photo['wrongSquares'] if r[mode+'Wrong']]
    return '; '.join(items) or 'OK'


def write_outputs(prefix, report):
    paths = [prefix.with_suffix('.json'), prefix.with_suffix('.csv'), prefix.with_name(prefix.name+'-development.csv')]
    if any(p.exists() for p in paths):
        raise ValueError('Choose a new prefix; never overwrite an inventory.')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with paths[0].open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    columns = ['id', 'stage', 'pieceAppearance', 'boardAppearance', 'orientation', 'conditions',
               'annotatedErrors', 'automaticErrors', 'maxCornerErrorPixels', 'maxGridErrorCellFraction',
               'recoveredSquares', 'introducedSquares', 'image', 'originalPath']
    with paths[1].open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for photo in report['photos']:
            if photo['stage'] == 'both-correct':
                continue
            row = {k: photo[k] for k in ('id', 'stage', 'pieceAppearance', 'boardAppearance', 'orientation', 'image', 'originalPath')}
            row.update({k: '; '.join(photo[k]) for k in ('conditions', 'recoveredSquares', 'introducedSquares')})
            row.update(annotatedErrors=error_text(photo, 'annotated'), automaticErrors=error_text(photo, 'automatic'))
            row.update({k: (photo['geometryMetrics'] or {}).get(k) for k in ('maxCornerErrorPixels', 'maxGridErrorCellFraction')})
            writer.writerow(row)
    with paths[2].open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['id', 'category', 'conditions', 'errorCode', 'image', 'originalPath'])
        writer.writeheader()
        for row in report['developmentGeometryOnly']['gaps']:
            writer.writerow({k: row[k] for k in ('id', 'category', 'image', 'originalPath')} |
                            {'conditions': '; '.join(row['conditions']), 'errorCode': (row['geometryError'] or {}).get('code', 'OUTSIDE_GEOMETRY_POLICY')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    result = generate()
    write_outputs(args.output_prefix, result)
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
