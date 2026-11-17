"""Run the single frozen mixed-data experiment with paired gates and exact resume."""

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import numpy as np
import torch
from torch import nn

from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, load_model, preprocess
from tools.mixed_training_policy import DEFAULT_PLAN, assess_accuracy, preflight, reference_records
from tools.neural_data import digest, load_board
from tools.prepare_mixed_training import load_prepared_epoch
from tools.prepare_phone_photos import ROOT, write_json
from tools.train_neural import atomic_save, seed_run


def teacher_mask_for(refs, board_indices, teacher_pools):
    if any(r['row']['split'] != 'training' for r in refs):
        raise ValueError('Teacher input must contain training records only.')
    return np.asarray([refs[int(i)]['pool'] in teacher_pools for i in board_indices],dtype=np.bool_)


def choose_best(best, assessment, epoch):
    if not assessment['safeCheckpoint']:
        return False
    return best is None or assessment['rankingKey'] > best['assessment']['rankingKey']


def run_epochs(model, train, targets, teacher_mask, evaluate, config, run, metadata,
               *, resume=False, stop_after=None):
    """Persist an epoch only after its full paired validation and predictions exist."""
    seed_run(config)
    checkpoint=run/'last.pt'
    if checkpoint.exists() and not resume:
        raise ValueError('Checkpoint exists; resume the same run.')
    images,labels=train
    if (teacher_mask.dtype!=np.bool_ or teacher_mask.shape!=labels.shape
            or targets.shape!=(len(labels),13) or not teacher_mask.any()
            or not np.isfinite(targets).all()):
        raise ValueError('Invalid training teacher targets or mask.')
    optimizer= torch.optim.AdamW(model.parameters(),lr=config['learningRate'],
                                weight_decay=config['weightDecay'],betas=(.9,.999),eps=1e-8,amsgrad=False)
    criterion=nn.CrossEntropyLoss(weight=torch.tensor(metadata['classWeights'],dtype=torch.float32))
    start,history,best,best_state=0,[],None,None
    if resume and checkpoint.exists():
        saved=torch.load(checkpoint,map_location='cpu',weights_only=True)
        if saved['metadata']!=metadata:raise ValueError('Checkpoint recipe, environment or code changed.')
        model.load_state_dict(saved['state_dict']);optimizer.load_state_dict(saved['optimizer'])
        torch.set_rng_state(saved['rngState'])
        start,history,best,best_state=saved['epoch'],saved['history'],saved['best'],saved['bestState']
    elif resume:
        # Execution/cache may have been prepared before an interruption at epoch zero.
        start=0
    for epoch in range(start,min(config['epochs'],stop_after or config['epochs'])):
        began=time.perf_counter();model.train()
        order=np.random.default_rng(config['seed']+epoch).permutation(len(labels))
        for offset in range(0,len(order),config['batchSize']):
            indices=order[offset:offset+config['batchSize']]
            optimizer.zero_grad(set_to_none=True)
            logits=model(preprocess(images[indices]))
            loss=criterion(logits,torch.from_numpy(np.array(labels[indices],copy=True)))
            keep=teacher_mask[indices]
            if keep.any():
                t=config['distillationTemperature']
                loss=loss+config['distillationWeight']*t*t*nn.functional.kl_div(
                    (logits[keep]/t).log_softmax(1),torch.from_numpy(np.array(targets[indices[keep]],copy=True)),
                    reduction='batchmean')
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss.')
            loss.backward();optimizer.step()
        model.eval()
        assessment,records=evaluate(model)
        if choose_best(best,assessment,epoch+1):
            best={'epoch':epoch+1,'assessment':assessment};best_state=deepcopy(model.state_dict())
        record_path=run/f'epoch-{epoch+1:03d}-validation.json'
        write_json(record_path,{'epoch':epoch+1,'assessment':assessment,'records':records})
        history.append({'epoch':epoch+1,'assessment':assessment,'seconds':time.perf_counter()-began,
                        'predictions':record_path.name,'predictionsSha256':digest(record_path)})
        atomic_save({'metadata':metadata,'state_dict':model.state_dict(),'optimizer':optimizer.state_dict(),
                     'rngState':torch.get_rng_state(),'epoch':epoch+1,'history':history,
                     'best':best,'bestState':best_state},checkpoint)
        p=assessment['domains']['phone']['candidate'];d=assessment['domains']['digital']['candidate']
        print(f"Epoch {epoch+1}/{config['epochs']}: photo {p['exactBoards']}/{p['boards']}, "
              f"digital {d['exactBoards']}/{d['boards']}, safe={assessment['safeCheckpoint']}; "
              f"{history[-1]['seconds']:.1f}s",flush=True)
    if best is not None:
        atomic_save({'metadata':dict(metadata,selectedEpoch=best['epoch']),'state_dict':best_state},run/'best.pt')
    result={'metadata':metadata,'complete':len(history)==config['epochs'],'completedEpochs':len(history),
            'selected':best,'history':history,'promoted':False,
            'decision': 'quality-passed-further-checks-required' if best and best['assessment']['accuracyAccepted']
                        else 'keep-baseline-no-qualifying-candidate',
            'weightsSha256':digest(run/'best.pt') if best else None,
            'lastCheckpointSha256':digest(checkpoint),'finalEvaluationAccessed':False}
    write_json(run/'training.json',result)
    return result


