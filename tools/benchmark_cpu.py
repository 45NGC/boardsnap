"""Fresh-process CPU measurements on validation data, never final acceptance data."""

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import time


def benchmark(model, samples):
    started = time.perf_counter()
    import cv2
    import torch
    import numpy
    import PIL
    from boardsnap.neural import NeuralClassifier
    from boardsnap.classification import ClassificationError
    from boardsnap.detection import BoardDetectionError
    from boardsnap.image_input import ImageInputError
    from tools.evaluate_neural import timing
    from tools.neural_data import digest
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    classifier = NeuralClassifier(model)
    first = samples[0]
    classifier.recognize_image(first['image'], orientation=first['orientation'])
    cold = (time.perf_counter()-started)*1000
    times, errors = [], []
    for sample in samples:
        start = time.perf_counter()
        try:
            result = classifier.recognize_image(sample['image'], orientation=sample['orientation'])
            if result != {'piecePlacement': sample['piecePlacement']}:
                errors.append({'image': sample['image'], 'result': result})
        except (ClassificationError, BoardDetectionError, ImageInputError) as error:
            errors.append({'image': sample['image'], 'result': error.to_dict()})
        times.append(time.perf_counter()-start)
    cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')), platform.processor())
    return {'modelSha256': digest(model), 'dataRole': 'validation', 'warm': timing(times),
            'coldMilliseconds': cold, 'peakRssMiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            'scope': 'fresh Linux process imports + model + 40 validation images; warm full pipeline; cold includes imports, load and first image',
            'correctImages': len(samples)-len(errors), 'errors': errors,
            'environment': {'python': platform.python_version(), 'torch': str(torch.__version__),
                            'numpy':numpy.__version__,'pillow':PIL.__version__,'opencv':cv2.__version__,
                            'platform': platform.platform(), 'cpu': cpu, 'logicalCpus': os.cpu_count(),
                            'torchThreads': 4, 'opencvThreads': 1}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Stream metadata before importing ML; do not load the large square corpus.
    metadata = json.loads((args.dataset/'dataset.json').read_text())
    unique, remaining = {}, []
    for line in (args.dataset/'verified.jsonl').open():
        row = json.loads(line)
        if row['split'] != 'validation':
            continue
        sample = {k: row[k] for k in ('orientation', 'piecePlacement')}
        sample['image'] = str(Path(metadata['sourceRoot'])/row['image'])
        key = (row['style']['combination'], row['style']['layout'])
        if key not in unique:
            unique[key] = sample
        elif len(remaining) < 40:
            remaining.append(sample)
    samples = (list(unique.values())+remaining)[:40]
    if len(samples) != 40:
        raise ValueError('Need 40 validation images for CPU measurements.')
    report = benchmark(args.model, samples)
    from tools.neural_data import digest
    report.update(datasetSha256=digest(args.dataset/'dataset.json'), samples=samples,
                  benchmarkCodeSha256=digest(Path(__file__)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('samples','errors')}))


if __name__ == '__main__':
    main()
