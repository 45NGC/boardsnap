# Analysis of the 11 tolerance regressions

[Español](../es/tolerance-regressions.md) · [Step 4](classifier-tolerance.md)

**Recommendation: keep the current candidate**,
`.cache/neural-tolerance-v1-conservative/best.pt`, with v8 as the reference.
No models were trained, weights replaced or production recognition changed.
The simple alternative tested sacrifices substantially more gains than it recovers.
These losses deserve tracking, but do not justify blocking the next step or adding
a special rule for these images.

## Evidence and scope

The [existing full comparison](../../data/reports/neural-tolerance-validation.json)
is reused. Only the 11 transitions from a correct whole board with v8 to an
incorrect one with the candidate are reproduced. Their original crops, clean
controls, internal logits and detection are checked. An additional probe uses
only the 11 losses and 674 gains already identified in that report.

The [detailed report](../../data/reports/neural-tolerance-loss-analysis.json)
records source hashes, squares, conditions, coordinates, predictions and alternative
results. All inputs are **already consulted validation data**, not independent
final evaluation. These 11 whole-board transitions do not necessarily enumerate
all square-level regressions on boards that both models already got wrong.

## Common features

All images use **Chess.com Neo pieces**, the **blue background**, the desktop-web
`chesscom-analysis` layout, `black-bottom` orientation and a **704 × 704 pixel**
board with 88-pixel squares.

| Position | Variants | Perturbation | Square | Error |
| --- | ---: | --- | --- | --- |
| `digital-034` | 1, circle | Up 2 px | g2 | White bishop → white queen |
| `digital-070` | 1, circle | Up 2 px | d3 | White bishop → white queen |
| `digital-035` | 1, clean | Asymmetric edges | h1 | White bishop → white queen |
| `digital-036` | 8 | Asymmetric edges | h1 | White bishop → white queen |

The eight `digital-036` variants are clean, last move, selection, check, arrow over
empty squares, arrow over pieces, crossed arrows and combined marks. There are
**four positions in two groups**: 034/035/036 belong to `sequence-009`, and 070 to
`sequence-018`. They are not 11 independent examples.

Each board has **one incorrect square**, always a white bishop on a light square.
There are no color changes, empty-square confusions or other piece classes among
these losses. The nine h1 cases essentially reuse one local crop: eight are
byte-identical; the combined variant differs by one pixel from its clean control.
There are four distinct crop hashes across the eleven errors.

The arrows elsewhere in several screenshots therefore **do not explain the local
h1 errors**: the bishop crop matches the clean one, except for that single pixel
in the combined case. The two remaining errors have a green circle around the
bishop: 1152 and 1151 of 4096 pixels differ from their circle-free controls.

## Bounds and probable mechanism

Original exclusive bounds are `(228, 66, 932, 770)`.

| Scenario | Left/top/right/bottom offsets | Resulting crop |
| --- | --- | --- |
| `shift-y-2` | `(0, -2, 0, -2)` | `(228, 64, 932, 768)`, 704 × 704 |
| `asymmetric-2` | `(1, -2, 2, -1)` | `(229, 64, 934, 769)`, 705 × 705 |

These are small, plausible localization errors: at most 2 pixels per edge,
0.284% of the board side or 2.27% of a square. The vertical shift is about 1.45
pixels after normalization to 64 × 64 squares. The asymmetric case also changes
scale by 0.142% and shifts the center 1.5 pixels right and up. Neither crop escapes
the screenshot or removes the bishop's identifying information.

Visual inspection shows an added strip of board border or adjacent square and a
small shift of the silhouette. In h1, the top-left visual corner in this orientation,
the coordinate label “1” is also present. This is consistent with sensitivity to
framing and resampling combined with a small decision-boundary change from weight
averaging. **It does not establish that the label, border strip or circle alone
causes the error**; no element-by-element ablation was performed.

Internal margins between the bishop logit and its strongest competitor show how
close these inputs were to a class change. They are not probabilities or new
public output fields:

| Perturbed crop | v8 margin | Candidate margin |
| --- | ---: | ---: |
| g2 with circle | +1.2530 | −0.2327 |
| d3 with circle | +1.3495 | −0.1336 |
| h1, clean case | +0.0415 | −0.0985 |

With original bounds, the candidate margins for these squares are +22.42 to
+30.55, and all eleven complete boards are correct. The actual detector also
returns **exactly the original bounds on all eleven images**. These are induced
tolerance failures, not current automatic-pipeline failures on the original PNGs.

Nor does this pattern mean bishops became worse overall: across all applicable
perturbed variants already measured, the candidate recognizes **46348/47228** white
bishops versus **46189/47228** with v8. White-bishop → white-queen confusions decrease
from 167 to 161. These aggregate gains do not erase the eleven local losses.

## Simple alternative tested

The **6.25% trained / 93.75% v8** parameter average was reconstructed in memory from
existing weights. The current candidate uses 12.5% / 87.5%. No new model was
trained or saved. That lower fraction was already part of the earlier selection;
this diagnosis adds the paired loss/gain detail.

- It recovers **2/11** losses: the two circled bishops.
- It does not recover the nine h1 cases.
- It loses **400/674** perturbed boards recovered by the current candidate.
- In the previous selection block it already scored 6006/6264 exact boards,
  versus 6037/6264 for the current candidate.

This directed subset is sufficient to reject the claim that the alternative
preserves gains, but **does not estimate its full-validation performance**.
There was therefore no need to repeat a full evaluation of that alternative.

No simple correction has been established as safe. Restoring annotated bounds
fixes all eleven, but those bounds are unavailable on a new image. Always shifting
the crop would move the error onto correctly localized boards. Forcing queen →
bishop, shaving all square borders or falling back to v8 at a threshold would
need controls containing actual queens and the rest of the corpus; these examples
do not justify deployment. The probe does not rule out future improvements from
other techniques.

## Decision and follow-up

Keep the candidate: original controls and checked regressions remain preserved,
and its net improvement is still **674 gains minus 11 losses = 663** additional
exact perturbed boards. Provisionally accepting these limitations does not accept
the digital release.

Another training run has not been shown necessary now. If this pattern appears
in new captures with actual detection, expand **training only** with Neo bishops
and queens on both backgrounds, circles, coordinates and small boundary errors.
Preserve groups and splits: do not copy these validation positions into training
or tune a special h1 rule. Any replacement must retain the gains and pass the
relevant validation and full regressions.

## Reproduction

With the existing local datasets and models:

```bash
python -m tools.analyze_tolerance_regressions
python -m pytest tests/test_tolerance_loss_analysis.py
```

The tool checks model, source, index and original comparison code hashes. A crop
contact sheet is saved to `.cache/tolerance-loss-analysis/regression-crops.png`;
data and weights remain in cache. The CLI and its `piecePlacement` contract are
unchanged.
