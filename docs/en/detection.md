# Board detection

**English** | [Spanish](../es/detection.md) · [Overview](README.md)

`boardsnap.detection.detect_board(image)` locates a complete, axis-aligned
8 × 8 grid in a decoded RGB Pillow image. Digital detection now combines known
palette proposals with a **palette-independent structural path**. It reads
pixels only: no filenames, annotations, browser state or known board position.

```python
from boardsnap.image_input import read_image
from boardsnap.detection import BoardDetectionError, detect_board

with read_image("image.png") as image:
    try:
        bounds = detect_board(image)
        print(bounds.as_box())  # (left, top, right, bottom)
    except BoardDetectionError as error:
        print(error.to_dict())
```

`BoardBounds` contains integer `x`, `y`, `width`, `height` in input-image pixels;
right/bottom edges are exclusive. EXIF normalization happens in `read_image`.
The detector preserves the input and does not crop, read orientation or classify
pieces. These bounds are internal data, not additional recognition JSON fields.
The public recognition output remains exclusively `piecePlacement`.

## How it works

1. Keep the existing palette masks as candidate proposals. Their strict
   all-cell alternation check preserves exact bounds on supported legacy themes.
2. Independently find connected RGB edges. RGB differences retain some boundaries
   that grayscale would lose between colors of similar brightness. A small blur
   and morphological closing suppress tiny seams; approximately square connected
   regions supply candidate geometry.
3. For each structural candidate, locate seven interior boundaries in each axis.
   Fit regular spacing to at least five agreeing peaks: piece bases or text may
   produce stronger peaks than one or two real boundaries. Refine the rectangle
   in original-image pixels, rejecting extrapolation outside the image.
4. Divide that rectangle into 8 × 8 cells. Sample each cell's inner rim to reduce
   interference from piece centers and thin arrows. Estimate the two alternating
   background appearances from the image, rather than comparing against fixed RGB
   colors. Require at least 52 consistent cells and at least five per row/column.
5. Require sustained changes along the predicted grid boundaries in both axes.
   Alternation, regular spacing and boundary support are all required; a square
   outline or a uniform lined table is insufficient.
6. Merge proposals describing the same rectangle. Return one grid, or a structured
   error for zero/multiple grids. The structural search always runs, even when a
   palette proposal succeeds, so a second board of another color is not ignored.

Edge proposals use images at most 1600 pixels on the longest side; boundary
refinement uses original coordinates and samples rows to bound working memory.
The minimum original board side is 128 pixels; candidates also need at least
24 pixels at proposal scale. Large-image/small-board combinations can therefore
be missed. This is deterministic OpenCV/NumPy processing, not a learned model.
No new dependencies or PyTorch are required.

Digital profiles share this structural path. The selected profile still supplies
legacy palette proposals and, elsewhere, orientation/classification templates.
**Detecting a new theme does not imply recognizing its pieces.** The experimental
print profile retains its separate framed-diagram detector; see [profiles](profiles.md).

## Previews and independent measurement

```bash
# Real-use images, without classifying pieces
python -m tools.preview_detection .cache/real-captures --output-dir .cache/detection-real
# Versioned development corpus
python -m tools.preview_detection data/detection/development --output-dir .cache/detection-development
# Rectangle metrics only; choose the split explicitly
python -m tools.evaluate_detection --split development
python -m tools.evaluate_detection --split evaluation
```

Preview folders contain `detection.png` (rectangle on the full image) and
`board.png` (unmarked crop). Originals are unchanged. Input/output folders must
not overlap. Rerunning replaces previews; failed inputs remove stale previews.
The preview command exits 1 if any image fails. `--squares` adds normalized/cell
previews; `--recognition` explicitly enables the separate classification stage.

The evaluator emits a **detection report**, not the recognition JSON contract.
It checks image hashes, reports each rectangle's maximum edge error and
intersection-over-union (IoU), and counts failures. It also removes the annotated
board from a copy and checks that the remaining interface is rejected. Use
`--output path.json` to save a report. Exit 1 indicates missed/inaccurate rectangles
or false positives on those paired negatives. No classification is run.

