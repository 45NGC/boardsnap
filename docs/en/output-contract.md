# Output contract

**English** | [Spanish](../es/output-contract.md) · [Overview](README.md)

This document defines the output contract. Success results can be built from
already-classified matrices through the Python API below. Image loading and its
three input error codes are implemented in [image_input](image-input.md).
[Detection](detection.md) implements `BOARD_NOT_FOUND` and rejects multiple
detected grids with `UNSUPPORTED_IMAGE`. [Classification](classification.md) adds
first-profile template recognition and `PROCESSING_FAILED` for unavailable assets.
`boardsnap.pipeline.recognize_image(path)` returns the success dictionary or
propagates these structured exceptions for adapters to serialize. The [CLI](cli.md)
implements this transport and maps unexpected recognition exceptions to `PROCESSING_FAILED`.

## Success

A single JSON object with exactly one field, `piecePlacement`, of type string:

```json
{
  "piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
}
```

This is only the first field of FEN, with no spaces or additional fields:

- Eight ranks separated by `/`, from the eighth rank to the first.
- Within each rank, files run from `a` to `h`.
- White pieces: `P`, `N`, `B`, `R`, `Q`, `K`; Black pieces: `p`, `n`, `b`, `r`, `q`, `k`.
- Each run of empty squares is compressed into a single digit from `1` to `8`.
- Each rank represents exactly eight squares.

No side to move, castling rights, en passant state, counters, confidence,
uncertain squares, alternatives, or orientation metadata are added. The app
will decide how to edit the position and complete the remaining game data.
An incorrect classification can be corrected there; the engine will not request
confirmation.

## Python output API

`boardsnap.output.build_result(board)` returns a dictionary with exactly
`{"piecePlacement": "..."}`; JSON encoding belongs to the external adapter.
For example, an explicitly empty board can be serialized with:

```python
from boardsnap.output import build_result

board = [[None] * 8 for _ in range(8)]
result = build_result(board)
assert result == {"piecePlacement": "8/8/8/8/8/8/8/8"}
```

The input is an 8 × 8 matrix of already-classified squares, ordered from `a8`
to `h1`. The board and its rows support lists and tuples. Each cell is `None`
for empty or a single character from `PNBRQKpnbrqk`. Strings, bytes, and mappings
are not valid board or row containers. Dots in the test fixtures are converted
to `None` before calling this API; they are not valid cell values.

- Incorrect board, row, or cell types raise `TypeError`.
- Incorrect dimensions or invalid string symbols raise `ValueError`.
- The input matrix is not modified.
- An explicitly empty matrix of 64 squares is valid, as are arrangements that
  would be illegal in a game; the function only serializes placement.

These are internal matrix validation errors, distinct from the structured
image-processing errors below. This function does not recognize pieces or
infer orientation; those stages must supply the matrix in canonical order.

## Orientation

The Python pipeline accepts `orientation="white-bottom"`, `"black-bottom"` or
`"auto"` (default). Explicit orientation **takes priority over coordinates** and
bypasses their reader. It describes the image view, not the side to move. See the
[orientation guide](orientation.md). Invalid values raise `ValueError` before
image I/O. Existing calls without the parameter retain automatic behavior.

In `auto`, the engine reads the selected profile's supported coordinate layout;
insufficient, unreadable or conflicting labels fall back to White at the bottom.
An explicit choice is honored even when it contradicts readable coordinates.
Orientation is input only: no field is added to the response.
Resolving it assigns chess coordinates to squares without rotating piece drawings.

| Image view | Mapping to the output |
| --- | --- |
| White at the bottom | Top left = `a8`; bottom right = `h1`. |
| Black at the bottom | Top left = `h1`; bottom right = `a8`; both matrix rows and columns are reversed. |

In `auto`, when there are insufficient clues or labels cannot be read consistently, the
engine will assume **White at the bottom**: top left is `a8` and bottom right
is `h1`. This rule is deterministic and produces no additional field or
confirmation request. It can produce an incorrect orientation if the actual
board was viewed from Black's side.

Piece distribution, piece color, and square color alone are not enough to
establish orientation. Pawns and kings will not be assumed to occupy their
starting ranks. Normalizing image metadata is separate from resolving chess
orientation; 90-degree rotations, reflections, and arbitrary perspectives are
outside the first profile's scope.

## Failure

If a failure prevents a position from being obtained, the response will contain
only `error`, with a stable machine-readable code and a human-readable message:

```json
{
  "error": {
    "code": "BOARD_NOT_FOUND",
    "message": "No chessboard was detected in the image."
  }
}
```

| Code | Meaning |
| --- | --- |
| `INPUT_READ_ERROR` | The input bytes cannot be read, for example because the file does not exist. |
| `INVALID_IMAGE` | Content is empty, corrupt, or cannot be decoded as an image. |
| `UNSUPPORTED_IMAGE` | The implemented profile explicitly does not support the input format or condition. |
| `BOARD_NOT_FOUND` | No usable board can be located. |
| `PROCESSING_FAILED` | A processing failure prevents completing all 64 squares and generating piece placement. |

Consumers will depend on `code`, not the exact text of `message`. The engine
will not return `piecePlacement` alongside an error, a partial position, or an
empty board as a substitute for failure. An unknown design may not be
automatically distinguishable from a detection failure or an incorrect
classification; style coverage will be documented using evaluated examples.

## CLI transport

The interface is `boardsnap image.png` (also `python -m boardsnap image.png`).
For a valid invocation, `stdout` contains exactly one JSON object followed by a newline: success with process
exit code `0`, or an image/processing failure with exit code `1`. Diagnostics
go to `stderr`. `--help` prints help to stdout and exits `0`, not a JSON result.
Invocation errors, such as a missing path or extra arguments, print usage to
stderr, leave stdout empty and exit `2`; no image was processed.

The result format does not assume HTTP or server status codes.
