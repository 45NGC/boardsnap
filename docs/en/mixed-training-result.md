# Mixed training result

**English** | [Español](../es/mixed-training-result.md)

**The bounded run completed all 12 epochs and is rejected for replacement. Keep
`.cache/neural-phone-v1/best.pt`.** No epochs, quotas, thresholds or validation
assignments were changed after seeing results.

- [Frozen plan](mixed-training-plan.md).
- [History, class/condition metrics and changed-cell report](../../data/reports/neural-mixed-v1.json).
- [Complete local training history](../../.cache/neural-mixed-v1/training.json).

## Implementation and execution

`tools/train_mixed.py` wires the checked mixed loader, distillation on 27,200 old-data
samples and separate domain/stratum gates. The 4,800 new-photo samples use supervised
labels only. The fixed 32,000-sample draw and original preprocessing remain unchanged.

**One real twelve-epoch training run** completed, taking approximately 87 seconds
across its training/validation cycles, excluding cache preparation and integrity
checks. Runner tests use tiny synthetic inputs, not additional real-corpus experiments.

Validation streams batches from a disk cache of the same verified crops; it does
not rerun detection/rectification or open independent final images. Teacher targets
are cached only for training samples. Every completed epoch saves predictions,
acceptance assessment, weights, optimizer, RNG and selection history. Resume requires
identical recipe, data, code and environment and reuses hash-checked caches.

No epoch met every preservation gate, so **no `best.pt` was generated**.

## Last epoch: diagnosis, not a selected checkpoint

The last three epochs reach 20/30 photos and 3,128/3,132 digital boards, but fail
preservation gates. These numbers specifically describe epoch 12:

| Metric | `phone-v1` | Epoch 12 |
| --- | ---: | ---: |
| Exact photo boards | 19/30 | 20/30 |
| Correct photo squares | 1,871/1,920 | 1,877/1,920 |
| Empty photo squares predicted as pieces | 3 | 8 |
| Real photo pieces predicted empty | 26 | 19 |
| Exact digital boards | 3,128/3,132 | 3,128/3,132 |
| Correct digital squares | 200,444/200,448 | 200,444/200,448 |

At epoch 12 **every digital prediction matches baseline**, including its four errors.
Digital successes were preserved, but photographic successes were not:

- `chesscom-img_5399` and `video-img_5403` become completely correct.
- `lichess-img_5390` is lost: empty d8 becomes a black queen.
- Additional false pieces occur in already incorrect images: `chesscom-img_5397`
  e3 → black knight; `lichess-img_5392` c5 → black queen; `video-img_5404`
  e4 → white king and e3 → black knight.
- `lichess-img_5392` a7 also regresses from black pawn to black rook.
- Several pieces in thin-pawn photos `5401` and `5402` recover, without making
  their complete boards correct. The report lists all affected cells.

A net gain of one photo is insufficient: two boards recover while one protected
success is lost. False pieces increase, empty-class recall drops and photographic
strata worsen. The candidate fails the frozen policy.

## Preserved artifacts

Under `.cache/neural-mixed-v1/`:

- `execution.json`: recipe, runner, baseline, dataset and environment fingerprints.
- `last.pt`: full epoch-12 checkpoint, **diagnostic/audit only; not recommended**.
- `epoch-001-validation.json` … `epoch-012-validation.json`: complete saved predictions
  and per-epoch gate assessments.
- `training.json`: history and keep-baseline decision.
- Validation and training-teacher caches with integrity metadata.

Original source data, baseline models, the conservative digital model and the frozen
plan remain unchanged. CLI behavior/configuration is unchanged.

## Verification and decision

**26 focused tests pass**, covering quotas/partitions, quality gates, safe-only
selection, earliest ties, teacher masks/cache reuse and resume equivalence to an
uninterrupted run. Tests also verify that resuming a completed run repeats no epochs.
The real final checkpoint is checked for compatibility with the classifier loader.

**Promotion CPU benchmarks and full CLI regressions were not run** because no epoch
passed the prerequisite quality gate. Those checks are not approved and are not
needed to justify rejection. Independent final evaluation remains untouched.
The 30 photo boards are consulted validation, not fresh independent generalization
evidence.

Next, investigate empty-versus-piece separation under texture/moire using these
saved predictions and existing training examples. The mixed replay retains digital
successes at the end of the run but does not by itself solve photographic false
pieces. Do not extend this run or start another without a specific diagnosis.
Continue using `--model .cache/neural-phone-v1/best.pt`.

Maintenance commands, not a request for another experiment:

```bash
# Only resume an interrupted identical run; a completed run does not extend.
python -m tools.train_mixed --resume
# Rebuild the summary from saved predictions, without inference.
python -m tools.report_mixed_training
python -m pytest tests/test_train_mixed.py tests/test_mixed_training_policy.py tests/test_mixed_training.py -q
```

The [bounded mixed-training review](mixed-training-review.md) identifies conflicting teacher targets on verified empty cells and proposes a single-variable test. No further training has started.
