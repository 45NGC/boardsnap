# Normalization and square segmentation

**English** | [Spanish](../es/normalization.md) · [Overview](README.md)

After detection, `normalize_board(image, bounds)` crops the grid and resizes it
to **512 × 512 RGB pixels** by default. `split_squares(board.image)` then returns
a list of **eight rows of eight independent 64 × 64 RGB images**.
These stages use the existing Pillow dependency and do not recognize pieces.

## Python API

```python
from contextlib import ExitStack

from boardsnap.image_input import read_image
from boardsnap.detection import detect_board
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares

with ExitStack() as stack:
    source = stack.enter_context(read_image(
        "data/tuning/lichess-cburnett-brown-v1/pos-001-white.png"
    ))
    bounds = detect_board(source)
    board = stack.enter_context(normalize_board(source, bounds))
    squares = split_squares(board.image)
    for row in squares:
        for square in row:
            stack.enter_context(square)

    print(board.image.size)           # (512, 512)
    print(squares[0][0].size)          # (64, 64)
    print(board.source_bounds)        # Bounds in the decoded source image
    # Use squares for classification and board.source_image for orientation.
```

`ExitStack` closes the images when the block ends. You can also manage the images
yourself: call `board.close()` and close each square after use. The normalized
board owns two images; the original caller's image and all square crops have
independent pixel storage. Closing the source or normalized board does not
invalidate previously extracted squares. Frozen dataclass fields prevent field
reassignment, but do not make Pillow pixels immutable.

## Geometry and order

`normalize_board(image, bounds, square_size=64)` accepts decoded RGB input and
integer `BoardBounds`. Right and bottom edges are exclusive. Bounds must have
positive dimensions and fit entirely inside the image; invalid crops are rejected
instead of padded. The target side is `8 * square_size`, with `square_size` a
positive integer. The 64-pixel default is an initial engineering choice, not a
classifier accuracy claim or a size selected using evaluation images.

The crop is resized with LANCZOS. Slight width/height differences allowed by the
detector are scaled independently onto the square output. This does not correct
perspective or detect whether arbitrary supplied bounds contain a board. Scaling
can blend colors at cell boundaries; segmentation adds no further resampling.

`split_squares(image)` requires an RGB square image with a positive side divisible
by eight. For square side `s`, row `r` and column `c`, the crop is
`(c*s, r*s, (c+1)*s, (r+1)*s)`, with exclusive end coordinates. Every normalized
pixel belongs to exactly one square, with no gaps, overlap or discarded borders.

Indices follow **image order**, top-to-bottom and left-to-right, starting at zero.
`squares[0][0]` is the visible top-left cell in either chess orientation. No image
rotation, reflection or matrix reversal occurs here; do not assume it is `a8`
until orientation is resolved. Internal coordinate labels remain in the crops.

## Preserving orientation clues

`NormalizedBoard.source_image` is a full-resolution copy of the entire decoded
input, taken before discarding margins or resizing. It preserves coordinates
outside and inside the board, without trying to read them. `source_bounds`
locates the board within this copy. The copy survives changes or closure of the
caller's input, at the cost of keeping one additional full input image in memory.

For a normalized edge coordinate `(u, v)` on a board of side `N`, its source edge
coordinate is `(bounds.x + u * bounds.width / N,
bounds.y + v * bounds.height / N)`. These coordinates refer to the decoded image
after EXIF normalization, not to the original file's uncorrected pixel layout.
This is a geometric mapping; LANCZOS samples neighboring pixels when resizing.

Chess orientation remains pending. Its future stage can inspect preserved
coordinates and reorder classified cells according to the
[output contract](output-contract.md). When clues are insufficient, that stage
will apply the documented White-at-the-bottom convention. These modules do not
apply that fallback or add fields to the public JSON.

## Errors and limits

Invalid internal argument types raise `TypeError`; invalid modes, dimensions,
bounds or target sizes raise `ValueError`, consistent with the existing internal
APIs. No partial board or substitute empty position is returned. The future
pipeline/adapter remains responsible for translating processing failures into
the output error contract. No new public error code is introduced here.

These functions assume detection has supplied a complete, axis-aligned grid.
They do not expand style support, remove highlights or repair incorrect detection.
Piece classification, coordinate reading, perspective correction and the
recognition CLI remain pending.

## Visual inspection

From the repository root:

```bash
.venv/bin/python -m tools.preview_detection --squares
```

Under `.cache/detection-preview/<profile>/<capture>/`, open:

- `detection.png`: the detected rectangle on the full image.
- `board.png`: the unscaled crop.
- `normalized.png`: the 512 × 512 board.
- `squares/row-0-col-0.png` through `squares/row-7-col-7.png`: the 64 crops.

Names use image indices, not chess ranks/files. The command processes tuning
images by default; an explicit image path is also accepted. Rerunning replaces
the previews for each processed image. Running without `--squares` removes its
previous normalization/square previews. Originals remain unchanged and generated
files stay in Git-ignored `.cache`. Core functions never save files automatically.

## Tests

```bash
python -m pytest tests/test_normalization.py tests/test_segmentation.py tests/test_preprocessing_images.py -m 'not evaluation'
python -m pytest tests/test_preprocessing_images.py -m evaluation
python -m pytest
```

Synthetic tests use unique cell colors, asymmetric arrangements and pixel
patterns to check exact bounds, unchanged ordering in both views, all 64 cells,
reconstruction without gaps/overlap, odd source sizes, custom target sizes,
invalid inputs and independent ownership of orientation context and crops.

Real-image checks run input → detection → normalization → segmentation on all
16 tuning and 4 held-out captures, with separate markers. Expected crops use the
existing reviewed bounds, not detector output. These checks verify geometry and
preservation of pixels; they do not measure piece recognition or orientation
accuracy. Parameters are fixed before running the reserved images, and no crops
from evaluation images are added to tuning data.

Validation on 2026-10-05: all 59 new cases passed (39 synthetic, 16 tuning and
4 reserved). The complete suite passed 346 cases; 7 optional browser cases were
skipped. These results do not establish compatibility with additional styles.
