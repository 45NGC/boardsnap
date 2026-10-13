# Arrows and combined overlays

**English** | [Español](../es/arrows.md) · [Overview](README.md)

Step 8 extends the [simple-mark baseline](simple-marks.md) with controlled arrows
and combinations. Detection and classification remain separate. The recognizer
still returns only `piecePlacement`, and templates remain the default CLI backend.

## Rendering and traceability

`tools/arrow_marks.py` supports horizontal, vertical and diagonal arrows, plus
L-shaped knight paths with either bend order. The renderer draws a continuous
shaft, bend and triangular head on the full screenshot **before normalization or
square extraction**. Black-bottom changes the arrow's image coordinates; it does
not rotate piece glyphs. Separate alpha layers preserve crossing colors in order.

The pilot varies four colors (green, orange, blue, red), three widths
(0.08, 0.14, 0.22 square sides) and three alpha values (96, 144, 192). Endpoints,
paths, bend orders, RGBA, width and renderer version are recorded for every PNG.
These are synthetic overlays over real platform artwork, not exact native
browser/mobile arrow rendering or legal-move annotations.

Four mutually exclusive cases are measured:

| Case | Meaning |
| --- | --- |
| `arrow-empty` | One arrow; all cells under its shaft, bend and head are empty |
| `arrow-piece` | One arrow intersects at least one occupied cell |
| `arrow-crossed` | Two arrows actually intersect, as a plus or an X |
| `arrow-combined` | One arrow with last-move highlights on its endpoints and a circle at its tip |

Occupancy is checked against the placement using the complete raster mask,
including a four-pixel resize halo at normalized board size. Empty endpoints
alone are insufficient. “Over a piece” means an occupied square, not a measured
percentage of the piece's distinguishing strokes. An unavailable requested route
is reported and skipped, never relabeled as a successful empty route.

The [corpus report](../../data/reports/digital-arrows-v1.json) describes **5760 new
images**, derived from the same 1440 clean pilot sources, plus all **10800 clean
and simple-mark controls**. There were no unavailable routes. The 80 positions,
source groups and partitions stay fixed: 11592 training, 2484 validation and 2484
evaluation boards. Both views/sizes and all 18 piece/background combinations are
represented. Captures inherit the original `pairId`, group, split and placement;
sidecars add `overlayCase`, `arrowCoverage` and the original clean PNG hash.

Single-arrow directions and occupied/empty coverage are selected reproducibly
before training, without recognition predictions. Coverage counts are reported
per class/background and partition. This is a bounded pilot, not an exhaustive
cross-product of colors, widths, views, arrow positions and styles. Arbitrary
numbers of arrows, native app layouts and crosses combined with additional marks
are not established by these four benchmark cases.

## Training and evaluation

The [fixed configuration](../../tools/train-arrows-v1.json) trains the same small
CPU network from scratch for 30 epochs. All clean training cells are retained;
marked variants contribute affected cells, including intermediate arrow cells
and a resize halo. Loss weights use training frequencies only. Validation and
evaluation keep all 64 squares per image without balancing or sampling.

`--preserve-controls` selects checkpoints by **clean/simple-mark validation
whole-board correctness first**, then total exact boards, macro recall and loss.
This prevents an aggregate arrow improvement from hiding a control regression
during selection. Checkpoints record a hash of the control mask and reject a
different selection mask on resume. The resumed/uninterrupted test compares the
selected weights exactly. Evaluation is never used for checkpoint selection.

This run used 233957 training cells from 11592 boards. Epoch 30 was selected:
2484/2484 validation boards, including all 1620 clean/simple controls. The artifact
is `.cache/neural-arrows-v1/best.pt`; its metadata pins preprocessing, classes,
dataset/index hashes, training configuration and source-code hashes.

The [comparison report](../../data/reports/neural-arrows-v1-evaluation.json)
compares the step-7 artifact with the new candidate on identical pixels. It
contains per-class metrics, complete positions, clean/marked paired results,
exclusive scenario results and direction subsets. Geometry subsets can overlap
for crossed arrows; exclusive case counts are the additive totals.

Measured evaluation results (complete screenshots correct):

| Case | Step 7, verified bounds | Arrow model, verified bounds | Arrow model, detected bounds |
| --- | ---: | ---: | ---: |
| Clean | 540/540 | 540/540 | 540/540 |
| Simple marks, all five kinds | 1080/1080 | 1080/1080 | 1080/1080 |
| Arrow over empty cells | 183/216 | 216/216 | 216/216 |
| Arrow over occupied cells | 188/216 | 216/216 | 216/216 |
| Crossed arrows | 136/216 | 216/216 | 216/216 |
| Arrow + highlights + circle | 175/216 | 216/216 | 216/216 |
| **Total** | **2302/2484** | **2484/2484** | **2484/2484** |

