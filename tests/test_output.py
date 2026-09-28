"""Behavioral specification for the boardsnap.output.build_result API."""

from copy import deepcopy

import pytest


pytestmark = pytest.mark.unit


def _build_result(board):
    # Import during execution so all cases can be collected before implementation.
    from boardsnap.output import build_result

    return build_result(board)


def _board(*ranks):
    """Create a test matrix; dots are fixture notation for empty squares only."""
    assert len(ranks) == 8
    assert all(len(rank) == 8 for rank in ranks)
    return [[None if symbol == "." else symbol for symbol in rank] for rank in ranks]


@pytest.fixture
def empty_board():
    return [[None] * 8 for _ in range(8)]


@pytest.mark.parametrize(
    ("ranks", "expected"),
    [
        pytest.param(
            (
                "rnbqkbnr",
                "pppppppp",
                "........",
                "........",
                "........",
                "........",
                "PPPPPPPP",
                "RNBQKBNR",
            ),
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            id="starting-position",
        ),
        pytest.param(
            ("........",) * 8,
            "8/8/8/8/8/8/8/8",
            id="empty-board-without-kings",
        ),
        pytest.param(
            (
                "r......k",
                "..p.....",
                "....N...",
                "........",
                ".B......",
                "......q.",
                "P.......",
                "...K...R",
            ),
            "r6k/2p5/4N3/8/1B6/6q1/P7/3K3R",
            id="asymmetric-position",
        ),
    ],
)
def test_builds_exact_result_without_additional_fen_fields(ranks, expected):
    result = _build_result(_board(*ranks))

    assert isinstance(result, dict)
    assert result == {"piecePlacement": expected}


def test_preserves_all_twelve_piece_symbols():
    board = _board("PNBRQKpn", "brqk....", *("........",) * 6)

    assert _build_result(board) == {
        "piecePlacement": "PNBRQKpn/brqk4/8/8/8/8/8/8",
    }


def test_serializes_a_full_board_without_enforcing_chess_legality():
    board = _board(*("PNBRQKpn",) * 8)

    assert _build_result(board) == {
        "piecePlacement": (
            "PNBRQKpn/PNBRQKpn/PNBRQKpn/PNBRQKpn/"
            "PNBRQKpn/PNBRQKpn/PNBRQKpn/PNBRQKpn"
        ),
    }


@pytest.mark.parametrize(
    ("rank", "expected_rank"),
    [
        ("PPPPPPP.", "PPPPPPP1"),
        ("PPPPPP..", "PPPPPP2"),
        ("PPPPP...", "PPPPP3"),
        ("PPPP....", "PPPP4"),
        ("PPP.....", "PPP5"),
        ("PP......", "PP6"),
        ("P.......", "P7"),
        ("........", "8"),
        (".......p", "7p"),
        (".P..n...", "1P2n3"),
        ("P.p.P.p.", "P1p1P1p1"),
    ],
)
def test_compresses_empty_runs_and_resets_at_rank_boundaries(rank, expected_rank):
    board = _board(rank, *("........",) * 7)

    assert _build_result(board) == {
        "piecePlacement": expected_rank + "/8/8/8/8/8/8/8",
    }


@pytest.mark.parametrize(
    ("row", "column", "expected"),
    [
        pytest.param(0, 0, "Q7/8/8/8/8/8/8/8", id="a8"),
        pytest.param(0, 7, "7Q/8/8/8/8/8/8/8", id="h8"),
        pytest.param(7, 0, "8/8/8/8/8/8/8/Q7", id="a1"),
        pytest.param(7, 7, "8/8/8/8/8/8/8/7Q", id="h1"),
    ],
)
def test_preserves_the_canonical_square_order(empty_board, row, column, expected):
    empty_board[row][column] = "Q"

    assert _build_result(empty_board) == {"piecePlacement": expected}


def test_accepts_tuple_rows_and_board():
    board = ((None,) * 8,) * 8

    assert _build_result(board) == {"piecePlacement": "8/8/8/8/8/8/8/8"}


def test_does_not_mutate_the_input_matrix(empty_board):
    empty_board[1][6] = "n"
    empty_board[5][2] = "K"
    original = deepcopy(empty_board)

    assert _build_result(empty_board) == {
        "piecePlacement": "8/6n1/8/8/8/2K5/8/8",
    }
    assert empty_board == original


@pytest.mark.parametrize("row_count", [0, 7, 9], ids=["empty", "too-few", "too-many"])
def test_rejects_incorrect_number_of_rows(row_count):
    board = [[None] * 8 for _ in range(row_count)]

    with pytest.raises(ValueError):
        _build_result(board)


@pytest.mark.parametrize(
    "row_lengths",
    [
        pytest.param([0, 8, 8, 8, 8, 8, 8, 8], id="empty-first-row"),
        pytest.param([8, 8, 8, 7, 8, 8, 8, 8], id="short-middle-row"),
        pytest.param([8, 8, 8, 8, 8, 8, 8, 9], id="long-last-row"),
        pytest.param([7, 9, 8, 8, 8, 8, 8, 8], id="ragged-but-64-squares"),
    ],
)
def test_rejects_incorrect_row_lengths(row_lengths):
    board = [[None] * length for length in row_lengths]

    with pytest.raises(ValueError):
        _build_result(board)


@pytest.mark.parametrize(
    "board",
    [
        pytest.param(None, id="none"),
        pytest.param(8, id="integer"),
        pytest.param("........", id="text"),
        pytest.param(b"........", id="bytes"),
        pytest.param({index: [None] * 8 for index in range(8)}, id="mapping"),
    ],
)
def test_rejects_invalid_board_types(board):
    with pytest.raises(TypeError):
        _build_result(board)


@pytest.mark.parametrize(
    "row",
    [
        pytest.param(None, id="none"),
        pytest.param(8, id="integer"),
        pytest.param("PPPPPPPP", id="text-with-valid-piece-symbols"),
        pytest.param({index: None for index in range(8)}, id="mapping"),
    ],
)
def test_rejects_invalid_row_types(empty_board, row):
    empty_board[7] = row

    with pytest.raises(TypeError):
        _build_result(empty_board)


@pytest.mark.parametrize(
    "symbol",
    [
        pytest.param("x", id="unknown-piece"),
        pytest.param(".", id="dot-is-not-an-empty-square"),
        pytest.param("1", id="fen-digit"),
        pytest.param("", id="empty-string"),
        pytest.param(" ", id="whitespace"),
        pytest.param("PP", id="multiple-pieces"),
        pytest.param("P\n", id="trailing-newline"),
        pytest.param("/", id="rank-separator"),
        pytest.param("\u2659", id="unicode-piece"),
    ],
)
def test_rejects_invalid_piece_symbols(empty_board, symbol):
    empty_board[7][7] = symbol

    with pytest.raises(ValueError):
        _build_result(empty_board)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="zero-is-not-an-empty-square"),
        pytest.param(1, id="integer"),
        pytest.param(False, id="false-is-not-an-empty-square"),
        pytest.param(True, id="boolean"),
        pytest.param([], id="list"),
        pytest.param({}, id="mapping"),
    ],
)
def test_rejects_invalid_cell_types(empty_board, value):
    empty_board[7][7] = value

    with pytest.raises(TypeError):
        _build_result(empty_board)
