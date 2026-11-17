"""Overlap checks distinguish equal positions, known games and unknown origins."""

import pytest

from tools.audit_targeted_photo_overlap import compare_position, source_key

pytestmark = pytest.mark.unit


def session(source=None):
    return {'label': {'piecePlacement': 'k7/8/8/8/8/8/8/6NK'},
            'source': source or {}}


def test_same_position_detected_without_source_identity():
    s = session()
    result = compare_position(s, [{'id': 'reference', 'label': s['label'], 'source': {}}])
    assert result['exactPositionMatches'] == ['reference']
    assert result['positionFamilyMatches'] == ['reference']
    assert result['knownSourceMatches'] == []
    assert result['minimumDifferentSquares'] == 0


def test_reflected_position_detected_despite_different_placement():
    result = compare_position(session(), [{'id': 'reflection', 'piecePlacement': '7k/8/8/8/8/8/8/KN6'}])
    assert result['exactPositionMatches'] == []
    assert result['positionFamilyMatches'] == ['reflection']


def test_same_known_game_detected_even_when_pieces_differ():
    result = compare_position(session({'platform': 'chesscom', 'gameId': '123'}), [
        {'id': 'related', 'piecePlacement': '8/8/8/8/8/8/8/8',
         'source': {'category': 'chesscom', 'gameId': 123}},
        {'id': 'other-platform', 'piecePlacement': '8/8/8/8/8/8/8/8',
         'source': {'category': 'lichess', 'gameId': '123'}},
    ])
    assert result['knownSourceMatches'] == ['related']
    assert result['positionFamilyMatches'] == []


@pytest.mark.parametrize('source', [{}, {'gameId': None}, {'category': 'video', 'videoId': None}])
def test_unknown_sources_never_become_shared_identity(source):
    assert source_key(source) is None
    assert compare_position(session(source), [{'id': 'unknown', 'source': source}])['knownSourceMatches'] == []
