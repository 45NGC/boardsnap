"""Validate and measure reviewed development cases without changing runtime code."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board
from boardsnap.output import build_result
from tools.evaluate_detection import rectangle_metrics
from tools.neural_data import child, digest
from tools.position_dataset import placement_family

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data/manifests/video-development-v2.json'


def load_cases(path=MANIFEST, *, root=ROOT, verify_images=True):
    data = json.loads(path.read_text())
    if (data['schemaVersion'] != 1 or data['dataRole'] != 'development-regression'
            or data['independentFinalEvaluation'] is not False or not data['samples']):
        raise ValueError('Reviewed cases must remain development-only.')
    ids, positions, families = {}, {}, {}
    for row in data['samples']:
        if row['split'] != 'development' or row['orientation'] not in ('white-bottom', 'black-bottom'):
            raise ValueError('Use development and an explicitly reviewed orientation.')
        if row['id'] in ids:
            raise ValueError('Duplicate development sample ID.')
        ids[row['id']] = row
        identity = (row['piecePlacement'], row['sourceGroupId'])
        if positions.setdefault(row['positionId'], identity) != identity:
            raise ValueError('Position identity or source group changed.')
        family = placement_family(row['piecePlacement'])
        if families.setdefault(family, row['sourceGroupId']) != row['sourceGroupId']:
            raise ValueError('Equivalent positions must retain their source group.')
        w, h = row['imageSize']
        if any(type(v) is not int for v in [w, h, *row['box'], *row['gridBox']]) or min(w, h) <= 0:
            raise ValueError('Image dimensions and reviewed bounds must be integers.')
        x, y, right, bottom = row['box']
        gx, gy, gr, gb = row['gridBox']
        if not (0 <= x < right <= w and 0 <= y < bottom <= h and gx < gr and gy < gb):
            raise ValueError('Invalid reviewed board bounds.')
        if row['box'] != [max(0, gx), max(0, gy), min(w, gr), min(h, gb)]:
            raise ValueError('Visible bounds must be the clipped nominal grid.')
        if row['clippedBoardPixels'] != dict(left=max(0, -gx), top=max(0, -gy),
                                             right=max(0, gr-w), bottom=max(0, gb-h)):
            raise ValueError('Clipping annotation differs from the grid bounds.')
        image_path = child(root, row['path'])
        if verify_images:
            if digest(image_path) != row['sha256']:
                raise ValueError('Development image bytes changed.')
            with Image.open(image_path) as image:
                image.load()
                if list(image.size) != row['imageSize']:
                    raise ValueError('Development image dimensions changed.')
    for row in data['samples']:
        if 'derivedFrom' not in row:
            continue
        parent = ids.get(row['derivedFrom']['sampleId'])
        if parent is None or parent['id'] == row['id']:
            raise ValueError('Unknown or self-referencing variant source.')
        for key in ('positionId', 'sourceGroupId', 'split', 'piecePlacement', 'orientation'):
            if row[key] != parent[key]:
                raise ValueError('Crop variants must retain their source identity.')
        x, y, right, bottom = row['derivedFrom']['cropBox']
        w, h = parent['imageSize']
        if not (0 <= x < right <= w and 0 <= y < bottom <= h):
            raise ValueError('Crop escapes its source image.')
        if row['imageSize'] != [right-x, bottom-y] or row['gridBox'] != [
                a-b for a, b in zip(parent['gridBox'], (x, y, x, y), strict=True)]:
            raise ValueError('Crop geometry differs from the source grid.')
        if verify_images:
            with Image.open(child(root, parent['path'])) as source, Image.open(child(root, row['path'])) as variant:
                with source.crop((x, y, right, bottom)) as cropped:
                    if not np.array_equal(np.asarray(cropped), np.asarray(variant)):
                        raise ValueError('Recorded crop does not reproduce the variant pixels.')
    return data


def evaluate(manifest=MANIFEST, *, root=ROOT, model=None):
    data = load_cases(manifest, root=root)
    classifier = None
    if model is not None:
        import torch
        from boardsnap.neural import NeuralClassifier
        torch.set_num_threads(4)
        classifier = NeuralClassifier(model)
    from tools.build_square_dataset import extract_squares
    from tools.position_dataset import LABELS
    results = []
    for row in data['samples']:
        image_path = child(root, row['path'])
        item = {key: row[key] for key in ('id', 'sha256', 'positionId', 'sourceGroupId', 'split', 'orientation')}
        item.update(expected={'piecePlacement': row['piecePlacement']}, expectedBox=row['box'])
        x, y, right, bottom = row['box']
        with Image.open(image_path) as source, source.convert('RGB') as image:
            try:
                bounds = detect_board(image)  # No expected rectangle or position is passed.
                geometry = rectangle_metrics(bounds.as_box(), row['box'])
                item['detection'] = dict(box=list(bounds.as_box()), **geometry,
                                        correct=geometry['maxEdgeErrorPixels'] <= data['maxEdgeErrorPixels'])
            except BoardDetectionError as error:
                item['detection'] = dict(correct=False, **error.to_dict())
            if classifier is not None:
                ids = classifier.predict_ids(extract_squares(image, BoardBounds(x, y, right-x, bottom-y), row['orientation']))
                labels = [None if value == 0 else LABELS[value] for value in ids]
                result = build_result([labels[i:i+8] for i in range(0, 64, 8)])
                item['reviewedBoundsRecognition'] = dict(result=result, correct=result == item['expected'])
        if classifier is not None:
            from boardsnap.classification import ClassificationError
            try:
                result = classifier.recognize_image(image_path, orientation=row['orientation'])
            except (BoardDetectionError, ClassificationError) as error:
                result = error.to_dict()
            item['fullPipeline'] = dict(result=result, correct=result == item['expected'])
        results.append(item)
    return {'schemaVersion': 1, 'datasetId': data['datasetId'], 'dataRole': data['dataRole'],
            'independentFinalEvaluation': False, 'manifestSha256': digest(manifest),
            'modelSha256': digest(model) if model is not None else None,
            'runtimeSha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))},
            'toolSha256': digest(Path(__file__)),
            'images': len(results), 'positions': len({r['positionId'] for r in results}),
            'sourceGroups': len({r['sourceGroupId'] for r in results}),
            'passed': all(r['detection']['correct'] and (classifier is None or
                          r['fullPipeline']['correct'] and r['reviewedBoundsRecognition']['correct']) for r in results),
            'results': results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--model', type=Path, help='Optional classifier; omit for detection-only measurement')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = evaluate(args.manifest, model=args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f"Development detection: {sum(r['detection']['correct'] for r in report['results'])}/{report['images']}; "
          f"overall passed: {report['passed']}")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