def validation_cache(dataset, run, baseline, root):
    path=run/'validation-images.npy';manifest=run/'validation-cache.json'
    index=dataset/'validation.jsonl'
    signature={'sourceIndexSha256':digest(index),
               'images':{d:[r['image'] for r in records] for d,records in baseline.items()}}
    if manifest.exists():
        cached=json.loads(manifest.read_text())
        if cached['signature']!=signature or digest(path)!=cached['sha256']:
            raise ValueError('Validation cache differs.')
        return np.load(path,mmap_mode='r',allow_pickle=False)
    refs={r['row']['image']:r for r in map(json.loads,index.read_text().splitlines())}
    rows=[r for records in baseline.values() for r in records]
    temp=run/'validation-images.tmp.npy'
    pixels=np.lib.format.open_memmap(temp,mode='w+',dtype=np.uint8,shape=(64*len(rows),64,64,3))
    for i,row in enumerate(rows):
        reference=refs[row['image']]
        if reference['row']['split']!='validation':raise ValueError('Nonvalidation cache entry.')
        images,labels=load_board(root/reference['sourceDataset'],reference['row'])
        if labels.tolist()!=row['expected']:raise ValueError('Validation labels differ.')
        pixels[i*64:(i+1)*64]=images
        if (i+1)%500==0:print(f'Prepared validation cache: {i+1}/{len(rows)} boards',flush=True)
    pixels.flush();del pixels;os.replace(temp,path)
    write_json(manifest,{'signature':signature,'sha256':digest(path)})
    return np.load(path,mmap_mode='r',allow_pickle=False)


@torch.inference_mode()
def validation_predictions(model,pixels,baseline,batch_size):
    result={};cursor=0
    for domain,records in baseline.items():
        end=cursor+64*len(records);pred=[]
        for start in range(cursor,end,batch_size):
            pred.extend(model(preprocess(pixels[start:min(start+batch_size,end)])).argmax(1).tolist())
        result[domain]=[dict({k:v for k,v in row.items() if k!='seconds'},
                             predictions=pred[i*64:(i+1)*64]) for i,row in enumerate(records)]
        cursor=end
    return result


@torch.inference_mode()
def teacher_cache(model,images,mask,config,run,signature):
    path=run/'teacher-targets.npy';manifest=run/'teacher-cache.json'
    key=dict(signature,maskSha256=hashlib.sha256(mask.tobytes()).hexdigest())
    if manifest.exists():
        cached=json.loads(manifest.read_text())
        if cached['signature']!=key or digest(path)!=cached['sha256']:raise ValueError('Teacher cache changed.')
        return np.load(path,mmap_mode='r',allow_pickle=False)
    targets=np.zeros((len(images),13),np.float32)
    indices=np.flatnonzero(mask)
    for start in range(0,len(indices),config['batchSize']):
        selected=indices[start:start+config['batchSize']]
        targets[selected]=(model(preprocess(images[selected]))/config['distillationTemperature']).softmax(1).numpy()
    np.save(path,targets,allow_pickle=False)
    write_json(manifest,{'signature':key,'sha256':digest(path)})
    return np.load(path,mmap_mode='r',allow_pickle=False)


