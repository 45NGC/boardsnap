"""Select a parameter average of compatible related models using validation only."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
import torch

from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, load_model
from tools.neural_data import digest, load_split, read_index
from tools.train_neural import atomic_save, selection_key, validate

FRACTIONS = (0., .25, .5, .75, 1.)


def average_state(left, right, fraction):
    if not 0 <= fraction <= 1 or left.keys() != right.keys():
        raise ValueError('A parameter average requires compatible states and a fraction in [0, 1].')
    result = {}
    for name, tensor in left.items():
        other = right[name]
        if tensor.shape != other.shape or tensor.dtype != other.dtype or not tensor.is_floating_point():
            raise ValueError('A parameter average requires matching floating-point parameters.')
        result[name] = tensor * (1-fraction) + other * fraction
    return result


def select(dataset, left_path, right_path, run, threads=4):
    if run.exists():
        raise ValueError('Use a new averaging run directory.')
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    left, left_meta = load_model(left_path)
    right, right_meta = load_model(right_path)
    source, rows = read_index(dataset)
    validation_rows = [r for r in rows if r['split'] == 'validation']
    controls = np.array([r.get('cohort') == 'previous' for r in validation_rows], dtype=np.bool_)
    if not controls.any():
        raise ValueError('The validation set must identify previous-cohort controls.')
    # Only the original validation arrays are loaded; no regression pixels are used.
    images, labels = load_split(dataset, rows, 'validation')
    model = deepcopy(left)
    best, best_state, history = None, None, []
    for fraction in FRACTIONS:
        started = time.perf_counter()
        model.load_state_dict(average_state(left.state_dict(), right.state_dict(), fraction))
        metrics = validate(model, images, labels, 512, control_boards=controls)
        item = {'rightFraction': fraction, 'metrics': metrics}
        if best is None or selection_key(metrics) > selection_key(best['metrics']):
            best, best_state = item, deepcopy(model.state_dict())
        history.append(dict(item, seconds=time.perf_counter()-started))
        print(f"Fraction {fraction}: {metrics['exactBoards']}/{metrics['boards']} validation boards", flush=True)
    metadata = {'formatVersion': 1, 'architecture': ARCHITECTURE, 'classOrder': list(CLASSES),
                'preprocessing': PREPROCESSING,
                'dataVersion': {'datasetId': source['datasetId'], 'manifestSha256': digest(dataset/'dataset.json'),
                                'verifiedIndexSha256': source['indexes']['verified']['sha256'],
                                'validationBoards': len(validation_rows)},
                'trainingConfig': {'method': 'validation-selected-parameter-average',
                                   'fractions': list(FRACTIONS), 'threads': threads},
                'parameterAverage': {'leftSha256': digest(left_path), 'rightSha256': digest(right_path),
                                     'rightFraction': best['rightFraction'],
                                     'leftDataVersion': left_meta['dataVersion'], 'rightDataVersion': right_meta['dataVersion']},
                'selection': 'previous-cohort validation exact boards, total exact boards, macro recall, lower loss; earlier tie',
                'selectionCodeSha256': digest(Path(__file__))}
    run.mkdir(parents=True)
    atomic_save({'metadata': metadata, 'state_dict': best_state}, run/'best.pt')
    report = {'metadata': metadata, 'complete': True, 'selected': best, 'history': history,
              'weightsSha256': digest(run/'best.pt'), 'evaluationUsedForSelection': False,
              'selectionDataRole': 'validation only; exposed regressions informed earlier development'}
    (run/'training.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'left', 'right', 'run'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    select(args.dataset, args.left, args.right, args.run, args.threads)


if __name__ == '__main__':
    main()
