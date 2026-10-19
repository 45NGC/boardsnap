"""Deterministic digital geometry controls, unrelated to screenshot labels or weights."""

import argparse
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from boardsnap.detection import BoardDetectionError, detect_board
from tools.evaluate_real_use import ROOT, digest
from tools.evaluate_detection import rectangle_metrics


def scene(side, ratio, axis, condition, *, count=8, cut=0, hidden=0):
    """Return pixels and a priori bounds; artwork is not a classifier dataset."""
    index = np.minimum(np.arange(side)*count//side, count-1)
    palette = np.array([[201,218,242],[75,105,151]],dtype=np.int16)
    pixels = palette[(index[:,None]+index[None,:])%2].copy()
    if condition == 'texture-jpeg':
        pixels += np.random.default_rng(1807).integers(-10,11,(side,side,1))
    board = Image.fromarray(np.clip(pixels,0,255).astype(np.uint8))
    draw = ImageDraw.Draw(board)
    cell = side/count
    if condition == 'marks':
        for row,col in ((2,1),(5,4)):
            draw.rectangle((round(col*cell),round(row*cell),round((col+1)*cell)-1,
                            round((row+1)*cell)-1),fill='#c5c978')
    for row in (0,count-1):
        for col in range(count):
            draw.ellipse(((col+.25)*cell,(row+.2)*cell,(col+.75)*cell,(row+.82)*cell),
                         fill='#171717' if row==0 else '#fafafa')
    if condition == 'marks':
        draw.line((side*.16,side*.8,side*.8,side*.25),fill='#369267',width=max(2,side//70))
        draw.polygon([(side*.8,side*.25),(side*.70,side*.28),(side*.78,side*.36)],fill='#369267')
    size = (round(side*ratio),side) if axis == 'x' else (side,round(side*ratio))
    resampling = Image.Resampling.BILINEAR if condition=='marks' else Image.Resampling.BICUBIC
    resized = board.resize(size,resampling)
    board.close()
    if cut:
        cropped = resized.crop((cut,0,resized.width,resized.height)); resized.close();resized=cropped
    if hidden:
        ImageDraw.Draw(resized).rectangle((0,0,hidden-1,resized.height-1),fill='#333333')
    x,y = (13,29) if side%2 else (43,17)
    canvas = Image.new('RGB',(x+resized.width+61,y+resized.height+37),'#333333')
    canvas.paste(resized,(x,y))
    expected = (x,y,x+resized.width,y+resized.height)
    resized.close()
    if condition=='texture-jpeg':
        encoded=BytesIO(); canvas.save(encoded,format='JPEG',quality=82)
        canvas.close()
        with Image.open(BytesIO(encoded.getvalue())) as decoded:
            canvas=decoded.convert('RGB')
    return canvas, expected


def scenarios():
    for side in (160,257,512):
        for ratio in (1.02,1.04):
            for axis in ('x','y'):
                for condition in ('clean','marks','texture-jpeg'):
                    yield dict(id=f'{side}-{ratio}-{axis}-{condition}',side=side,ratio=ratio,
                               axis=axis,condition=condition,positive=True)
    for axis in ('x','y'):
        for kind,kwargs in [('hidden14',{'hidden':14}),('cut14',{'cut':14}),
                            ('missing-file',{'cut':48}),('grid7',{'count':7}),
                            ('grid9',{'count':9})]:
            yield dict(id=f'negative-{axis}-{kind}',side=384,ratio=1.04,axis=axis,
                       condition='marks',positive=False,**kwargs)
    for ratio in (1.08,1.15):
        yield dict(id=f'outside-scope-{ratio}',side=384,ratio=ratio,axis='x',
                   condition='clean',positive=False)


def evaluate():
    rows=[]
    for spec in scenarios():
        params={k:v for k,v in spec.items() if k not in ('id','positive')}
        image,expected=scene(**params)
        with image:
            try:
                bounds=detect_board(image)
                metrics=rectangle_metrics(bounds.as_box(),expected)
                measured={'box':list(bounds.as_box()),**metrics}
                passed=spec['positive'] and metrics['maxEdgeErrorPixels']<=2
            except BoardDetectionError as error:
                measured=error.to_dict();passed=not spec['positive'] and error.code=='BOARD_NOT_FOUND'
        rows.append(dict(specification=spec,expectedBox=list(expected),measurement=measured,passed=passed))
    return {'schemaVersion':1,'dataRole':'synthetic-development-geometry','independentFinalEvaluation':False,
            'classificationMeasured':False,'generatorSha256':digest(Path(__file__)),
            'detectorSha256':digest(ROOT/'src/boardsnap/detection.py'),
            'positiveCount':sum(r['specification']['positive'] for r in rows),
            'positivePassed':sum(r['passed'] and r['specification']['positive'] for r in rows),
            'negativeCount':sum(not r['specification']['positive'] for r in rows),
            'negativePassed':sum(r['passed'] and not r['specification']['positive'] for r in rows),
            'cases':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Refusing to overwrite an existing report.')
    result=evaluate()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k.endswith(('Count','Passed'))})


if __name__=='__main__':main()
