"""Freeze an audited mixed training pool and reproducible draws; never train a model."""

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

from tools.audit_targeted_photo_overlap import source_key
from tools.build_square_dataset import square_labels
from tools.inventory_training_coverage import DATASETS, training_rows
from tools.neural_data import child, digest, load_board, training_indices
from tools.position_dataset import LABELS, placement_family
from tools.prepare_phone_photos import ROOT, write_json

PLAN = ROOT/'data/manifests/mixed-training-v1.json'
family = lru_cache(maxsize=None)(placement_family)


def overlap_keys(row):
    keys = [('group', row['groupId']), ('position-id', row['positionId']),
            ('placement-family', family(row['piecePlacement']))]
    for key in ('sha256', 'originalSha256', 'sourceSha256', 'arraySha256', 'pixelSha256'):
        if row.get(key):
            # Source/normalized/original file identities share a namespace.
            kind = 'pixels' if key == 'pixelSha256' else 'archive' if key == 'arraySha256' else 'image-file'
            keys.append((kind, row[key]))
    source = source_key(row.get('source', {}))
    if source:
        keys.append(('known-source', source))
    return keys


def audit_overlap(training, validation):
    """No image/square reassignment: reject the entire proposed assembly on conflict."""
    reserved = defaultdict(list)
    for row in validation:
        if row['split'] != 'validation':
            raise ValueError('Only existing validation is allowed in this audit.')
        for key in overlap_keys(row):
            reserved[key].append(row['image'])
    conflicts = []
    for row in training:
        if row['split'] != 'training':
            raise ValueError('Nontraining row in the training pool.')
        hits = [{'kind':kind, 'validationExamples':reserved[(kind,value)][:3]}
                for kind,value in overlap_keys(row) if (kind,value) in reserved]
        if hits:
            conflicts.append({'image':row['image'], 'groupId':row['groupId'], 'matches':hits})
    return conflicts


def pool_for(row, dataset, backgrounds):
    if dataset == 'phone-targeted-training-v1':
        if 'trainingAssignment' in row:
            return 'photo-targeted'
        review = backgrounds[row['photoId']]
        if review['arraySha256'] != row['arraySha256'] or review['imageSha256'] != row['sha256']:
            raise ValueError('Changed photo background annotation.')
        return 'photo-old-wood' if review['boardAppearance'] == 'wood-texture' else 'photo-old-other'
    if dataset == 'arrowhead-training-squares-v1':
        return 'digital-arrowheads'
    if row.get('conditions') == ['clean']:
        return 'digital-clean'
    if any(m['kind'] == 'arrow' for m in row.get('marks', [])):
        return 'digital-arrows'
    if row.get('marks'):
        return 'digital-simple-marks'
    raise ValueError('Unknown digital training condition.')


def allocate(total, keys, rng):
    """Even allocation with deterministic random tie breaking, no fixed-key bias."""
    keys = sorted(keys)
    base, remainder = divmod(total, len(keys))
    extra = set(rng.permutation(len(keys))[:remainder].tolist())
    return [(key, base+(i in extra)) for i,key in enumerate(keys)]


