# Bounded review of mixed training

**English** | [Español](../es/mixed-training-review.md)

The [empty-label teacher guard experiment](mixed-empty-guard-result.md) is complete: final predictions do not improve over the mixed control. Keep phone-v1; no further training is started.

**Keep `neural-phone-v1`. One specific future intervention is justified: stop
distilling the teacher's false pieces on verified empty training cells. This
review does not execute that intervention or start another training run.**

The review reuses all twelve saved epoch predictions, cached teacher targets and
existing verified crops. No new inference, model changes, detector/preprocessing
changes, partition changes or final evaluation access occurred.

- [Reproducible report](../../data/reports/mixed-training-review-v1.json).
- [Local gallery: validation errors and training empty cells](../../.cache/mixed-review-v1/index.html).
- [Completed attempt](mixed-training-result.md).

## What regresses

At the last epoch, photos have **12 recovered cells, six regressions and two
wrong-to-wrong changes**. Every digital prediction matches phone-v1. The six
photographic regressions belong to four images:

| Photo | Square | Expected → candidate | Visual review |
| --- | --- | --- | --- |
| chesscom-img_5397 | e3 | empty → black knight | Dark wood, moire, small arrow fragments at left corners |
| lichess-img_5390 | d8 | empty → black queen | Dark wood with grain/banding; no overlay within the cell |
| lichess-img_5392 | c5 | empty → black queen | Dark wood with diagonal interference; no piece or overlay |
| lichess-img_5392 | a7 | black pawn → black rook | Complete centered shaded pawn, visible head, collar and base |
| video-img_5404 | e4 | empty → white king | Light background with strong coloured screen interference |
| video-img_5404 | e3 | empty → black knight | Dark green background with strong periodic interference |

All five new false pieces appear at epoch one and persist through all twelve.
The pawn-to-rook error starts at epoch two. There is no observed recovery trend
justifying a longer run. Several piece classes are affected, but foreground versus
background separation dominates.

## Crops and labels

Both models consumed identical crop archives from annotated corners, not automatic
detection. The analysis checks hashes and labels and reconstructs the existing
boards for inspection without changing their pixels.

The four boards show no swapped rows, cut pieces or neighbouring piece bodies
explaining the five empty-cell errors. Chess.com e3 has a small line along its
bottom border and arrow fragments, not a knight. The a7 pawn remains inside its
cell. **These observations do not justify changing geometry or orientation.**
They are not a new detector evaluation or proof of perfect subpixel boundaries.

Grain and screen interference are visible. Their individual causal contributions,
including 64×64 resampling and overlays, have not been isolated. Blanket smoothing
could erase thin pawns; a filter would need a controlled comparison including real
pieces before adoption.

## Available data and conflicting objectives

The fixed sample contains **19,409 empty cells out of 32,000 (60.65%)**:

| Photo pool | Empty exposures | Distinct photo/cell identities | Sampled photos |
| --- | ---: | ---: | ---: |
| Old photos outside the wood pool | 5,873 | 5,802 | 155 |
| Old wood photos | 970 | 194 | 5 |
| New targeted photos | 2,720 | 867 | 24 |

Repetition is not diversity: the 194 old wood empty cells each occur five times.
Pool names do not classify every texture or annotate overlays per cell. Relevant
backgrounds exist, but these counts do not establish coverage of all interference.

The teacher is phone-v1. Its cached soft targets show:

- **71 of 27,200 teacher exposures** contradict the labels: 59 distinct cells,
  all photographic. None of the 16,000 selected digital samples disagree.
- **19 exposures represent seven empty cells** predicted as pieces. Visual review
  of all seven supports their empty labels.
- Wood: `lichess-photo-42` d8 and `lichess-photo-44` d8 predict black queen;
  `lichess-photo-44` e8 predicts white king. Each occurs five times. Their d8
  grain/banding resembles the validation d8 failure.
- The other four are `lichess-photo-39` e5, `video-photo-45` d6,
  `chesscom-photo-38` d6 and `video-photo-39` d4: interference backgrounds, one
  exposure each. Paths, predictions and temperature-2 probabilities are recorded.

**The hard labels were not replaced with pieces.** Supervised loss teaches empty,
while the preservation term opposes moving away from the wrong distribution.
Initially KL loss is zero because teacher and student match; the conflict matters
as that distribution is corrected. This demonstrates conflicting objectives, not
causation for all six validation regressions. The remaining 52 nonempty conflicting
cells were not visually re-reviewed here.

Inverse-frequency weights also deserve monitoring: empty receives approximately
**7.69% of nominal summed CE weights**, despite accounting for 60.65% of examples.
A black-queen target has 48.52 times the per-sample weight of empty. This protects
rare classes by design. These are not measured gradient magnitudes: per-batch
weighted-mean normalization and KL matter. This alone does not justify changing
class weights, especially simultaneously with another variable.

## Intervention proposed by this review (subsequently executed)

1. Keep the frozen 32,000 samples, seed, class weights, splits, twelve epochs and
   phone-v1 initialization from the previous attempt.
2. Change only the distillation mask using the general training-label rule:
   `old_teacher_mask & ~((label == empty) & (teacher_argmax != empty))`.
   Do not use validation identities or predictions to select cells.
3. Keep supervised CE on **every** sample. This removes 19 teacher exposures
   (seven visually verified empty cells), leaving **27,181**. No images, labels,
   thin-piece examples or digital teacher targets are removed. Leave other
   conflicts unchanged to isolate this intervention.
4. Freeze a new plan and output directory before running; keep the completed mixed
   attempt as the control. Reuse its dataset and teacher cache; do not resume from
   the rejected epoch-twelve weights.
5. Compare the same full validations: false/missed pieces, classes, exact photos,
   digital results and individual losses. A useful change should reduce the mixed
   attempt's eight false pieces without sacrificing its recoveries. This is **not
   promotion**: original acceptance rules still apply, including retaining phone-v1
   successes, not exceeding its three false pieces and improving exact photos.
6. If unsuccessful, stop this hypothesis. Do not repeat seeds, extend epochs or
   lower thresholds after seeing results. Choose a separately planned data-diversity
   or loss-balancing intervention next, not both without evidence.

**No additional photos or architecture change are recommended yet.** The baseline
already solves these six cells, so insufficient network capacity is not established.
This is a small measurable intervention, but may be insufficient: only 0.07% of
teacher exposures change and the pawn-to-rook error is not directly addressed.
It does not guarantee acceptance or recovery of every photo.

Old provenance remains partly unknown: different placements do not prove unrelated
games. Previously consulted validation is model-selection material, not a substitute
for independent final evaluation.

## Reproduction

```bash
python -m tools.review_mixed_training
python -m pytest tests/test_mixed_training_review.py -q
```

Four tests pass, covering repeated exposures versus cell identity, new samples
without a teacher, exclusion of validation, consistent repeated targets and label
alignment. The real analysis has run against saved artifacts. Neither trainer nor
models are changed by this review.
