"""Explain saved targeted-training regressions without inference or training."""
import argparse
from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.neural_data import digest, load_board, read_index
from tools.position_dataset import LABELS
from tools.prepare_phone_photos import ROOT, write_json


def changes(expected, baseline, candidate):
    if not (len(expected) == len(baseline) == len(candidate) == 64):
        raise ValueError('Expected three complete aligned boards.')
    return [{'index': i, 'square': f'{"abcdefgh"[i%8]}{8-i//8}',
             'expected': LABELS[e], 'baseline': LABELS[a], 'candidate': LABELS[b],
             'change': 'regression' if a == e else 'recovery' if b == e else 'changed-error'}
            for i, (e, a, b) in enumerate(zip(expected, baseline, candidate, strict=True)) if a != b]


def analyze(output, *, root=ROOT):
    output.mkdir(parents=True, exist_ok=True)
    sources = [('phone', '.cache/phone-targeted-training-v1'),
               ('digital', '.cache/digital-style-squares-v2')]
    summary, cases, inputs = {}, [], {}
    appearances_path = root/'data/manifests/phone-validation-appearance-v1.json'
    appearances = {r['photoId']: r for r in json.loads(appearances_path.read_text())['samples']}
    inputs['appearanceManifest'] = {'path': str(appearances_path.relative_to(root)), 'sha256': digest(appearances_path)}
    for kind, relative in sources:
        dataset = root/relative
        path = root/f'.cache/neural-phone-targeted-v1/{kind}-validation.json'
        comparison = json.loads(path.read_text())
        metadata, rows = read_index(dataset)
        if (comparison['split'] != 'validation' or digest(dataset/'dataset.json') != comparison['datasetSha256']
                or metadata['indexes']['verified']['sha256'] != comparison['indexSha256']):
            raise ValueError('Stale validation comparison.')
        for model in comparison['models'].values():
            if digest(root/model['path']) != model['sha256']:
                raise ValueError('Reference model changed.')
        inputs[kind] = {'path': str(path.relative_to(root)), 'sha256': digest(path),
                        'datasetSha256': comparison['datasetSha256'], 'indexSha256': comparison['indexSha256']}
        rows = {r['image']: r for r in rows if r['split'] == 'validation'}
        paired = {}
        all_changes, loss_count = [], 0
        for a,b in zip(comparison['records']['baseline'], comparison['records']['candidate'], strict=True):
            if a['image'] != b['image'] or a['expected'] != b['expected']:
                raise ValueError('Unaligned predictions.')
            paired[a['image']] = (a,b)
        if len(paired) != len(rows) or set(paired) != set(rows):
            raise ValueError('Incomplete or duplicate prediction records.')
        for image,(a,b) in paired.items():
            delta = changes(a['expected'],a['predictions'],b['predictions'])
            all_changes.extend(dict(image=image, **d) for d in delta)
            if a['expected'] != a['predictions'] or b['expected'] == b['predictions']:
                continue
            loss_count += 1
            row = rows[image]
            pixels, labels = load_board(dataset,row)
            if labels.tolist() != a['expected']:
                raise ValueError('Predictions refer to other labels.')
            clean = [r for r in rows.values() if row.get('pairId') and r.get('pairId') == row['pairId'] and r['conditions'] == ['clean']]
            case = {'caseId': f'{kind}-{loss_count:02d}', 'kind':kind, 'image':image,
                    'positionId':row['positionId'],'groupId':row['groupId'],'orientation':row['orientation'],
                    'style':row.get('style'), 'conditions':row.get('conditions',[]), 'marks':row.get('marks',[]),
                    'array':row['array'],'arraySha256':row['arraySha256'],'changes':delta,
                    'cleanControl':None}
            if row.get('photoId') in appearances:
                appearance = appearances[row['photoId']]
                if appearance['imageSha256'] != row['sha256']:
                    raise ValueError('Appearance annotation refers to another photograph.')
                case['observedAppearance'] = appearance
            if len(clean)==1:
                control=clean[0]; ca,cb=paired[control['image']]
                cp,_=load_board(dataset,control)
                case['cleanControl']={'image':control['image'],'baselineExact':ca['expected']==ca['predictions'],
                    'candidateExact':cb['expected']==cb['predictions'],
                    'affectedCellPredictions':[{'square':d['square'],'baseline':LABELS[ca['predictions'][d['index']]],
                        'candidate':LABELS[cb['predictions'][d['index']]]} for d in delta]}
            board=Image.new('RGB',(512,512))
            for i in range(64): board.paste(Image.fromarray(pixels[i]),(i%8*64,i//8*64))
            panel=Image.new('RGB',(850,575),'#eeeeee');draw=ImageDraw.Draw(panel)
            panel.paste(board,(0,35));draw.text((5,5),f'{case["caseId"]} | {Path(image).name}',fill='black')
            for j,d in enumerate(delta):
                i=d['index']; d['pixelSha256']=hashlib.sha256(pixels[i].tobytes()).hexdigest()
                d['background']=row['cells'][i]['background']
                draw.rectangle((i%8*64,35+i//8*64,i%8*64+63,35+i//8*64+63),outline='red',width=2)
                panel.paste(Image.fromarray(pixels[i]).resize((192,192),Image.Resampling.NEAREST),(530,55+j*240))
                draw.text((530,35+j*240),f'{d["square"]}: {d["expected"]} -> {d["candidate"]}',fill='black')
                if len(clean)==1:
                    panel.paste(Image.fromarray(cp[i]).resize((96,96),Image.Resampling.NEAREST),(735,55+j*240))
                    draw.text((735,155+j*240),'Clean control',fill='black')
            panel.save(output/f'{case["caseId"]}.jpg',quality=95)
            case['preview']=str((output/f'{case["caseId"]}.jpg').relative_to(root))
            cases.append(case)
        summary[kind]={'validationBoards':len(rows),'lostExactBoards':loss_count,
            'changedSquares':dict(Counter(d['change'] for d in all_changes)),
            'newFalsePieces':sum(d['change']=='regression' and d['expected']=='empty' for d in all_changes),
            'changes':all_changes}
    training_path = root/'.cache/neural-phone-targeted-v1/training.json'
    training = json.loads(training_path.read_text())
    base_training_path = root/'.cache/neural-phone-v1/training.json'
    base_training = json.loads(base_training_path.read_text())
    training_index = root/'.cache/phone-targeted-training-v1/training.jsonl'
    training_rows = [json.loads(line) for line in training_index.read_text().splitlines()]
    composition = {}
    for cohort in ('previous', 'targeted'):
        selected = [r for r in training_rows if ('trainingAssignment' in r) == (cohort == 'targeted')]
        composition[cohort] = {'boards': len(selected), 'classCounts': dict(Counter(c['label'] for r in selected for c in r['cells']))}
    for key,path in [('training',training_path),('baselineTraining',base_training_path),('trainingIndex',training_index)]:
        inputs[key] = {'path':str(path.relative_to(root)), 'sha256':digest(path)}
    report={'schemaVersion':1,'reportId':'targeted-photo-regressions-v1','inputs':inputs,
            'scope':'Saved validation predictions and original verified crop archives; no detection rerun, inference, training or final evaluation.',
            'summary':summary,'lostBoardCases':cases,
            'trainingContext': {'composition':composition,
                'baselineClassWeights':dict(zip(LABELS,base_training['metadata']['classWeights'],strict=True)),
                'candidateClassWeights':dict(zip(LABELS,training['metadata']['classWeights'],strict=True)),
                'distillation':training['metadata'].get('distillation'),
                'digitalTrainingBoardsInThisRun':0},
            'lostBoardErrorCount':sum(len(c['changes']) for c in cases),
            'lostBoardFalsePieceCount':sum(d['expected']=='empty' for c in cases for d in c['changes']),
            'uniqueLostCropHashes':len({d['pixelSha256'] for c in cases for d in c['changes']}),
            'finalEvaluationAccessed':False,'trainingRun':False,'inferenceRun':False,
            'analysisCodeSha256':digest(Path(__file__))}
    cards=''.join(f'<article><h2>{c["caseId"]}</h2><p>{escape(c["image"])}</p><img src="{c["caseId"]}.jpg"></article>' for c in cases)
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Targeted regressions</title><style>body{font-family:sans-serif}img{max-width:100%}p{overflow-wrap:anywhere}</style><h1>Saved validation regressions</h1><p>Canonical cell order; glyphs not rotated. Right: failing crop and available clean control.</p>'+cards)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.cache/phone-targeted-regressions-v1')
    parser.add_argument('--report',type=Path,default=ROOT/'data/reports/targeted-photo-regressions-v1.json')
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'.cache'):
        raise ValueError('Keep derived previews inside .cache.')
    report=analyze(output)
    write_json(args.report,report)
    print(json.dumps({k:report[k] for k in ('lostBoardErrorCount','lostBoardFalsePieceCount','uniqueLostCropHashes')}))


if __name__=='__main__':
    main()
