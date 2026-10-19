"""Audit paired tolerance losses and a conservative diagnostic alternative on validation only."""

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
import torch

from boardsnap.detection import detect_board
from boardsnap.neural import CLASSES, load_model, preprocess
from tools.average_neural import average_state
from tools.bounds_tolerance import SCENARIOS, perturbed_squares
from tools.build_square_dataset import raster_bounds
from tools.neural_data import child, digest, read_index

ROOT = Path(__file__).resolve().parents[1]


def margin(logits, expected):
    """Internal logit gap, not calibrated confidence or a production output field."""
    other = logits.copy()
    other[expected] = -np.inf
    return float(logits[expected] - other.max())


def cell_hash(pixels):
    return hashlib.sha256(pixels.tobytes()).hexdigest()


@torch.inference_mode()
def analyze(dataset, comparison_path, trained_path, output, previews):
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    comparison = json.loads(comparison_path.read_text())
    if comparison['dataRole'] != 'validation' or comparison['independentFinalEvaluation']:
        raise ValueError('Use the existing development validation comparison.')
    if digest(dataset/'dataset.json') != comparison['datasetSha256']:
        raise ValueError('Dataset changed.')
    for path, sha in comparison['codeSha256'].items():
        if digest(ROOT/path) != sha:
            raise ValueError(f'Measured code changed: {path}')
    metadata, rows = read_index(dataset)
    if metadata['indexes']['verified']['sha256'] != comparison['indexSha256']:
        raise ValueError('Index changed.')
    rows = {r['image']: r for r in rows if r['split'] == 'validation'}
    clean = {r['pairId']: r for r in rows.values() if r['conditions'] == ['clean']}
    model_paths = list(comparison['models'])
    if len(model_paths) != 2:
        raise ValueError('Expected baseline followed by candidate.')
    models, model_metadata = [], []
    for path in model_paths:
        if digest(path) != comparison['models'][path]:
            raise ValueError('Model changed.')
        model, meta = load_model(path)
        models.append(model)
        model_metadata.append(meta)
    scenarios = {s.name: s for s in SCENARIOS}
    if [asdict(s) for s in SCENARIOS] != [dict(s, edges=tuple(s['edges'])) for s in comparison['scenarios']]:
        raise ValueError('Perturbation definitions changed.')
    source_root = Path(metadata['sourceRoot'])
    pixels_cache, detected_cache = {}, {}

    def pixels(row, scenario):
        key = (row['image'], scenario.name)
        if key not in pixels_cache:
            path = child(source_root, row['image'])
            if digest(path) != row['sha256']:
                raise ValueError('Source pixels changed.')
            with Image.open(path) as source, source.convert('RGB') as image:
                pixels_cache[key] = perturbed_squares(image, raster_bounds(row['boardBounds']), row['orientation'], scenario)
        return pixels_cache[key]

    losses = [(s, image) for s, pairs in comparison['pairedModelComparison'].items()
              for image in pairs['baselineCorrectCandidateWrong']]
    gains = [(s, image) for s, pairs in comparison['pairedModelComparison'].items()
             for image in pairs['baselineWrongCandidateCorrect']]
    cases, pictures = [], []
    for scenario_name, name in losses:
        row, scenario = rows[name], scenarios[scenario_name]
        values, edges = pixels(row, scenario)
        reference, _ = pixels(row, scenarios['reference'])
        control, _ = pixels(clean[row['pairId']], scenario)
        expected = np.array([c['classId'] for c in row['cells']])
        logits = [m(preprocess(values)).numpy() for m in models]
        ref_logits = [m(preprocess(reference)).numpy() for m in models]
        predictions = [v.argmax(1) for v in logits]
        if not (np.array_equal(predictions[0], expected) and not np.array_equal(predictions[1], expected)):
            raise ValueError('Reported paired loss did not reproduce.')
        source_box = raster_bounds(row['boardBounds']).as_box()
        path = child(source_root, name)
        # Measure the actual detector separately from the deliberately wrong crop.
        if name not in detected_cache:
            with Image.open(path) as source, source.convert('RGB') as image:
                detected_cache[name] = detect_board(image).as_box()
        item = {k: row[k] for k in ('image', 'sha256', 'positionId', 'groupId', 'orientation', 'style', 'conditions')}
        item.update(scenario=scenario_name, originalBox=list(source_box), perturbedBox=list(edges),
                    edgeDelta=list(scenario.edges), detectedBox=list(detected_cache[name]),
                    detectorEdgeError=max(abs(a-b) for a,b in zip(source_box,detected_cache[name])),
                    originalCorrect=[bool(np.array_equal(v.argmax(1),expected)) for v in ref_logits],
                    marks=row.get('marks', []), wrongCells=[])
        for i in np.flatnonzero(predictions[1] != expected):
            cell = row['cells'][i]
            error = {k: cell[k] for k in ('index', 'square', 'label', 'background', 'imageRow', 'imageColumn')}
            error.update(predicted=CLASSES[predictions[1][i]], baselinePredicted=CLASSES[predictions[0][i]],
                         cropSha256=cell_hash(values[i]), referenceCropSha256=cell_hash(reference[i]),
                         cleanPerturbedCropSha256=cell_hash(control[i]),
                         changedPixelsFromClean=int(np.any(values[i] != control[i],axis=2).sum()),
                         margins={label: {'perturbed':margin(logits[j][i],expected[i]),
                                          'reference':margin(ref_logits[j][i],expected[i])}
                                  for j,label in enumerate(('v8','candidate'))})
            item['wrongCells'].append(error)
            pictures.append((f"{row['positionId']} {scenario_name} {row.get('overlayCase')} {cell['square']} "
                             f"{cell['label']}->{error['predicted']}",reference[i],values[i],control[i]))
        cases.append(item)

    # One already explored lower fraction: diagnostic only, no training or new saved model.
    average = model_metadata[1]['parameterAverage']
    if digest(trained_path) != average['trainedSha256'] or comparison['models'][model_paths[0]] != average['baselineSha256']:
        raise ValueError('The trained endpoint must match the selected candidate.')
    trained, _ = load_model(trained_path)
    probe = deepcopy(models[0])
    probe.load_state_dict(average_state(models[0].state_dict(), trained.state_dict(), average['trainedFraction']/2))
    probe_results = {}
    for label, selected in (('losses', losses), ('gains', gains)):
        result = []
        for scenario_name, name in selected:
            row = rows[name]
            values, _ = pixels(row,scenarios[scenario_name])
            target = np.array([c['classId'] for c in row['cells']])
            actual = probe(preprocess(values)).argmax(1).numpy()
            result.append({'scenario':scenario_name,'image':name,'exact':bool(np.array_equal(target,actual)),
                           'wrongSquares':[row['cells'][i]['square'] for i in np.flatnonzero(target != actual)]})
        probe_results[label] = result
    previews.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB',(780,50+len(pictures)*155),'white')
    draw = ImageDraw.Draw(sheet)
    draw.text((10,10),'Original crop                  Perturbed crop                 Clean, same perturbation',fill='black')
    for n,(label,reference,perturbed,control) in enumerate(pictures):
        y=50+n*155
        draw.text((10,y),label,fill='black')
        for j,p in enumerate((reference,perturbed,control)):
            sheet.paste(Image.fromarray(p).resize((128,128),Image.Resampling.NEAREST),(10+j*255,y+18))
    sheet.save(previews/'regression-crops.png')
    report = {'schemaVersion':1,'dataRole':'targeted-validation-diagnosis','independentFinalEvaluation':False,
              'comparisonSha256':digest(comparison_path),'datasetSha256':digest(dataset/'dataset.json'),
              'models':comparison['models'],'analysisCodeSha256':digest(Path(__file__)),
              'sourceCodeSha256':comparison['codeSha256'],
              'environment':{'torch':str(torch.__version__),'numpy':np.__version__,'threads':4},
              'cases':cases, 'summary':{
                  'variants':len(cases),'positions':len({r['positionId'] for r in cases}),
                  'groups':len({r['groupId'] for r in cases}),
                  'wrongCells':sum(len(r['wrongCells']) for r in cases),
                  'uniqueWrongCropPixels':len({c['cropSha256'] for r in cases for c in r['wrongCells']}),
                  'confusions':dict(Counter(c['label']+'->'+c['predicted'] for r in cases for c in r['wrongCells']))},
              'halfStepProbe':{'trainedFraction':average['trainedFraction']/2,'trainedSha256':digest(trained_path),
                               'scope':'only the existing paired gains/losses; not a complete validation or selection',
                               'recoveredLosses':sum(r['exact'] for r in probe_results['losses']),
                               'lostGains':sum(not r['exact'] for r in probe_results['gains']),
                               'results':probe_results},
              'preview':str(previews/'regression-crops.png'), 'trainingPerformed':False,
              'productionChanged':False,'recommendation':'Keep the current candidate; inspect the documented trade-off.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=Path('.cache/digital-style-squares-v2'))
    parser.add_argument('--comparison',type=Path,default=Path('data/reports/neural-tolerance-validation.json'))
    parser.add_argument('--trained',type=Path,default=Path('.cache/neural-tolerance-v1/best.pt'))
    parser.add_argument('--output',type=Path,default=Path('data/reports/neural-tolerance-loss-analysis.json'))
    parser.add_argument('--previews',type=Path,default=Path('.cache/tolerance-loss-analysis'))
    args=parser.parse_args()
    report=analyze(args.dataset,args.comparison,args.trained,args.output,args.previews)
    print(json.dumps({'summary':report['summary'], 'halfStep':{k:v for k,v in report['halfStepProbe'].items() if k!='results'}},indent=2))


if __name__=='__main__':
    main()
