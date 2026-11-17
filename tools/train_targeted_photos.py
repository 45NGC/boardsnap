"""Assemble reviewed targeted photos and fine-tune one resumable CPU candidate."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from boardsnap.neural import NeuralClassifier
from tools.neural_data import digest, load_board, load_split, read_index
from tools.position_dataset import placement_family
from tools.prepare_phone_photos import ROOT, write_json
from tools.train_neural import fit, seed_run


def check_additions(old_rows, additions):
    """Protect validation by source group, position family and file identity."""
    reserved = [r for r in old_rows if r['split'] != 'training']
    groups = {r['groupId'] for r in reserved}
    families = {placement_family(r['piecePlacement']) for r in reserved}
    hashes = {r['sha256'] for r in reserved}
    identities = {(r['positionId'], r['configurationId'], r['orientation']) for r in old_rows}
    for row in additions:
        if row['split'] != 'development' or row['status'] != 'ok':
            raise ValueError('Add only reviewed development photographs.')
        identity = (row['positionId'], row['configurationId'], row['orientation'])
        if identity in identities:
            raise ValueError('Duplicate training variant.')
        identities.add(identity)
        if (row['groupId'] in groups or placement_family(row['piecePlacement']) in families
                or row['sha256'] in hashes):
            raise ValueError('New training data overlaps a reserved partition.')


def assemble(plan, destination, *, root=ROOT):
    """Reuse crop archives byte-for-byte; never recrop or alter validation."""
    destination = destination.resolve()
    if not destination.is_relative_to(root.resolve()/'.cache') or destination.exists():
        raise ValueError('Choose a new dataset destination inside .cache.')
    for value in plan['inputs'].values():
        if digest(root/value['path']) != value['sha256']:
            raise ValueError(f'Changed frozen input: {value["path"]}')
    overlap = json.loads((root/plan['inputs']['overlapReport']['path']).read_text())
    if overlap['observedOverlap'] or overlap['finalEvaluationAccessed']:
        raise ValueError('Unresolved detected conflict or final evaluation access.')
    for value in overlap['inputs'].values():
        if digest(root/value['path']) != value['sha256']:
            raise ValueError('Overlap review is stale.')
    base = (root/plan['inputs']['baseDataset']['path']).parent
    extra = (root/plan['inputs']['targetedDataset']['path']).parent
    metadata, old_rows = read_index(base)
    added_meta = json.loads((extra/'dataset.json').read_text())
    idx = extra/added_meta['indexes']['verified']['path']
    if digest(idx) != added_meta['indexes']['verified']['sha256']:
        raise ValueError('Targeted index changed.')
    if added_meta['sourceManifestSha256'] != plan['inputs']['targetedManifest']['sha256']:
        raise ValueError('Targeted crop reviews differ from the frozen manifest.')
    additions = [json.loads(line) for line in idx.read_text().splitlines()]
    check_additions(old_rows, additions)
    if sorted(r['photoId'] for r in additions) != sorted(plan['addedPhotoIds']):
        raise ValueError('Training assignments differ from the plan.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.targeted-training-') as tmp:
        stage = Path(tmp)
        rows = []
        paths = set()
        for source, records in ((base, old_rows), (extra, additions)):
            for original in records:
                row = deepcopy(original)
                load_board(source, row)  # Verify arrays and labels before copying.
                if source == extra:
                    row['split'] = 'training'
                    row['trainingAssignment'] = plan['datasetId']
                path = row['array']
                if path in paths or not (stage/path).resolve().is_relative_to(stage.resolve()):
                    raise ValueError('Duplicate or unsafe archive path.')
                paths.add(path)
                (stage/path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source/path, stage/path)
                if digest(stage/path) != row['arraySha256']:
                    raise ValueError('Copied archive differs.')
                rows.append(row)
        indexes = {}
        for name in ('verified', 'training', 'validation'):
            selected = rows if name == 'verified' else [r for r in rows if r['split'] == name]
            path = stage/f'{name}.jsonl'
            path.write_text(''.join(json.dumps(r)+'\n' for r in selected))
            indexes[name] = {'path': path.name, 'sha256': digest(path), 'boards': len(selected)}
        old_validation = [r for r in old_rows if r['split'] == 'validation']
        assert [r for r in rows if r['split'] == 'validation'] == old_validation
        result = {'schemaVersion': 1, 'complete': True, 'datasetId': plan['datasetId'],
                  'classOrder': metadata['classOrder'], 'preprocessing': metadata['preprocessing'],
                  'indexes': indexes, 'splitCounts': {s: indexes[s]['boards'] for s in ('training','validation')},
                  'validationRowsUnchanged': True, 'validationArrayHashesUnchanged': True,
                  'inputs': plan['inputs'], 'provenanceLimitations': plan['provenanceLimitations'],
                  'assemblyCodeSha256': digest(Path(__file__)), 'finalEvaluationAccessed': False}
        write_json(stage/'dataset.json', result)
        read_index(stage)
        stage.rename(destination)
    return result


def train(dataset, baseline, run, config, *, resume=False):
    metadata, rows = read_index(dataset)
    if metadata['datasetId'] != 'phone-targeted-training-v1':
        raise ValueError('Use the frozen targeted photographic training dataset.')
    seed_run(config)
    training = load_split(dataset, rows, 'training')
    validation = load_split(dataset, rows, 'validation')
    baseline_hash = digest(baseline)
    classifier = NeuralClassifier(baseline)
    pred = np.concatenate([classifier.predict_ids(validation[0][i:i+256])
                           for i in range(0,len(validation[0]),256)])
    controls = (pred == validation[1]).reshape(-1,64).all(1)
    teacher_mask = np.concatenate([np.full(64, 'trainingAssignment' not in r, dtype=bool)
                                   for r in rows if r['split'] == 'training'])
    version = {'datasetId': metadata['datasetId'], 'datasetSha256': digest(dataset/'dataset.json'),
               'verifiedIndexSha256': metadata['indexes']['verified']['sha256'],
               'trainingBoards': len(training[1])//64, 'validationBoards': len(validation[1])//64,
               'baselineSha256': baseline_hash, 'baselineExactValidationBoards': int(controls.sum()),
               'validationChanged': False, 'finalEvaluationAccessed': False,
               'trainingCodeSha256': digest(ROOT/'tools/train_neural.py'),
               'runnerCodeSha256': digest(Path(__file__)),
               'policy': 'Preserve baseline-exact validation controls first; then exact boards, macro recall and loss. Distill only previous training photos, never validation or newly targeted photos.'}
    report = fit(training, validation, config, run, version, resume=resume,
                 initialize_from=baseline, teacher_from=baseline, teacher_mask=teacher_mask,
                 control_boards=controls)
    if digest(baseline) != baseline_hash:
        raise ValueError('Baseline was modified.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT/'data/manifests/phone-targeted-training-v1.json')
    parser.add_argument('--dataset', type=Path, default=ROOT/'.cache/phone-targeted-training-v1')
    parser.add_argument('--run', type=Path, default=ROOT/'.cache/neural-phone-targeted-v1')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text())
    if not args.dataset.exists():
        assemble(plan, args.dataset)
    else:
        metadata, _ = read_index(args.dataset)
        if metadata['inputs'] != plan['inputs']:
            raise ValueError('Existing dataset differs from plan.')
    if args.prepare_only:
        return
    baseline = ROOT/plan['baseline']['path']
    if digest(baseline) != plan['baseline']['sha256']:
        raise ValueError('Baseline differs from plan.')
    if args.run.exists() and not args.resume:
        raise ValueError('Preserve previous runs; use --resume for this exact configuration.')
    result = train(args.dataset, baseline, args.run, plan['trainingConfig'], resume=args.resume)
    print(json.dumps(result['selected']))


if __name__ == '__main__':
    main()
