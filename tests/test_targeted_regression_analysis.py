"""Classify saved prediction changes without rerunning model inference."""
import pytest
from tools.analyze_targeted_regressions import changes

pytestmark = pytest.mark.unit


def test_recovery_regression_and_changed_error_are_distinct():
    expected = [0]*64
    old = [0]*64
    new = [0]*64
    new[3] = 11  # empty d8 becomes black queen
    old[8] = 1  # wrong pawn recovered
    old[63], new[63] = 2, 3  # wrong knight becomes wrong bishop
    result = changes(expected, old, new)
    assert [(r['square'],r['change']) for r in result] == [
        ('d8','regression'),('a7','recovery'),('h1','changed-error')]
    assert result[0]['expected']=='empty' and result[0]['candidate']=='q'


def test_unchanged_errors_are_not_counted_as_regressions():
    assert changes([0]*64,[1]*64,[1]*64)==[]


def test_reject_unaligned_board_sizes():
    with pytest.raises(ValueError):
        changes([0]*63,[0]*64,[0]*64)
