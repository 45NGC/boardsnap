# First piece recognition baseline

**English** | [Spanish](../es/classification.md) · [Overview](README.md)

This guide records the original brown-profile implementation. See [evaluated profiles](profiles.md) for subsequent digital styles, the experimental book profile and current coverage.

The initial template classifier supports **cburnett pieces on the lichess brown
board**. It chooses one of thirteen classes for each square: empty (`None`),
white `PNBRQK`, or black `pnbrqk`. Classification uses only square pixels, not
annotations, expected positions, filenames or legality rules.

An optional [PyTorch baseline](neural-classifier.md) now has its own measured
comparison. This guide describes the template backend, which remains the default.

## API and method

`classify_square(square)` requires a **64 × 64 RGB Pillow image** and returns one
symbol or `None`. `classify_squares(matrix)` accepts eight list/tuple rows of eight
images and returns eight lists of eight labels in the same visual order. Input
images remain open, owned by the caller and unchanged. Canonical ordering belongs
to `to_canonical`, not to the classifier.

The algorithm estimates the known background from pixel counts near the two
brown-profile colors, then constructs two channels: contrast darker than that
background and contrast lighter than it. Thus silhouettes/outlines and white
fills contribute separately. It ignores the outer two pixels and the 16 × 16
upper-right/lower-left coordinate regions in every square. Ignoring these corners
also discards some piece pixels; this is a profile-specific compromise.

It compares those features against **26 templates**, one per class/background,
using mean squared distance. The nearest template determines the class; ties
follow the fixed template order. There are no confidence fields, candidate lists,
confirmation requests or postprocessing to force a legal position. An unsupported
piece design can still be assigned an incorrect known class: this baseline does
not detect every unknown style. A valid empty square is a class, never an error
substitute.

All existing dependencies are reused. No neural model or PyTorch dependency has
been introduced for this baseline.

## Template data and reproducibility

The builder selects the first example of each class/background in stable filename
and visual row/column order, using **only the fixed tuning split**. Its 16 captures
contain 1,024 squares and cover all 26 combinations. Labels come from known FEN
placements mapped into the annotated capture view. Reviewed/rounded annotated
bounds are used to extract training crops; runtime detection uses image pixels.

`piece-templates.png` is a 128 × 832 atlas, with columns light/dark and rows
empty, P, N, B, R, Q, K, p, n, b, r, q, k. `piece-templates.json` records source
image and annotation hashes, crop coordinates, class/background counts, atlas
mapping and hash. Both are installed package data and loaded through
`importlib.resources`; the engine does not need repository data at runtime.
See [artwork provenance](../../src/boardsnap/assets/README.md).

```bash
.venv/bin/python -m tools.build_piece_templates
```

No evaluation pixels or labels are used to choose templates or feature parameters.
Development checks on tuning images are not independent accuracy estimates,
including checks that exclude the exact selected crop but share its position.

## Image-to-result Python API

```python
from boardsnap.pipeline import recognize_image
from boardsnap.image_input import ImageInputError
from boardsnap.detection import BoardDetectionError
from boardsnap.classification import ClassificationError

try:
    result = recognize_image("data/tuning/lichess-cburnett-brown-v1/pos-002-black.png")
except (ImageInputError, BoardDetectionError, ClassificationError) as error:
    result = error.to_dict()
```

`recognize_image(path)` composes input, detection, normalization, segmentation,
orientation, classification and output, and closes all owned images on success
or failure. Success is exactly `{"piecePlacement": "..."}`. It propagates the
stage exceptions; adapters serialize `error.to_dict()`. Missing/corrupt templates
raise `ClassificationError` with `PROCESSING_FAILED`, never an empty position.
Invalid internal image types, modes or dimensions raise `TypeError`/`ValueError`.
The [registered recognition CLI](cli.md) serializes these outcomes. the [Flutter HTTPS design](flutter-integration.md) is documented separately.

## Evaluation protocol fixed before held-out execution

Acceptance for the initial corpus is **zero wrong squares and exact piece placement
on every reserved original capture**. Report all thirteen classes, separately
on light/dark backgrounds, occupied-square accuracy, macro recall for present
classes and exact whole-position matches. Missing class/background support must
remain visible, not be counted as perfect accuracy. Processing failures count
as failed positions and 64 incorrect squares in the report.

