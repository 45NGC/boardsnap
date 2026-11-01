"""Bounded validation of photo resampling; never changes runtime or model weights."""

import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np
import torch

from boardsnap.image_input import read_image
from boardsnap.neural import NeuralClassifier, preprocess
from tools.evaluate_photo_detection import ROOT, DETECTOR, digest
from tools.evaluate_photo_pipeline import placement_ids
from tools.evaluate_neural import score


def acceptance(rows):
    """Do not hide lost correct boards behind equal or higher aggregate accuracy."""
    lost = [r['id'] for r in rows if r['baseline'] == r['expected'] and r['predictions'] != r['expected']]
    gained = [r['id'] for r in rows if r['baseline'] != r['expected'] and r['predictions'] == r['expected']]
    baseline_errors = sum(a != b for r in rows for a, b in zip(r['expected'], r['baseline'], strict=True))
    errors = sum(a != b for r in rows for a, b in zip(r['expected'], r['predictions'], strict=True))
    return {'images': len(rows), 'baselineExact': sum(r['expected'] == r['baseline'] for r in rows),
            'candidateExact': sum(r['expected'] == r['predictions'] for r in rows),
            'baselineErrors': baseline_errors, 'candidateErrors': errors, 'gained': gained, 'lost': lost,
            'passes': bool(gained) and not lost and errors <= baseline_errors}


def board_pixels(image, corners, factor):
    side = 512 * factor
    transform = cv2.getPerspectiveTransform(np.float32(corners), np.float32([[0, 0], [side, 0], [side, side], [0, side]]))
    pixels = cv2.warpPerspective(np.asarray(image), transform, (side, side), flags=cv2.INTER_LINEAR)
    return pixels if factor == 1 else cv2.resize(pixels, (512, 512), interpolation=cv2.INTER_AREA)


def cells(pixels, orientation):
    visual = pixels.reshape(8, 64, 8, 64, 3).transpose(0, 2, 1, 3, 4)
    if orientation == 'black-bottom':
        visual = visual[::-1, ::-1]
    elif orientation != 'white-bottom':
        raise ValueError('Require an explicit view.')
    return np.ascontiguousarray(visual.reshape(64, 64, 64, 3))


def evaluate():
    manifest = ROOT/'data/manifests/phone-validation-v1.json'
    baseline = ROOT/'data/reports/photo-pipeline-validation-v1.json'
    data, base = json.loads(manifest.read_text()), json.loads(baseline.read_text())
    model_path = ROOT/base['model']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in (manifest, baseline, model_path, DETECTOR, Path(__file__))}
    if (data.get('independentFinalEvaluation') is not False
            or any(r['split'] != 'validation' for r in data['samples'])
            or base['manifestSha256'] != digest(manifest)
            or base['modelSha256'] != digest(model_path)
            or base['codeSha256']['src/boardsnap/photo_detection.py'] != digest(DETECTOR)):
        raise ValueError('Require the frozen consulted validation baseline and unchanged inputs.')
    model = NeuralClassifier(model_path)
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    records = []
    for row, old in zip(data['samples'], base['records'], strict=True):
        path = (ROOT/row['imagePath']).resolve()
        if not path.is_relative_to(ROOT) or row['id'] != old['id'] or digest(path) != row['imageSha256']:
            raise ValueError('Validation image identity changed.')
        with read_image(path) as image:
            for geometry, corners, original in [
                ('annotated', row['boardCorners'], old['annotatedPlacement']),
                ('automatic', old.get('automaticCorners'), old['cliResult'].get('piecePlacement')),
            ]:
                if corners is None:
                    continue
                start = time.perf_counter()
                with torch.inference_mode():
                    logits = {factor: model.model(preprocess(cells(board_pixels(image, corners, factor), row['label']['orientation'])))
                              for factor in (1, 2, 4)}
                if logits[1].argmax(1).tolist() != placement_ids(original):
                    raise ValueError('Baseline predictions cannot be reproduced.')
                for variant, prediction in [('supersample2', logits[2]), ('supersample4', logits[4]),
                                             ('mean2', (logits[1]+logits[2])/2)]:
                    records.append({'id': row['id'], 'imageSha256': row['imageSha256'], 'groupId': row['groupId'],
                                    'split': row['split'], 'conditions': row.get('conditions', []),
                                    'geometry': geometry, 'variant': variant, 'expected': placement_ids(row['label']['piecePlacement']),
                                    'baseline': placement_ids(original), 'predictions': prediction.argmax(1).tolist()})
                print(f"{row['id']} {geometry}: {time.perf_counter()-start:.3f}s", flush=True)
    summaries = {}
    for variant in ('supersample2', 'supersample4', 'mean2'):
        modes = {}
        for geometry in ('annotated', 'automatic'):
            selected = [r for r in records if r['variant'] == variant and r['geometry'] == geometry]
            modes[geometry] = acceptance(selected)
            modes[geometry]['candidateClasses'] = score([dict(r, positionId=str(r['expected'])) for r in selected])['classes']
            modes[geometry]['byCondition'] = {c: acceptance([r for r in selected if c in r['conditions']])
                                             for c in sorted({c for r in selected for c in r['conditions']})}
        summaries[variant] = {'geometry': modes, 'accepted': all(m['passes'] for m in modes.values())}
    if any(digest(ROOT/p) != sha for p, sha in hashes.items()):
        raise ValueError('Inputs changed during comparison.')
    return {'schemaVersion': 1, 'finalEvaluationAccessed': False, 'trainingRun': False,
            'policy': 'Require a whole-board gain, zero lost baseline-exact boards and no increase in square errors in BOTH geometries.',
            'hashes': hashes, 'variantsPlanned': ['supersample2', 'supersample4', 'mean2'],
            'selectionScope': 'Exploratory consulted validation; not independent acceptance.',
            'summary': summaries, 'records': records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Preserve reports; choose a new output file.')
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
