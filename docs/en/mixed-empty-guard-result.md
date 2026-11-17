# Result of excluding false-piece teacher targets on empty cells

**English** | [Español](../es/mixed-empty-guard-result.md)

**The change does not improve validation. Keep `.cache/neural-phone-v1/best.pt`.**
One bounded twelve-epoch attempt completed on November 16, 2026. No epoch passes
the acceptance gates and no `best.pt` is exported.

- [Plan frozen before execution](../../data/manifests/neural-mixed-empty-guard-v1-plan.json).
- [Complete report and paired epoch/cell comparison](../../data/reports/neural-mixed-empty-guard-v1.json).
- [Motivating diagnosis](mixed-training-review.md).
- [Mixed-training control](mixed-training-result.md).

## The single experimental change

The fixed 32,000 samples, labels, splits, cached teacher targets, validation crops,
phone-v1 initialization, seed, architecture, preprocessing, class weights,
optimizer, twelve epochs and checkpoint rules remain unchanged. Training does
not resume from rejected mixed weights.

The new mask uses only training labels:

```python
old_teacher_mask & ~((label == empty) & (teacher_argmax != empty))
```

The 19 exposures of seven reviewed empty cells are removed from **distillation**,
not supervised learning. There are 27,181 teacher-supervised and 4,819 supervised-only
samples; all 32,000 retain their labels and supervised loss. Original teacher-cache
cohort counts remain in the plan's `loss` section; effective counts are recorded
in `intervention` and `mask-audit.json`. Other conflicts on occupied cells and all
digital replay remain unchanged. KL is averaged over the new mask, using the same
implementation as the original runner.

The unchanged `run_epochs` provides domain/condition gates, safe-only selection
and resume. The new wrapper checks that no other scientific setting differs and
that excluded cells match the reviewed training empties. There are no rules based
on validation photo names.

## Last-epoch result

The final epoch is diagnostic, **not an accepted checkpoint selection**.

| Metric | phone-v1 | Previous mixed run | Guarded mixed run |
| --- | ---: | ---: | ---: |
| Exact photographic boards | 19/30 | 20/30 | 20/30 |
| Correct photographic squares | 1,871/1,920 | 1,877/1,920 | 1,877/1,920 |
| Photographic empty cells predicted as pieces | 3 | 8 | 8 |
| Photographic pieces predicted as empty | 26 | 19 | 19 |
| Exact digital boards | 3,128/3,132 | 3,128/3,132 | 3,128/3,132 |
| Correct digital squares | 200,444/200,448 | 200,444/200,448 | 200,444/200,448 |

All **202,368 final predictions individually match the mixed control**, not just
its aggregate accuracy. Its six photographic regressions relative to phone-v1
remain, including `lichess-img_5392` a7 (black pawn → black rook) and
`lichess-img_5390` d8 (empty → black queen).

Across all twelve epochs, only two transient differences occur:

- Epoch 5: `chesscom-img_5398` e3 becomes a black knight instead of empty; the
  same-epoch control was correct.
- Epoch 10: `lichess-img_5388` d8 becomes a black queen instead of empty; the
  same-epoch control was correct. The guarded run reaches 20 exact photos one
  epoch later.

Digital predictions match the control at every epoch. Training/validation loops
sum to approximately 91 seconds, excluding initial file/cache verification; this
is not a CLI latency benchmark.

## Interpretation

The conflict between empty labels and erroneous teacher targets existed and was
removed for the seven intended cells. **That change was insufficient to improve
validation predictions under this configuration.** This does not show that
teacher targets never matter, that the architecture is too small, or that more
epochs would help. Training-set classification was not measured again.

Keep the original decision: retain phone-v1, do not extend epochs, do not lower
thresholds after seeing results, and do not automatically start another attempt.
A further experiment needs a different hypothesis and an explicit plan; repeating
this same intervention is not supported by the observed results.

## Artifacts and verification

`.cache/neural-mixed-empty-guard-v1/` contains `execution.json`, `mask-audit.json`,
`training.json`, `last.pt` and all twelve prediction files. `last.pt` is diagnostic
only, not the recommended model. Both caches are read from the control run after
hash verification, without duplication or recomputation. Reference models and
artifacts remain intact.

**18 targeted tests pass**, covering mask scope and immutability, unchanged recipe,
acceptance rules, runner resume/selection and image-level comparison that exposes
trades hidden by aggregate accuracy. The actual checkpoint loads successfully
and frozen reference hashes are verified.

Promotion CPU benchmarks and complete CLI regressions **were not run**, because
no epoch passed the quality gate. Independent final evaluation remains untouched,
and application behavior is unchanged. The validation set remains previously
consulted model-selection data.

```bash
# Regenerate the report from saved predictions, without training or inference.
python -m tools.report_mixed_empty_guard
# Only for interruption of the identical attempt; a complete run is not extended.
python -m tools.train_mixed_empty_guard --resume
```

The [square-root weighting experiment](mixed-sqrt-result.md) reduces false pieces from 8 to 5 without increasing omissions versus control. This is partial improvement; phone-v1 remains the reference and the new model is experimental.
