"""Verify an isolated wheel installation and model loading outside the repository."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile

from PIL import Image

from tools.model_bundle import verify_bundle
from tools.neural_data import digest


def check_installation(python, wheel, bundle, bundle_hash, dataset):
    manifest=verify_bundle(bundle,bundle_hash)
    samples={}
    metadata=json.loads((dataset/'dataset.json').read_text())
    for line in (dataset/'verified.jsonl').open():
        row=json.loads(line)
        if row['split']=='validation' and row['cohort']=='expansion' and row['conditions']==['clean']:
            samples.setdefault((row['style']['platform'],row['orientation']),row)
    if len(samples)!=4:raise ValueError('Need validation samples from both platforms and views.')
    env=dict(os.environ,BOARDSNAP_MODEL=str((bundle/'model.pt').resolve()),OMP_NUM_THREADS='1')
    env.pop('PYTHONPATH',None)
    results=[]
    with tempfile.TemporaryDirectory(prefix='boardsnap-installed-',dir='/tmp') as temporary:
        directory=Path(temporary)
        code="import json,sys,boardsnap; from importlib.metadata import distributions; print(json.dumps({'prefix':sys.prefix,'basePrefix':sys.base_prefix,'module':boardsnap.__file__,'packages':{d.metadata['Name']:d.version for d in distributions()}}))"
        info=json.loads(subprocess.run([str(python),'-I','-c',code],cwd=directory,env=env,check=True,capture_output=True,text=True).stdout)
        if info['prefix']==info['basePrefix'] or not Path(info['module']).resolve().is_relative_to(python.parent.parent):
            raise ValueError('Expected a wheel installed in an isolated environment.')
        site_packages=Path(info['module']).parent.parent
        with ZipFile(wheel) as archive:
            for name in archive.namelist():
                if name.startswith('boardsnap/') and not name.endswith('/'):
                    if (site_packages/name).read_bytes()!=archive.read(name):
                        raise ValueError('Installed runtime/assets differ from the specified wheel.')
        def run(path,view,expected,exit_code,extra=()):
            process=subprocess.run([str(python.parent/'boardsnap'),str(path),'--orientation',view,*extra],cwd=directory,
                                   env=env,capture_output=True,text=True,timeout=60)
            result=json.loads(process.stdout)
            passed=process.returncode==exit_code and process.stderr=='' and result==expected
            results.append({'input':path.name,'orientation':view,'passed':passed,'returnCode':process.returncode,
                            'stdout':process.stdout,'stderr':process.stderr})
        for index,row in enumerate(samples.values()):
            target=directory/f'image-{index}.png'
            source=Path(metadata['sourceRoot'])/row['image']
            if digest(source)!=row['sha256']:raise ValueError('Validation screenshot changed.')
            target.write_bytes(source.read_bytes())
            run(target,row['orientation'],{'piecePlacement':row['piecePlacement']},0)
        blank=directory/'blank.png'
        with Image.new('RGB',(512,512),'white') as image:image.save(blank)
        run(blank,'white-bottom',{'error':{'code':'BOARD_NOT_FOUND','message':'No supported chessboard was detected in the image.'}},1)
        empty=directory/'empty.png'; empty.write_bytes(b'')
        run(empty,'white-bottom',{'error':{'code':'INVALID_IMAGE','message':'The image file is empty.'}},1)
        root=Path(__file__).resolve().parents[1]
        legacy=directory/'legacy.png'
        legacy.write_bytes((root/'data/tuning/lichess-cburnett-brown-v1/pos-004-white.png').read_bytes())
        run(legacy,'white-bottom',{'piecePlacement':'8/8/8/8/8/8/8/8'},0,('--profile','lichess-cburnett-brown-v1'))
        usage=subprocess.run([str(python.parent/'boardsnap'),str(blank),'--orientation','invalid'],cwd=directory,env=env,capture_output=True,text=True,timeout=30)
        results.append({'input':'invalid orientation','passed':usage.returncode==2 and usage.stdout=='' and bool(usage.stderr)})
        process=subprocess.run([str(python),'-m','boardsnap','--help'],cwd=directory,env=env,capture_output=True,text=True,timeout=30)
        results.append({'input':'python -m boardsnap --help','passed':process.returncode==0 and '--model' in process.stdout and not process.stderr})
    return {'passed':all(r['passed'] for r in results),'modelSha256':manifest['sha256'],
            'wheelSha256':digest(wheel),'bundleManifestSha256':bundle_hash,
            'scope':'fresh venv without system site packages; non-editable wheel; standalone CLI and module from /tmp; validation only',
            'installation':info,'checks':results,'verificationCodeSha256':digest(Path(__file__))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Keep the venv path, not the resolved system-python symlink.
    report=check_installation(args.python.absolute(),args.wheel,args.bundle,args.manifest_sha256,args.dataset)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Clean installation checks:', 'passed' if report['passed'] else 'failed')
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
