"""Frozen releases and measurements fail closed on missing or modified evidence."""

import json
from pathlib import Path

import pytest

from tools.benchmark_preview import performance_passed
from tools.prepare_screen_preview import check_frozen, runtime_files, write_new
from tools.verify_preview import sha256, verify


def make_preview(tmp_path):
    (tmp_path/'model.pt').write_bytes(b'weights')
    data = {'schemaVersion': 1, 'status': 'preview-not-accepted', 'releaseId': 'test',
            'files': {'model.pt': sha256(tmp_path/'model.pt')}}
    (tmp_path/'release.json').write_text(json.dumps(data))
    return sha256(tmp_path/'release.json')


def test_checksum_requires_independent_manifest_digest(tmp_path):
    expected = make_preview(tmp_path)
    assert verify(tmp_path, expected)['releaseId'] == 'test'
    (tmp_path/'model.pt').write_bytes(b'changed')
    with pytest.raises(ValueError, match='Checksum mismatch'):
        verify(tmp_path, expected)


def test_modified_manifest_cannot_authorize_modified_weights(tmp_path):
    expected = make_preview(tmp_path)
    (tmp_path/'release.json').write_text('{}')
    with pytest.raises(ValueError, match='independently recorded'):
        verify(tmp_path, expected)


def test_unlisted_file_is_not_silently_distributed(tmp_path):
    expected = make_preview(tmp_path)
    (tmp_path/'unexpected.pt').touch()
    with pytest.raises(ValueError, match='Unlisted'):
        verify(tmp_path, expected)


def test_release_cannot_verify_files_outside_its_directory(tmp_path):
    make_preview(tmp_path)
    data = json.loads((tmp_path/'release.json').read_text())
    data['files'] = {'../outside.pt': 'unused'}
    (tmp_path/'release.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='escapes'):
        verify(tmp_path, sha256(tmp_path/'release.json'))


def test_frozen_runtime_includes_added_files_and_assets(tmp_path):
    package = tmp_path/'src/boardsnap'
    package.mkdir(parents=True)
    (package/'__init__.py').touch()
    (package/'template.png').write_bytes(b'asset')
    (tmp_path/'pyproject.toml').write_text('version = "test"')
    policy = {'runtimeSha256': runtime_files(tmp_path), 'models': {}}
    check_frozen(policy, tmp_path)
    (package/'new.py').touch()
    with pytest.raises(ValueError, match='Runtime'):
        check_frozen(policy, tmp_path)
    (package/'new.py').unlink()
    (package/'template.png').write_bytes(b'altered')
    with pytest.raises(ValueError, match='Runtime'):
        check_frozen(policy, tmp_path)


def test_frozen_weights_cannot_be_replaced(tmp_path):
    (tmp_path/'src/boardsnap').mkdir(parents=True)
    (tmp_path/'pyproject.toml').touch()
    weights = tmp_path/'weights.pt'
    weights.write_bytes(b'old')
    policy = {'runtimeSha256': runtime_files(tmp_path),
              'models': {'photo': {'source': 'weights.pt', 'sha256': sha256(weights)}}}
    weights.write_bytes(b'new')
    with pytest.raises(ValueError, match='model'):
        check_frozen(policy, tmp_path)


def test_policy_cannot_be_overwritten(tmp_path):
    path = tmp_path/'policy.json'
    write_new(path, {'version': 1})
    with pytest.raises(FileExistsError):
        write_new(path, {'version': 2})
    assert json.loads(path.read_text()) == {'version': 1}


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, True, None, 6001])
def test_invalid_or_slow_measurement_fails(value):
    report = {'warm': {'samples': 40, 'p95Milliseconds': value},
              'coldMilliseconds': 1000, 'peakRssMiB': 300}
    limits = {'minimumSamples': 40, 'warmP95Ms': 1000, 'coldMs': 5000, 'peakRssMiB': 1024}
    assert not performance_passed(report, limits)


def test_insufficient_samples_fail_despite_good_latency():
    limits = {'minimumSamples': 40, 'warmP95Ms': 1000, 'coldMs': 5000, 'peakRssMiB': 1024}
    report = {'warm': {'samples': 40, 'p95Milliseconds': 100}, 'coldMilliseconds': 1000, 'peakRssMiB': 300}
    assert performance_passed(report, limits)
    report['warm']['samples'] = 1
    assert not performance_passed(report, limits)


@pytest.mark.parametrize('change', ['policy', 'slow'])
def test_seal_rechecks_policy_and_performance_instead_of_trusting_flags(tmp_path, monkeypatch, change):
    from tools import prepare_screen_preview as module
    monkeypatch.setattr(module, 'MODELS', {'digital': 'unused'})
    monkeypatch.setattr(module, 'check_frozen', lambda *_: None)
    (tmp_path/'dependencies').mkdir()
    (tmp_path/'dependencies/boardsnap-test.whl').touch()
    reports = tmp_path/'reports'
    reports.mkdir()
    policy = {'runtimeSha256': {}, 'models': {'digital': {'sha256': 'weights'}},
              'cpu': {'digital': {'minimumSamples': 40, 'warmP95Ms': 1000, 'coldMs': 5000, 'peakRssMiB': 1024}}}
    write_new(tmp_path/'policy.json', policy)
    write_new(tmp_path/'model-bundles.json', {})
    policy_hash = sha256(tmp_path/'policy.json')
    write_new(reports/'digital-installation.json', dict(passed=True, modelSha256='weights', policySha256=policy_hash))
    cpu = {'warm': {'samples': 40, 'p95Milliseconds': 100}, 'coldMilliseconds': 1000,
           'peakRssMiB': 300, 'performancePassed': True, 'modelSha256': 'weights', 'policySha256': policy_hash}
    if change == 'policy':
        cpu['policySha256'] = 'another-policy'
    else:
        cpu['warm']['p95Milliseconds'] = 9999
    write_new(reports/'digital-cpu.json', cpu)
    with pytest.raises(ValueError, match='policy' if change == 'policy' else 'CPU gates'):
        module.seal(tmp_path, tmp_path/'report.json')
    assert not (tmp_path/'release.json').exists()