def sample_epoch(boards, quotas, seed, epoch=0):
    """Exact pool quotas, then balanced group/position/style/board allocations."""
    if type(epoch) is not int or epoch < 0:
        raise ValueError('Epoch must be a nonnegative integer.')
    if not quotas or any(type(v) is not int or v <= 0 for v in quotas.values()):
        raise ValueError('Quotas must be positive integers.')
    rng = np.random.default_rng(np.random.SeedSequence([seed, epoch]))
    pools = defaultdict(list)
    for i, board in enumerate(boards):
        if board['row']['split'] != 'training' or not board['eligibleIndices']:
            raise ValueError('Sampling is restricted to nonempty training records.')
        pools[board['pool']].append(i)
    if set(pools) != set(quotas):
        raise ValueError('Missing or unexpected sampling pool.')
    pairs = []

    def distribute(indices, count, depth=0):
        if not count:
            return
        if depth == 4:
            if len(indices) != 1:
                raise ValueError('Ambiguous board identity.')
            i = indices[0]
            cells = boards[i]['eligibleIndices']
            # Cycle through a shuffled cell set before repeating it.
            for _ in range(count//len(cells)):
                pairs.extend((i,int(c)) for c in rng.permutation(cells))
            pairs.extend((i,int(c)) for c in rng.permutation(cells)[:count%len(cells)])
            return
        groups = defaultdict(list)
        for i in indices:
            row = boards[i]['row']
            key = (row['groupId'], row['positionId'],
                   row.get('style',{}).get('combination', row.get('appearanceGroup','photo')),
                   str(i))[depth]
            groups[key].append(i)
        for key, n in allocate(count, groups, rng):
            distribute(groups[key], n, depth+1)

    for pool in sorted(quotas):
        distribute(pools[pool], quotas[pool])
    pairs = np.asarray(pairs, dtype=np.int32)
    rng.shuffle(pairs)
    return pairs


def load_validation(source):
    meta = json.loads((source/'dataset.json').read_text())
    entry = meta['indexes'].get('validation', meta['indexes']['verified'])
    path = child(source,entry['path'])
    if digest(path) != entry['sha256']:
        raise ValueError('Changed validation index.')
    rows = []
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row['split'] != 'validation':
            continue  # Never inspect final evaluation records or open their archives.
        if row['status'] != 'ok' or row['cells'] != square_labels(row['piecePlacement'],row['orientation']):
            raise ValueError('Invalid validation annotation.')
        rows.append(row)
    return rows


def freeze_input(path, root):
    return {'path':str(path.relative_to(root)), 'sha256':digest(path)}


def verify_inputs(plan, root):
    for entry in plan['inputs']:
        if digest(child(root,entry['path'])) != entry['sha256']:
            raise ValueError('Changed frozen source: '+entry['path'])


def materialize(boards, draws, destination, root):
    """Copy selected pixels unchanged into mmap arrays; no transforms or inference."""
    images = np.lib.format.open_memmap(destination/'training-images.npy', mode='w+', dtype=np.uint8,
                                      shape=(len(draws),64,64,3))
    labels = np.lib.format.open_memmap(destination/'training-labels.npy', mode='w+', dtype=np.int64,
                                      shape=(len(draws),))
    by_board = defaultdict(list)
    for offset,(board,cell) in enumerate(draws):
        if not 0 <= board < len(boards) or int(cell) not in boards[int(board)]['eligibleIndices']:
            raise ValueError('Draw outside the approved training pool.')
        by_board[int(board)].append((offset,int(cell)))
    for index, occurrences in by_board.items():
        reference = boards[index]
        if reference['row']['split'] != 'training':
            raise ValueError('Cannot materialize held-out samples for training.')
        pixels, targets = load_board(child(root,reference['sourceDataset']),reference['row'])
        offsets,cells = np.asarray(occurrences).T
        images[offsets],labels[offsets] = pixels[cells],targets[cells]
    images.flush(); labels.flush()
    del images,labels


def prepare(plan, destination, root=ROOT):
    root = root.resolve()
    destination = destination.resolve()
    if destination.exists() or not destination.is_relative_to(root/'.cache'):
        raise ValueError('Choose a new destination inside .cache; existing datasets are preserved.')
    verify_inputs(plan, root)
    backgrounds = {r['photoId']:r for r in json.loads((root/plan['backgroundReview']).read_text())['samples']}
    boards, validation, inputs = [], [], []
    for name in plan['datasets']:
        source = root/'.cache'/name
        meta = json.loads((source/'dataset.json').read_text())
        if meta['preprocessing']['squareSize'] != 64 or meta['preprocessing']['colorMode'] != 'RGB':
            raise ValueError('Incompatible crop preprocessing.')
        rows,_ = training_rows(source)
        for row in rows:
            pool = pool_for(row,name,backgrounds)
            boards.append({'sourceDataset':str(source.relative_to(root)), 'pool':pool,
                           'eligibleIndices':training_indices(row), 'row':row})
        if name in plan['validationDatasets']:
            for row in load_validation(source):
                validation.append({'sourceDataset':str(source.relative_to(root)), 'row':row})
        inputs.append({'dataset':name,'preprocessing':meta['preprocessing']})
    train_rows = [b['row'] for b in boards]
    val_rows = [b['row'] for b in validation]
    conflicts = audit_overlap(train_rows,val_rows)
    if conflicts:
        raise ValueError('Training/validation conflict; no output created: '+json.dumps(conflicts[:5]))
    # Verify and compare decoded complete crop arrays, not just ZIP container hashes.
    pixel_rows = []
    for reference in [*validation,*boards]:
        pixels,_ = load_board(child(root,reference['sourceDataset']),reference['row'])
        pixel_sha = hashlib.sha256(pixels.tobytes()).hexdigest()
        pixel_rows.append(dict(reference['row'],pixelSha256=pixel_sha))
        reference['canonicalPixelsSha256'] = pixel_sha
    conflicts = audit_overlap(pixel_rows[len(validation):],pixel_rows[:len(validation)])
    if conflicts:
        raise ValueError('Decoded training/validation pixel overlap; no output created: '+json.dumps(conflicts[:5]))
    # Duplicate board variants across training sources should not gain accidental weight.
    archive_counts = Counter(r['arraySha256'] for r in train_rows)
    if any(n > 1 for n in archive_counts.values()):
        raise ValueError('Duplicate training archive: resolve source ownership before sampling.')
    draws = sample_epoch(boards,plan['poolQuotas'],plan['seed'])
    pools = {}
    for pool, quota in plan['poolQuotas'].items():
        eligible = [b for b in boards if b['pool']==pool]
        chosen = [(int(b),int(c)) for b,c in draws if boards[int(b)]['pool']==pool]
        classes = Counter(boards[b]['row']['cells'][c]['label'] for b,c in chosen)
        colors = Counter(boards[b]['row']['cells'][c]['label']+'|'+boards[b]['row']['cells'][c]['background'] for b,c in chosen)
        pools[pool] = {'quota':quota, 'fraction':quota/len(draws),'boards':len(eligible),
            'groups':len({b['row']['groupId'] for b in eligible}),
            'positions':len({b['row']['positionId'] for b in eligible}),
            'eligibleSquares':sum(len(b['eligibleIndices']) for b in eligible),
            'sampledBoards':len({b for b,c in chosen}), 'uniqueBoardCells':len(set(chosen)),
            'sampledClasses':dict(classes),'sampledClassColors':dict(colors),
            'sampledGroups':dict(Counter(boards[b]['row']['groupId'] for b,c in chosen))}
    audit = {'trainingBoards':len(boards),'validationBoards':len(validation),
        'validationCounts':dict(Counter(b['sourceDataset'] for b in validation)),
        'observedConflicts':[], 'checks':['group','position-id','placement-family',
            'known-source','image-file','archive','decoded-canonical-board-pixels'],
        'fullyVerifiedSourceIndependence':False,
        'unknownPhotoTrainingSources':sum('photoId' in r and source_key(r.get('source',{})) is None for r in train_rows),
        'unknownPhotoValidationSources':sum('photoId' in r and source_key(r.get('source',{})) is None for r in val_rows),
        'limitations':plan['limitations']}
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.mixed-prepare-') as tmp:
        stage=Path(tmp)
        for name,rows in [('training-boards',boards),('validation',validation)]:
            (stage/f'{name}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        np.savez_compressed(stage/'sampling-epoch-000.npz',board_indices=draws[:,0],cell_indices=draws[:,1])
        materialize(boards,draws,stage,root)
        report={'schemaVersion':1,'format':'boardsnap-mixed-reference-dataset-v1',
            'datasetId':plan['datasetId'],'complete':True,'seed':plan['seed'],'epoch':0,
            'classOrder':list(LABELS),'squareShape':[64,64,3],'dtype':'uint8','colorMode':'RGB',
            'sampleCount':len(draws),'pools':pools,'audit':audit,'sourcePreprocessing':inputs,
            'inputs':plan['inputs'],'plan':plan,'assemblyCodeSha256':digest(Path(__file__)),
            'artifacts':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(stage.iterdir())},
            'validationSampling':'All original 64 cells of every existing validation board; no balancing.',
            'trainingRun':False,'inferenceRun':False,'finalEvaluationAccessed':False}
        write_json(stage/'dataset.json',report)
        verify_inputs(plan,root)
        stage.rename(destination)
    return report


def load_prepared_epoch(destination, root=ROOT):
    """Return immutable mmap arrays only after verifying the frozen preparation."""
    metadata=json.loads((destination/'dataset.json').read_text())
    if not metadata['complete'] or metadata['format'] != 'boardsnap-mixed-reference-dataset-v1':
        raise ValueError('Not a complete mixed dataset.')
    verify_inputs(metadata['plan'],root)
    for name,entry in metadata['artifacts'].items():
        if digest(child(destination,name)) != entry['sha256']:
            raise ValueError('Changed mixed dataset artifact.')
    return (np.load(destination/'training-images.npy',mmap_mode='r',allow_pickle=False),
            np.load(destination/'training-labels.npy',mmap_mode='r',allow_pickle=False))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=PLAN)
    parser.add_argument('--output',type=Path,default=ROOT/'.cache/mixed-training-v1')
    parser.add_argument('--report',type=Path,default=ROOT/'data/reports/mixed-training-v1.json')
    args=parser.parse_args(argv)
    result=prepare(json.loads(args.plan.read_text()),args.output)
    write_json(args.report,result)
    print(json.dumps({'samples':result['sampleCount'],'trainingBoards':result['audit']['trainingBoards'],
                      'validationBoards':result['audit']['validationBoards'],'conflicts':0}))


if __name__=='__main__':
    main()
