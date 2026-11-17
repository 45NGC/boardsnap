# Mixed training configuration and acceptance

The [mixed training result](mixed-training-result.md) completes the frozen 12-epoch run. Digital predictions are preserved at the last epoch, but a lost photo and additional false pieces block promotion; keep phone-v1.

**English** | [Español](../es/mixed-training-plan.md)

Frozen on **November 14, 2026**, before launching training. The goal is to improve
the photographic classifier while retaining `neural-phone-v1` successes, including
screenshots. This does not automatically replace the separate conservative digital
model or establish final application release acceptance.

- [Machine-readable plan and frozen inputs](../../data/manifests/neural-mixed-v1-plan.json).
- [Preflight report](../../data/reports/neural-mixed-v1-preflight.json).
- [Mixed dataset preparation](mixed-training.md).

## One bounded attempt

| Setting | Value |
| --- | --- |
| Initialization | `.cache/neural-phone-v1/best.pt`, pinned SHA-256 |
| Architecture | Unchanged `small-square-cnn-v1` |
| Input | 64 × 64 RGB; `uint8` → NCHW `float32` / 255 |
| Data | Existing 32,000-sample draw; 50% digital, 50% photographic |
| Maximum epochs | 12 |
| Batch size | 256 squares |
| Optimizer | Fresh AdamW; learning rate `0.00002`, weight decay `0.0001` |
| Seed | `20261114` |
| Execution | CPU, four threads, deterministic algorithms |
| New augmentation | None |
| Epoch resampling | None; shuffle the fixed draw with seed + epoch |

Initialize from the stable model, not the rejected candidate. The lower learning
rate (previously `0.00005`) and bounded horizon aim to limit abrupt changes; they
do not guarantee improvement or establish the causal contribution of each factor.

Supervised loss keeps inverse-frequency weighted cross entropy, calculated only
from the frozen 32,000 training labels. The plan records all class counts and exact
weights. No additional class resampling is applied.

Distill the same `phone-v1` at temperature 2 and weight 1 on **27,200 previous-data
samples**, including digital replay. The **4,800 new targeted samples** use their
supervised labels only, avoiding teacher targets that would preserve errors on
new appearances. There is no second teacher and no validation-derived training
target. The old-wood quota repeats five photographs and carries overfitting risk.
These proportions and optimizer settings are initial engineering choices, not
proven optimal parameters.

## Frozen reference and quality gates

These are existing predictions on **verified board crops**, not detection or CLI
performance:

| Metric | Photographs | Digital screenshots |
| --- | ---: | ---: |
| Validation boards | 30 | 3,132 |
| Baseline exact boards | 19 | 3,128 |
| Baseline correct squares | 1,871 / 1,920 | 200,444 / 200,448 |
| Empty squares predicted as pieces | 3 | 1 |
| Real pieces predicted empty | 26 | 0 |

All accuracy conditions must pass:

1. Reach **at least 20/30 exact photos**, preserving each of the previous 19.
2. Preserve each of the **3,128 exact digital boards** from `phone-v1`.
3. Do not decrease correct-square counts or increase false/missed-piece counts
   in either domain.
4. Do not decrease correct counts for any of the 13 true classes in either domain.
   With unchanged labels and class frequencies, this is nondecreasing class recall.
   Report class precision and confusion matrices as well.
5. Do not reduce exact boards/correct squares or increase false/missed pieces within
   frozen strata: platform, orientation, visual condition; photo appearance and
   background; digital piece/background/layout/mark configuration. Conditions can
   overlap and their counts must not be added.

These are intentionally strict gates. A tradeoff that gains some boards while
losing protected successes does not pass. Any later policy change requires an
explicit documented revision, not a threshold adjustment after seeing results.

## Epoch selection

Validate both complete datasets after each epoch, retaining their full 64 squares
and natural frequencies. Discard unsafe epochs before ranking eligible checkpoints
by descending:

1. Photo exact boards.
2. Photo macro recall.
3. Photo correct squares.
4. Digital exact boards.
5. Digital correct squares.

Keep the earliest tie. A safe checkpoint still at 19/30 may be the best saved epoch
but does not satisfy the improvement gate. If no epoch is safe, there is no
promotable `best.pt`. The old `fit` selection rule is insufficient: summing controls
across domains could hide photo losses among thousands of digital boards.

Save configuration, hashes, weights, optimizer, RNG, history and selection state.
Resume interrupted work from the last completed checkpoint without restarting
completed epochs or extending the twelve-epoch horizon. No automatic parameter
search or additional runs are included in this plan.

## Selected-candidate checks before promotion

Passing accuracy alone does not authorize model replacement:

- **Comparable CPU measurements:** same machine, environment and four threads;
  one model per process, one frozen 64-square input, 20 warmups and 100 measurements
  in each of three fresh processes per model. Use the median of trial medians,
  median of trial p95 values and median of fresh-process peak RSS. None may exceed
  **1.25 times** baseline. This includes preprocessing/classification, excluding
  I/O, detection and rectification. Old two-model/full-corpus comparison RSS cannot
  be used as this memory baseline.
- **Complete pipeline:** retain existing baseline-correct CLI results on development
  and regression cases. Preserve detection, negative controls, orientation,
  piecePlacement-only success JSON, structured errors and exit codes. Reuse compatible
  saved results; if stale, compare both models under identical current code first.
- **Stratified evidence:** report every changed cell and board gain/loss by condition.
  Results on the 24 trained photos are training diagnostics, not generalization evidence.

Missing evidence means pending; any failed gate retains `phone-v1`. Independent
final images remain reserved. Consulted validation selects candidates and cannot
establish final release acceptance.

## State when the plan was frozen (historical record)

Preflight verifies baseline weights, data, labels, quotas, class counts, saved
prediction correspondence and input hashes, without inference or training. Policy
tests cover regressions hidden by aggregates, class/condition losses and changed
labels. Applying the policy to saved rejected-candidate predictions rejects its
two lost photos and nine lost digital boards again, without rerunning evaluation.

**Configuration is ready; the checked mixed loader and these gates still need to
be wired into a resumable runner before launch.** Existing weights remain intact.
There is no new model to try yet.

```bash
python -m tools.mixed_training_policy
python -m pytest tests/test_mixed_training_policy.py tests/test_mixed_training.py -q
```
