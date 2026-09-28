"""Serialize already-classified chessboard squares into piece placement."""

_PIECE_SYMBOLS = frozenset("PNBRQKpnbrqk")
_Row = list[str | None] | tuple[str | None, ...]


def build_result(board: list[_Row] | tuple[_Row, ...]) -> dict[str, str]:
    """Build the output dictionary from an 8 by 8 matrix in a8-to-h1 order.

    The board and its rows must be lists or tuples. Cells contain a single
    FEN piece symbol or None for an empty square. The input is not modified;
    orientation and chess legality are not inferred or checked.

    Raises:
        TypeError: A board, row, or cell has an unsupported type.
        ValueError: Dimensions or string piece symbols are invalid.
    """
    if not isinstance(board, (list, tuple)):
        raise TypeError("Board must be a list or tuple of rows.")
    if len(board) != 8:
        raise ValueError("Board must contain exactly 8 rows.")

    ranks: list[str] = []
    for row_index, row in enumerate(board):
        if not isinstance(row, (list, tuple)):
            raise TypeError(f"board[{row_index}] must be a list or tuple.")
        if len(row) != 8:
            raise ValueError(f"board[{row_index}] must contain exactly 8 squares.")

        rank: list[str] = []
        empty_count = 0
        for column_index, piece in enumerate(row):
            if piece is None:
                empty_count += 1
                continue

            if not isinstance(piece, str):
                raise TypeError(
                    f"board[{row_index}][{column_index}] must be a piece symbol or None."
                )
            if piece not in _PIECE_SYMBOLS:
                raise ValueError(
                    f"Invalid piece symbol at board[{row_index}][{column_index}]: {piece!r}."
                )

            if empty_count:
                rank.append(str(empty_count))
                empty_count = 0
            rank.append(piece)

        if empty_count:
            rank.append(str(empty_count))
        ranks.append("".join(rank))

    return {"piecePlacement": "/".join(ranks)}
