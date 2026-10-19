"""Choose a conservative parameter average on fixed validation challenges only."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from boardsnap.neural import load_model, preprocess
from tools.average_neural import average_state
from tools.neural_data import digest
from tools.train_neural import atomic_save, selection_key, validate

# Include conservative steps near the untouched reference before larger changes.
FRACTIONS = (0., .0625, .125, .25, .5, .75, 1.)


@torch.inference_mode()
def correctness(model, images, labels, batch_size=512):
    return np.concatenate([(model(preprocess(images[i:i+batch_size])).argmax(1).numpy() == labels[i:i+batch_size])
                           for i in range(0,len(labels),batch_size)]).reshape(-1,64)


def preserves_reference(baseline, candidate):
    return bool(candidate[baseline.all(1)].all() and candidate.sum() >= baseline.sum())


def select(cache, baseline_path, trained_path, run, threads=4):
    if run.exists():
        raise ValueError('Use a new selection run directory.')
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    prepared = json.loads((cache/'dataset.json').read_text())
    if not prepared['complete'] or prepared['validationUsedForTraining'] or prepared['evaluationArraysLoaded']:
        raise ValueError('Expected completed training-only augmentation and untouched validation partitions.')
    training = json.loads((trained_path.parent/'training.json').read_text())
    if not training['complete'] or training['weightsSha256'] != digest(trained_path):
        raise ValueError('Select only from completed training weights.')
    if training['metadata']['dataVersion']['preparedDatasetSha256'] != digest(cache/'dataset.json'):
        raise ValueError('Training and selection datasets differ.')
    for name in ('validation-images.npy','validation-labels.npy'):
        with (cache/name).open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != prepared['files'][name]:
            raise ValueError('Validation pixels/labels changed.')
    images = np.load(cache/'validation-images.npy',mmap_mode='r')
    labels = np.load(cache/'validation-labels.npy')
    original = prepared['originalValidationBoards']
    controls = np.arange(len(labels)//64) < original
    left,left_meta = load_model(baseline_path)
    right,right_meta = load_model(trained_path)
    baseline = correctness(left,images[:original*64],labels[:original*64])
    model = deepcopy(left)
    best,state,history = None,None,[]
    for fraction in FRACTIONS:
        model.load_state_dict(average_state(left.state_dict(),right.state_dict(),fraction))
        correct = correctness(model,images[:original*64],labels[:original*64])
        metrics = validate(model,images,labels,512,control_boards=controls)
        eligible = preserves_reference(baseline,correct)
        item = {'trainedFraction':fraction,'referencePreserved':eligible,'metrics':metrics}
        history.append(item)
        if eligible and (best is None or selection_key(metrics)>selection_key(best['metrics'])):
            best,state = item,deepcopy(model.state_dict())
        print(f"Fraction {fraction}: original {metrics['controlExactBoards']}/{original}, "
              f"total {metrics['exactBoards']}/{metrics['boards']}, eligible={eligible}",flush=True)
    metadata = {k:left_meta[k] for k in ('formatVersion','architecture','classOrder','preprocessing')}
    metadata.update(dataVersion={'datasetId':'bounds-tolerance-v1',
                                 'preparedDatasetSha256':digest(cache/'dataset.json'),
                                 'originalValidationBoards':original,'challengeValidationBoards':original},
                    trainingConfig={'method':'validation-selected-parameter-average','fractions':list(FRACTIONS),'threads':threads},
                    parameterAverage={'baselineSha256':digest(baseline_path),'trainedSha256':digest(trained_path),
                                      'trainedFraction':best['trainedFraction'],'trainedDataVersion':right_meta['dataVersion']},
                    selection='preserve every originally correct board and total original correct squares; '
                              'then original exact boards, total exact boards, macro recall, lower loss; earlier tie',
                    selectionCodeSha256=digest(Path(__file__)),
                    averagingCodeSha256=digest(Path(__file__).with_name('average_neural.py')),
                    validationCodeSha256=digest(Path(__file__).with_name('train_neural.py')))
    run.mkdir(parents=True)
    atomic_save({'metadata':metadata,'state_dict':state},run/'best.pt')
    report = {'metadata':metadata,'complete':True,'selected':best,'history':history,
              'weightsSha256':digest(run/'best.pt'),'evaluationUsedForSelection':False,
              'dataRole':'validation','independentFinalEvaluation':False}
    (run/'training.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cache','baseline','trained','run'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--threads',type=int,default=4)
    args = parser.parse_args(argv)
    if args.threads < 1:
        parser.error('Threads must be positive.')
    select(args.cache,args.baseline,args.trained,args.run,args.threads)


if __name__ == '__main__':
    main()
