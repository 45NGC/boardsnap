"""Compare the installed photo CLI with annotated crops on consulted validation only.

Reuse the frozen detector report for crop comparisons; independently execute the
full CLI for every image and require identical predictions or detection errors.
No expected corners or positions are supplied to the CLI.
"""

import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import torch

from boardsnap.image_input import read_image
from boardsnap.neural import NeuralClassifier, CLASSES
from boardsnap.orientation import to_canonical
from boardsnap.output import build_result
from boardsnap.rectification import rectify_board
from boardsnap.segmentation import split_squares
from tools.capture_lichess import expand_placement
from tools.evaluate_neural import score
from tools.evaluate_photo_detection import ROOT, DETECTOR, digest


def placement_ids(placement):
    return [0 if piece == '.' else CLASSES.index(piece)
            for row in expand_placement(placement) for piece in row]


def classify_crop(classifier, image, corners, orientation):
    with ExitStack() as stack:
        board = stack.enter_context(rectify_board(image, corners))
        stack.callback(board.close)
        pixels = np.array(board)
        squares = split_squares(board)
        for row in squares:
            for square in row:
                stack.callback(square.close)
        result = build_result(to_canonical(classifier.classify_squares(squares), orientation))
    return result, pixels


def compare(manifest_path, detection_report, model_path):
    data = json.loads(manifest_path.read_text())
    detection = json.loads(detection_report.read_text())
    if (data.get('independentFinalEvaluation') is not False or not data.get('samples')
            or any(row['split'] != 'validation' for row in data['samples'])):
        raise ValueError('Use a consulted validation manifest only, never final evaluation.')
    if (detection['manifestSha256'] != digest(manifest_path)
            or detection['detectorSha256'] != digest(DETECTOR)):
        raise ValueError('Detector report does not match current geometry code and annotations.')
    by_id = {row['id']: row for row in detection['records']}
    if len(by_id) != len(data['samples']) or set(by_id) != {row['id'] for row in data['samples']}:
        raise ValueError('Detector report must cover exactly the validation images.')
    code_paths = [DETECTOR, Path(__file__), *[ROOT / 'src/boardsnap' / name for name in
        ('rectification.py', 'pipeline.py', 'neural.py', 'adapters/cli.py', 'image_input.py', 'segmentation.py', 'orientation.py', 'output.py')]]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in code_paths}
    model_hash, manifest_hash = digest(model_path), digest(manifest_path)
    detector_report_hash = digest(detection_report)
    torch.set_num_threads(4)
    classifier = NeuralClassifier(model_path)
    records, manual_records, auto_records = [], [], []
    for row in data['samples']:
        geometry = by_id[row['id']]
        image_path = (ROOT / row['imagePath']).resolve()
        if (not image_path.is_relative_to(ROOT) or digest(image_path) != row['imageSha256']
                or geometry['imageSha256'] != row['imageSha256']):
            raise ValueError('Photo changed since annotation/detection.')
        if (row['label']['status'] != 'visual-transcription'
                or row.get('geometryReview', {}).get('status') != 'visual-reviewed'):
            raise ValueError('Require reviewed placement and corners.')
        orientation = row['label']['orientation']
        expected = row['label']['piecePlacement']
        record = {'id': row['id'], 'image': row['imagePath'], 'imageSha256': row['imageSha256'],
                  'groupId': row['groupId'], 'split': row['split'], 'category': row['source']['category'],
                  'orientation': orientation, 'expected': expected}
        with read_image(image_path) as image:
            manual, manual_pixels = classify_crop(classifier, image, row['boardCorners'], orientation)
            record['annotatedPlacement'] = manual['piecePlacement']
            record['annotatedExact'] = manual['piecePlacement'] == expected
            manual_records.append({'positionId': expected, 'expected': placement_ids(expected),
                                   'predictions': placement_ids(manual['piecePlacement'])})
            if 'detectedCorners' in geometry:
                automatic, auto_pixels = classify_crop(classifier, image, geometry['detectedCorners'], orientation)
                record['automaticCorners'] = geometry['detectedCorners']
                record['geometryMetrics'] = geometry['metrics']
                record['cropMeanAbsoluteRgbDifference'] = float(np.abs(auto_pixels.astype(float)-manual_pixels).mean())
                record['cropDifferenceScope'] = 'Mean absolute RGB difference on 0..255; includes geometric alignment, not an acceptance threshold.'
            else:
                automatic = {'error': geometry['error']}
        command = [sys.executable, '-m', 'boardsnap', str(image_path), '--input-type', 'photo',
                   '--model', str(model_path.resolve()), '--orientation', orientation]
        started = time.perf_counter()
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90,
                                 env={**os.environ, 'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4'})
        result = json.loads(process.stdout)
        expected_status = 0 if 'piecePlacement' in automatic else 1
        if (process.returncode != expected_status or result != automatic or process.stderr
                or process.stdout != json.dumps(result) + '\n'):
            raise ValueError(f"CLI/crop disagreement or output contract violation: {row['id']}: {process.stderr}")
        record.update(cliResult=result, cliExitCode=process.returncode, cliSeconds=time.perf_counter()-started,
                      automaticExact=result.get('piecePlacement') == expected)
        if 'piecePlacement' in result:
            auto_records.append({'positionId': expected, 'expected': placement_ids(expected),
                                 'predictions': placement_ids(result['piecePlacement'])})
            record['changedSquaresVsAnnotated'] = [i for i, (a, b) in enumerate(zip(
                placement_ids(manual['piecePlacement']), placement_ids(result['piecePlacement']), strict=True)) if a != b]
        records.append(record)
        print(f"{len(records)}/{len(data['samples'])}: {row['id']} manual={record['annotatedExact']} automatic={record['automaticExact']}", flush=True)
    if (digest(model_path) != model_hash or digest(manifest_path) != manifest_hash
            or digest(detection_report) != detector_report_hash
            or hashes != {str(path.relative_to(ROOT)): digest(path) for path in code_paths}):
        raise ValueError('Inputs or implementation changed during comparison.')
    def summary(rows):
        return {'images': len(rows), 'detected': sum(r['cliExitCode'] == 0 for r in rows),
                'annotatedExactBoards': sum(r['annotatedExact'] for r in rows),
                'automaticExactBoards': sum(r['automaticExact'] for r in rows)}
    return {'schemaVersion': 1, 'scope': 'Consulted validation, full photo CLI versus annotated geometry; no training or final evaluation.',
            'finalEvaluationAccessed': False, 'manifest': str(manifest_path), 'manifestSha256': manifest_hash,
            'model': str(model_path), 'modelSha256': model_hash, 'detectionReport': str(detection_report),
            'detectionReportSha256': detector_report_hash, 'codeSha256': hashes,
            'versions': {'torch': str(torch.__version__)}, 'threads': 4,
            'timingScope': 'Each CLI process includes Python/PyTorch startup, model loading, decoding, detection, rectification and classification.',
            'summary': summary(records),
            'byCategory': {c: summary([r for r in records if r['category'] == c]) for c in sorted({r['category'] for r in records})},
            'annotatedClassification': score(manual_records),
            'automaticClassificationOnDetectedOnly': score(auto_records) if auto_records else None,
            'gainedExactBoards': [r['id'] for r in records if r['automaticExact'] and not r['annotatedExact']],
            'lostExactBoards': [r['id'] for r in records if r['annotatedExact'] and not r['automaticExact']],
            'records': records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'data/manifests/phone-validation-v1.json')
    parser.add_argument('--detection-report', type=Path, default=ROOT / 'data/reports/photo-detection-validation-v1.json')
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Choose a new output file to preserve previous measurements.')
    report = compare(args.manifest, args.detection_report, args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    main()
