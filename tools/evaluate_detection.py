"""Measure rectangle accuracy and board-removal negatives, without classification."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import ImageDraw

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import read_image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / 'data/manifests/digital-detection-v1.json'


def rectangle_metrics(actual, expected):
    intersection = max(0, min(actual[2], expected[2]) - max(actual[0], expected[0])) * max(
        0, min(actual[3], expected[3]) - max(actual[1], expected[1]))
    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in (actual, expected)]
    return {'maxEdgeErrorPixels': max(abs(a-b) for a,b in zip(actual,expected,strict=True)),
            'intersectionOverUnion': intersection / (sum(areas) - intersection)}


def evaluate(split, manifest_path=DEFAULT_MANIFEST):
    if split not in ('development', 'evaluation'):
        raise ValueError('Choose development or evaluation explicitly.')
    manifest = json.loads(manifest_path.read_text())
    results, groups = [], {}
    for item in manifest['samples']:
        if groups.setdefault(item['sourceGroupId'], item['split']) != item['split']:
            raise ValueError('A source group crosses partitions.')
    samples = [s for s in manifest['samples'] if s['split'] == split]
    if not samples:
        raise ValueError('No samples in requested split.')
    for item in samples:
        path = ROOT / item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f"Image changed since rectangle review: {item['id']}")
        expected = item['box']
        row = {'id': item['id'], 'sourceGroupId': item['sourceGroupId'],
               'conditions': item['conditions'], 'expectedBox': expected, 'withinTolerance': False}
        with read_image(path) as image:
            if list(image.size) != item['imageSize']:
                raise ValueError('Reference image dimensions changed.')
            try:
                actual = detect_board(image).as_box()
                row.update(actualBox=list(actual), **rectangle_metrics(actual, expected))
                row['withinTolerance'] = row['maxEdgeErrorPixels'] <= manifest['maxEdgeErrorPixels']
            except BoardDetectionError as error:
                row['error'] = error.to_dict()['error']
            # A paired negative retains the original interface. This transform
            # uses ground truth to remove the board, never to guide detection.
            with image.copy() as negative:
                x,y,right,bottom = expected
                ImageDraw.Draw(negative).rectangle((x-5,y-5,right+5,bottom+5),fill='#cccccc')
                try:
                    detect_board(negative)
                    row['boardRemovalRejected'] = False
                except BoardDetectionError as error:
                    row['boardRemovalRejected'] = error.code == 'BOARD_NOT_FOUND'
        results.append(row)
    localized = [r for r in results if 'actualBox' in r]
    return {'datasetId': manifest['datasetId'], 'stage': 'detection-only', 'split': split,
            'manifestSha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'detectorSha256': hashlib.sha256((ROOT / 'src/boardsnap/detection.py').read_bytes()).hexdigest(),
            'classificationEvaluated': False, 'imageCount': len(results),
            'sourceGroupCount': len({r['sourceGroupId'] for r in results}),
            'detectedCount': len(localized), 'withinToleranceCount': sum(r['withinTolerance'] for r in results),
            'maxAllowedEdgeErrorPixels': manifest['maxEdgeErrorPixels'],
            'maxObservedEdgeErrorPixels': max((r['maxEdgeErrorPixels'] for r in localized),default=None),
            'meanIntersectionOverUnion': (sum(r['intersectionOverUnion'] for r in localized)/len(localized)
                                          if localized else None),
            'boardRemovalNegativeCount': len(results),
            'boardRemovalFalsePositives': sum(not r['boardRemovalRejected'] for r in results),
            'images': results}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',required=True,choices=('development','evaluation'))
    parser.add_argument('--manifest',type=Path,default=DEFAULT_MANIFEST)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    report=evaluate(args.split,args.manifest)
    text=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text)
    else:
        print(text,end='')
    return int(report['withinToleranceCount'] != report['imageCount'] or report['boardRemovalFalsePositives'] > 0)


if __name__=='__main__':
    raise SystemExit(main())
