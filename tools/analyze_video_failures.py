"""Separate detection and crop geometry failures in the two deferred development images."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
import torch

import boardsnap.detection as detection
from boardsnap.neural import CLASSES, NeuralClassifier
from boardsnap.output import build_result
from tools.build_square_dataset import extract_squares, square_labels
from tools.development_cases import MANIFEST, ROOT, load_cases
from tools.neural_data import child, digest

IDS = ('chesscom-video-009', 'chesscom-video-010')


def error_details(predictions, cells):
    return [dict(square=cell['square'], expected=cell['label'], predicted=CLASSES[int(value)])
            for cell, value in zip(cells, predictions, strict=True) if cell['classId'] != value]


def placement(predictions):
    labels = [None if value == 0 else CLASSES[int(value)] for value in predictions]
    return build_result([labels[i:i+8] for i in range(0, 64, 8)])


def bounds(box):
    left, top, right, bottom = box
    return detection.BoardBounds(left, top, right-left, bottom-top)


def internal_proposals(pixels):
    """Diagnostic proposals only: do not bypass the runtime acceptance gate."""
    columns = detection._axis_grids(pixels, detection._MIN_BOARD_SIDE)
    rows = detection._axis_grids(pixels.transpose(1, 0, 2), detection._MIN_BOARD_SIDE)
    proposals = {}
    for left, right in columns:
        for top, bottom in rows:
            if abs((right-left)-(bottom-top)) > max(2, (right-left)*.01):
                continue
            refined = detection._refine_grid(pixels, bounds((left, top, right, bottom)))
            if refined is not None:
                proposals[refined.as_box()] = refined
    return columns, rows, list(proposals.values())


def trace_detection(image):
    """Inspect rejection sites without changing a detector function or threshold."""
    calls = []
    filename = detection.__file__

    def trace(frame, event, value):
        if event == 'return' and frame.f_code.co_filename == filename:
            name, local = frame.f_code.co_name, frame.f_locals
            if name in ('_refine_grid', '_visible_edges', '_structural_pattern'):
                item = {'function': name, 'returnLine': frame.f_lineno,
                        'inputBox': list(local['bounds'].as_box()),
                        'result': asdict(value) if isinstance(value, detection.BoardBounds) else value}
                for key in ('coordinates', 'peaks', 'support', 'matching', 'axis', 'a', 'b', 'complete_edges'):
                    if key in local:
                        v = local[key]
                        item[key] = v.tolist() if isinstance(v, np.ndarray) else v
                if name == '_structural_pattern' and value is False and 'band' in local:
                    horizontal = local['array'].strides == local['patch'].strides
                    item['rejectedOuterEdge'] = (('top', 'bottom') if horizontal else ('left', 'right'))[local['first']]
                    item['matchingEdgeCells'] = int(np.count_nonzero(
                        (local['own'] < local['contrast']*.65)
                        & (local['other']-local['own'] > local['contrast']*.2)))
                calls.append(item)
        return trace

    previous = sys.gettrace()
    try:
        sys.settrace(trace)
        try:
            result = {'box': list(detection.detect_board(image).as_box())}
        except detection.BoardDetectionError as error:
            result = error.to_dict()
    finally:
        sys.settrace(previous)
    return result, calls


def analyze(output, previews):
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    manifest = load_cases(verify_images=False)
    selected = [row for row in manifest['samples'] if row['id'] in IDS]
    if len(selected) != 2:
        raise ValueError('Both reviewed development cases are required.')
    selection = json.loads((ROOT/'data/reports/neural-tolerance-summary.json').read_text())
    paths = {'v8': selection['baseline'], 'candidate': selection['candidate']}
    for model in paths.values():
        if digest(ROOT/model['path']) != model['sha256']:
            raise ValueError('Reference model changed.')
    models = {name: NeuralClassifier(ROOT/model['path']) for name, model in paths.items()}
    results, preview_rows = [], []
    for row in selected:
        path = child(ROOT, row['path'])
        if digest(path) != row['sha256']:
            raise ValueError('Development screenshot changed.')
        cells = square_labels(row['piecePlacement'], row['orientation'])
        with Image.open(path) as source, source.convert('RGB') as image:
            pixels = np.asarray(image)
            automatic, trace = trace_detection(image)
            columns, ranks, proposals = internal_proposals(pixels)
            structural = [p for p in proposals if detection._structural_pattern(pixels, p)]
            if len(structural) != 1:
                raise ValueError('Expected one diagnostic interior-grid fit, not a ground-truth-selected crop.')
            fitted = structural[0]
            # This is not an accepted runtime detection: preserve its rejected status.
            fitted_complete = detection._structural_pattern(pixels, fitted, complete_edges=True)
            visible_fit = detection._refine_grid(pixels, fitted, visible=True)
            # Negative control: hiding a quarter of the first file must not become a board.
            hidden = pixels.copy()
            hidden[fitted.y:fitted.y+fitted.height,
                   fitted.x:fitted.x+round(fitted.width/32)] = (32, 32, 32)
            negative = {'hiddenFirstFilePixels': round(fitted.width/32),
                        'structuralOnly': detection._structural_pattern(hidden, fitted),
                        'completeEdges': detection._structural_pattern(hidden, fitted, complete_edges=True)}
            original = bounds(row['box'])
            horizontal = detection.BoardBounds(fitted.x, original.y, fitted.width, original.height)
            cases = {}
            for name, box in (('reviewed', original), ('interior-grid', fitted), ('horizontal-grid-only', horizontal)):
                crops = extract_squares(image, box, row['orientation'])
                cases[name] = {'box': list(box.as_box()), 'models': {}}
                for label, model in models.items():
                    predicted = model.predict_ids(crops)
                    cases[name]['models'][label] = {'result': placement(predicted),
                                                   'wrongCells': error_details(predicted, cells)}
                wrong = sorted({c['square'] for m in cases['reviewed']['models'].values() for c in m['wrongCells']})
                indexes = [c['index'] for c in cells if c['square'] in wrong]
                preview_rows.append((row['id']+' '+name, [(cells[i]['square'], crops[i]) for i in indexes]))
            # Small controlled comparison of interpolation with identical reviewed bounds.
            interpolation = {}
            for method in ('NEAREST', 'BILINEAR', 'BICUBIC'):
                with image.crop(original.as_box()) as crop:
                    with crop.resize((512, 512), getattr(Image.Resampling, method)) as normalized:
                        crops = extract_squares(normalized, detection.BoardBounds(0,0,512,512), row['orientation'])
                interpolation[method] = {label: error_details(model.predict_ids(crops),cells)
                                         for label,model in models.items()}
            # Keep a diagnostic visual of proposals over the actual screenshot.
            annotated = image.copy()
            draw = ImageDraw.Draw(annotated)
            draw.rectangle(original.as_box(),outline='red',width=1)
            draw.rectangle(fitted.as_box(),outline='cyan',width=1)
            previews.mkdir(parents=True,exist_ok=True)
            annotated.save(previews/f"{row['id']}-bounds.png")
            results.append({k:row[k] for k in ('id','path','sha256','positionId','sourceGroupId','split',
                                              'orientation','piecePlacement','box','gridBox','imageSize')}
                           | {'automaticDetection':automatic, 'detectorTrace':trace,
                              'axisProposals':{'columns':columns,'rows':ranks},
                              'interiorFit':list(fitted.as_box()),
                              'visibleRefinement':list(visible_fit.as_box()) if visible_fit is not None else None,
                              'interiorFitStructuralCheck':True,'interiorFitCompleteEdgesCheck':fitted_complete,
                              'reviewedBoxStructuralCheck':detection._structural_pattern(pixels,original),
                              'reviewedBoxCompleteEdgesCheck':detection._structural_pattern(pixels,original,complete_edges=True),
                              'partialBoardNegativeControl':negative,'classification':cases,
                              'reviewedBoundsInterpolationProbe':interpolation})
    sheet = Image.new('RGB',(760,180*len(preview_rows)),'white')
    draw = ImageDraw.Draw(sheet)
    for j,(title,crops) in enumerate(preview_rows):
        draw.text((8,180*j+3),title,fill='black')
        for i,(square,crop) in enumerate(crops):
            sheet.paste(Image.fromarray(crop).resize((128,128),Image.Resampling.NEAREST),(i*150,180*j+35))
            draw.text((i*150,180*j+18),square,fill='black')
    sheet.save(previews/'classification-crops.png')
    report = {'schemaVersion':1,'dataRole':'development-diagnosis','independentFinalEvaluation':False,
              'manifestSha256':digest(MANIFEST),'models':paths,'analysisCodeSha256':digest(Path(__file__)),
              'runtimeSha256':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))},
              'environment':{'torch':str(torch.__version__),'numpy':np.__version__,'threads':4},
              'trainingPerformed':False,'productionChanged':False,'annotationsChanged':False,
              'results':results,'previews':str(previews),
              'scope':'two reviewed development images; geometric hypotheses and interpolation controls, not release validation'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    # Preserve the archived pre-fix report when diagnosing a newer detector.
    parser.add_argument('--output',type=Path,default=Path('.cache/video-failure-analysis/current-diagnosis.json'))
    parser.add_argument('--previews',type=Path,default=Path('.cache/video-failure-analysis'))
    args=parser.parse_args()
    report=analyze(args.output,args.previews)
    for case in report['results']:
        print(case['id'], {variant:{name:len(m['wrongCells']) for name,m in data['models'].items()}
                          for variant,data in case['classification'].items()})


if __name__=='__main__':
    main()
