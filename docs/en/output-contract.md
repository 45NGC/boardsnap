# Planned output contract

**English** | [Spanish](../es/output-contract.md) · [Overview](README.md)

This document defines the contract to be implemented in future iterations.
The initial scaffold does not process images or emit these responses.

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

## Orientation

Legible coordinates along the border will take priority when identifying ranks
and files. Resolving orientation means assigning coordinates to squares; it
does not mean rotating piece drawings to classify them.

| Image view | Mapping to the output |
| --- | --- |
| White at the bottom | Top left = `a8`; bottom right = `h1`. |
| Black at the bottom | Top left = `h1`; bottom right = `a8`; both matrix rows and columns are reversed. |

When there are insufficient clues or labels cannot be read consistently, the
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

## CLI transport (pending)

The planned interface is `boardsnap image.png`. For a valid invocation, `stdout`
will contain exactly one JSON object followed by a newline: success with process
exit code `0`, or an image/processing failure with exit code `1`. Diagnostics
will go to `stderr`. Help and invocation errors, such as a missing path, will
follow the CLI's argument interface; they do not represent a processed image,
and invocation errors will use exit code `2`.

The result format does not assume HTTP or server status codes.
