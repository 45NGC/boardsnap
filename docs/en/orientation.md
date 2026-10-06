# Board orientation

**English** | [Spanish](../es/orientation.md) · [Overview](README.md)

`detect_orientation(board)` reads coordinate pixels from the full-resolution
source retained by `normalize_board`. It returns `"white-bottom"` or
`"black-bottom"`. `to_canonical(matrix, orientation)` maps an 8 × 8 matrix from
image order to chess order: ranks 8 to 1, files a to h.

## Current scope and method

The first implementation reads **internal file labels along the bottom and rank
labels down the right edge** in `lichess-cburnett-brown-v1`. It is a small template
reader for `abcdefgh12345678`, not general OCR. It uses existing Pillow, NumPy
and OpenCV dependencies; no OCR executable, network service or PyTorch is needed.

1. Locate small label regions relative to the detected board bounds in the
   original decoded image, excluding the board's outer shadow.
2. Require a known brown-profile background and extract contrasting text pixels
   using grayscale, which tolerates colored subpixel antialiasing.
3. Compare the glyph silhouette against packaged examples, preserving aspect
   ratio. Accept only a best overlap of at least 0.78 and a lead of at least 0.05
   over the next character. These are internal gates, not output confidence.
4. Require at least **four readable coordinates**, all consistent with one view.
   File labels read `abcdefgh` and ranks `87654321` for White at the bottom;
   both sequences reverse for Black at the bottom. Either axis can suffice.
5. If labels are absent, insufficient, unreadable, misplaced or contradictory,
   return **White at the bottom**, as specified by the output contract.

Piece identities, occupied squares, checkerboard parity, interface text outside
these regions, filenames, annotations and image metadata do not determine the
orientation. In particular, an unlabelled Black-view board also uses the White
fallback; that result can be wrong but is deterministic and needs no confirmation.

The 32 glyph examples come **only from the empty tuning position `pos-004` in
both views**. The installed asset records provenance and source hashes and is
included in the wheel. No training/evaluation directory is read at runtime.
See [asset provenance](../../src/boardsnap/assets/README.md). To rebuild:

```bash
.venv/bin/python -m tools.build_coordinate_templates
```

External-margin coordinates, different fonts/layouts, other board themes,
rotated/reflected images and book labels are not supported by this reader.
Their clues may be unreadable and trigger the fallback. Boards under 256 source
pixels per side and extracted glyphs under 6 pixels high are treated as unreadable.
Preserving the source avoids losing labels when the normalized board is small,
but cannot recover text missing from the input. New fonts and renderings require
new tuning examples and separate evaluation; resized samples alone do not prove
support for independently rendered sizes.

## Python API and ownership

```python
from contextlib import ExitStack

from boardsnap.image_input import read_image
from boardsnap.detection import detect_board
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares
from boardsnap.orientation import detect_orientation, to_canonical

with ExitStack() as stack:
    image = stack.enter_context(read_image(
        "data/tuning/lichess-cburnett-brown-v1/pos-002-black.png"
    ))
    board = stack.enter_context(normalize_board(image, detect_board(image)))
    visual = split_squares(board.image)
    for row in visual:
        for square in row:
            stack.enter_context(square)
    orientation = detect_orientation(board)
    canonical = to_canonical(visual, orientation)
    # canonical[0][0] corresponds to a8; drawings remain upright.
```

`to_canonical` accepts rows/matrices stored in lists or tuples, with arbitrary
cell values. White-bottom copies row containers; Black-bottom reverses both
axes. Cells themselves are shared, not copied or rotated. The input matrix is
not mutated. Crops remain owned by the caller and should be closed only once.
The same mapping can be applied to a classified piece-symbol matrix before
`build_result`. Classification is not implemented by this stage.

Invalid internal argument types raise `TypeError`; malformed dimensions, bounds,
mode or orientation values raise `ValueError`. Missing labels are not errors.
The [public JSON contract](output-contract.md) is unchanged: orientation is
internal data, never a new field, confidence score or confirmation request.

## Preview and tests

```bash
.venv/bin/python -m tools.preview_detection --orientation
python -m pytest tests/test_orientation.py tests/test_orientation_images.py -m 'not evaluation'
python -m pytest tests/test_orientation_images.py -m evaluation
python -m pytest
```

The preview option includes square previews and saves `orientation.txt` and
`canonical.png` under `.cache/detection-preview/<profile>/<capture>/`. The latter
is assembled from reordered crops without rotating glyphs or pieces. Printed
coordinate labels stay attached to their crops, so their position within a cell
is unchanged; this is a debugging image, not a redrawn chessboard. Running without
the option removes previous orientation previews for each processed image.

Unit tests cover fallback/consistency policy (with an explicitly stubbed glyph
reader), blank pixels, all 64 cell mappings, ownership and invalid inputs.
Pixel-based tests use all 16 tuning and 4 reserved captures with eight variants:
original, board crop, translated frame, doubled pixels, no labels, only files,
only ranks and one remaining label. A real conflicting-axis case also tests fallback.
Coordinates and piece distributions remain independent: expected piece matrices
come from annotations and test the mapping hand-off, not piece recognition.
Asymmetric positions in opposite views must produce identical canonical matrices
and `piecePlacement` when coordinates are readable.

All templates, gates and variant expectations are fixed using tuning data before
reserved evaluation. Variants stay in their original partition and all generated
evaluation images remain in memory. No evaluation crop becomes a template.

Validation on 2026-10-07: **200 new cases passed** (38 unit, 130 development,
32 reserved). All four original reserved captures had the annotated orientation.
Those 32 cases represent two positions in both views plus derivatives, not 32
independent scenes. No thresholds or templates changed after reserved evaluation.
The full suite passed 546 cases and skipped 7 optional browser cases. The built
wheel was also checked for assets and coordinate reading outside the repository
working directory. This does not establish general OCR or piece recognition.
