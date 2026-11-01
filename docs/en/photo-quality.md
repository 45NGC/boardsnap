# First-version quality priorities

**English** | [Español](../es/photo-quality.md)

**Decision: retain the digital candidate and photo v1. None of the experiments
passed the replacement checks.** The review and bounded experiments are complete;
photographic quality work and first-version acceptance are not declared complete.
Runtime behavior, thresholds, labels and partitions remain unchanged.

## Frequent failures

Reused digital measurements show 3,131/3,132 exact validation boards with verified
crops and 29/30 full-pipeline real-use screenshots. These are different consulted
sets, not new independent tests. Photo v1 scores 3,128/3,132 on those digital crops
and should not replace the digital candidate.

The photo pipeline detects 27/30 boards and recognizes 19/30 complete positions.
There are 31 square errors among detected boards. Priorities:

1. **Pawn presence:** 13 black and four white pawns become empty squares.
   `chesscom-img_5401` and `5402` account for 18/31 errors. The
   [visual training audit](../../data/reports/photo-training-style-audit-v1.json)
   found no matching thin-stem pawn design among representative pieces from all
   160 training photos. More epochs alone do not address this variety gap.
2. **Shaded pieces on wood:** `5397–5398` have five errors. Ten training photos
   contain similar shaded pieces, mainly over plain backgrounds; design absence
   alone cannot explain these failures.
3. **Rounded Lichess designs:** `5391–5392` have five errors involving queens,
   knights and kings. Related designs exist in training; no single cause is proven.
4. **Video/moire:** `video-img_5404` has two piece errors; `5403`, `5406` and `5407`
   are detection rejections. Classifier changes cannot fix their geometry alone.
5. **Marks:** exact photo positions are 9/12 with arrows and 17/26 with highlights.
   These overlapping subsets mix styles and detection failures. The single error
   in `5395` visually overlaps arrows on a pawn, not proof of a universal cause.

Forty of 55 direct Chess.com training photos repeat a conventional appearance.
Photo count overstates design diversity. The audit reviews representative pawns,
knights and kings; it does not establish official theme names or review every glyph.

## Rejected experiments

Require a whole-board gain, preservation of every previously exact board, and no
increase in square errors under both annotated and detected geometry.

| Method | Annotated: exact / square errors | Automatic: exact / square errors | Decision |
| --- | --- | --- | --- |
| Baseline | 19/30 · 49 | 19/27 · 31 | Keep |
| Warp to 1024, area resize | 19/30 · 47 | 20/27 · 31 | Loses two annotated boards |
| Warp to 2048, area resize | 19/30 · 47 | 20/27 · 33 | Loses two, more automatic errors |
| Average original + 1024 logits | 19/30 · 47 | 20/27 · 29 | Loses one annotated board |

Recovering `video-img_5404` does not justify a universal filter. Averaging loses
`video-img_5406` with correct corners. No filename, expected-position or theme
exception was added to hide this regression. See the
[resampling report](../../data/reports/photo-resampling-validation-v1.json).

One bounded 12-epoch training experiment then initialized from photo v1, with
one mild variant per training board: illumination, contrast, slight blur and
low-amplitude sinusoidal interference. This is not a physical camera simulator.
Labels/groups and validation stay fixed; distillation on original training
examples preserves previous-model predictions as a reference.

The selected candidate reaches 19/30, but correct squares fall from 1,871 to 1,864
and only 17/19 previously exact boards survive. It loses `lichess-img_5388` and
`5390`. **Rejected:** `.cache/neural-phone-robustness-v2/best.pt` is a failed
experiment, not the recommended replacement. Another run on unchanged data is
not justified. Previous weights and the reserved final evaluation are untouched.

## Targeted data and scope

- First collect approximately **8–12 training photos** of the `5401–5402` pawn
  design from at least three distinct games/positions. Include both piece colors,
  both square colors, empty cells and two board backgrounds.
- Then approximately **6–8 photos** of shaded pieces on wood and failing Lichess
  designs, prioritizing missing combinations. Counts are a pilot, not guarantees.
- Retain a direct screenshot and placement for each position. To isolate moire,
  photograph some positions from two distances/angles. Keep all related variants
  and game positions together; collect different games for validation before
  training. Do not move the existing 30 validation photos into training.
- Severe reflections hiding pieces, strong defocus, major clipping and extreme
  perspective can remain outside the first version. General glare/focus tolerance
  has not been measured.

Retain existing successes, improve priority classes and report whole-board results
by condition. Complete grids with moderate perspective remain an experimental
photo scope, not general style/video compatibility. Evidence comes from one phone
and includes related game images.

## Verification and reproduction

The [joint report](../../data/reports/photo-quality-review-v1.json) records square
confusions, condition breakdowns, digital references, hashes, training history and
candidate rejection. All 81 targeted tests pass, covering partition guards,
repeatable transforms, cell ordering and equal-total hidden regressions. The full
digital evaluation was not repeated because its runtime and weights are unchanged;
previous measurements are explicitly identified as reused.

Use new report paths if deliberately reproducing; no rerun is needed now:

```bash
python -m tools.evaluate_photo_resampling --output .cache/photo-resampling-recheck.json
python -m tools.review_photo_quality --output .cache/photo-quality-recheck.json
python -m pytest tests/test_phone_robustness.py tests/test_photo_pipeline.py tests/test_cli.py tests/test_orientation_input.py -q
```

`tools.train_phone_robustness` preserves the rejected training recipe and requires
a new output directory. It never promotes or configures models. Continue using:

```bash
boardsnap "my-photo.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```
