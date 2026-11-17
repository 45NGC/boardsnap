# Targeted photographic training

**English** | [Español](../es/targeted-photo-training.md)

One bounded training run completed on November 13, 2026. The candidate is stored
at `.cache/neural-phone-targeted-v1/best.pt`. **Keep using
`.cache/neural-phone-v1/best.pt`: the new candidate was not promoted.** It improves
some piece classes but loses previously correct photographic and digital boards.

- [Frozen training plan](../../data/manifests/phone-targeted-training-v1.json).
- [Measured results, per-class metrics and prediction changes](../../data/reports/neural-phone-targeted-v1.json).
- [Paired intake, geometry and overlap review](targeted-photo-intake.md).

## Data and reproducibility

The new dataset at `.cache/phone-targeted-training-v1/` contains **184 training
boards (11,776 squares)**: 160 existing photographs plus the 24 targeted photos.
The **30 validation boards (1,920 squares)** remain unchanged. Their JSONL index
checksum and every crop archive are identical to the previous dataset. The 16
paired screenshots remain references, not additional training boards.

The eight new source groups stay intact and enter training only in this derived
plan; the original development intake and crop export are preserved. No observed
overlap was found, but unknown game/video identities still prevent a fully
verified source-independence claim. Existing validation is reused development
evidence, not independent release acceptance.

Training starts from **phone-v1**, not the previously rejected robustness-v2
experiment. It uses the existing small CNN, RGB 64×64 inputs, CPU, seed 20261113,
20 epochs, batch size 256, AdamW learning rate 0.00005 and weight decay 0.0001.
Inverse-frequency class weights use training labels only. Distillation from
phone-v1 applies only to the 160 previous training photos (temperature 2,
weight 1), allowing the new photographs to learn from their reviewed labels.
No new image augmentation was introduced in this run.

Checkpoint selection first prioritizes the 19 validation boards that phone-v1
already gets completely correct, then total exact boards, macro recall and loss.
The selected checkpoint is **epoch 12**, retaining 17 of those 19 controls.
`last.pt` stores epoch 20 and optimizer state for interruption recovery;
`best.pt` stores the selected candidate. Selection does not imply acceptance.
The plan and report record hashes of inputs, baseline, candidate and code.

## Comparison with phone-v1

Both models receive the same crops from reviewed geometry, isolating classification.

| Measurement | phone-v1 | Targeted candidate |
| --- | ---: | ---: |
| Photo-validation exact boards | 19/30 | 19/30 |
| Photo-validation correct squares | 1,871/1,920 (97.45%) | 1,873/1,920 (97.55%) |
| Photo-validation macro recall | 94.15% | 95.55% |
| Digital-validation exact boards | 3,128/3,132 | 3,119/3,132 |
| Digital-validation square accuracy | 99.9980% | 99.9930% |

Photographic gains: `chesscom-img_5399`, `video-img_5403`.
Photographic losses: `lichess-img_5388`, `lichess-img_5390`.
Digital validation loses nine exact boards and gains none; the report lists them.

The candidate improves black-pawn, black-knight and black-bishop recall, among
other classes, but correct empty squares decrease from **1,185/1,188 to
1,176/1,188**. Those false pieces matter for complete-position accuracy.

On the **24 new training photos**, square accuracy increases from **87.57% to
97.53%**, and exact boards from **2/24 to 7/24**. This measures learning on seen
examples, not generalization. By appearance, exact boards change from 0/12 to
2/12 for thin-stem pieces, 0/6 to 3/6 for shaded pieces, and remain 2/6 for the
rounded-king appearance.

Warm classification of 64 squares has a candidate median of about **1.4 ms** on
this machine. File loading, detection and rectification are excluded. Peak RSS
was about **333 MiB** for the photo comparison and **1,196 MiB** for the digital
comparison; these figures include both models, imports and report/index data,
not model-only memory or mobile-device requirements.

## Checks and decision

The 56 focused tests passed (training overlap guards, paired export, overlap
review, neural loading and resumable training). Baseline weights are unchanged.
A full photo CLI smoke test on `position7-IMG_5490.png` returned exit code 0,
only `piecePlacement` on stdout and empty stderr. **Its position was incorrect**;
this confirms command/model loading, not successful recognition of that photo.

The candidate fails the preservation criteria fixed before training. Keep it as
an experimental artifact and retain phone-v1 as the recommendation. Before another
run, inspect false pieces on empty cells and plan replay of existing **digital
training** examples together with the photographs. Do not move validation failures
into training or repeat runs against final reserved data. No final evaluation,
model distribution, default-model change or detector change was performed.

## Commands

The completed run is already available; do not retrain to load it. For an explicit
experimental test (not a recommended replacement):

```bash
boardsnap "my-photo.jpg" --input-type photo --model .cache/neural-phone-targeted-v1/best.pt --orientation white-bottom
```

The training command uses the frozen plan and refuses to overwrite a run:

```bash
python -m tools.train_targeted_photos
```

For an actual interruption, `--resume` reuses the checkpoint and verifies the
configuration. To reproduce separately, use `--dataset .cache/phone-targeted-training-rebuild
--run .cache/neural-phone-targeted-rebuild` with the same plan. All local source
manifests, reports, arrays and baseline weights are required.

```bash
python -m tools.compare_validation --dataset .cache/phone-targeted-training-v1 --baseline .cache/neural-phone-v1/best.pt --candidate .cache/neural-phone-targeted-v1/best.pt --output .cache/phone-targeted-comparison-recheck.json
python -m pytest tests/test_targeted_photo_training.py tests/test_targeted_photo_overlap.py tests/test_targeted_photo_squares.py tests/test_neural.py -q
```

The [completed regression diagnosis](targeted-photo-regressions.md) inspects the eleven lost boards, their clean controls and all changed validation squares without another training run.
