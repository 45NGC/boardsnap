# Targeted photographic training regressions

**English** | [Español](../es/targeted-photo-regressions.md)

Analysis dated November 14, 2026. **Retain `neural-phone-v1`.** The targeted
candidate mainly loses the ability to ignore marks and texture on empty squares.
This is not a new detection failure: the saved comparisons use identical verified
crops and labels for both classifiers.

Saved predictions were reused and the affected crops were inspected visually.
No inference, training or final evaluation was run. Models, detection,
preprocessing and partitions remain unchanged.

- [Reproducible square-level report](../../data/reports/targeted-photo-regressions-v1.json).
- [Local gallery of 11 cases and clean controls](../../.cache/phone-targeted-regressions-v1/index.html).
- [Training results](targeted-photo-training.md).

## Eleven formerly correct boards

Each board loses **one square**. Ten errors invent a piece on an empty square;
one changes a black pawn into a black bishop. Seven affected squares are light
and four dark. There is no general orientation or piece-color inversion.

| Gallery case | Image / combination | Square | Expected → candidate | Visible evidence |
| --- | --- | --- | --- | --- |
| phone-01 | lichess-img_5388; observed `lc-classic-a` | d8, dark | empty → black queen | Wood grain and photographic interference; arrows do not cross d8 |
| phone-02 | lichess-img_5390; observed `lc-classic-b` | d8, dark | empty → black queen | Wood grain; no mark or piece on this square |
| digital-01 | digital-014; Lichess cburnett/green | g6, light | empty → white pawn | Red triangular arrowhead |
| digital-02 | digital-034; Chess.com neo/green | b5, light | empty → white king | Green arrowhead inside circle and highlight |
| digital-03 | digital-034; Lichess alpha/green | g4, light | empty → white pawn | Red triangular arrowhead |
| digital-04 | digital-036; Chess.com classic/blue | f1, light | empty → white bishop | Green arrowhead beside coordinate label |
| digital-05 | digital-036; Chess.com neo/blue | c2, light | empty → white knight | Rounded start of diagonal red arrow |
| digital-06 | digital-070; Lichess merida/blue | d4, dark | black pawn → black bishop | Thick orange and thin blue arrows crossing the pawn |
| digital-07 | digital-033; Lichess staunty/wood4 | h7, light | empty → white knight | Diagonal red arrow start over wood |
| digital-08 | digital-035; Lichess staunty/wood4 | d8, dark | empty → black king | Vertical orange arrow start over wood |
| digital-09 | digital-014; Chess.com alpha/green | f3, light | empty → white king | Green arrow, circle and highlight |

Short digital filenames recur across configurations; the report retains complete
paths. Photographic appearance names are corpus visual labels, not confirmed
platform selector names.

**All nine matching digital controls without marks remain completely correct with
both models.** The eight empty cells are classified as empty and d4 as a black
pawn. This links those losses to overlay tolerance rather than a general inability
to recognize the piece designs.

The 64×64 red-arrowhead crops in digital-01 and digital-03 are **byte-identical
pixels**, despite different positions and piece styles. They count as two lost
boards, but not two independent visual patterns. The eleven failing crops contain
ten unique patterns; the two photographic crops are similar, not identical.

## Changes beyond exact-board totals

| Validation | Newly incorrect squares | Recovered squares | New false pieces |
| --- | ---: | ---: | ---: |
| Photographic, 30 photos | 10 | 12 | 9 |
| Digital, 3,132 captures | 10 | 0 | 9 |

Photographic validation also has two changes from one wrong class to another;
these are neither recoveries nor newly incorrect cells. Eight photographic losses
outside the two newly broken boards occur in already incorrect photographs:
`chesscom-img_5397` (f4/e3), `5398` (e3), `lichess-img_5392` (a7/c5/e1), and
`video-img_5404` (e4/e3). Digital validation has an additional empty a4 becoming a
white knight in an already incorrect `digital-071`, Chess.com bases/brown case.
All changes are retained in the report.

The small net photographic accuracy improvement therefore hides instability:
twelve cells recover while ten fail. Correct photographic empty squares decrease
from 1,185 to 1,176 out of 1,188.

## Evidence versus hypotheses

**Training facts:** 160 previous photos plus 24 new photos from eight positions
were used, with no digital screenshot training examples. Distillation preserved
old-model predictions only on the previous photos, not digital arrow examples.

Empty squares remain common: 6,270/10,240 previous training cells and 867/1,536
new cells. It would be inaccurate to conclude that empty examples were generally
missing. The next audit should check coverage of **empty cells with wood texture,
arrowheads, shafts and circles**, rather than raw empty-cell totals alone.

The empty-class loss weight changes from 0.1256 to 0.1269, while black queen stays
at 5.6264. Rare-class weighting could affect the tradeoff between finding thin
pieces and inventing pieces, but **its causal role is not established**. The
weights barely changed; a sudden weighting change cannot explain this run.

**Leading hypothesis:** photographic adaptation shifted piece/background
separation and reduced some digital overlay tolerance. Clean controls and the
absence of digital replay support this interpretation, but no additional
training ablation has tested causality. In the photographs, visible grain/moire
is being classified as a queen; the individual effects of those factors have not
been separated experimentally.

## Recommended next preparation

1. Preserve the rejected candidate as a reference and retain phone-v1.
2. Inventory **training-only** digital arrowheads, starts, circles and crossings,
   plus photographic empty wood squares. Include clean controls, occupied cells
   and thin pieces so reducing false positives does not erase real pieces.
3. Prepare mixed training that replays those groups alongside previous and new
   photos, controlling source/condition proportions rather than indiscriminately
   multiplying variants of eight new positions.
4. Fix a comparison that preserves previous correct boards and measures empty-cell
   and occupied-cell errors separately. Never move these validation cases into
   training or hard-code their crops.

Do not change the detector, remove arrows or impose an arbitrary empty-cell
threshold on this evidence. Additional collection is not yet necessary: first
inventory the training examples already available. This step ends with diagnosis;
mixed training has not started.

Reproduce without inference:

```bash
python -m tools.analyze_targeted_regressions
python -m pytest tests/test_targeted_regression_analysis.py -q
```

The [training coverage inventory](training-coverage.md) identifies reusable digital overlays and photographic wood/thin-piece examples. No new training is started; prepare a balanced mixed corpus next.
