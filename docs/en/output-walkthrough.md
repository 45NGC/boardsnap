# How output.py works

**English** | [Spanish](../es/output-walkthrough.md) · [Overview](README.md)

[output.py](../../src/boardsnap/output.py) receives a board whose pieces have
already been identified and ordered, validates its structure, and returns a
dictionary containing only `piecePlacement`, the first field of FEN.

This guide explains the implementation step by step. The
[output contract](output-contract.md) defines the expected behavior, and
[test_output.py](../../tests/test_output.py) contains its tests.

## 1. Allowed symbols

```python
_PIECE_SYMBOLS = frozenset("PNBRQKpnbrqk")
```

This constant contains the twelve valid characters for representing pieces:

| Piece | White | Black |
| --- | --- | --- |
| Pawn | `P` | `p` |
| Knight | `N` | `n` |
| Bishop | `B` | `b` |
| Rook | `R` | `r` |
| Queen | `Q` | `q` |
| King | `K` | `k` |

`frozenset` creates an immutable set. It allows membership checks against the
valid piece symbols: `"P" in _PIECE_SYMBOLS` is true, and
`"x" in _PIECE_SYMBOLS` is false.

The leading underscore indicates, by convention, that this is an internal
module detail. Python does not prevent access to it.

## 2. The row type

```python
_Row = list[str | None] | tuple[str | None, ...]
```

`_Row` is a type alias: a short name describing how a row can be represented.
It does not create a new class.

The `|` symbol means "or". A row can be a list or a tuple whose elements are
strings or `None`. For example:

```python
["r", None, None, None, None, None, None, "k"]
```

`None` represents an empty square. In `tuple[str | None, ...]`, the ellipsis
means a variable number of elements of those types. The requirement for eight
squares is checked inside the function.

## 3. The function definition

The function signature is shown below; the ellipsis in this snippet represents
the omitted body:

```python
def build_result(board: list[_Row] | tuple[_Row, ...]) -> dict[str, str]:
    ...
```

`board` can be a list or a tuple of rows. The function returns a dictionary
whose keys and values are strings.

These annotations help the editor and analysis tools, but Python does not
automatically validate arguments just because annotations are present. That
is why the implementation adds explicit checks.

The triple-quoted block following the signature in the source file is the
*docstring*. It documents what the function does, what input it expects, and
which exceptions it can raise. The first line of the file is also a docstring,
but it describes the entire module.

The matrix must arrive in this order:

| Matrix position | Square |
| --- | --- |
| `board[0][0]` | `a8` |
| `board[0][7]` | `h8` |
| `board[7][0]` | `a1` |
| `board[7][7]` | `h1` |

Indices start at zero. The function preserves this order; it does not infer
which side the board was viewed from in the image.

## 4. Validating the whole board

```python
if not isinstance(board, (list, tuple)):
    raise TypeError("Board must be a list or tuple of rows.")
if len(board) != 8:
    raise ValueError("Board must contain exactly 8 rows.")
```

First, the function checks that `board` is a list or tuple. Then it checks
that it has eight rows.

| Exception | When it is used | Example |
| --- | --- | --- |
| `TypeError` | The supplied type is incorrect. | `None`, a number, or a string supplied as the board. |
| `ValueError` | The type is valid, but its value violates the contract. | A list with seven rows. |

`raise` interrupts execution and reports the error to the caller. No partial
position is returned. Checking the type before calling `len()` also allows a
clear message when something like `None` is supplied.

These exceptions validate an internal matrix. Structured image-processing
errors belong to the input, detection and classification stages; see the
[output contract](output-contract.md).

## 5. Iterating over rows

```python
ranks: list[str] = []
for row_index, row in enumerate(board):
    if not isinstance(row, (list, tuple)):
        raise TypeError(f"board[{row_index}] must be a list or tuple.")
    if len(row) != 8:
        raise ValueError(f"board[{row_index}] must contain exactly 8 squares.")
```

`ranks` will store the eight rows already converted to FEN text. A *rank* is a
horizontal row on a chessboard.

