"""Inventory existing training labels and overlays without inference or resplitting."""

import argparse
import html
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.arrow_marks import affected_indices, coordinate, draw_arrow
from tools.board_marks import validate_marks
from tools.build_square_dataset import square_labels
from tools.neural_data import child, digest, load_board, training_indices
from tools.position_dataset import LABELS
from tools.prepare_phone_photos import ROOT, write_json

DATASETS = ('digital-style-squares-v2', 'arrowhead-training-squares-v1',
            'phone-targeted-training-v1')


def training_rows(root):
    """Verify the index; exclude nontraining records before inspecting annotations."""
    root = Path(root).resolve()
    meta = json.loads((root/'dataset.json').read_text())
    entry = meta['indexes'].get('training', meta['indexes']['verified'])
    index = child(root, entry['path'])
    if not meta['complete'] or meta['classOrder'] != list(LABELS) or digest(index) != entry['sha256']:
        raise ValueError('Incompatible or changed dataset index.')
    rows = []
    with index.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['split'] != 'training':
                continue
            if row['status'] != 'ok' or row['cells'] != square_labels(row['piecePlacement'], row['orientation']):
                raise ValueError('Invalid training labels.')
            if row.get('style', {}).get('combination') in meta.get('heldOutCombinations', []):
                raise ValueError('Reserved combination in training.')
            if 'marks' in row:
                validate_marks(row['marks'], row['piecePlacement'])
            rows.append(row)
    return rows, {'metadataSha256': digest(root/'dataset.json'),
                  'index': str(index.relative_to(root)), 'indexSha256': digest(index)}


def square_index(square):
    x, y = coordinate(square)
    return y*8+x


@lru_cache(maxsize=8192)
def crossing_cells(serialized):
    """Actual overlap pixels, not merely two arrows passing through one cell."""
    count = np.zeros((512, 512), dtype=np.uint16)
    for mark in json.loads(serialized):
        with Image.new('L', (512, 512)) as canvas:
            draw_arrow(canvas, mark, {'x': 0, 'y': 0, 'width': 512, 'height': 512},
                       'white-bottom', mask=True)
            count += (np.asarray(canvas) > 0)
    return tuple(np.flatnonzero((count > 1).reshape(8, 64, 8, 64).any(axis=(1, 3))).tolist())


def cell_features(row):
    """Return overlapping canonical cell tags; unknown photo marks stay unknown."""
    tags = [set() for _ in range(64)]
    if row.get('conditions') == ['clean']:
        for tag in tags:
            tag.add('clean-control')
    arrows = []
    for mark in row.get('marks', []):
        if mark['kind'] == 'arrow':
            arrows.append(mark)
            for i in affected_indices(mark, halo=0):
                tags[i].add('arrow-touch')
            tags[square_index(mark['from'])].add('arrow-start')
            tags[square_index(mark['to'])].add('arrow-tip')
        else:
            for square in mark['squares']:
                tags[square_index(square)].add(mark['kind'])
    if len(arrows) > 1:
        for i in crossing_cells(json.dumps(arrows, sort_keys=True)):
            tags[i].add('arrow-crossing')
    for tag in tags:
        if 'arrow-touch' in tag and tag.intersection({'circle', 'last-move', 'selection', 'check', 'move-dot'}):
            tag.add('arrow-with-other-mark')
    return tags


def new_stat():
    return {'boards': set(), 'positions': set(), 'groups': set(), 'cells': Counter(),
            'selectedCells': 0, 'examples': {}}


def record(stat, row, indices, selected):
    indices = list(indices)
    if not indices:
        return
    stat['boards'].add(row['arraySha256'])
    stat['positions'].add(row['positionId'])
    stat['groups'].add(row['groupId'])
    for i in indices:
        cell = row['cells'][i]
        key = cell['label']+'|'+cell['background']
        stat['cells'][key] += 1
        stat['selectedCells'] += i in selected
        stat['examples'].setdefault(key, {'image': row['image'], 'array': row['array'],
            'arraySha256': row['arraySha256'], 'square': cell['square'],
            'groupId': row['groupId'], 'positionId': row['positionId']})


