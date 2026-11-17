"""Saved-target audit must distinguish exposure, identity and supervision scope."""

import numpy as np
import pytest

from tools.review_mixed_training import audit_teacher


def fixture_data():
    refs = [{'pool': pool, 'row': {'split': 'training', 'image': str(i),
                                 'cells': [{'classId': 0, 'square': 'd8'}] * 64}}
            for i, pool in enumerate(['old', 'new'])]
    targets = np.zeros((3, 13), dtype=np.float32)
    targets[:2, 11] = 0.9
    targets[:2, 0] = 0.1
    return np.zeros(3, dtype=int), targets, np.array([0, 0, 1]), np.array([0, 0, 0]), refs


def test_repeated_false_piece_and_unsupervised_new_targets():
    result = audit_teacher(*fixture_data(), ['old'])
    assert result['teacherSamples'] == 2
    assert result['conflictingSamples'] == 2
    assert result['distinctConflictingCells'] == 1
    assert result['falsePieceSamples'] == 2
    assert result['distinctFalsePieceCells'] == 1
    assert result['conflicts'][0]['teacher'] == 'q'
    assert result['conflicts'][0]['exposures'] == 2
    assert next(c for c in result['coverage'] if c['pool'] == 'new')['teacherConflictingSamples'] == 0


def test_validation_cannot_enter_teacher_audit():
    args = fixture_data()
    args[-1][0]['row']['split'] = 'validation'
    with pytest.raises(ValueError, match='training records'):
        audit_teacher(*args, ['old'])


def test_inconsistent_repeated_targets_rejected():
    args = fixture_data()
    args[1][1, 11], args[1][1, 0] = 0.8, 0.2
    with pytest.raises(ValueError, match='inconsistent targets'):
        audit_teacher(*args, ['old'])


def test_label_mismatch_rejected_even_if_teacher_is_correct():
    args = fixture_data()
    args[0][2] = 1
    with pytest.raises(ValueError, match='differs from annotation'):
        audit_teacher(*args, ['old'])
