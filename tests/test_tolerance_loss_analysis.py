"""Check that the focused diagnosis remains traceable to its frozen comparison."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'data/reports'
pytestmark = pytest.mark.unit


def reports():
    source = REPORTS / 'neural-tolerance-validation.json'
    analysis = json.loads((REPORTS / 'neural-tolerance-loss-analysis.json').read_text())
    assert analysis['comparisonSha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    return json.loads(source.read_text()), analysis


def test_diagnosis_covers_exactly_the_existing_paired_losses():
    comparison, analysis = reports()
    expected = {(scenario, image) for scenario, pairs in comparison['pairedModelComparison'].items()
                for image in pairs['baselineCorrectCandidateWrong']}
    actual = [(row['scenario'], row['image']) for row in analysis['cases']]
    assert len(actual) == len(set(actual)) == 11
    assert set(actual) == expected
    assert analysis['models'] == comparison['models']
    assert analysis['datasetSha256'] == comparison['datasetSha256']
    assert not analysis['trainingPerformed'] and not analysis['productionChanged']
    assert not analysis['independentFinalEvaluation']


def test_reported_error_pattern_and_original_controls_are_supported():
    _, analysis = reports()
    crops = set()
    for row in analysis['cases']:
        assert row['originalCorrect'] == [True, True]
        assert row['detectedBox'] == row['originalBox']
        assert len(row['wrongCells']) == 1
        cell = row['wrongCells'][0]
        assert (cell['label'], cell['predicted'], cell['background']) == ('B', 'Q', 'light')
        assert cell['margins']['v8']['perturbed'] > 0
        assert cell['margins']['candidate']['perturbed'] < 0
        assert cell['margins']['candidate']['reference'] > 0
        crops.add(cell['cropSha256'])
    assert len(crops) == analysis['summary']['uniqueWrongCropPixels'] == 4
    assert len({r['positionId'] for r in analysis['cases']}) == 4
    assert len({r['groupId'] for r in analysis['cases']}) == 2


def test_alternative_probe_covers_both_losses_and_gains_without_claiming_full_validation():
    comparison, analysis = reports()
    probe = analysis['halfStepProbe']
    for cohort, field in [('losses', 'baselineCorrectCandidateWrong'),
                          ('gains', 'baselineWrongCandidateCorrect')]:
        expected = {(scenario, image) for scenario, pairs in comparison['pairedModelComparison'].items()
                    for image in pairs[field]}
        actual = [(r['scenario'], r['image']) for r in probe['results'][cohort]]
        assert len(actual) == len(set(actual))
        assert set(actual) == expected
        assert all(r['exact'] == (r['wrongSquares'] == []) for r in probe['results'][cohort])
    assert sum(r['exact'] for r in probe['results']['losses']) == probe['recoveredLosses'] == 2
    assert sum(not r['exact'] for r in probe['results']['gains']) == probe['lostGains'] == 400
    assert 'not a complete validation' in probe['scope']
