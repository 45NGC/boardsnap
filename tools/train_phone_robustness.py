"""One bounded photo-only robustness candidate; no validation augmentation or final data."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from boardsnap.neural import NeuralClassifier
from tools.neural_data import digest, load_split, read_index
from tools.train_neural import fit, seed_run

CONFIG = {'seed': 20261101, 'epochs': 12, 'batchSize': 256, 'learningRate': .00002,
          'weightDecay': .0001, 'threads': 4, 'distillationTemperature': 2,
          'distillationWeight': 1}


def augment_training(images, seed):
    """One deterministic mild optical variant per training board; labels unchanged.

    Same parameters for all cells of each board: gain/contrast, low-amplitude
    screen interference, mild Gaussian blur. No geometry or label transforms.
    This is a controlled training perturbation, not a physical camera simulator.
    """
    if images.dtype != np.uint8 or images.shape[1:] != (64, 64, 3) or len(images) % 64:
        raise ValueError('Expected complete uint8 RGB training boards.')
    rng = np.random.default_rng(seed)
    output = np.empty_like(images)
    yy, xx = np.indices((64, 64))
    for offset in range(0, len(images), 64):
        gain, contrast = rng.uniform(.85, 1.15, 2)
        amplitude, phase = rng.uniform(0, 5), rng.uniform(0, 2*np.pi)
        period, sigma = rng.uniform(3, 9), rng.uniform(.15, .55)
        ripple = amplitude*np.sin((xx+yy)*2*np.pi/period+phase)
        for index in range(offset, offset+64):
            pixel = ((images[index].astype(np.float32)-127.5)*contrast+127.5)*gain
            pixel = cv2.GaussianBlur(pixel, (5, 5), sigma) + ripple[..., None]
            output[index] = np.clip(np.rint(pixel), 0, 255).astype(np.uint8)
    return output


def train(dataset, baseline, run):
    metadata, rows = read_index(dataset)
    if metadata['datasetId'] != 'phone-training-v1' or any(r['split'] not in ('training', 'validation') for r in rows):
        raise ValueError('Use the audited phone training/validation dataset only.')
    seed_run(CONFIG)
    cv2.setNumThreads(1)
    train_pixels, train_labels = load_split(dataset, rows, 'training')
    validation = load_split(dataset, rows, 'validation')
    baseline_hash = digest(baseline)
    classifier = NeuralClassifier(baseline)
    predictions = np.concatenate([classifier.predict_ids(validation[0][i:i+256])
                                 for i in range(0, len(validation[0]), 256)])
    controls = (predictions == validation[1]).reshape(-1, 64).all(1)
    augmented = augment_training(train_pixels, CONFIG['seed'])
    combined = (np.concatenate([train_pixels, augmented]), np.tile(train_labels, 2))
    teacher_mask = np.r_[np.ones(len(train_labels), bool), np.zeros(len(train_labels), bool)]
    version = {'datasetId': 'phone-robustness-v2', 'sourceDatasetSha256': digest(dataset/'dataset.json'),
               'sourceIndexSha256': metadata['indexes']['verified']['sha256'],
               'trainingBoards': len(train_labels)//64, 'trainingSquaresWithVariants': len(combined[1]),
               'validationBoards': len(validation[1])//64, 'validationChanged': False,
               'augmentationCodeSha256': digest(Path(__file__)),
               'trainingCodeSha256': digest(Path(__file__).with_name('train_neural.py')),
               'augmentedPixelsSha256': hashlib.sha256(augmented.tobytes()).hexdigest(),
               'baselineSha256': baseline_hash, 'baselineExactValidationBoards': int(controls.sum()),
               'controlMaskSha256': hashlib.sha256(controls.tobytes()).hexdigest(),
               'controlPolicy': 'Preserve baseline-exact annotated validation boards first; then total exact boards. Reject candidate if baseline controls are lost.',
               'finalEvaluationAccessed': False}
    result = fit(combined, validation, CONFIG, run, version, initialize_from=baseline,
                 teacher_from=baseline, teacher_mask=teacher_mask, control_boards=controls)
    if digest(baseline) != baseline_hash:
        raise ValueError('Baseline changed during training.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path('.cache/phone-training-v1'))
    parser.add_argument('--baseline', type=Path, default=Path('.cache/neural-phone-v1/best.pt'))
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.run.exists():
        parser.error('Use a new run directory; preserve previous models.')
    report = train(args.dataset, args.baseline, args.run)
    print(json.dumps(report['selected']))


if __name__ == '__main__':
    main()
