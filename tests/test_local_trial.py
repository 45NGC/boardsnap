"""Explicit mode selection and pinned weights must not silently fall back."""
import json
import subprocess

import pytest

from tools.trial_config import select_model, sha256
from tools.try_model import main
from tools.benchmark_local_trial import aggregate


def trial(tmp_path):
    models={}
    for mode in ('digital','photo'):
        path=tmp_path/(mode+'.pt');path.write_bytes(mode.encode())
        models[mode]={'path':path.name,'sha256':sha256(path)}
    config=tmp_path/'trial.json';config.write_text(json.dumps({'schemaVersion':1,'status':'local-trial-not-accepted','models':models}))
    return config


def test_explicit_models_and_checksum_failure(tmp_path):
    config=trial(tmp_path)
    assert select_model(config,'photo',tmp_path).name=='photo.pt'
    assert select_model(config,'digital',tmp_path).name=='digital.pt'
    (tmp_path/'photo.pt').write_bytes(b'changed')
    with pytest.raises(ValueError):select_model(config,'photo',tmp_path)
    with pytest.raises(ValueError):select_model(config,'auto',tmp_path)


def test_outside_repository_rejected(tmp_path):
    config=trial(tmp_path);r=json.loads(config.read_text());r['models']['photo']['path']='../outside.pt';config.write_text(json.dumps(r))
    with pytest.raises(ValueError):select_model(config,'photo',tmp_path)


def test_launcher_forwards_exact_mode_orientation_and_cli_status(monkeypatch):
    calls=[]
    monkeypatch.setattr('tools.try_model.select_model',lambda *a:'/pinned/photo.pt')
    def run(command,**kwargs):
        calls.append((command,kwargs));return subprocess.CompletedProcess(command,1)
    monkeypatch.setattr('tools.try_model.subprocess.run',run)
    assert main(['image with spaces.jpg','--input-type','photo','--orientation','black-bottom'])==1
    command,kwargs=calls[0]
    assert command[-6:]==['--model','/pinned/photo.pt','--input-type','photo','--orientation','black-bottom']
    assert 'image with spaces.jpg' in command and not kwargs.get('shell')


def test_configuration_error_is_structured_and_never_invokes_cli(monkeypatch,capsys):
    def bad(*args):raise ValueError('Checksum mismatch.')
    monkeypatch.setattr('tools.try_model.select_model',bad)
    assert main(['x','--input-type','digital','--orientation','white-bottom'])==1
    assert json.loads(capsys.readouterr().out)['error']['code']=='CONFIGURATION_ERROR'


def test_fresh_process_aggregation_uses_median_of_trial_statistics():
    trials=[{'warm':{'medianMilliseconds':v,'p95Milliseconds':v*2},'peakRssMiB':v*10} for v in (1,100,3)]
    assert aggregate(trials)=={'medianMilliseconds':3,'p95Milliseconds':6,'peakRssMiB':30}
