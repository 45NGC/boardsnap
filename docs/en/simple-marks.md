# Simple highlights and marks

**English** | [Español](../es/simple-marks.md) · [Overview](README.md)

Step 7 adds controlled `last-move`, `selection`, `check`, `circle` and `move-dot`
variants, reviewed external-game imports and a separately trained CPU model.
The output remains exclusively `piecePlacement`. Templates remain the default
CLI/pipeline backend; select the neural artifact explicitly to try the new model.

## What was generated and measured

The original 3600 clean captures remain immutable. The derivative corpus contains
those 3600 controls plus **7200 marked images**: five conditions for 1440 sources.
A deterministic SHA-256 rule selects one existing view/size per position and
appearance, covering all 80 positions and 18 piece/background combinations.
Both views and viewport sizes occur in the pilot. This is not an exhaustive
cross-product of marks, sizes and orientations.

Every PNG has a sidecar with its placement, group, split, original configuration,
paired clean image ID, bounds, SHA-256, marked chess coordinates, RGBA colors and
renderer version. Marks are drawn on the **full source image before resizing**;
orientation determines their visual locations. No piece or label is changed.

These are **synthetic alpha overlays**, including tint over foreground pieces.
They do not reproduce each platform's native under-piece layers exactly. A
last-move pair, check glow or dot is a visual stress test, not a claim that the
move/check is legal. Check targets kings; the other marks sample class/background
buckets so that empty cells do not dominate. Circles/dots target up to six cells.
Colors, opacity and geometry are fixed for this measured renderer. Other colors,
thicknesses, combined marks and native mobile layouts remain unverified.

The [corpus report](../../data/reports/digital-marks-v1.json) records coverage:
7560 training, 1620 validation and 1620 evaluation boards. Original source groups
and partitions are preserved. Training covers every applicable class/background
for each mark. Selection lacks a white queen on dark squares in validation and a
black king on dark squares in evaluation; these gaps are reported, not repaired
after consulting evaluation. Check coverage applies only to the two king classes.

Training retains every clean square and, for marked training variants, the marked
cells plus immediate neighbours for rectangular highlights (LANCZOS can blend
edges). This avoids repeating all untouched cells five times. The run uses
**194720 training squares** and inverse class-frequency loss weights computed
from those training samples. Validation/evaluation retain **all 64 cells** per
board, without balancing or sampling. Selection uses validation only.

The [fixed configuration](../../tools/train-marks-v1.json) trains the existing
39709-parameter network from scratch for 20 epochs, seed 20261013, on CPU.
Epoch 19 was selected: 1620/1620 validation boards correct. The clean artifact is
preserved as the comparison baseline; neither artifact becomes the CLI default.

A [second complete run](../../data/reports/neural-marks-v1-reproducibility.json)
reproduced every selected weight tensor and every epoch's validation metrics.
Artifact metadata records each run's code provenance, so serialized file hashes
are not asserted equal. Reproducibility is scoped to the recorded CPU/software.

The [reserved evaluation report](../../data/reports/neural-marks-v1-evaluation.json)
compares **identical clean/marked pairs**. Verified-bound classification gives:

| Condition | Clean model: correct boards | Mark-trained model: correct boards |
| --- | ---: | ---: |
| Clean | 540/540 | 540/540 |
| Last move | 214/216 | 216/216 |
| Selection | 216/216 | 216/216 |
| Check | 215/216 | 216/216 |
| Circles | 197/216 | 216/216 |
| Move dots | 142/216 | 216/216 |

The candidate also gets all 1620 boards correct using **detected bounds**. All
detected rectangles are within two pixels of references. The report separates
detection, classification, per-class confusion counts, paired regressions and
each mark condition. Its detected branch decodes PNGs, detects from pixels only,
normalizes and classifies in canonical order; annotated bounds only score the
detector and supply the isolated-classifier branch. No bounds are repaired.

These are only **12 reserved positions from three groups**, rendered in many
variants of known designs. The result establishes clean-data regression and this
controlled-mark baseline, not universal real-play accuracy or arrow support.

## Reproduce or try the model

Use the existing environment with `.[ml]`; no additional library is required.
Run from the repository root. Destination folders must be new; completed local
artifacts already exist at the paths below.

