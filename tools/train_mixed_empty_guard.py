"""Run one frozen ablation excluding false-piece targets on empty training cells."""

import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import torch

from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, load_model
from tools.mixed_training_policy import assess_accuracy, preflight, reference_records
from tools.neural_data import digest
from tools.prepare_mixed_training import load_prepared_epoch
from tools.prepare_phone_photos import ROOT, write_json
from tools.train_mixed import run_epochs, teacher_mask_for, validation_cache, validation_predictions
from tools.train_neural import seed_run

DEFAULT_PLAN = ROOT / 'data/manifests/neural-mixed-empty-guard-v1-plan.json'


def guarded_teacher_mask(old_mask, labels, targets):
    """Keep CE on all samples; omit KL only for empty labels with a piece teacher."""
    if (old_mask.dtype != np.bool_ or old_mask.shape != labels.shape
            or targets.shape != (len(labels), len(CLASSES))
            or not np.isfinite(targets).all() or np.any(targets < 0)
            or not np.allclose(targets[old_mask].sum(1), 1, atol=1e-5)):
        raise ValueError('Invalid training teacher arrays.')
    return old_mask & ~((labels == 0) & (targets.argmax(axis=1) != 0))


def check_control_plan(plan, control):
    # Every scientific setting other than the explicit empty-label mask is inherited.
    mutable = {'planId', 'status', 'runDirectory', 'frozenInputs', 'intervention', 'implementationBeforeLaunch'}
    if {k: v for k, v in plan.items() if k not in mutable} != {k: v for k, v in control.items() if k not in mutable}:
        raise ValueError('A setting besides the teacher mask differs from the control.')
    if plan['runDirectory'] == control['runDirectory']:
        raise ValueError('Do not overwrite the control run.')


def execute(plan_path=DEFAULT_PLAN, *, resume=False, root=ROOT):
    plan = json.loads(plan_path.read_text())
    preflight(plan, root)
    intervention = plan['intervention']
    control_plan = json.loads((root / intervention['controlPlan']).read_text())
    check_control_plan(plan, control_plan)
    config = plan['trainingConfig']
    seed_run(config)
    environment = {'python': platform.python_version(), 'numpy': np.__version__, 'torch': str(torch.__version__),
                   'device': 'cpu', 'deterministicAlgorithms': True}
    if environment != plan['environment']:
        raise ValueError('Frozen environment changed.')
    data = root / plan['dataset']
    control_run = root / control_plan['runDirectory']
    images, labels = load_prepared_epoch(data, root)
    refs = [json.loads(s) for s in (data / 'training-boards.jsonl').read_text().splitlines()]
    with np.load(data / plan['sampling']['draw'], allow_pickle=False) as draws:
        board_ids, cell_ids = draws['board_indices'], draws['cell_indices']
    old_mask = teacher_mask_for(refs, board_ids, plan['loss']['teacherPools'])
    cache = json.loads((control_run / 'teacher-cache.json').read_text())
    control_signature = json.loads((control_run / 'execution.json').read_text())
    if (control_signature['planSha256'] != digest(root / intervention['controlPlan'])
            or cache['signature'] != dict(control_signature, maskSha256=hashlib.sha256(old_mask.tobytes()).hexdigest())
            or digest(control_run / 'teacher-targets.npy') != cache['sha256']):
        raise ValueError('Control teacher cache differs.')
    targets = np.load(control_run / 'teacher-targets.npy', mmap_mode='r', allow_pickle=False)
    mask = guarded_teacher_mask(old_mask, labels, targets)
    excluded = np.flatnonzero(old_mask & ~mask)
    identities = set(zip(board_ids[excluded].tolist(), cell_ids[excluded].tolist()))
    review = json.loads((root / intervention['review']).read_text())
    reviewed = {(c['boardIndex'], c['cellIndex']) for c in review['teacher']['conflicts'] if c['expected'] == 'empty'}
    if (len(excluded) != intervention['excludedExposures'] or identities != reviewed
            or len(identities) != intervention['excludedDistinctCells']
            or int(mask.sum()) != intervention['effectiveTeacherSamples']):
        raise ValueError('Excluded training cells differ from reviewed empty cells.')
    for b, c in identities:
        if refs[b]['row']['cells'][c]['classId'] != 0:
            raise ValueError('Excluded cell label is not empty.')
    del refs
    baseline = reference_records(plan, root)
    # Require existing caches; never regenerate control artifacts.
    if not (control_run / 'validation-cache.json').exists():
        raise ValueError('Expected existing control validation cache.')
    val_pixels = validation_cache(data, control_run, baseline, root)
    run = root / plan['runDirectory']
    signature = {'planSha256': digest(plan_path), 'runnerSha256': digest(Path(__file__)),
                 'baselineSha256': plan['baseline']['sha256'], 'datasetSha256': digest(data / 'dataset.json'),
                 'environment': environment}
    if run.exists():
        if not resume:
            raise ValueError('Run exists; use --resume for the identical attempt.')
        if json.loads((run / 'execution.json').read_text()) != signature:
            raise ValueError('Resume inputs/code differ.')
    else:
        if resume:
            raise ValueError('No existing execution to resume.')
        run.mkdir(parents=True)
        write_json(run / 'execution.json', signature)
    audit = {'originalTeacherSamples': int(old_mask.sum()), 'effectiveTeacherSamples': int(mask.sum()),
             'excludedExposures': len(excluded), 'excludedDistinctCells': len(identities),
             'excludedSampleIndices': excluded.tolist(), 'supervisedSamples': len(labels),
             'effectiveSupervisedOnlySamples': int((~mask).sum()),
             'maskSha256': hashlib.sha256(mask.tobytes()).hexdigest(),
             'rule': 'old_mask & ~((label == empty) & (teacher_argmax != empty))',
             'teacherCacheReused': str((control_run / 'teacher-targets.npy').relative_to(root)),
             'validationCacheReused': str((control_run / 'validation-images.npy').relative_to(root))}
    write_json(run / 'mask-audit.json', audit)
    metadata = {'formatVersion': 1, 'architecture': ARCHITECTURE, 'classOrder': list(CLASSES),
                'preprocessing': PREPROCESSING, 'dataVersion': signature, 'trainingConfig': config,
                'classWeights': plan['loss']['classWeights'], 'environment': environment,
                'distillation': {'teacherSha256': plan['baseline']['sha256'], 'maskSha256': audit['maskSha256'],
                                 'trainingSquares': int(mask.sum()), 'temperature': config['distillationTemperature'],
                                 'weight': config['distillationWeight'], 'emptyGuard': audit['rule']},
                'selection': 'Unchanged per-domain/per-stratum gates; rank safe epochs only; earlier tie.',
                'loss': plan['loss']['name']}
    model, _ = load_model(root / plan['baseline']['path'])

    def evaluate(candidate):
        records = validation_predictions(candidate, val_pixels, baseline, config['batchSize'])
        return assess_accuracy(baseline, records, minimum_photo_gain=plan['acceptance']['minimumPhotoExactGain']), records

    print(f'Excluded {len(excluded)} teacher exposures; CE retains all {len(labels)} samples. Reusing both caches.', flush=True)
    result = run_epochs(model, (images, labels), targets, mask, evaluate, config, run, metadata, resume=resume)
    if any(digest(root / e['path']) != e['sha256'] for e in plan['frozenInputs']):
        raise ValueError('Frozen reference inputs changed.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    result = execute(args.plan, resume=args.resume)
    print(json.dumps({'completedEpochs': result['completedEpochs'], 'decision': result['decision']}))


if __name__ == '__main__':
    main()
