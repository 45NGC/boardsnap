# First PyTorch baseline

**English** | [Español](../es/neural-classifier.md) · [Overview](README.md)

Step 6.4 adds an optional CPU classifier and a measured comparison. The existing
`boardsnap` CLI and `pipeline.recognize_image` continue to use templates. The
network is explicitly loaded through `boardsnap.neural.NeuralClassifier`.

## Scope and architecture

`small-square-cnn-v1` has **39709 parameters**. It receives RGB 64 × 64 crops,
converts uint8 NHWC to float32 NCHW and divides by 255. The model applies 2× average
pooling, three 3×3 stride-2 convolutions (8/16/32 channels with ReLU), a 64-unit
hidden layer and 13 output logits. Classification returns only the argmax label;
public recognition still returns only `piecePlacement`.

The fixed class order is `empty, P, N, B, R, Q, K, p, n, b, r, q, k`. Empty becomes
`None` when calling the existing output builder. Training and inference share one
preprocessing function; no implicit resizing, channel swapping or augmentation
is performed. Production board normalization still creates the 64 × 64 crops.
No pretrained weights, Torchvision, GPU or network service is required at runtime.

## Data and reproducible training

The [square corpus](square-dataset.md) supplies 161280 verified-bound training
squares and 34560 validation squares. Training does not open evaluation archives.
Index and array hashes, canonical labels and group/position partition boundaries
are checked. This baseline preserves the original distributions and uses inverse
class-frequency cross-entropy weights calculated exclusively from training.
It does not use the optional class/background sampling weights from step 6.3.

[The frozen configuration](../../tools/train-clean-v1.json) specifies seed 20261009,
12 epochs, batch size 512, AdamW learning rate 0.002, weight decay 0.0001 and four
CPU threads. Every epoch uses a deterministic shuffle from seed + epoch. PyTorch
deterministic algorithms are enabled. Python, NumPy and PyTorch seeds are fixed.

Selection maximizes **validation whole-board correctness**, then macro recall,
then minimizes unweighted validation cross-entropy. Exact ties keep the earlier
epoch. There is no selection by training accuracy or final-evaluation results.
The measured run selected epoch 12. Epoch count and settings were fixed before
consulting the evaluation set; no tuning followed its results.

Checkpoints contain current weights, optimizer, epoch, PyTorch RNG state,
validation history and the best weights so far. `last.pt` is replaced atomically
after each completed epoch. An interruption within an epoch resumes from its
start. Configuration/data/environment changes are rejected on resume. Tests
compare resumed and uninterrupted weights and validation results exactly.
Reproducibility is scoped to the recorded software/CPU configuration, not arbitrary
PyTorch versions or hardware. Wall-clock times are naturally not deterministic.

A second complete 12-epoch run on the real corpus reproduced every selected
weight tensor, every epoch's validation metrics and even the saved artifact's
SHA-256 exactly. The [reproduction record](../../data/reports/neural-clean-v1-reproducibility.json)
pins both runs and their environment. It is a reproduction check, not another
hyperparameter trial.

## Installation and commands

Run from the repository root in the existing virtual environment. For this Linux
CPU baseline, install the official CPU build first:

```bash
python -m pip install 'torch==2.14.1' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev,ml]'
python -m tools.train_neural --dataset .cache/digital-square-corpus-v1 --run .cache/neural-clean-v1
# Resume the same frozen run after an interruption
python -m tools.train_neural --dataset .cache/digital-square-corpus-v1 --run .cache/neural-clean-v1 --resume
python -m pytest tests/test_neural.py
```

The completed run already exists locally. Use another `--run` directory for an
independent reproduction. The original source captures and square corpus are
required for training/evaluation. Commands are repository tools, not part of the
installed recognition CLI.

Each run writes:

