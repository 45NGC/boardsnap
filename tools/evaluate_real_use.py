"""Audit current-name development screenshots; never read final acceptance data."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board
from boardsnap.image_input import read_image
from boardsnap.output import build_result
from tools.capture_lichess import expand_placement
from tools.evaluate_detection import rectangle_metrics

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data/manifests/real-use-development-v1.json'
MODELS = {'v8': ROOT / '.cache/neural-styles-v8/best.pt',
          'candidate': ROOT / '.cache/neural-tolerance-v1-conservative/best.pt'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(path=MANIFEST, *, image_root=None):
    data = json.loads(path.read_text())
    if data['dataRole'] != 'development-regression' or data['independentFinalEvaluation'] is not False:
        raise ValueError('Only consulted development screenshots are allowed.')
    legacy = json.loads((ROOT / 'data/manifests/video-development-v2.json').read_text())
    inherited = {r['sha256']: r for r in legacy['samples']}
    seen, placements = set(), {}
    for row in data['samples']:
        if row['id'] in seen or row['split'] != 'development':
            raise ValueError('Duplicate identity or changed development partition.')
        seen.add(row['id'])
        expand_placement(row['piecePlacement'])
        if row['orientation'] not in ('white-bottom', 'black-bottom'):
            raise ValueError('Explicit reviewed orientation is required.')
        previous = inherited.get(row['sha256'])
        if previous and any(row[k] != previous[k] for k in
                            ('positionId', 'sourceGroupId', 'split', 'piecePlacement', 'orientation')):
            raise ValueError('Inherited identity or annotation changed.')
        identity = (row['sourceGroupId'], row['split'])
        if placements.setdefault(row['piecePlacement'], identity) != identity:
            raise ValueError('Equivalent positions must retain a common group and partition.')
        path = (image_root / Path(row['path']).name) if image_root else ROOT / row['path']
        if digest(path) != row['sha256']:
            raise ValueError(f"Image bytes changed: {row['id']}")
        with read_image(path) as image:
            if list(image.size) != row['imageSize']:
                raise ValueError('Image dimensions changed.')
            for key in ('gridBox', 'visibleBox'):
                x,y,r,b = row[key]
                if (any(type(v) is not int for v in row[key]) or
                        not (0 <= x < r <= image.width and 0 <= y < b <= image.height)):
                    raise ValueError('Reference geometry leaves the image.')
    return data


def compare_placement(actual, expected):
    predicted = ''.join(expand_placement(actual))
    reference = ''.join(expand_placement(expected))
    errors = [{'square': f"{'abcdefgh'[i%8]}{8-i//8}",
               'expected': a, 'actual': b}
              for i,(a,b) in enumerate(zip(reference,predicted,strict=True)) if a != b]
    return {'correct': not errors, 'correctSquares': 64-len(errors), 'errors': errors}


def summarize(results):
    summary = {'images': len(results), 'detected': sum('box' in r['detection'] for r in results),
               'geometryCorrect': sum(r['detection']['correct'] for r in results), 'models': {}}
    for name in MODELS:
        cases = [r['models'][name] for r in results]
        confusions = Counter(f"{e['expected']}->{e['actual']}" for r in cases for e in r['verifiedGeometry']['errors'])
        classes = {}
        for label in '.PNBRQKpnbrqk':
            support = sum(''.join(expand_placement(r['expected'])).count(label) for r in results)
            fn = sum(e['expected'] == label for r in cases for e in r['verifiedGeometry']['errors'])
            fp = sum(e['actual'] == label for r in cases for e in r['verifiedGeometry']['errors'])
            tp = support-fn
            classes['empty' if label == '.' else label] = {
                'support': support, 'truePositive': tp, 'falseNegative': fn, 'falsePositive': fp,
                'precision': tp/(tp+fp) if tp+fp else None,
                'recall': tp/support if support else None}
        summary['models'][name] = {
            'verifiedExactBoards': sum(r['verifiedGeometry']['correct'] for r in cases),
            'verifiedCorrectSquares': sum(r['verifiedGeometry']['correctSquares'] for r in cases),
            'pipelineExactBoards': sum(r['pipeline']['correct'] for r in cases),
            'cliExactBoards': sum(r.get('cli',{}).get('correct',False) for r in cases),
            'cliMeasured': sum('cli' in r for r in cases), 'verifiedConfusions': dict(confusions),
            'verifiedClasses': classes}
    return summary


def evaluate(manifest=MANIFEST, *, image_root=None, cli=False):
    import cv2
    import torch
    from boardsnap.neural import NeuralClassifier, CLASSES
    from tools.build_square_dataset import extract_squares

    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    data = load_manifest(manifest, image_root=image_root)
    hashes = {name:digest(path) for name,path in MODELS.items()}
    classifiers = {name:NeuralClassifier(path) for name,path in MODELS.items()}
    results = []
    for row in data['samples']:
        path = (image_root / Path(row['path']).name) if image_root else ROOT / row['path']
        item = {k:row[k] for k in ('id','sha256','sourceGroupId','positionId','split','conditions','orientation')}
        item.update(expected=row['piecePlacement'],gridBox=row['gridBox'],visibleBox=row['visibleBox'],models={})
        x,y,r,b = row['gridBox']
        item['axisRatio'] = max(r-x,b-y)/min(r-x,b-y)
        with read_image(path) as image:
            try:
                bounds = detect_board(image)
                metrics = rectangle_metrics(bounds.as_box(),row['gridBox'])
                item['detection'] = dict(box=list(bounds.as_box()), **metrics,
                                         correct=metrics['maxEdgeErrorPixels'] <= row['maxEdgeErrorPixels'])
            except BoardDetectionError as error:
                item['detection'] = dict(correct=False,**error.to_dict())
            squares = extract_squares(image,BoardBounds(x,y,r-x,b-y),row['orientation'])
            for name,classifier in classifiers.items():
                labels = [None if v == 0 else CLASSES[v] for v in classifier.predict_ids(squares)]
                placement = build_result([labels[i:i+8] for i in range(0,64,8)])['piecePlacement']
                verified = dict(result={'piecePlacement':placement},**compare_placement(placement,row['piecePlacement']))
                try:
                    result = classifier.recognize_image(path,orientation=row['orientation'])
                except BoardDetectionError as error:
                    result = error.to_dict()
                pipeline = {'result':result,'correct':result == {'piecePlacement':row['piecePlacement']}}
                if 'piecePlacement' in result:
                    pipeline.update(compare_placement(result['piecePlacement'],row['piecePlacement']))
                measurement = dict(verifiedGeometry=verified,pipeline=pipeline)
                if cli:
                    env = dict(os.environ,OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
                    process = subprocess.run([sys.executable,'-m','boardsnap',str(path),
                        '--model',str(MODELS[name]),'--orientation',row['orientation']],
                        cwd=ROOT,env=env,text=True,capture_output=True,timeout=60)
                    try: payload = json.loads(process.stdout)
                    except json.JSONDecodeError: payload = None
                    measurement['cli'] = {'result':payload,'exitCode':process.returncode,'stderr':process.stderr,
                        'correct':payload == {'piecePlacement':row['piecePlacement']} and process.returncode == 0 and not process.stderr,
                        'matchesPipeline':payload == result,
                        'contractValid':payload == result and not process.stderr and process.returncode == (1 if 'error' in result else 0)}
                item['models'][name] = measurement
        results.append(item)
        print(f"{row['id']}: detected={'box' in item['detection']}; " +
              ', '.join(f"{n}: verified={m['verifiedGeometry']['correct']} pipeline={m['pipeline']['correct']}"
                        for n,m in item['models'].items()),flush=True)
    if hashes != {name:digest(path) for name,path in MODELS.items()}:
        raise ValueError('Reference model changed during evaluation.')
    categories = sorted({c for row in results for c in row['conditions']})
    return {'schemaVersion':1,'dataRole':'development-regression','independentFinalEvaluation':False,
            'manifestSha256':digest(manifest),'toolSha256':digest(Path(__file__)),
            'modelSha256':hashes,'runtimeSha256':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))},
            'environment':{'python':sys.version,'opencv':cv2.__version__,'torch':torch.__version__,
                           'torchThreads':4,'opencvThreads':1},
            'summary':summarize(results),'categories':{c:summarize([r for r in results if c in r['conditions']]) for c in categories},
            'groups':{g:summarize([r for r in results if r['sourceGroupId']==g]) for g in sorted({r['sourceGroupId'] for r in results})},
            'results':results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=MANIFEST)
    parser.add_argument('--image-root',type=Path,help='Directory containing the current real-use-N filenames')
    parser.add_argument('--cli',action='store_true',help='Also run an actual CLI subprocess for every image/model')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite an existing report.')
    report = evaluate(args.manifest,image_root=args.image_root,cli=args.cli)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report['summary'].items() if k!='models'}))


if __name__ == '__main__':
    main()
