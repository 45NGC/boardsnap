# Board detection

**English** | [Spanish](../es/detection.md) · [Overview](README.md)

`boardsnap.detection.detect_board(image)` locates a complete, axis-aligned
8 × 8 grid in a decoded RGB Pillow image. The initial implementation targets
the brown board in `lichess-cburnett-brown-v1`. It uses only pixels; it does not
read filenames, annotations, manifests, browser state or a known board position.

```python
from boardsnap.image_input import read_image
from boardsnap.detection import BoardDetectionError, detect_board

with read_image("data/tuning/lichess-cburnett-brown-v1/pos-001-white.png") as image:
    try:
        bounds = detect_board(image)
        print(bounds)  # BoardBounds(x=190, y=158, width=584, height=584)
        print(bounds.as_box())  # (190, 158, 774, 742)
    except BoardDetectionError as error:
        print(error.to_dict())
```

`BoardBounds` is an immutable dataclass with integer `x`, `y`, `width` and
`height`. Coordinates refer to the image passed to the detector, after EXIF
normalization if it came from `read_image`. Right and bottom edges are exclusive.
`as_box()` provides Pillow-compatible crop coordinates. The function preserves
the original image and does not crop, normalize, classify pieces or resolve
chess orientation. Bounds are internal stage data, not extra public JSON fields.

## Visual previews

From the repository root, generate previews for all tuning captures:

```bash
.venv/bin/python -m tools.preview_detection
```

Open `.cache/detection-preview/lichess-cburnett-brown-v1/pos-001-white/`
in VS Code. Each capture gets its own folder containing `detection.png`
(the full image with a red rectangle around the detected grid) and `board.png`
(the unmarked crop at its original resolution). The default command processes
only `data/tuning`; evaluation images remain separate.

To inspect a particular image:

```bash
.venv/bin/python -m tools.preview_detection path/to/image.png
```

A single image produces `.cache/detection-preview/image/`. You can also pass
a directory to scan PNG/JPEG files recursively and use `--output-dir` to choose
a separate output directory. Input and output directories must not overlap.
Rerunning replaces that image's previews; detection/input failures are printed
with their error codes and old previews for that image are removed. The command
exits with status 1 if any image fails. Original captures are never modified.

This development tool does not recognize pieces or generate FEN. The detector
and tests do not save previews automatically; run the command after changes.
The default output is ignored by Git because it lives under `.cache`.

## Method and dependencies

1. Create masks around the profile's light and dark RGB colors, allowing a
   difference of 12 per channel for rendering variation.
2. Join those masks and close tiny seams with a 3 × 3 kernel. Find connected
   regions with OpenCV and retain approximately square candidates at least
   128 pixels per side.
3. Divide each candidate geometrically into 8 × 8 cells. Every cell must retain
   at least 25% expected background color and at most 10% opposite color in its
   interior. Test both alternating color parities. Piece-shaped holes are allowed.
4. Return the sole valid candidate. No candidates produce `BOARD_NOT_FOUND`;
   multiple candidates produce `UNSUPPORTED_IMAGE`, without choosing arbitrarily.

These are fixed initial-profile rules, not a learned model. OpenCV's
[range masks](https://docs.opencv.org/4.x/da/d97/tutorial_threshold_inRange.html)
and [connected components](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html)
provide the primitives. NumPy holds pixel arrays; `opencv-python-headless` avoids
a GUI dependency. Install both through `python -m pip install -e '.[dev]'`.
PyTorch is not needed for this stage.

## Error contract

`BoardDetectionError` exposes `code`, an English `message`, and `to_dict()`:

```json
{"error": {"code": "BOARD_NOT_FOUND", "message": "No supported chessboard was detected in the image."}}
```

The same result applies when a board exists but its style, scale or condition
does not pass the detector. It does not prove that the picture contains no board.
`UNSUPPORTED_IMAGE` is used when multiple supported grids are detected.
A non-Pillow input raises `TypeError`; a non-RGB image raises `ValueError`.
Adapters remain responsible for JSON transport. No confidence, partial position
or fabricated empty board is returned.

## Tests and measured scope (2026-10-01)

```bash
# Development checks, excluding reserved images
python -m pytest tests/test_detection.py tests/test_detection_images.py -m 'not evaluation'
# Reserved cases after parameters are fixed
python -m pytest tests/test_detection_images.py -m evaluation
python -m pytest
```

The 35 synthetic unit cases have independently specified placement/size bounds.
They include border-to-border grids, offsets, sides 128/193/256/584/1024 pixels,
piece-like occlusions, distracting solid rectangles, stripes, uniform images,
wrong grid dimensions, partial boards, another palette and multiple boards.
They test geometry, not piece recognition.

Real-image tests cover all 16 tuning and 4 reserved captures, each with six
variants: original interface, board-only crop, a 192-pixel board, a 960-pixel
board, translated interface, and an interface with the board removed. Variants
stay in their parent's split and are generated only in memory. The negative
variants retain the real menus and spare pieces. Resized/translated images are
controlled transformations, not independently collected screenshots.

Acceptance was fixed at **at most 2 pixels of error on any edge** before running
the reserved cases. References are in
[references.json](../../tests/fixtures/detection/references.json). Real-capture
integer edges were visually reviewed and rounded from existing DOM annotations;
they are not an independent subpixel measurement or human annotation study.
Tests also compare the original fractional sidecars. Transformed expectations
are calculated from the reference and the known transform, never detector output.

Results: **131 development cases and 24 reserved cases passed**. All four
original reserved captures returned `(190, 158, 774, 742)`, matching the integer
reference exactly, with maximum error **0.46875 pixels** against the original
fractional annotation. The 24 reserved cases represent only **two positions**
in both orientations plus derivatives, not 24 independent scenes. Parameters
were not changed after inspecting the reserved results.

## Limitations and next step

Coverage is limited to this two-color profile with a single complete, aligned
grid and enough background visible. Other themes, books, perspective, arbitrary
rotation, strong overlays or color changes are not supported. Large connected
regions of matching colors attached to the grid may merge with it and cause a
miss. An ordinary 8 × 8 checker pattern is visually indistinguishable from an
empty chessboard at this stage and may be accepted.

The initial corpus is small and shares one source layout. Broader negative
images and independently captured sizes/layouts are still needed before claiming
generalization. Reading JPEG is supported by input, but detection accuracy on
compressed JPEGs has not been measured. Full piece-placement recognition is
still pending. [Normalization and segmentation](normalization.md) now produce
64 square crops and preserve the full original image for orientation. Add
`--squares` to the preview command to inspect `normalized.png` and `squares/`.
