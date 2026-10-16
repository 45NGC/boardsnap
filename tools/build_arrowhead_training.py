"""Cover opaque blue arrowheads on every training class/background/style/view."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import tempfile

from tools.arrow_marks import coordinate, square
from tools.board_marks import mark_png
from tools.build_square_dataset import build_dataset
from tools.neural_data import child, digest, read_index
from tools.position_dataset import DEFAULT_MANIFEST, LABELS


def choose_sources(rows):
    buckets = {}
    for row in rows:
        if row['split'] != 'training' or row.get('conditions') != ['clean'] or row['style']['layout'] not in ('lichess-editor', 'chesscom-analysis', 'captured-desktop'):
            continue
        for cell in row['cells']:
            key = (row['style']['combination'], row['orientation'], cell['label'], cell['background'])
            rank = hashlib.sha256(f"arrowheads-v1:{row['image']}:{cell['square']}".encode()).hexdigest()
            if key not in buckets or rank < buckets[key][0]:
                buckets[key] = (rank, row, cell)
    combinations = {key[0] for key in buckets}
    expected = {(c, view, label, bg) for c in combinations for view in ('white-bottom','black-bottom')
                for label in LABELS for bg in ('light','dark')}
    if not combinations or set(buckets) != expected:
        raise ValueError('Missing training class/background/style/view coverage.')
    return [(key, *buckets[key]) for key in sorted(buckets)]


def arrow_to(target, seed):
    rng = random.Random(seed)
    x, y = coordinate(target)
    routes = []
    for a in range(8):
        for b in range(8):
            dx, dy = abs(a-x), abs(b-y)
            if not (dx or dy):
                continue
            if dx == 0 or dy == 0 or dx == dy:
                routes.append({'from':square(a,b),'path':'straight'})
            elif sorted((dx,dy)) == [1,2]:
                routes.append({'from':square(a,b),'path':'knight','bend':rng.choice(['horizontal-first','vertical-first'])})
    return dict(rng.choice(routes), kind='arrow', to=target, width=.22, rgba=[45,110,220,192])


def build(parent, captures, output, report_path):
    if captures.exists() or output.exists():
        raise ValueError('Use new augmentation destinations.')
    metadata, rows = read_index(parent)
    selected = choose_sources(rows)
    captures.parent.mkdir(parents=True,exist_ok=True)
    records=[]
    with tempfile.TemporaryDirectory(dir=captures.parent,prefix='.arrowheads-') as temporary:
        stage=Path(temporary)
        for index,(key,seed,row,cell) in enumerate(selected):
            path=child(Path(metadata['sourceRoot']),row['image'])
            if digest(path)!=row['sha256']:raise ValueError('Training source image changed.')
            mark=arrow_to(cell['square'],seed)
            png,evidence=mark_png(path.read_bytes(),row['boardBounds'],row['orientation'],[mark],row['piecePlacement'])
            target=stage/f'arrowhead-{index:04d}.png';target.write_bytes(png)
            record={k:row[k] for k in ('datasetId','positionId','groupId','split','piecePlacement','orientation','boardBounds','imageSize')}
            record.update(image=target.name,sha256=digest(target),configurationId=f'arrowhead-{index:04d}',
                          conditions=['arrow'],marks=[mark],augmentation=evidence,
                          sourceImage=row['image'],sourceSha256=row['sha256'],style=row['style'],cohort=row['cohort'],
                          targetClass=cell['label'],targetBackground=cell['background'],targetSquare=cell['square'])
            target.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');records.append(record)
            if (index+1)%100==0:print(f'Arrowheads {index+1}/{len(selected)}',flush=True)
        (stage/'captures.json').write_text(json.dumps({'images':records},indent=2)+'\n')
        stage.rename(captures)
    manifest=json.loads(DEFAULT_MANIFEST.read_text())
    build_dataset(captures.resolve(),records,manifest,output,provenance={
        'datasetId':'arrowhead-training-v1','parentDatasetSha256':digest(parent/'dataset.json'),
        'sourceCaptureReportSha256':digest(captures/'captures.json')})
    report={'dataRole':'training-only','images':len(records),'sourceGroups':len({r['groupId'] for r in records}),
            'parentDatasetSha256':digest(parent/'dataset.json'),'datasetSha256':digest(output/'dataset.json'),
            'generatorSha256':digest(Path(__file__)),
            'coverage':dict(Counter(f"{r['style']['combination']}/{r['orientation']}/{r['targetClass']}/{r['targetBackground']}" for r in records)),
            'scope':'all classes, square colors and views of seen training combinations; blue width .22 opacity 192 arrowheads; full-board rendering before crops',
            'reservedDataUsed':False}
    report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','captures','output','report'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();build(args.parent,args.captures,args.output,args.report)


if __name__=='__main__':main()
