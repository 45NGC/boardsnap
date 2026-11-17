"""Measure fixed local-trial models in sequential fresh CPU processes with resume."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from tools.trial_config import ROOT, DEFAULT_CONFIG, select_model, sha256

RUN = ROOT / '.cache/local-trial-cpu-v1'


def classifier_worker(model, archive, recipe):
    started = time.perf_counter()
    import resource
    import platform
    import torch
    import numpy as np
    from boardsnap.neural import load_model, preprocess
    from tools.evaluate_neural import timing
    torch.set_num_threads(recipe['threads'])
    with np.load(archive, allow_pickle=False) as data:
        images = data['images']
    if images.shape != (64,64,64,3):
        raise ValueError('Expected one verified board, not the full corpus.')
    network, _ = load_model(model)
    cold = (time.perf_counter()-started)*1000
    values=[]
    with torch.inference_mode():
        for _ in range(recipe['warmupsPerTrial']): network(preprocess(images))
        for _ in range(recipe['measuredBatchesPerTrial']):
            start=time.perf_counter();network(preprocess(images));values.append(time.perf_counter()-start)
    return {'warm':timing(values),'loadAndImportMilliseconds':cold,
            'peakRssMiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            'scope':'One model and one 64-square board; preprocessing plus classifier only, fresh Linux process.',
            'environment':{'python':platform.python_version(),'torch':str(torch.__version__),'threads':torch.get_num_threads()}}


def worker(request):
    model=ROOT/request['model']['path']
    if sha256(model)!=request['model']['sha256']:raise ValueError('Model checksum differs.')
    if request['kind']=='classifier':
        archive=ROOT/request['archive']['path']
        if sha256(archive)!=request['archive']['sha256']:raise ValueError('Input archive changed.')
        return classifier_worker(model,archive,request['recipe'])
    from tools.benchmark_preview import validation_samples
    from tools.benchmark_cpu import benchmark
    samples,provenance=validation_samples(request['mode'])
    result=benchmark(model,samples,input_type=request['mode'])
    result.update(samples=samples,provenance=provenance)
    return result


def checked_worker(request, name):
    path=RUN/(name+'.json');request_path=RUN/(name+'-request.json')
    if path.exists():
        result=json.loads(path.read_text())
        if result['request']!=request:raise ValueError('Measurement recipe changed; preserve old results.')
        return result['measurement']
    request_path.write_text(json.dumps(request,indent=2)+'\n')
    process=subprocess.run([sys.executable,'-m','tools.benchmark_local_trial','--worker',str(request_path)],
                            cwd=ROOT,capture_output=True,text=True,timeout=300,
                            env={**os.environ,'OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4'})
    if process.returncode or process.stderr:raise ValueError('CPU worker failed: '+process.stderr)
    result=json.loads(process.stdout)
    # Save only after the complete measurement; resume never repeats completed workers.
    path.write_text(json.dumps({'request':request,'measurement':result},indent=2)+'\n')
    return result


def aggregate(trials):
    return {'medianMilliseconds':statistics.median(t['warm']['medianMilliseconds'] for t in trials),
            'p95Milliseconds':statistics.median(t['warm']['p95Milliseconds'] for t in trials),
            'peakRssMiB':statistics.median(t['peakRssMiB'] for t in trials)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--worker',type=Path)
    args=parser.parse_args()
    if args.worker:
        print(json.dumps(worker(json.loads(args.worker.read_text()))));return
    config=json.loads(DEFAULT_CONFIG.read_text())
    for mode in ('digital','photo'):select_model(DEFAULT_CONFIG,mode)
    reference=config['photoReference']
    if sha256(ROOT/reference['path'])!=reference['sha256']:raise ValueError('Photo reference changed.')
    runtime={str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))}
    helpers=('tools/benchmark_local_trial.py','tools/benchmark_cpu.py','tools/benchmark_preview.py','tools/trial_config.py')
    code={name:sha256(ROOT/name) for name in helpers}
    shared={'configSha256':sha256(DEFAULT_CONFIG),'runtime':runtime,'benchmarkCode':code}
    RUN.mkdir(parents=True,exist_ok=True)
    # Classifier comparisons use the exact board required by the frozen mixed policy.
    manifest=ROOT/'.cache/mixed-training-v1/validation.jsonl'
    with manifest.open() as stream:
        first=next(json.loads(s) for s in stream if json.loads(s)['sourceDataset']=='.cache/phone-targeted-training-v1')
    archive=Path(first['sourceDataset'])/first['row']['array']
    archive_info={'path':str(archive),'sha256':first['row']['arraySha256'],'image':first['row']['image']}
    classifiers={}
    for label,model in [('photoReference',reference),('photoCandidate',config['models']['photo'])]:
        trials=[]
        for n in range(config['classifierComparison']['freshProcessTrialsPerModel']):
            req={**shared,'kind':'classifier','model':model,'archive':archive_info,'recipe':config['classifierComparison']}
            trials.append(checked_worker(req,f'classifier-{label}-{n+1}'))
            print(f'Completed classifier {label} trial {n+1}',flush=True)
        classifiers[label]={'trials':trials,'aggregate':aggregate(trials)}
    a,b=(classifiers[k]['aggregate'] for k in ('photoReference','photoCandidate'))
    ratios={k:b[k]/a[k] for k in a}
    limits=config['classifierComparison']
    relative_passed=(ratios['medianMilliseconds']<=limits['maximumMedianLatencyRatio']
                     and ratios['p95Milliseconds']<=limits['maximumP95LatencyRatio']
                     and ratios['peakRssMiB']<=limits['maximumPeakRssRatio'])
    pipeline={}
    from tools.benchmark_preview import performance_passed
    for mode,model in config['models'].items():
        # The worker imports ML only after starting its own cold timer.
        req={**shared,'kind':'pipeline','mode':mode,'model':model}
        result=checked_worker(req,f'pipeline-{mode}')
        result['performancePassed']=performance_passed(result,config['cpu'][mode])
        pipeline[mode]=result
        print(f'Completed {mode} pipeline: {result["warm"]}',flush=True)
    if runtime!={str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))}:
        raise ValueError('Runtime changed during measurement.')
    if any(sha256(ROOT/p)!=h for p,h in code.items()):raise ValueError('Benchmark implementation changed.')
    report={'schemaVersion':1,'configuration':str(DEFAULT_CONFIG.relative_to(ROOT)),**shared,
            'scope':'Existing consulted validation only; one full pipeline pass per mode, three isolated classifier processes per photographic model. No training or independent final evaluation.',
            'finalEvaluationAccessed':False,'trainingRun':False,'models':config['models'],'photoReference':reference,
            'classifier':classifiers,'classifierRatios':ratios,'classifierRelativePerformancePassed':relative_passed,
            'pipeline':pipeline,'qualityAccepted':False,'status':'local-trial-not-accepted',
            'limitations':['Measurements apply to this Linux CPU, not a phone or HTTP service.',
                           'Full-pipeline p95 describes heterogeneous validation images, not repeated latency of each image.',
                           'Peak RSS includes imports, image decoding and allocator retention in a single process.',
                           'Performance passing does not supersede known quality-gate failures.']}
    output=ROOT/'data/reports/local-trial-cpu-v1.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'classifierRelativePerformancePassed':relative_passed,'pipelinePerformancePassed':{m:r['performancePassed'] for m,r in pipeline.items()}}))


if __name__=='__main__':main()
