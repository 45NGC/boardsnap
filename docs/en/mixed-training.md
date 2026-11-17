# Mixed training dataset preparation

**English** | [Español](../es/mixed-training.md)

This preparation combines already annotated digital screenshots and photographs,
without training another model. Original data, groups and both existing validation
sets remain unchanged. `neural-phone-v1` remains the recommended baseline.

- [Plan and frozen source hashes](../../data/manifests/mixed-training-v1.json).
- [Preparation and overlap report](../../data/reports/mixed-training-v1.json).
- [Previous inventory](training-coverage.md).

## Explicit proportions

The initial draw contains **32,000 square samples**:

| Pool | Samples | Share |
| --- | ---: | ---: |
| Clean digital boards | 6,400 | 20% |
| Digital simple marks | 3,200 | 10% |
| Digital arrows, crossings and combinations | 4,800 | 15% |
| Additional arrowhead corpus | 1,600 | 5% |
| Old photos without visible wood | 9,600 | 30% |
| Old wood photos | 1,600 | 5% |
| The 24 new targeted photos | 4,800 | 15% |

Digital and photographic material each contribute 50%. Digital variants cannot
dominate merely through their number, and new photos do not replace most prior
experience. The targeted pool also includes six wood photos; wood coverage is not
limited to the 5% old-wood pool.

**These are initial quotas, not demonstrated optimal proportions.** Repeating the
five old wood photographs is deliberate and carries an overfitting risk. The draw
does not represent 32,000 independent or different squares. The report distinguishes
occurrences, unique board/cell pairs, boards and positions.

Within each pool, allocate evenly by group, position, style combination and board
variant. A fixed seed distributes remainders without always favoring the first
identifier. Eligible cells are shuffled before repeating them. Marked digital
variants reuse `training_indices` with its safety halos; photos and clean controls
retain all 64 cells. No transformations, losses or class reweighting are introduced.
The seed is `20261114`.

Old unresolved provenance remains a conservative group, not an identified game.
Balancing its positions does not establish new origins or permit splitting related
photographs between training and validation.

## Validation overlap checks

Protected data comprise the existing **3,132 digital and 30 photographic validation
boards**. Checks across sources cover:

- Source group and position identifiers.
- Placement families, including rotations, reflections and swapped piece colors.
- Known game/video identities.
- Available original, normalized and source image file hashes.
- Crop archive hashes and complete decoded canonical board pixel hashes.

Any match blocks assembly. Images and variants are never silently moved or removed
to hide an overlap; the entire affected group must be reviewed first. Duplicate
training archives also block assembly to prevent accidental double weighting.

No overlap was observed by these checks. **Unknown game origins are still not
proven independent**, and these checks cannot detect every approximate duplicate
with different compression or framing. Position and hash checks complement rather
than replace provenance. Previous audit limitations remain. These consulted sets
are model-selection validation, not a new independent final evaluation.

Validation is not balanced: each board retains its original record and 64 cells.
The mixed index wraps that record with a source-dataset reference. No final-evaluation
crop archives are opened and no inference runs.

## Prepared artifacts

Under `.cache/mixed-training-v1/`:

- `dataset.json`: quotas, counts, audit and hashes.
- `training-boards.jsonl`: eligible board inventory, eligible cells and original
  archive references with labels, groups and partitions.
- `validation.jsonl`: references to unchanged validation records.
- `sampling-epoch-000.npz`: board index / cell index for each drawn sample.
- `training-images.npy`: 32,000 unchanged 64 × 64 RGB `uint8` square crops.
- `training-labels.npy`: their classes in the existing class order.

The indices retain the complete eligible material. The initial draw is reproducible;
`sample_epoch` can produce a new draw with the same quotas for another epoch number.
Future resampling must materialize its corresponding pixels and preserve provenance;
the previous trainer does not do this automatically. Original NPZ archives are
unchanged, and entire corpora have not been duplicated.

This custom mixed format has its own reader; do not pass it to the old `load_split`,
which would treat all boards equally. From the repository:

```python
from pathlib import Path
from tools.prepare_mixed_training import load_prepared_epoch

images, labels = load_prepared_epoch(Path('.cache/mixed-training-v1'))
print(images.shape, labels.shape)  # (32000, 64, 64, 3), (32000,)
```

The reader checks hashes before returning read-only arrays. Next, wire this mixture
into training and freeze the configuration and regression criteria before running
one candidate. **No model has been trained or replaced in this step.**

Reproduce in a new directory without overwriting prepared data:

```bash
python -m tools.prepare_mixed_training --output .cache/mixed-training-v1-reproduction --report .cache/mixed-training-v1-reproduction-report.json
python -m pytest tests/test_mixed_training.py tests/test_training_coverage_inventory.py tests/test_targeted_photo_overlap.py -q
```

## Completed verification

**24 focused tests pass.** The prepared dataset was also loaded read-only; all
32,000 labels and exact quotas were checked, with exported crops compared against
original arrays from each of the seven pools. All sampled pools contain the 13
classes. The draw contains 27,290 distinct board/cell pairs; remaining occurrences
are deliberate repeats.

All 3,162 validation records match their originals, and baseline/rejected-candidate
model checksums remain unchanged. There are still 141 training photos and 20
validation photos without verified source identifiers: the audit establishes no
observed overlaps, not fully proven source independence.

The [mixed training configuration and acceptance plan](mixed-training-plan.md) freezes one 12-epoch attempt, separate photo/digital regression gates and CPU/CLI requirements. Training has not started.
