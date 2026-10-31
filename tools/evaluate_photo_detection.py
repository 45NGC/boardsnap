"""Measure photographic corner detection against reviewed geometry, without classification."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image

from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import read_image
from boardsnap.photo_detection import detect_photo_board

ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / 'src/boardsnap/photo_detection.py'
POLICY = {'minIntersectionOverUnion': .95, 'maxCornerErrorBoardFraction': .01,
          'maxGridErrorCellFraction': .08,
          'scope': 'Reviewed geometry agreement, not recognition or independent final acceptance.'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry_metrics(actual, expected):
    actual, expected = np.float32(actual), np.float32(expected)
    intersection, _ = cv2.intersectConvexConvex(actual, expected)
    union = cv2.contourArea(actual)+cv2.contourArea(expected)-intersection
    side = float(np.linalg.norm(expected-np.roll(expected, -1, axis=0), axis=1).mean())
    unit = np.float32([[0, 0], [8, 0], [8, 8], [0, 8]])
    points = np.float32([[(c, r) for r in range(9) for c in range(9)]])
    a = cv2.perspectiveTransform(points, cv2.getPerspectiveTransform(unit, actual))
    b = cv2.perspectiveTransform(points, cv2.getPerspectiveTransform(unit, expected))
    corner = float(np.linalg.norm(actual-expected, axis=1).max())
    grid = float(np.linalg.norm(a-b, axis=2).max())
    result = {'intersectionOverUnion': float(intersection/union), 'maxCornerErrorPixels': corner,
              'maxCornerErrorBoardFraction': corner/side, 'maxGridErrorCellFraction': grid/(side/8)}
    result['withinPolicy'] = bool(result['intersectionOverUnion'] >= POLICY['minIntersectionOverUnion']
        and result['maxCornerErrorBoardFraction'] <= POLICY['maxCornerErrorBoardFraction']
        and result['maxGridErrorCellFraction'] <= POLICY['maxGridErrorCellFraction'])
    return result


def summary(rows):
    detected = [r for r in rows if 'detectedCorners' in r]
    times = [r['seconds'] for r in rows]
    return {'images': len(rows), 'detected': len(detected),
            'withinPolicy': sum(r['metrics']['withinPolicy'] for r in detected),
            'failures': [r['id'] for r in rows if 'error' in r],
            'outOfTolerance': [r['id'] for r in detected if not r['metrics']['withinPolicy']],
            'medianSeconds': float(np.median(times)), 'p95Seconds': float(np.percentile(times, 95))}


def report_for(manifest_path, manifest, records, code_hash):
    return {'schemaVersion': 1, 'dataRole': 'consulted-photo-detection-measurement',
            'manifest': str(manifest_path), 'manifestSha256': digest(manifest_path),
            'detectorSha256': code_hash, 'evaluationCodeSha256': digest(Path(__file__)),
            'policy': POLICY, 'classificationMeasured': False, 'finalEvaluationAccessed': False,
            'annotationLimit': 'Assistant-reviewed corner annotations, not an independent metrology reference.',
            'splits': dict(Counter(r['split'] for r in records)), 'summary': summary(records),
            'byCategory': {c: summary([r for r in records if r['category'] == c])
                           for c in sorted({r['category'] for r in records})},
            'records': records}


def evaluate(manifest_path):
    data = json.loads(manifest_path.read_text())
    if data.get('independentFinalEvaluation') is not False or any(
            r['split'] not in ('development', 'training', 'validation') for r in data['samples']):
        raise ValueError('Only reviewed development/training/validation photos are allowed.')
    code_hash = digest(DETECTOR)
    manifest_hash = digest(manifest_path)
    records = []
    for i, row in enumerate(data['samples'], 1):
        path = (ROOT / row['imagePath']).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != row['imageSha256']:
            raise ValueError('Photograph path or checksum changed.')
        if row.get('geometryReview', {}).get('status') != 'visual-reviewed':
            raise ValueError('Require visually reviewed corners.')
        with read_image(path) as image:
            start = time.perf_counter()
            try:
                result = detect_photo_board(image)
                outcome = {'detectedCorners': result.corners,
                           'metrics': geometry_metrics(result.corners, row['boardCorners'])}
            except BoardDetectionError as error:
                outcome = error.to_dict()
            seconds = time.perf_counter()-start
        records.append({'id': row['id'], 'image': row['imagePath'], 'imageSha256': row['imageSha256'],
                        'category': row['source']['category'], 'split': row['split'], 'groupId': row['groupId'],
                        'expectedCorners': row['boardCorners'], 'seconds': seconds, **outcome})
        if i % 10 == 0:
            print(f'Checked {i}/{len(data["samples"])} photographic boards', flush=True)
    if code_hash != digest(DETECTOR) or manifest_hash != digest(manifest_path):
        raise ValueError('Detector or manifest changed during measurement.')
    return report_for(manifest_path, data, records, code_hash)


def evaluate_controls(manifest_path):
    """Deterministic counterfactuals on direct-platform development photos only.

    Keep real interface pixels, but remove the target board or obscure a known
    fraction of its first file. These are constructed controls, not independent
    naturally occurring negatives. Video scenes may contain additional boards
    and are deliberately excluded from this no-board labeling policy.
    """
    data = json.loads(manifest_path.read_text())
    if data.get('independentFinalEvaluation') is not False or any(
            r['split'] not in ('development', 'training') for r in data['samples']):
        raise ValueError('Construct controls from development/training only.')
    chosen = [r for category in ('chesscom', 'lichess')
              for r in [s for s in data['samples'] if s['source']['category'] == category][:3]]
    code_hash = digest(DETECTOR)
    records = []
    for row in chosen:
        path = (ROOT / row['imagePath']).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != row['imageSha256']:
            raise ValueError('Control source changed.')
        with read_image(path) as image:
            transform = cv2.getPerspectiveTransform(np.float32([[0, 0], [512, 0], [512, 512], [0, 512]]),
                                                    np.float32(row['boardCorners']))
            for variant, width in [('board-removed', 512), ('first-file-14-of-64-hidden', 14), ('first-file-missing', 64)]:
                polygon = cv2.perspectiveTransform(np.float32([[[0, 0], [width, 0], [width, 512], [0, 512]]]), transform)
                pixels = np.array(image)
                cv2.fillConvexPoly(pixels, np.rint(polygon[0]).astype(np.int32), (52, 59, 66))
                start = time.perf_counter()
                with Image.fromarray(pixels) as control:
                    try:
                        found = detect_photo_board(control)
                        outcome = {'rejected': False, 'detectedCorners': found.corners}
                    except BoardDetectionError as error:
                        outcome = {'rejected': error.code == 'BOARD_NOT_FOUND', **error.to_dict()}
                records.append({'id': row['id'], 'imageSha256': row['imageSha256'], 'variant': variant,
                                'maskPolygon': polygon[0].tolist(), 'seconds': time.perf_counter()-start, **outcome})
        print(f'Checked constructed controls for {row["id"]}', flush=True)
    if code_hash != digest(DETECTOR):
        raise ValueError('Detector changed during control evaluation.')
    return {'schemaVersion': 1, 'dataRole': 'constructed-development-negative-controls',
            'manifestSha256': digest(manifest_path), 'detectorSha256': code_hash,
            'evaluationCodeSha256': digest(Path(__file__)), 'finalEvaluationAccessed': False,
            'images': len(records), 'rejected': sum(r['rejected'] for r in records), 'records': records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controls-only', action='store_true')
    args = parser.parse_args(argv)
    result = evaluate_controls(args.manifest) if args.controls_only else evaluate(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result.get('summary', {'images': result.get('images'), 'rejected': result.get('rejected')})), flush=True)


if __name__ == '__main__':
    main()
