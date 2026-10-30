# Photographic training and validation data

**English** | [Español](../es/phone-training-data.md)

The reviewed photographs now have a loader-compatible dataset at
`.cache/phone-training-v1/`. The export itself did not train or change any model.
The subsequent [first photographic training run](phone-training.md) is now complete.

| Partition | Photographs | Squares | Export |
| --- | ---: | ---: | --- |
| Training | 160 | 10,240 | Existing development NPZ archives copied byte-for-byte |
| Validation | 30 | 1,920 | Newly rectified from the reviewed four corners |
| Final evaluation | 0 | 0 | Not accessed |

`lichess-photo-8` remains excluded because of its ambiguous capture animation.
The original manifests, originals, review images and `.cache/phone-squares-v1/`
are preserved. The [frozen partition plan](../../data/manifests/phone-training-v1.json)
records the explicit development-to-training migration, every included photo ID,
the exclusion and SHA-256 hashes of the three source documents.

## Files

- `verified.jsonl`: the combined 190-board index consumed by the training loader.
- `training.jsonl` and `validation.jsonl`: separate indexes of the same records.
- `training/*.npz` and `validation/*.npz`: 64 RGB images of 64×64 pixels plus
  64 class IDs per photograph. Class order is stored in `dataset.json`.
- `dataset.json`: preprocessing, split counts, coverage by class/background,
  provenance, index hashes and readiness flags.
- `partition-plan.json`: frozen plan copied into the export.
- `index.html` and `previews/`: all 64 labeled crops for each board.

Every record retains its photo, source, original group, canonical position,
orientation, corners, annotation review and pixel/archive hashes. Training
records additionally retain `sourceSplit: development` and `reusedFrom`.
The [export report](../../data/reports/phone-training-v1.json) is versioned;
the images and generated dataset stay in `.cache`.

The [loader verification report](../../data/reports/phone-training-v1-verification.json)
confirms that both complete partitions load through `tools.neural_data`, all 160
reused archives are byte-identical, and all 30 validation arrays match their
previously reviewed rectified images pixel-for-pixel after canonical ordering.

## Separation and preprocessing

The entire original usable group becomes training, and the entire new group
remains validation. Related positions and all their variants stay together.
Source separation is user-confirmed; unknown identities are not presented as
independently verified. The build rejects cross-partition position families,
known game overlaps, image overlap and inconsistent labels or reviews.

Validation uses the same preprocessing as the original crops: full RGB image,
reviewed quadrilateral to 512×512 with OpenCV linear interpolation, then 8×8
cells. Black-bottom reverses cell order, not the pixels inside each piece.
All 64 cells are retained, without balancing or augmentation. Validation
frequencies must stay unchanged; future balancing applies only to training.
Both partitions cover all 13 classes on light and dark squares, but coverage
is uneven: validation contains only one black queen on a light square.

The earlier intake manifests/reports describe their state before export and
remain pinned unchanged. The new dataset and export report are the current
readiness records: `readyForTraining` and `readyForValidation` are true.
They mean the arrays and indexes are available, not that a model meets accuracy
criteria. Automatic photographic detection is not measured by reviewed corners.
This export is a photo-only pilot; combining it with digital datasets requires
an additional overlap review and an explicit training configuration.

## Commands

Reproduce the export in a new directory (existing destinations are refused):

```bash
python -m tools.build_phone_training_dataset --output .cache/phone-training-v2 --report .cache/phone-training-v2-report.json
```

This uses the same frozen `phone-training-v1` data recipe; choosing a new output
directory alone does not create a new data version. Changed inputs require a new
reviewed plan. Corrupt archives, changed inputs or stale reviews prevent publication.
The complete directory is published only after checks pass.

The training tool's future `--dataset` value is `.cache/phone-training-v1`.
Do not start a new run merely to check the data. To inspect the indexes:

```bash
python -c 'from pathlib import Path; from tools.neural_data import read_index; m, rows = read_index(Path(".cache/phone-training-v1")); print(m["splitCounts"], len(rows))'
python -m pytest tests/test_phone_training_dataset.py tests/test_phone_squares.py tests/test_phone_validation.py -q
```

Training and model evaluation are separate from this export. See the completed
[photographic training run](phone-training.md) for its initial model, configuration,
results and test commands; the screenshot models remain preserved references.
