"""A paired comparison must expose trades hidden by identical aggregate accuracy."""

from copy import deepcopy

import pytest

from tools.report_mixed_empty_guard import compare


def records():
    expected = [0] * 64
    return [{'image': name, 'expected': expected.copy(), 'predictions': expected.copy()} for name in ('a', 'b')]


def test_equal_board_accuracy_still_records_gained_and_lost_cases():
    old = records()
    old[0]['predictions'][0] = 1
    new = records()
    new[1]['predictions'][0] = 1
    result = compare(old, new)
    assert result['control']['exactBoards'] == result['candidate']['exactBoards'] == 1
    assert result['gainedExactBoards'] == ['a']
    assert result['lostExactBoards'] == ['b']
    assert len(result['changedBoards']) == 2


def test_mismatched_labels_cannot_be_reported_as_an_improvement():
    old = records()
    new = deepcopy(old)
    new[0]['expected'][0] = 1
    with pytest.raises(ValueError, match='Unaligned'):
        compare(old, new)