Unit tests cover input errors, empty backgrounds/coordinate distractions, unchanged
inputs and broken assets. Real-image tests check every square against annotations,
all 26 class/background combinations on tuning crops other than the selected
templates, and the full pipeline using anonymous files without sidecars. Whole
positions are tested as originals, board-only crops, translated frames and doubled
pixels. Variants remain in the original split; evaluation derivatives stay in
memory or temporary test folders and are not added to tuning.

```bash
python -m pytest tests/test_classification.py tests/test_classification_images.py -m 'not evaluation'
python -m pytest tests/test_classification_images.py -m evaluation
.venv/bin/python -m tools.evaluate_classification --split tuning --output .cache/classification/tuning.json
.venv/bin/python -m tools.evaluate_classification --split evaluation --output .cache/classification/evaluation.json
python -m pytest
```

Reports score the complete pipeline in canonical order, so detection and orientation
errors also affect the square metrics. Isolated classifier tests use known bounds
and visual labels to distinguish that stage. The reports are development artifacts,
not the application response. The JSON output contract stays unchanged.

## Limits and the later PyTorch comparison

This is a small fixed-layout corpus, not a representative benchmark. The reserved
set has only two positions in both views. It cannot establish reliability for
other themes, piece designs, fonts, independently rendered sizes, compression,
highlights, arrows, occlusion or book diagrams. Detection and orientation retain
their existing profile limitations; unreadable coordinates still imply White at
the bottom. There is no game-legality correction.

A PyTorch comparison can start on this same profile; covering every theme first
is unnecessary. Before training, create a **training/validation split inside the
development data by whole source position/group** (including both orientations
and every crop, resize or synthetic variant in the same group). Keep the existing
evaluation groups reserved. Check all thirteen classes and background coverage
in both new splits; collect additional independent positions where necessary.

Training data fits weights, validation chooses hyperparameters, augmentations and
the stopping checkpoint, and evaluation measures the frozen model. Do not split
randomly by square or use held-out crops for augmentation/templates. The existing
eight tuning positions are too small to claim robust neural-model results. Since
this evaluation set has now informed development reports, add fresh untouched
positions for a stronger final comparison. Compare exact positions, per-class
results, latency, artifact size and maintenance against this frozen baseline;
PyTorch is a candidate, not a presumed improvement.

## Observed baseline (2026-10-07)

- Tuning: **16/16 exact images, 1,024/1,024 squares**; development results only.
- Reserved originals: **4/4 exact images, 256/256 squares**, including 74/74 occupied
  squares. Macro recall over the thirteen present classes is 1.0; no processing failures.
- Reserved position variants: **16/16** exact results (four originals and their three
  derivatives). These remain only **two independent positions**, not sixteen.
- No templates or feature parameters changed after reserved evaluation.

Reserved support and correct predictions (dash means no examples):

| Class | Light: correct/total | Dark: correct/total | Total |
| --- | --- | --- | --- |
| empty | 90/90 | 92/92 | 182/182 |
| P | 10/10 | 8/8 | 18/18 |
| N | 2/2 | 2/2 | 4/4 |
| B | 2/2 | 2/2 | 4/4 |
| R | 2/2 | 2/2 | 4/4 |
| Q | 2/2 | — | 2/2 |
| K | 2/2 | 2/2 | 4/4 |
| p | 10/10 | 10/10 | 20/20 |
| n | 2/2 | 2/2 | 4/4 |
| b | 2/2 | 2/2 | 4/4 |
| r | 2/2 | 2/2 | 4/4 |
| q | — | 2/2 | 2/2 |
| k | 2/2 | 2/2 | 4/4 |

White queens on dark squares and black queens on light squares have no reserved
examples. They are covered in tuning only; independent evaluation of those two
combinations still needs new positions. Full confusion counts and provenance are
in the frozen [evaluation report](../../data/reports/lichess-cburnett-brown-v1-classification-evaluation.json)
and [tuning report](../../data/reports/lichess-cburnett-brown-v1-classification-tuning.json).

## Visual inspection

```bash
.venv/bin/python -m tools.preview_detection --recognition
```

This includes orientation/square previews and saves `result.json` beside them
under `.cache/detection-preview/<profile>/<capture>/`, with only `piecePlacement`.
Rerunning without `--recognition` removes the prior recognition result for each
processed image. The default command uses tuning images only; original captures
are not changed. This development utility is separate from the [JSON CLI](cli.md).

Validation: 161 new tests passed (30 unit/report, 111 integration, 20 reserved);
the full suite passed **707 tests**, with 7 optional browser tests skipped.
