"""Only empty-label teacher conflicts may change the frozen experiment."""
from copy import deepcopy

import numpy as np
import pytest

from tools.train_mixed_empty_guard import check_control_plan, guarded_teacher_mask


def test_guard_excludes_only_old_empty_teacher_pieces_without_mutation():
    old = np.array([True, True, True, False, True])
    labels = np.array([0, 0, 7, 0, 0])
    targets = np.zeros((5, 13), np.float32)
    targets[[0, 1, 2, 4], [11, 0, 10, 0]] = 1
    saved = targets.copy()
    result = guarded_teacher_mask(old, labels, targets)
    assert result.tolist() == [False, True, True, False, True]
    assert old.tolist() == [True, True, True, False, True]
    assert labels.tolist() == [0, 0, 7, 0, 0]
    assert np.array_equal(saved, targets)


def test_guard_rejects_invalid_teacher_targets():
    with pytest.raises(ValueError):
        guarded_teacher_mask(np.ones(1, dtype=bool), np.array([0]), np.zeros((1, 13)))


def test_only_mask_intervention_can_differ_and_control_is_not_overwritten():
    control = {'runDirectory': 'old', 'trainingConfig': {'epochs': 12}, 'acceptance': {'minimum': 20}}
    plan = deepcopy(control)
    plan.update(runDirectory='new', intervention={'mask': True})
    check_control_plan(plan, control)
    plan['acceptance']['minimum'] = 19
    with pytest.raises(ValueError, match='besides'):
        check_control_plan(plan, control)
    with pytest.raises(ValueError, match='overwrite'):
        check_control_plan(control, control)
