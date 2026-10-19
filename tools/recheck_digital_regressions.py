"""Recheck previously reported digital failures with a fixed model, without selection."""

import argparse
import json
from pathlib import Path

from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from tools.build_square_dataset import raster_bounds
from tools.evaluate_detection import rectangle_metrics
from tools.neural_data import child, digest, read_index


def evaluate(previous, dataset, model, *, root=Path('.')):
    import cv2
    import torch
    from boardsnap.neural import NeuralClassifier

    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    source = json.loads(previous.read_text())
    metadata, rows = read_index(dataset)
    annotations = {child(Path(metadata['sourceRoot']), row['image']): row for row in rows}
    classifier = NeuralClassifier(model)
    results = []
    for case in source['images']:
        path = child(root, case['image'])
        row = annotations[path]
        if digest(path) != case['sha256'] or row['sha256'] != case['sha256']:
            raise ValueError('Regression image changed.')
        if (row['split'] != 'evaluation' or row['piecePlacement'] != case['expected']['piecePlacement']
                or any(row[key] != case[key] for key in ('positionId', 'groupId', 'orientation'))):
            raise ValueError('Regression identity or annotation changed.')
        with read_image(path) as image:
            bounds = detect_board(image)
        geometry = rectangle_metrics(bounds.as_box(), raster_bounds(row['boardBounds']).as_box())
        actual = classifier.recognize_image(path, orientation=case['orientation'])
        result = {key: case[key] for key in ('image', 'sha256', 'positionId', 'groupId', 'orientation', 'expected')}
        result.update(geometry=geometry, boundsCorrect=geometry['maxEdgeErrorPixels'] <= 2,
                      actual=actual, positionCorrect=actual == case['expected'])
        results.append(result)
    return {
        'dataRole': 'consulted-regression', 'independentFinalEvaluation': False,
        'previousReportSha256': digest(previous), 'datasetSha256': digest(dataset/'dataset.json'),
        'modelSha256': digest(model), 'checkCodeSha256': digest(Path(__file__)),
        'runtimeSha256': {str(p.relative_to(root)): digest(p) for p in sorted((root/'src/boardsnap').rglob('*.py'))},
        'passed': bool(results) and all(r['boundsCorrect'] and r['positionCorrect'] for r in results),
        'images': results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, default=Path('data/reports/digital-regressions-v8.json'))
    parser.add_argument('--dataset', type=Path, default=Path('.cache/digital-style-squares-v2'))
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = evaluate(args.previous, args.dataset, args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