`enumerate(board)` provides the row index and the row itself on each iteration.
For the starting position, the first iteration has `row_index = 0` and
`row = ["r", "n", "b", "q", "k", "b", "n", "r"]`.

Each row must be a list or tuple of eight elements. Having 64 elements in total
is not sufficient: a matrix with one row of seven and another of nine is also
rejected.

The messages use strings prefixed with `f`, which allow values to be inserted.
For example, if the fourth row fails validation, `{row_index}` is replaced by
`3`, and the message identifies `board[3]`.

## 6. Iterating over squares

```python
rank: list[str] = []
empty_count = 0
```

These variables are created inside the row loop. The singular `rank` stores
fragments of the current row. The plural `ranks` stores completed rows.
`empty_count` counts consecutive empty squares and starts at zero for each row.

The following check is applied while iterating over squares:

```python
for column_index, piece in enumerate(row):
    if piece is None:
        empty_count += 1
        continue
```

If the square is empty, the counter increases. `continue` moves directly to the
next square, skipping the rest of the loop body.

`piece is None` recognizes only the agreed value for an empty square. `0`,
`False`, and `""` must raise an error, even though Python also treats them as
false in a condition.

## 7. Validating a piece

If the square does not contain `None`, its contents are checked:

```python
if not isinstance(piece, str):
    raise TypeError(
        f"board[{row_index}][{column_index}] must be a piece symbol or None."
    )
if piece not in _PIECE_SYMBOLS:
    raise ValueError(
        f"Invalid piece symbol at board[{row_index}][{column_index}]: {piece!r}."
    )
```

First it must be a string. Then it must match one of the twelve allowed symbols.
`"P"` is valid; `"PP"`, `"."`, `"1"`, and `"♙"` are not.

`{piece!r}` uses Python's representation of the value. This makes otherwise
hard-to-see characters visible: a string containing a newline appears as
`'P\n'` in the message.

## 8. Compressing empty squares

When a valid piece is found, any preceding empty squares are recorded first:

```python
if empty_count:
    rank.append(str(empty_count))
    empty_count = 0
rank.append(piece)
```

`if empty_count` is true when the counter is nonzero. `str()` converts the number
to text, and `append()` adds that fragment to the list. The counter is then
reset, and the piece is added.

Consider this row:

```python
[None, "P", None, None, "n", None, None, None]
```

| After processing… | Empty counter | Stored fragments |
| --- | --- | --- |
| First empty square | 1 | `[]` |
| `"P"` | 0 | `["1", "P"]` |
| Two empty squares | 2 | `["1", "P"]` |
| `"n"` | 0 | `["1", "P", "2", "n"]` |
| Three trailing empty squares | 3 | `["1", "P", "2", "n"]` |

The final three empty squares have not been written yet because no piece follows
them. That is why this check runs after the loop:

```python
if empty_count:
    rank.append(str(empty_count))
```

The fragments are now `["1", "P", "2", "n", "3"]`. The same mechanism turns a
completely empty row into `"8"`.

## 9. Building the result

At the end of each row:

```python
ranks.append("".join(rank))
```

`"".join(rank)` joins the fragments without a separator. In the example, it
produces `"1P2n3"`. Once all eight rows have been processed, the function returns:

```python
return {"piecePlacement": "/".join(ranks)}
```

`"/".join(ranks)` inserts `/` between the eight rows. The result is a Python
dictionary; a future adapter will encode it as JSON for the CLI or application.

## Complete example

This example can be run with the package installed:

```python
from boardsnap.output import build_result

board = [[None] * 8 for _ in range(8)]
board[0] = [None, "P", None, None, "n", None, None, None]

result = build_result(board)
assert result == {"piecePlacement": "1P2n3/8/8/8/8/8/8/8"}
```

A new list is created for each row, so rows can be modified independently when
preparing the input.

## Scope and input preservation

The function does not modify `board`: it traverses it and builds new lists and
strings. It does not check chess legality either; it can serialize an empty
board or an arrangement containing multiple kings. Its responsibility is to
validate the representation of the 64 squares and convert it into piece placement.

Image reading, recognition, and orientation resolution belong to other stages.
No side to move, castling rights, en passant state, counters, or confidence
scores are added to the result.
