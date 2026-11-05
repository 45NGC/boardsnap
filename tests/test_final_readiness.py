"""External installation readiness must not silently become final acceptance."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.check_final_readiness import assess

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    read = lambda name: json.loads((ROOT/name).read_text())
    return (read('data/manifests/screen-preview-v1.json'),
            read('data/reports/photo-pipeline-validation-v2.json'),
            read('data/reports/digital-regressions-anisotropic-candidate.json'),
            {m: read(f'data/reports/screen-preview-{m}-cpu-v1.json') for m in ('digital', 'photo')},
            {m: read(f'data/reports/screen-preview-{m}-installation-v1.json') for m in ('digital', 'photo')})


def test_passing_installation_and_cpu_do_not_approve_photo_quality():
    result = assess(*inputs())
    assert all(result['technicalChecksPassed'].values())
    assert result['photo']['exactBoards'] == 20
    assert result['photo']['images'] == 30
    assert not result['photo']['qualityReady']
    assert not result['finalAcceptanceGranted']
    assert not result['independentDataConsumed']


def test_historical_success_is_not_fresh_runtime_evidence():
    result = assess(*inputs())
    assert result['digital']['previousRegressionPassed']
    assert result['digital']['runtimeFilesDifferentFromPreviousRegression']
    assert not result['digital']['currentRegressionEvidenceComplete']


def test_even_perfect_consulted_results_never_become_final_acceptance():
    policy, photo, digital, cpu, installation = deepcopy(inputs())
    photo['summary']['automaticExactBoards'] = photo['summary']['images']
    for entry in photo['byCategory'].values():
        entry['automaticExactBoards'] = entry['images']
    result = assess(policy, photo, digital, cpu, installation)
    assert result['photo']['qualityReady']
    assert not result['finalAcceptanceGranted']
    assert not result['finalEvaluationExecuted']
    assert not result['independentCorpus']['reviewed']


def test_absent_photo_category_fails_closed():
    policy, photo, digital, cpu, installation = deepcopy(inputs())
    del photo['byCategory']['video']
    result = assess(policy, photo, digital, cpu, installation)
    gate = next(g for g in result['photo']['gatesOnConsultedData'] if g['name'].endswith('/video'))
    assert not gate['passed']


@pytest.mark.parametrize('mode', ['digital', 'photo'])
def test_wrong_model_evidence_is_rejected(mode):
    policy, photo, digital, cpu, installation = deepcopy(inputs())
    cpu[mode]['modelSha256'] = 'other-model'
    with pytest.raises(ValueError, match='different weights'):
        assess(policy, photo, digital, cpu, installation)
