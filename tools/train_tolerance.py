"""Fine-tune from v8 with training-only crop errors and fixed validation challenges."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from tools.bounds_tolerance import SCENARIOS, fixed_training_scenario, labels_for, perturbed_squares
from tools.build_square_dataset import raster_bounds
from tools.neural_data import child, digest, load_board, read_index, training_indices
from tools.training_augmentation import validate_additions

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261017


def selected_for_augmentation(row):
    """A frozen quarter of training images, independent of labels or errors."""
    if row['split'] != 'training':
        return False
    return int(hashlib.sha256(row['image'].encode()).hexdigest()[:8], 16) % 4 == 0


def choose_valid_scenario(row, size):
    """Choose deterministically among applicable cases; never fabricate margins."""
    first = fixed_training_scenario(row, SEED)
    start = SCENARIOS.index(first)-1
    choices = SCENARIOS[1:]
    bounds = raster_bounds(row['boardBounds']).as_box()
    for i in range(len(choices)):
        scenario = choices[(start+i) % len(choices)]
        l,t,r,b = (a+d for a,d in zip(bounds,scenario.edges,strict=True))
        if 0 <= l < r <= size[0] and 0 <= t < b <= size[1]:
            return scenario
    raise ValueError('No valid challenge crop.')


def open_arrays(cache, prefix, count):
    return (np.lib.format.open_memmap(cache/f'{prefix}-images.npy', mode='w+', dtype=np.uint8,
                                      shape=(count,64,64,3)),
            np.lib.format.open_memmap(cache/f'{prefix}-labels.npy', mode='w+', dtype=np.int64, shape=(count,)))


def prepare(dataset, extra, cache):
    """Use disk-backed arrays to keep RAM bounded; cache hashes pin every input.

    Original validation arrays and frequencies are retained as the first block.
    A separate fixed challenge block selects tolerance; neither block is trained.
    Evaluation arrays and the independent final corpus are never opened.
    """
    metadata, rows = read_index(dataset)
    extra_metadata, extra_rows = read_index(extra)
    validate_additions(rows, extra_rows)
    identity = {
        'datasetSha256': digest(dataset/'dataset.json'),
        'indexSha256': metadata['indexes']['verified']['sha256'],
        'extraDatasetSha256': digest(extra/'dataset.json'),
        'extraIndexSha256': extra_metadata['indexes']['verified']['sha256'],
        'seed': SEED, 'scenarios': [asdict(s) for s in SCENARIOS],
        'codeSha256': {str(p.relative_to(ROOT)):digest(p) for p in
                       [Path(__file__).resolve(), ROOT/'tools/bounds_tolerance.py',
                        ROOT/'tools/neural_data.py', ROOT/'tools/training_augmentation.py',
                        ROOT/'tools/build_square_dataset.py', *sorted((ROOT/'src/boardsnap').rglob('*.py'))]},
    }
    # JSON persists edge tuples as lists; normalize before cache comparisons.
    identity = json.loads(json.dumps(identity))
    manifest = cache/'dataset.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if saved['identity'] != identity or not saved['complete']:
            raise ValueError('Prepared data configuration changed; choose another cache.')
        for name, sha in saved['files'].items():
            if digest(cache/name) != sha:
                raise ValueError('Prepared arrays changed.')
        return saved
    cache.mkdir(parents=True, exist_ok=True)
    if list(cache.iterdir()):
        raise ValueError('Incomplete cache; choose a new directory.')
    training = [r for r in rows if r['split']=='training']
    validation = [r for r in rows if r['split']=='validation']
    additions = [r for r in training if selected_for_augmentation(r)]
    if not training or not validation or not additions:
        raise ValueError('Nonempty training, validation and augmentation are required.')
    original_count = sum(len(training_indices(r)) for r in training+extra_rows)
    train = open_arrays(cache,'training',original_count+64*len(additions))
    valid = open_arrays(cache,'validation',128*len(validation))
    provenance = []
    offset = 0
    for root, group in ((dataset,training),(extra,extra_rows)):
        for row in group:
            pixels, labels = load_board(root,row)
            keep = training_indices(row)
            train[0][offset:offset+len(keep)] = pixels[keep]
            train[1][offset:offset+len(keep)] = labels[keep]
            offset += len(keep)
    for number,row in enumerate(validation):
        pixels,labels = load_board(dataset,row)
        valid[0][number*64:(number+1)*64] = pixels
        valid[1][number*64:(number+1)*64] = labels
    source_root = Path(metadata['sourceRoot'])
    for split, group in (('training',additions),('validation',validation)):
        for number,row in enumerate(group):
            path = child(source_root,row['image'])
            if digest(path) != row['sha256']:
                raise ValueError('Training/validation screenshot changed.')
            with Image.open(path) as source, source.convert('RGB') as image:
                scenario = choose_valid_scenario(row,image.size)
                pixels,edges = perturbed_squares(image,raster_bounds(row['boardBounds']),row['orientation'],scenario)
            labels = labels_for(row)
            if split == 'training':
                train[0][offset:offset+64],train[1][offset:offset+64] = pixels,labels
                offset += 64
            else:
                start = (len(validation)+number)*64
                valid[0][start:start+64],valid[1][start:start+64] = pixels,labels
            provenance.append({k:row[k] for k in ('image','sha256','positionId','groupId','split','orientation')}
                              | {'scenario':scenario.name,'bounds':list(edges)})
            if (number+1)%500 == 0:
                print(f'Prepared {number+1}/{len(group)} {split} challenges',flush=True)
    for array in (*train,*valid):
        array.flush()
    del train,valid
    (cache/'variants.json').write_text(json.dumps(provenance,indent=2)+'\n')
    files = {p.name:digest(p) for p in sorted(cache.iterdir())}
    report = {'complete':True, 'identity':identity, 'files':files,
              'originalTrainingSquares':original_count, 'augmentedTrainingBoards':len(additions),
              'originalValidationBoards':len(validation),'challengeValidationBoards':len(validation),
              'evaluationArraysLoaded':False,'validationUsedForTraining':False,
              'originalValidationDistributionChanged':False,
              'trainingSelection':'sha256(source image path) modulo 4 == 0; all 64 cells',
              'selection':'maximize original validation exact boards first, then total exact boards, macro recall and loss'}
    manifest.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--extra-training-dataset',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=ROOT/'tools/train-tolerance-v1.json')
    parser.add_argument('--resume',action='store_true')
    args = parser.parse_args(argv)
    report = prepare(args.dataset,args.extra_training_dataset,args.cache)
    train = tuple(np.load(args.cache/f'training-{k}.npy',mmap_mode='r') for k in ('images','labels'))
    valid = tuple(np.load(args.cache/f'validation-{k}.npy',mmap_mode='r') for k in ('images','labels'))
    controls = np.arange(len(valid[1])//64) < report['originalValidationBoards']
    teacher_mask = np.arange(len(train[1])) < report['originalTrainingSquares']
    from tools.train_neural import fit
    fit(train,valid,json.loads(args.config.read_text()),args.run,
        {'datasetId':'bounds-tolerance-v1','preparedDatasetSha256':digest(args.cache/'dataset.json'),
         'provenance':report,'trainingCodeSha256':digest(ROOT/'tools/train_neural.py')},
        resume=args.resume,control_boards=controls,initialize_from=args.baseline,
        teacher_from=args.baseline,teacher_mask=teacher_mask)


if __name__ == '__main__':
    main()
