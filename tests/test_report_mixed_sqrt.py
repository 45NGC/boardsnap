"""Track omissions separately from type/color mistakes to expose weight tradeoffs."""
from tools.report_mixed_sqrt import omission_metrics


def test_pawn_omissions_exclude_wrong_type_and_nonpawn_errors():
    expected = [1, 7, 1, 7, 11, 0] + [0] * 58
    predictions = [0, 0, 7, 7, 0, 8] + [0] * 58
    result = omission_metrics([{'image': 'one', 'expected': expected, 'predictions': predictions}])
    assert result['pawnSquares'] == 4
    assert result['missedPawns'] == 2
    assert result['wrongPawnTypeOrColor'] == 1
    assert result['missedPieces'] == 3
    assert result['falsePieces'] == 1