| File | Contents |
| --- | --- |
| `last.pt` | Resumable epoch checkpoint, including optimizer and best state |
| `best.pt` | Selected state dictionary plus architecture, class order, input/preprocessing, data hashes, config and environment |
| `training.json` | Epoch history, selected validation result and artifact hash |

`best.pt` is about 161 KiB. The artifact stays under ignored `.cache/`; committing
code and reports does not distribute it. Preserve it and its report separately.
The existing artwork/data terms still apply; this experimental baseline is not
a release or a change in licensing. No model download is performed automatically.

PyTorch's [saving/loading guide](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)
describes state dictionaries and optimizer checkpoints. Loading here uses
`weights_only=True`, CPU mapping, strict parameter validation and `eval()`;
inference uses `inference_mode()`. Invalid artifacts raise `ClassificationError`
with the existing `PROCESSING_FAILED` code.

## Explicit CPU inference

```python
from boardsnap.neural import NeuralClassifier

model = NeuralClassifier('.cache/neural-clean-v1/best.pt')
result = model.recognize_image('image.png', orientation='black-bottom')
print(result)  # only {"piecePlacement": "..."}
```

This method reads pixels only, runs detection/normalization/segmentation and
reorders predictions using the explicit view. It accepts `white-bottom` or
`black-bottom`; it does not implement automatic coordinate reading. The existing
template API retains its `auto` behavior. `predict_ids` accepts uint8 square
batches; `classify_squares` accepts an 8×8 matrix of Pillow crops. Runtime inference
never reads training labels, position manifests or evaluation reports.

## Evaluation and comparison

```bash
python -m tools.evaluate_neural --dataset .cache/digital-square-corpus-v1 --model .cache/neural-clean-v1/best.pt --split evaluation --output data/reports/neural-clean-v1-evaluation.json
```

The [measured report](../../data/reports/neural-clean-v1-evaluation.json) pins the
selected artifact and dataset, records per-class precision/recall/F1 and confusion
counts, exact boards, exact base positions across variants and each configuration.
It separates:

- Verified-bound square classification, using identical crops for both methods.
- The actual image-to-placement pipeline, re-reading the original PNG and running
  detection again. Reference bounds never enter the recognizer. Errors count as
  incorrect boards/squares rather than disappearing from the denominator.
- The paired template-supported subset: brown/cburnett, blue/cburnett and green/Neo.
- The remaining combinations, whose templates are unavailable and are not scored
  as if they supported those designs.

Both methods achieved **90/90 complete boards on the shared subset**. The network
also achieved **450/450 on the additional combinations**, for 540/540 total and
34560/34560 squares, both with verified bounds and through the full pipeline.
Every class's measured precision and recall is 1.0. These are **12 held-out base
positions in three source groups**, rendered in many variants, not 540 independent
positions. Same piece designs/backgrounds occur in training; this is not a test
of unseen designs, overlays, real-play interfaces, native apps or book diagrams.
Compact-size coverage gaps from the square-corpus report still apply.

CPU latency excludes dataset verification/archive loading for the classification
measurement; pipeline timing includes PNG I/O and all recognition stages. Reports
include median/p95 times for the shared subset separately from new coverage.
Each backend runs in its own fresh process. Reported peak RSS includes imports,
the verified dataset index, model and evaluation bookkeeping: it is **not just
weight memory**. Timing depends on machine load; accuracy does not establish that
a deployment's latency or memory budget is met.


On this Intel Core i5-10400 CPU (four PyTorch threads, one OpenCV thread), the
paired 90-image subset gave these measurements; models and file caches were warm:

| Measurement | Neural | Templates |
| --- | ---: | ---: |
| Median classification / board | 1.74 ms | 42.49 ms |
| Median full pipeline / image | 127.01 ms | 158.19 ms |
| Peak evaluation process RSS | 566.1 MiB | 209.0 MiB |

Templates remain the default. The network provides a reproducible clean-style
reference; next compare broader real captures, highlights and arrows, and decide
explicitly when/how to expose the learned backend in the main CLI and app.