def execute(plan_path=DEFAULT_PLAN, *, resume=False, root=ROOT):
    plan=json.loads(plan_path.read_text());preflight(plan,root)
    config=plan['trainingConfig'];seed_run(config)
    environment={'python':platform.python_version(),'numpy':np.__version__,'torch':str(torch.__version__),
                 'device':'cpu','deterministicAlgorithms':True}
    if environment!=plan['environment']:raise ValueError('Frozen environment changed.')
    if (config['epochs']!=plan['executionLimits']['maximumEpochs']
            or plan['architecture']!=ARCHITECTURE or plan['preprocessing']!=PREPROCESSING):
        raise ValueError('Unsupported recipe.')
    run=root/plan['runDirectory'];dataset=root/plan['dataset']
    signature={'planSha256':digest(plan_path),'runnerSha256':digest(Path(__file__)),
               'baselineSha256':plan['baseline']['sha256'],'datasetSha256':digest(dataset/'dataset.json'),
               'environment':environment}
    if run.exists():
        if not resume:raise ValueError('Run exists; use --resume, not a new experiment.')
        if json.loads((run/'execution.json').read_text())!=signature:raise ValueError('Resume inputs/code differ.')
    else:
        if resume:raise ValueError('No existing execution to resume.')
        run.mkdir(parents=True);write_json(run/'execution.json',signature)
    images,labels=load_prepared_epoch(dataset,root)
    refs=[json.loads(s) for s in (dataset/'training-boards.jsonl').read_text().splitlines()]
    with np.load(dataset/plan['sampling']['draw'],allow_pickle=False) as draws:
        mask=teacher_mask_for(refs,draws['board_indices'],plan['loss']['teacherPools'])
    del refs
    if int(mask.sum())!=plan['loss']['teacherSampleCount'] or int((~mask).sum())!=plan['loss']['supervisedOnlyCount']:
        raise ValueError('Distillation cohort mismatch.')
    model,_=load_model(root/plan['baseline']['path'])
    print('Preparing or reusing training-only teacher and validation caches.',flush=True)
    targets=teacher_cache(model,images,mask,config,run,signature)
    baseline=reference_records(plan,root)
    val_pixels=validation_cache(dataset,run,baseline,root)
    metadata={'formatVersion':1,'architecture':ARCHITECTURE,'classOrder':list(CLASSES),'preprocessing':PREPROCESSING,
              'dataVersion':signature,'trainingConfig':config,'classWeights':plan['loss']['classWeights'],
              'environment':environment,'distillation':{'teacherSha256':plan['baseline']['sha256'],
                  'maskSha256':hashlib.sha256(mask.tobytes()).hexdigest(),'trainingSquares':int(mask.sum()),
                  'temperature':config['distillationTemperature'],'weight':config['distillationWeight']},
              'selection':'Frozen per-domain and per-stratum safety gates; rank safe epochs only; earlier tie.',
              'loss':plan['loss']['name']}

    def evaluate(candidate):
        records=validation_predictions(candidate,val_pixels,baseline,config['batchSize'])
        return assess_accuracy(baseline,records,minimum_photo_gain=plan['acceptance']['minimumPhotoExactGain']),records

    result=run_epochs(model,(images,labels),targets,mask,evaluate,config,run,metadata,resume=resume)
    if digest(root/plan['baseline']['path'])!=plan['baseline']['sha256']:raise ValueError('Baseline weights changed.')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=DEFAULT_PLAN)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args(argv)
    result=execute(args.plan,resume=args.resume)
    print(json.dumps({'completedEpochs':result['completedEpochs'],'decision':result['decision']}))


if __name__=='__main__':main()