```bash
python -m tools.build_marked_dataset --clean-dataset .cache/digital-square-corpus-v1 --captures .cache/digital-marked-captures-v1 --output .cache/digital-marked-squares-v1 --report data/reports/digital-marks-v1.json
python -m tools.train_neural --dataset .cache/digital-marked-squares-v1 --run .cache/neural-marks-v1 --config tools/train-marks-v1.json --marked-cells-only
python -m tools.evaluate_marks --dataset .cache/digital-marked-squares-v1 --baseline .cache/neural-clean-v1/best.pt --candidate .cache/neural-marks-v1/best.pt --split evaluation --output data/reports/neural-marks-v1-evaluation.json
python -m pytest tests/test_board_marks.py tests/test_real_positions.py
```

```python
from boardsnap.neural import NeuralClassifier

model = NeuralClassifier(".cache/neural-marks-v1/best.pt")
print(model.recognize_image("image.png", orientation="white-bottom"))
```

For new platform captures, `tools/capture-marks.example.json` adds explicit `marks`
to each configuration. `conditions` must match their kinds in drawing order.
Each mark specifies `kind`, distinct algebraic `squares`, and four integer `rgba`
channels. A last-move mark needs two squares, selection one, check a king square.

```bash
python -m tools.capture_batch capture tools/capture-marks.example.json --output-root .cache/marked-example --validate-only
python -m tools.capture_batch capture tools/capture-marks.example.json --output-root .cache/marked-example
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_sites.py
```

The browser still verifies a clean board, artwork, labels and geometry before
and after the screenshot. Unrequested native overlays are still rejected/hidden
as described in the capture guide. The tool then composites the requested marks
and records `controlledMarks`, the clean PNG hash and synthetic provenance.
The offline browser tests cover both platforms and both views, not live-site
native-mark rendering. The 7200 variants use existing audited PNGs without
contacting the platforms again. PNGs, arrays and weights remain ignored in `.cache/`.

## Real screenshots: review before classification

The 20 real screenshots still have **no verified piece placements**. They have
not trained this model or contributed to its classification scores. Do not copy
the recognizer's prediction as a target without independent comparison.

A draft is available at `.cache/real-captures/review-v1.json`. To prepare a new
draft without overwriting review work:

```bash
python -m tools.prepare_real_reviews --output .cache/real-captures/new-review.json
```

It preserves image hashes and reviewed detection bounds. Before reviewing labels,
games 001–002 per platform are assigned to training, 003 to validation, and the
already-held-out 004–005 remain evaluation. Every screenshot and future variant
of a game must retain that assignment. The draft deliberately fails import.

For each sample, independently inspect the screenshot or compare against its
source FEN/PGN. Fill `externalPosition.piecePlacement`, `reviewedPlacement` (same
first FEN field), explicit `orientation`, reviewer name/date and `reviewMethod`
(`manual-board-comparison`, `source-fen` or `source-pgn`); then set `reviewed: true`.
Review conditions and any known style names too. Unknown source URL, capture date
or browser version may stay `null` with `provenanceNote`; never fabricate them.
To import only some completed reviews, copy those samples into a new batch spec.

Import schema **2** accepts `externalPosition` with `positionId`, `groupId`,
`split`, `piecePlacement`, using `real-` IDs. Existing planned-position schema 1
remains supported. A sample cannot specify both identities. Import rejects changed
PNG bytes, missing review, conflicting labels, cross-split source games or
equivalent positions, and attempts to move detection-held-out games into training.
Use one common import root so the checks also cover prior batches. External
positions overlapping the old/generated corpora require reviewing their original
identity; they cannot silently enter under a new ID.

```bash
python -m tools.capture_batch import-real .cache/real-captures/review-v1.json --output-root .cache/reviewed-real --validate-only
python -m tools.capture_batch import-real .cache/real-captures/review-v1.json --output-root .cache/reviewed-real
python -m tools.build_real_squares --imports .cache/reviewed-real/digital-positions-v1 --output .cache/real-squares-v1
```

Once reviewed, add `--real-dataset .cache/real-squares-v1` to a **new** training run.
It checks cross-corpus group/position isolation, merges only training/validation
arrays, records real-data hashes, and never loads evaluation arrays for training.
The subsequent [arrow stage](arrows.md) now accepts reviewed real arrows for
training/validation; badges remain excluded. The game-005 screenshots retain
their held-out partition.
Until labels are reviewed, the real-data portion of step 7 remains pending.