## Reviewed dataset and results

The [manifest](../../data/manifests/digital-detection-v1.json) contains **28 original
PNGs** with reviewed integer rectangles and preserved SHA-256 hashes:

| Split | Images | Source groups | Contents |
| --- | ---: | ---: | --- |
| Development | 20 | 7 | Real games 001–003 on each platform, plus eight automated style captures from one pre-existing training group |
| Evaluation | 8 | 4 | Real games 004–005 on each platform, including arrows, circles and highlighted squares |

Automated samples cover Lichess green/Merida and purple/Alpha, and Chess.com
blue/Classic and brown/Bases, in both orientations. Real samples use the supplied
brown boards and include last-move highlights; exact theme names and source
URLs/FEN/PGN were not supplied. Files are copied unchanged into
`data/detection/development/` and `tests/fixtures/detection/held-out/` so regression
tests do not depend on `.cache/`. These are **detection fixtures only**; they are
not imported into the 80-position training plan or used to build piece templates.

Real-image rectangles were entered after assistant visual inspection and checked
at border scanlines. Automated rectangles were rounded from DOM annotations and
visually checked. Neither uses detector output as its reference. This is not an
independent human annotation study. Games and all derived variants remain in
one partition; the split and **2-pixel maximum edge error** were fixed before
running the held-out cases. Visual inspection for annotation does not constitute
blind collection. The four held-out games are a small evaluation sample.

The [development report](../../data/reports/digital-detection-v1-development.json)
and [evaluation report](../../data/reports/digital-detection-v1-evaluation.json)
record original-image accuracy separately from recognition. Reports include
manifest and detector hashes so changes are traceable.

Measured originals: **20/20 development and 8/8 evaluation rectangles**, maximum
integer-edge error **0 pixels**, mean IoU **1.0**. All 28 paired board-removal
negatives were rejected. The 64 reserved regression cases (40 new variants and
24 legacy variants) pass; they are derivatives of a small number of source
images, not 64 independent captures.


```bash
python -m pytest tests/test_detection.py tests/test_detection_structure.py tests/test_detection_images.py tests/test_detection_corpus.py -m 'not evaluation'
python -m pytest tests/test_detection_images.py tests/test_detection_corpus.py -m evaluation
python -m pytest
```

Tests cover novel palettes, generated textures, piece-like occlusions, highlights,
arrows, borders, margins, sizes up to 2400 pixels, multiple boards, solid squares,
noise, stripes, nonalternating cells, plain grids, other grid dimensions and
incomplete boards. Real images also have board-only, reduced, translated and
board-removed variants; variants are generated in memory within the original
split. **Texture evidence is synthetic**, not a validated catalogue of real wood
or marble themes. Existing brown-profile references and other profile regressions
remain in place.

## Errors and limitations

`BoardDetectionError` exposes `code`, an English `message` and `to_dict()`:

```json
{"error": {"code": "BOARD_NOT_FOUND", "message": "No supported chessboard was detected in the image."}}
```

`BOARD_NOT_FOUND` means no accepted grid, including unsupported conditions;
`UNSUPPORTED_IMAGE` means multiple accepted grids. Non-Pillow and non-RGB inputs
raise `TypeError` and `ValueError`. No confidence or guessed position is returned.

The detector still assumes complete, aligned, approximately square 2D boards.
Perspective, arbitrary rotations, heavy occlusion, strong textures, very low
contrast or edges joined to surrounding interface elements may fail. Tolerance
of some highlighted cells does not guarantee tolerance of arbitrary overlays.
An empty 8 × 8 checkerboard is visually indistinguishable from an empty chessboard
at this stage. A larger board cropped to exactly eight intact rows/columns also
cannot always be distinguished from a complete 8 × 8 image. Negative examples
cannot establish that every unrelated square surface will be rejected.

More real themes, native mobile layouts and independent negative screenshots are
still needed. New detection success does not change the measured classification
scope or promise end-to-end recognition of marked screenshots.