The candidate classifies all 158976 squares correctly in both branches, with no
regression on any of the six control categories. All four arrow-direction subsets
are correct. Detection is within two pixels on every image, including all 864
arrow variants. The step-7 baseline scores 2303/2484 with detected bounds; small
crop differences can change its predictions, which is why both branches are kept.
The detector itself was not changed for this milestone.

These are **12 reserved positions in three source groups**, rendered in many
variants, not 2484 independent positions or proof of arbitrary native overlays.
The public `NeuralClassifier.recognize_image` API was also checked on 16 arrow
images spanning both platforms, four cases and both views; all returned the exact
expected `piecePlacement` with no additional output fields.

Verified bounds isolate classification. The detected branch runs detection on
pixels alone, scores its rectangle against the reference, then normalizes and
classifies without repairing its result. A detection failure counts as an
incorrect whole board and 64 incorrect cells. Reports distinguish detection
failures from correct bounds followed by classification errors, and report
regressions on clean and each previous simple-mark control separately.

No arrow removal, masking or inpainting is applied. Training with the visible
overlay is the current baseline; a removal experiment would need to improve
validation while preserving piece strokes and clean performance before adoption.

## Commands

Use the existing environment with the `ml` extra. Run from the repository root.
Destinations must be new; the named local artifacts already exist after this run.

```bash
python -m tools.build_arrow_dataset --parent-dataset .cache/digital-marked-squares-v1 --captures .cache/digital-arrow-captures-v1 --output .cache/digital-arrow-squares-v1 --report data/reports/digital-arrows-v1.json
python -m tools.train_neural --dataset .cache/digital-arrow-squares-v1 --run .cache/neural-arrows-v1 --config tools/train-arrows-v1.json --marked-cells-only --preserve-controls
python -m tools.evaluate_marks --dataset .cache/digital-arrow-squares-v1 --baseline .cache/neural-marks-v1/best.pt --candidate .cache/neural-arrows-v1/best.pt --baseline-name simpleMarksBaseline --candidate-name arrowCandidate --split evaluation --output data/reports/neural-arrows-v1-evaluation.json
python -m pytest tests/test_arrow_marks.py
```

Use `--split validation` and a separate output for development measurements.
Preserve the frozen evaluation set and choose settings before consulting it.
Snapshots have been reused across incremental milestones; a later release still
needs a fresh acceptance corpus rather than treating these repeated comparisons
as a new blind test each time.

```python
from boardsnap.neural import NeuralClassifier

model = NeuralClassifier(".cache/neural-arrows-v1/best.pt")
result = model.recognize_image("image.png", orientation="white-bottom")
```

Images, NPZ arrays and models stay under ignored `.cache/`. The previous artifacts
are preserved. The capture example also works with verified live platform boards:

```bash
python -m tools.capture_batch capture tools/capture-arrows.example.json --output-root .cache/arrow-example --validate-only
python -m tools.capture_batch capture tools/capture-arrows.example.json --output-root .cache/arrow-example
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_sites.py
```

An arrow specifies `kind: "arrow"`, algebraic `from`/`to`, `path: "straight"` or
`"knight"`, `width` (0.04–0.30 square sides), and RGBA bytes. Knight arrows also
require `bend: "horizontal-first"` or `"vertical-first"`. Straight endpoints must
align horizontally, vertically or diagonally. Multiple arrows may share a marks
list; `conditions` contains each kind once, in first-occurrence order.

The browser still verifies the clean source position, geometry and artwork before
and after capture, then records explicit synthetic augmentation. It does not
silently accept unexpected native overlays. Browser tests use offline fixtures
for both platforms and views; the main corpus reuses previously audited PNGs.

## Limits and real screenshots

**There is no guarantee of recovering a piece whose distinguishing information
is completely hidden.** An opaque mark can make different underlying positions
produce identical visible pixels. No extra FEN fields, confidence values or
legality-based guesses are added to compensate.

The 20 real screenshots still require independently verified placements before
classification use; their existing detection-only roles do not establish arrow
recognition. Continue the [review/import workflow](simple-marks.md#real-screenshots-review-before-classification).
Reviewed arrow screenshots may now be included with `--real-dataset`; their game
partitions are preserved, including held-out game 005. Badges remain outside this
stage. This run does not train on or claim classification results for unreviewed
real screenshots, physical boards or book diagrams.
