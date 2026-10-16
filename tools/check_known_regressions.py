"""Recheck exposed failures through the public neural path, never final holdouts."""

import argparse
import json
from pathlib import Path

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import read_image
from tools.build_square_dataset import raster_bounds
from tools.evaluate_detection import rectangle_metrics
from tools.neural_data import child, digest, read_index

ROOT = Path(__file__).resolve().parents[1]


def check(dataset, model, previous_report, previous_name='styleCandidate'):
    import cv2
    import torch
    from boardsnap.neural import NeuralClassifier
    from boardsnap.classification import ClassificationError
    from boardsnap.image_input import ImageInputError
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    previous = json.loads(previous_report.read_text())
    if previous['datasetSha256'] != digest(dataset/'dataset.json'):
        raise ValueError('Regression dataset differs from the original report.')
    failures = {r['image'] for r in previous['results'][previous_name]['detected']['errors']}
    if not failures:
        raise ValueError('No exposed failures in the chosen report.')
    metadata, rows = read_index(dataset)
    selected = [r for r in rows if r['image'] in failures]
    if len(selected) != len(failures):
        raise ValueError('Missing or duplicate regression images.')
    classifier = NeuralClassifier(model)
    results = []
    for row in selected:
        path = child(Path(metadata['sourceRoot']), row['image'])
        if digest(path) != row['sha256']:
            raise ValueError('Regression pixels changed.')
        item = {k: row[k] for k in ('image', 'sha256', 'positionId', 'groupId', 'orientation')}
        item.update(expected={'piecePlacement': row['piecePlacement']}, boundsCorrect=False, positionCorrect=False)
        with read_image(path) as image:
            try:
                bounds = detect_board(image)
                item['geometry'] = rectangle_metrics(bounds.as_box(), raster_bounds(row['boardBounds']).as_box())
                item['boundsCorrect'] = item['geometry']['maxEdgeErrorPixels'] <= 2
            except BoardDetectionError as error:
                item['detectionError'] = error.to_dict()
        try:
            item['actual'] = classifier.recognize_image(path, orientation=row['orientation'])
            item['positionCorrect'] = item['actual'] == item['expected']
        except (BoardDetectionError, ClassificationError, ImageInputError) as error:
            item['actual'] = error.to_dict()
        results.append(item)
    return {'dataRole': 'consulted-regression', 'independentFinalEvaluation': False,
            'previousReportSha256': digest(previous_report), 'modelSha256': digest(model),
            'runtimeSha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))},
            'checkCodeSha256': digest(Path(__file__)),
            'passed': all(r['boundsCorrect'] and r['positionCorrect'] for r in results), 'images': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'model', 'previous-report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--previous-name', default='styleCandidate')
    args = parser.parse_args()
    report = check(args.dataset, args.model, args.previous_report, args.previous_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f"Known regressions: {sum(r['boundsCorrect'] and r['positionCorrect'] for r in report['images'])}/{len(report['images'])}")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