def finish(stat):
    counts = dict(sorted(stat['cells'].items()))
    return {'uniqueBoardArchives': len(stat['boards']), 'positions': len(stat['positions']),
            'groups': len(stat['groups']), 'squares': sum(counts.values()),
            'emptySquares': sum(v for k,v in counts.items() if k.startswith('empty|')),
            'occupiedSquares': sum(v for k,v in counts.items() if not k.startswith('empty|')),
            'cellsRetainedByExistingTrainingSelector': stat['selectedCells'],
            'byClassAndSquareColor': counts,
            'missingClassColorPairs': [label+'|'+color for label in LABELS for color in ('light','dark')
                                       if label+'|'+color not in counts],
            'examples': stat['examples']}


def inventory(root=ROOT):
    backgrounds_path = root/'data/manifests/phone-training-backgrounds-v1.json'
    backgrounds = {r['photoId']: r for r in json.loads(backgrounds_path.read_text())['samples']}
    result = {'schemaVersion': 1, 'dataRole': 'training-only-coverage-inventory',
              'inferenceRun': False, 'trainingRun': False, 'reservedImagesAccessed': False,
              'backgroundReview': {'path': str(backgrounds_path.relative_to(root)), 'sha256': digest(backgrounds_path)},
              'inventoryCodeSha256': digest(Path(__file__)), 'datasets': {}}
    seen_archives = set()
    previous_clean_hashes = set()
    for name in DATASETS:
        source = root/'.cache'/name
        rows, inputs = training_rows(source)
        stats = defaultdict(new_stat)
        conditions, controls, external_controls, duplicate_archives = Counter(), 0, 0, 0
        clean_pairs = {r['pairId'] for r in rows if r.get('pairId') and r.get('conditions') == ['clean']}
        clean_hashes = {r['sha256'] for r in rows if r.get('conditions') == ['clean']}
        # This corpus already includes previous digital corpora: never sum its ancestors.
        for row in rows:
            path = child(source, row['array'])
            if digest(path) != row['arraySha256']:
                raise ValueError(f'Changed training archive: {path}')
            duplicate_archives += row['arraySha256'] in seen_archives
            seen_archives.add(row['arraySha256'])
            selected = set(training_indices(row))
            record(stats['all'], row, range(64), selected)
            conditions.update(row.get('conditions') or ['unannotated'])
            if row.get('marks') and (row.get('pairId') in clean_pairs or row.get('sourceSha256') in clean_hashes):
                controls += 1
            if row.get('marks') and row.get('sourceSha256') in previous_clean_hashes:
                external_controls += 1
            features = cell_features(row)
            for tag in sorted(set().union(*features)):
                record(stats['cell:'+tag], row, [i for i,t in enumerate(features) if tag in t], selected)
            if 'photoId' in row:
                if 'trainingAssignment' in row:
                    background = row['boardAppearance']
                    appearance = row['appearanceGroup']
                    cohort = 'new-photos'
                else:
                    review = backgrounds[row['photoId']]
                    if review['arraySha256'] != row['arraySha256'] or review['imageSha256'] != row['sha256']:
                        raise ValueError('Photo background review is stale.')
                    background = review['boardAppearance']
                    appearance = 'not-reidentified'
                    cohort = 'old-photos'
                record(stats['cohort:'+cohort], row, range(64), selected)
                record(stats['photo-background:'+background], row, range(64), selected)
                record(stats['photo-appearance:'+appearance], row, range(64), selected)
                # Board-level conditions cannot locate overlays on individual squares.
                for condition in row.get('conditions') or ['unannotated']:
                    record(stats['photo-board-condition:'+condition], row, range(64), selected)
            elif 'style' in row:
                record(stats['digital-style:'+row['style']['combination']], row, range(64), selected)
        result['datasets'][name] = {'inputs': inputs, 'trainingBoardRows': len(rows),
            'trainingArchivesChecksumVerified': len(rows),
            'duplicateArchiveRowsAcrossInventoriedSources': duplicate_archives,
            'boardConditionCounts': dict(conditions), 'markedBoardsWithCleanControlInSameSource': controls,
            'markedBoardsWithCleanControlInEarlierSources': external_controls,
            'coverage': {key:finish(value) for key,value in sorted(stats.items())}}
        previous_clean_hashes.update(clean_hashes)
        for key, coverage in result['datasets'][name]['coverage'].items():
            if not key.startswith(('cell:', 'photo-background:', 'photo-appearance:')):
                coverage.pop('examples')
    result['limitations'] = [
        'Counts are crop occurrences, not independent observations or distinct pixel patterns.',
        'Cell features overlap; arrow-tip/start refer to endpoint cells, not every pixel of the head.',
        'Arrow touch/crossing use rendered 512px masks without halo; training selection retains its existing halo.',
        'Photo conditions are board-level; no claim that all empty squares are marked or unmarked.',
        'Old photo group is conservative unresolved provenance, not a known single game.',
        'No validation/final image arrays or predictions read; shared digital index is filtered before annotation inspection.',
        'This is not approval to mix datasets: check cross-source held-out groups and position families before assembly.',
        'Archive SHA verification checks existing bytes; no exhaustive visual relabeling or evaluation performed.']
    return result


