# Square-root class-weight experiment

**English** | [Español](../es/mixed-sqrt-result.md)

**Partial improvement, but no epoch meets every acceptance gate.** Keep phone-v1
as the reference. The new weights are experimental only; CLI behavior and existing
models remain unchanged.

- [Plan fixed before execution](../../data/manifests/neural-mixed-sqrt-v1-plan.json).
- [Report by epoch, class, appearance and cell](../../data/reports/neural-mixed-sqrt-v1.json).
- [Inverse-weight control](mixed-empty-guard-result.md).

## Experiment

**One twelve-epoch run completed on November 16, 2026.** Weights change from
`N / (13 * count)` to `sqrt(N / (13 * count))`, computed solely from the same
32,000 training labels. Black-queen/empty weight contrast falls from **48.52 to
6.97**. No other exponents were searched or tuned after viewing results.

CrossEntropyLoss with weighted `mean` divides by the sum of target weights in the
batch. Scaling all weights equally leaves this loss unchanged; no additional
normalization parameter was introduced.

The direct control is `neural-mixed-empty-guard-v1`. Its 19 excluded false-piece
teacher exposures and 27,181 remaining distillation samples are preserved. All
samples retain supervised loss. Data, splits, phone-v1 initialization, seed,
architecture, preprocessing, optimizer, twelve epochs and acceptance rules remain
unchanged. Teacher targets and validation crops are reused without inference or
regeneration. The original data preflight stays intact; the new formula has a
separate check against actual training counts.

## Final epoch: diagnosis, not accepted checkpoint selection

| Metric | phone-v1 | Guarded inverse-weight control | Square root |
| --- | ---: | ---: | ---: |
| Exact photographic boards | 19/30 | 20/30 | 20/30 |
| Correct photographic squares | 1,871/1,920 | 1,877/1,920 | 1,880/1,920 |
| Photographic false pieces | 3 | 8 | 5 |
| Missed photographic pieces | 26 | 19 | 19 |
| Missed photographic pawns | 19/370 | 13/370 | 13/370 |
| Exact digital boards | 3,128/3,132 | 3,128/3,132 | 3,128/3,132 |
| Correct digital squares | 200,444/200,448 | 200,444/200,448 | 200,444/200,448 |

The last epoch retains **every phone-v1 exact photo** and gains `video-img_5403`.
All final digital predictions match phone-v1 and the control. These are consulted
validation results, not independent generalization evidence.

Five cells change relative to the control:

| Image and square | Change | Outcome |
| --- | --- | --- |
| chesscom-img_5397 e3 | black knight → empty | Recovery |
| lichess-img_5390 d8 | black queen → empty | Recovery; whole photo correct again |
| video-img_5404 e3 | black knight → empty | Recovery |
| chesscom-img_5401 b2 | white rook → white pawn | Recovery |
| chesscom-img_5399 f8 | black bishop → white bishop | Regression versus control; phone-v1 also failed here |

Three cell regressions relative to phone-v1 remain: `lichess-img_5392` a7 (black
pawn → black rook), c5 (empty → black queen), and `video-img_5404` e4 (empty →
white king). Phone-v1 already failed these photos elsewhere, so none of its exact
photos are lost.

Epoch eleven reached 21/30 exact photos and 1,881 correct cells, but still had
five false pieces and was ineligible. The f8 bishop colour confusion returns in
epoch twelve. Epoch eleven was not selected by bypassing the gates or retrained
to recover its weights: policy only exports safe `best.pt` checkpoints. Saved
predictions remain available for every epoch.

## Thin pawns

The **two** `cc-thin-stem` photos contain 22 pawns:

| Metric | phone-v1 | Control | Square root |
| --- | ---: | ---: | ---: |
| Correct cells | 105/128 | 112/128 | 113/128 |
| Missed pawns | 16/22 | 11/22 | 11/22 |
| Pawns assigned another piece/colour | 5 | 5 | 4 |
| Exact photos | 0/2 | 0/2 | 0/2 |

Lower weight contrast does not increase omissions in these cases and recovers a
pawn previously called a rook. Both complete positions still fail; this small
sample does not establish style compatibility.

The reduction in false pieces supports this intervention on consulted validation.
It does not establish weighting as the only cause or this formula as optimal, nor
authorize automatic searches over further exponents.

## Decision and next step

Do not replace the reference: false pieces still exceed baseline (5 versus 3),
empty-class recall falls and some condition strata regress. Original gates remain
unchanged. Preserve this partial improvement as an experimental result rather
than restarting from scratch.

Before deciding whether to expose it as an experimental app option, compare its
full CLI pipeline against phone-v1 on known development screenshots and photos.
That would test whether gains with annotated corners survive automatic detection.
This needs no further training and is not final acceptance. The three remaining
cell regressions can guide later targeted data collection.

## Artifacts and checks

`.cache/neural-mixed-sqrt-v1/` contains `last.pt`, `training.json`, `execution.json`,
`mask-audit.json` and all twelve prediction files. **No `best.pt` exists.** The last
checkpoint loads with the standard loader, but is not promoted. Prior models and
plans retain their hashes.

**28 targeted tests pass**, covering weight derivation, isolated change, protected
control, teacher mask, runner/resume, acceptance and omission reporting. Training
and validation loops sum to approximately 94 seconds; this is not an inference
benchmark. Reporting uses saved predictions only.

**Pending:** CPU benchmarking and complete CLI regressions for this candidate.
Promotion checks were not run because quality gates fail. Independent final
evaluation remains untouched.

```bash
# Rebuild the report from saved predictions only.
python -m tools.report_mixed_sqrt
# Resume only an interrupted identical attempt; never extend completed epochs.
python -m tools.train_mixed_sqrt --resume
```

The [full CLI comparison](mixed-sqrt-cli.md) confirms improvement from 20 to 22 exact photos, but loses two real digital screenshots. The candidate remains photographic and experimental.
