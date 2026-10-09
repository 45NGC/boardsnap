# Labeled square dataset

**English** | [Español](../es/square-dataset.md) · [Overview](README.md)

Step 6.3 builds normalized squares from the audited [clean capture corpus](first-clean-corpus.md).
It prepares data and records detection behavior; it does not train or evaluate a
classifier. No PyTorch dependency is needed yet.

## Two independent inputs for future measurements

- **`verified`** uses capture-time verified board bounds. Use these arrays to
  train the initial classifier and measure classification independently of detection.
- **`detected`** passes the complete screenshot to the existing detector, then
  crops its returned bounds. The detector receives pixels only, with its default
  digital profile; no position, annotation, theme or expected rectangle is supplied.
  Use this branch to measure the combined detection/normalization/classification
  path once a classifier exists. Both branches use the explicit capture orientation;
  automatic coordinate reading is not being evaluated.

The branches use the same source images, canonical target labels and original
partitions. Keep them separate: detected arrays are not additional independent
training examples. Wrong detections are measured against the verified rectangle
and kept unchanged; a detection failure produces an error record with no array.
Never repair a detected rectangle using ground truth or exclude failed boards
from future whole-position accuracy denominators. Labels in this branch are the
**intended targets**, not a claim that a badly detected crop contains those pieces.

The report records detection failures and rectangles within one pixel of the
rounded reference. Per-image IoU and maximum edge error are in `detected.jsonl`.
These are data-preparation diagnostics, not new claims of classifier compatibility.
Do not use final-evaluation outcomes to tune detection or the future model.

## Contents and preprocessing

The verified branch contains **230400 squares** (3600 boards × 64):

| Partition | Boards | Squares |
| --- | ---: | ---: |
| Training | 2520 | 161280 |
| Validation | 540 | 34560 |
| Evaluation | 540 | 34560 |

Each board is saved as a compressed NumPy `.npz` containing:

- `images`: `uint8`, shape `(64, 64, 64, 3)`, RGB values 0–255.
- `class_ids`: `uint8`, shape `(64,)`, matching the documented class order.

The fixed order is `empty, P, N, B, R, Q, K, p, n, b, r, q, k`. Uppercase means
White, lowercase Black. This metadata format is separate from BoardSnap's public
`piecePlacement` JSON contract.

Capture bounds may be fractional. Round **left, top, right and bottom** to nearest
integer pixels, with ties to even, before calling production normalization. Crop
the full board, resize to 512 × 512 with Pillow LANCZOS, then split into 64 squares
of 64 × 64. Keep coordinate glyphs; no marks are erased. Order cells from a8 to h1.
For Black at the bottom, reverse the row/column order **without rotating the
piece drawings inside a square**. The normalization and segmentation functions
are the same ones used by the recognition pipeline.

`verified.jsonl` and `detected.jsonl` contain one record per source board. Each
record links to the original PNG and SHA-256, position, source group, partition,
configuration, orientation, piece placement, reference bounds and actual crop
bounds. Successful records link to the array and its SHA-256, and contain 64
`cells`: canonical index, algebraic square, label/class ID, light/dark background,
and original visual row/column. The cell identity is `(boundsMode, image, index)`;
its pixel array is `images[index]`. Full capture provenance and style configuration
remain in the original PNG sidecar. No source image loses its group association.

`background` describes the chess square's parity (a8 is light), not a color
estimated from the screenshot. The selected clean profiles follow that convention.

## Results of this build

Both modes completed all 3600 boards: **230400 squares per mode**, with identical
split counts. There were no detection failures; all 3600 detected rectangles
were within one pixel of the rounded references. This only covers these clean,
automated desktop captures, not overlays or other interfaces.

All 26 class/background combinations occur in each full partition and in each
standard-size configuration. However, the **compact subset is incomplete**:
White queens on dark squares are absent in training/validation, and Black kings
on dark squares are absent in evaluation, across all 18 combinations. These
cases exist at standard size. No samples were moved, synthesized or added to
validation/evaluation to conceal those gaps. Do not claim full per-size coverage;
any future corpus expansion needs a versioned, group-preserving capture plan.

Training contains **111240 empty squares out of 161280** (about 69%). The least
represented class/background has five distinct training positions; validation
and evaluation have minima of two. This supports testing a training-only sampler,
not claiming the initial data is balanced or guarantees generalization.

## Distribution and balancing

All squares are retained, including repeated empty squares. No oversampling,
undersampling, augmentation or deduplication is applied. Validation/evaluation
keep their natural source distributions. Related game positions and every
style/size/view stay in their original source-group partition. Never split crops
randomly, or use pixel duplicates alone to decide which partition owns a square.

The [build report](../../data/reports/digital-square-corpus-v1.json) records class ×
background counts by partition and configuration, unique position/group counts,
missing combinations and distinct positions supporting each class/background.
Large screenshot counts do not compensate for few independent positions.

Optional inverse-frequency weights are provided **only from verified training**:
`training_square_count / (26 × training_count_for_class_and_background)`.
They are not applied. A future training sampler may use them after validation;
a missing bucket gets `null` rather than an invented weight. Do not apply this
sampling to validation/evaluation or recompute it from those partitions.

## Build and inspect

Run from the repository root with the existing Python environment. The original
captured PNG/JSON files must be present; the committed capture report alone is
not sufficient. No network or browser is used.

```bash
python -m tools.build_square_dataset --mode both --output-root .cache/digital-square-corpus-v1 --report data/reports/digital-square-corpus-v1.json
python -m pytest tests/test_square_dataset.py
```

`--mode verified` (default) builds only classifier-isolation data;
`--mode detected` builds only the detected-bound inputs. A complete build is
published atomically, with `dataset.json`, one JSONL index per mode, and arrays
under `<mode>/<split>/<configurationId>/<positionId>-<orientation>.npz`.
Invalid source labels/hashes abort the build, leaving no partial destination.
Existing destinations are never overwritten; use a new directory for another
build. Expected detection failures are retained as records, not treated as corrupt
source data. Exit codes are 0 for a completed build and 1 for a build failure.

Inspect a real training crop without needing PyTorch:

```python
import json
from pathlib import Path
import numpy as np
from PIL import Image

root = Path('.cache/digital-square-corpus-v1')
with (root / 'verified.jsonl').open() as index:
    row = next(json.loads(line) for line in index
               if json.loads(line)['split'] == 'training')
with np.load(root / row['array'], allow_pickle=False) as board:
    print(row['cells'][0])  # a8 label and source image coordinates
    Image.fromarray(board['images'][0]).save('.cache/square-preview.png')
```

Arrays and indexes stay in ignored `.cache/`; only code, tests, documentation and
the summary report are committed. Preserve them before clearing the cache, or
rebuild from preserved source captures. The report pins capture/position metadata,
preprocessing, class order, source-code hashes and index hashes. Each index pins
its arrays and source PNGs.

Tests cover all 64 pixel identities in both views, upright drawings, all 13 labels,
square parity, fractional bounds, saved arrays, changed sources, split violations,
atomic publication, detection failures/wrong bounds and training-only weights.
The [first trained classifier and independent comparison](neural-classifier.md)
now use this dataset; templates remain the default recognition backend.