def write_gallery(report, destination, root=ROOT):
    """Render existing training crops only; no source-image rectification."""
    destination.mkdir(parents=True, exist_ok=True)
    pages = ['<!doctype html><meta charset="utf-8"><title>Training coverage</title>',
             '<h1>Existing training material</h1><p>Training only; not model predictions. '
             'Counts include related variants. Photo overlays are not annotated per square.</p>']
    for name, dataset in report['datasets'].items():
        source = root/'.cache'/name
        rows, _ = training_rows(source)
        by_array = {r['array']: r for r in rows}
        pages.append('<h2>'+html.escape(name)+'</h2>')
        for key, coverage in dataset['coverage'].items():
            if not key.startswith(('cell:', 'photo-background:wood', 'photo-appearance:cc-thin')):
                continue
            examples = coverage['examples']
            picks = []
            for color in ('light', 'dark'):
                for labels in (('empty',), tuple('PNBRQK'), tuple('pnbrqk')):
                    found = next((label+'|'+color for label in labels if label+'|'+color in examples), None)
                    if found:
                        picks.append(found)
            panel = Image.new('RGB', (max(1,len(picks))*164, 212), 'white')
            draw = ImageDraw.Draw(panel)
            for j, label in enumerate(picks):
                item = examples[label]
                row = by_array[item['array']]
                pixels, _ = load_board(source,row)
                i = square_index(item['square'])
                panel.paste(Image.fromarray(pixels[i]).resize((160,160),Image.Resampling.NEAREST),(j*164,0))
                draw.text((j*164,162), label+' '+item['square'],fill='black')
                draw.text((j*164,180),row['positionId'][:23],fill='black')
            filename = name+'-'+key.replace(':','-')+'.jpg'
            panel.save(destination/filename)
            pages.append('<h3>'+html.escape(key)+'</h3><p>'+str(coverage['squares'])+
                         ' square occurrences</p><img style="max-width:100%" src="'+html.escape(filename)+'">')
        if name == 'phone-targeted-training-v1':
            old = [r for r in rows if 'trainingAssignment' not in r]
            for start in range(0,len(old),20):
                sheet = Image.new('RGB',(1100,960),'white')
                draw = ImageDraw.Draw(sheet)
                for j,row in enumerate(old[start:start+20]):
                    pixels,_ = load_board(source,row)
                    board = Image.new('RGB',(512,512))
                    for i,pixel in enumerate(pixels):
                        board.paste(Image.fromarray(pixel),((i%8)*64,(i//8)*64))
                    x,y = (j%5)*220,(j//5)*240
                    sheet.paste(board.resize((216,216)),(x,y))
                    draw.text((x,y+217),f'{start+j+1}: '+Path(row['originalPath']).stem,fill='black')
                filename = f'old-photos-{start//20+1}.jpg'
                sheet.save(destination/filename)
                pages.append('<h3>Old training backgrounds '+str(start+1)+'–'+str(start+len(old[start:start+20]))+
                             '</h3><img style="max-width:100%" src="'+filename+'">')
    (destination/'index.html').write_text('\n'.join(pages)+'\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/reports/training-coverage-v1.json')
    parser.add_argument('--gallery', type=Path, default=None, help='Optional local training-only contact sheets.')
    args = parser.parse_args(argv)
    report = inventory()
    write_json(args.output, report)
    if args.gallery:
        write_gallery(report, args.gallery)
    print(json.dumps({name: value['trainingBoardRows'] for name,value in report['datasets'].items()}))


if __name__ == '__main__':
    main()
