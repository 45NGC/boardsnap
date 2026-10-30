# Photographic classifier diagnosis

**English** | [Español](../es/phone-classifier-analysis.md)

The measurement step is complete, reusing existing predictions. **Recommendation:
keep photo v1 experimental and preserve the digital reference.** Work on photographic
localization can proceed, but photographic acceptance and general theme compatibility
have not been established.

The same 30 validation photos with reviewed corners produce 19 exact boards versus
18 previously, and 1,871/1,920 correct squares versus 1,863/1,920. No training, new
inference or final evaluation was performed. Weights, labels, corners and partitions
are unchanged.

The [reproducible report](../../data/reports/phone-classifier-analysis-v1.json)
includes every error, paired square changes, class support, square colors, visual
groups and conditions. The [appearance review](../../data/manifests/phone-validation-appearance-v1.json)
is separate and does not modify frozen training manifests.

## Pieces and squares

Precision is the fraction of predictions of a class that were correct; recall is
the fraction of that class's actual examples recovered. Uppercase denotes white,
lowercase black; `empty` means an empty square.

| Class | Examples | Previous recall | Photo v1 recall | Photo v1 precision |
| --- | ---: | ---: | ---: | ---: |
| `empty` | 1188 | 100.0% | 99.7% | 97.9% |
| `P` | 178 | 94.4% | 93.8% | 99.4% |
| `N` | 36 | 88.9% | 94.4% | 85.0% |
| `B` | 40 | 97.5% | 97.5% | 90.7% |
| `R` | 52 | 90.4% | 94.2% | 90.7% |
| `Q` | 22 | 86.4% | 95.5% | 95.5% |
| `K` | 30 | 93.3% | 93.3% | 100.0% |
| `p` | 192 | 90.6% | 92.7% | 99.4% |
| `n` | 39 | 92.3% | 92.3% | 92.3% |
| `b` | 41 | 85.4% | 87.8% | 97.3% |
| `r` | 49 | 98.0% | 100.0% | 100.0% |
| `q` | 23 | 82.6% | 82.6% | 95.0% |
| `k` | 30 | 100.0% | 100.0% | 100.0% |

The overall score is heavily influenced by 1,188 empty squares. Thirteen squares
are recovered and five regress: two empty squares become black knights, another
becomes a white pawn, a white pawn becomes a rook and a black bishop a queen.
These occur on already incorrect photos, so no previously exact photo is lost.

Main confusions: black pawn → empty (14), white pawn → rook (5), white pawn → empty
(5), black bishop → white bishop (4). Errors concern shape, presence and color,
not one piece alone. Black pawns fail on both square colors (8 light, 6 dark).
There is only one black queen on a light square and four white kings on light
squares: perfect recall in these slices is weak evidence.

## Observed appearances

The identifiers below are **local visual groups**, not official theme names.
Piece design and background are recorded separately. Similar groups across
platforms are not assumed identical. These are descriptive slices reviewed after
validation was consulted, not a new acceptance test.

| Visual group | Previous | Photo v1 | Photo v1 square errors |
| --- | ---: | ---: | ---: |
| `cc-classic` | 2/2 | 2/2 | 0 |
| `cc-flat` | 0/4 | 1/4 | 3 |
| `cc-shaded` | 0/2 | 0/2 | 10 |
| `cc-thin-stem` | 0/2 | 0/2 | 23 |
| `lc-classic-a` | 6/6 | 6/6 | 0 |
| `lc-classic-b` | 2/2 | 2/2 | 0 |
| `lc-rounded-king` | 0/2 | 0/2 | 5 |
| `video-chessbase` | 1/1 | 1/1 | 0 |
| `video-classic-a` | 2/2 | 2/2 | 0 |
| `video-classic-b` | 4/4 | 4/4 | 0 |
| `video-flat-brown` | 0/1 | 0/1 | 2 |
| `video-flat-green` | 0/1 | 0/1 | 6 |
| `video-flat-vibes` | 1/1 | 1/1 | 0 |

- `cc-classic`: detailed conventional pieces on plain brown.
- `cc-flat`: flat silhouettes on plain green/blue. The e5 failure in IMG_5395
  visually coincides with several arrows over a pawn; the other two errors are
  bishop color confusions. These are visual hypotheses, not demonstrated causes.
- `cc-shaded`: shaded pieces and brick rooks on wood. Ten errors in IMG_5397–5398,
  including false knights on empty wood-textured squares.
- `cc-thin-stem`: thin-stem, broad-cap pawns on purple. IMG_5401–5402 account for
  23/49 errors (47%): 12 missed black pawns and other pawn/knight confusions.
  Clear errors remain without arrows.
- `lc-classic-a/b`: two conventional groups on brown, blue-gray and wood.
- `lc-rounded-king`: shaded pieces with a rounded white king crown on wood.
  IMG_5391–5392 contain five queen, knight and king errors.
- `video-flat-brown/green`: IMG_5403–5404, with strong interference distorting
  piece strokes; eight errors. Style and moire cannot be isolated with these photos.
- Other video groups recovered all observed positions, including arrow examples;
  this does not imply support for arbitrary videos.

Exact photo/group/background membership is recorded in the report.
**Current useful scope:** experimental classification of already rectified boards
with explicit orientation in these observed appearances. The seven fully correct
appearance groups comprise 18 photos; `cc-flat` adds one success in four. Failing
groups remain incomplete coverage. One or two photos do not establish full
compatibility with any official theme.

## Source and conditions

| Subset | Previous | Photo v1 |
| --- | ---: | ---: |
| `chesscom` | 2/10 | 3/10 |
| `lichess` | 8/10 | 8/10 |
| `video` | 8/10 | 8/10 |
| `arrows` | 10/12 | 10/12 |
| `highlights` | 16/26 | 17/26 |
| `textured-board` | 6/10 | 6/10 |
| `strong-moire` | 1/3 | 1/3 |
| `circles` | 2/2 | 2/2 |
| `cursor` | 2/2 | 2/2 |

Subsets overlap and must not be added. “Video” describes the source, not the board
platform: four Lichess scenes and one ChessBase scene were identified; the other
five retain `unknown`. Scenes containing a physical board are scored only on
their digital diagram.

All 30 photos contain perspective and moire and come from the same iPhone 8.
Annotated short edges range from 1,788 to 2,398 pixels, or 224–300 pixels per cell
along that edge, **not effective optical resolution**. Opposite-edge ratios range
from 1.045 to 1.200; these are not camera angles. There is no cross-device evidence
or controls isolating blur, reflections, strong perspective or compression.
One of three strong-moire examples succeeds. Neither moire nor arrows alone
explain the failures. Related game/video photos are not independent observations;
the complete original validation group is preserved.

## Targeted data priorities

1. **Inventory the existing 160 training examples first** for the problematic
   appearances. Their absence has not been demonstrated; diversity or class/color
   coverage may be insufficient instead.
2. Prioritize thin-stem pawns in IMG_5401–5402, shaded pieces on wood in
   IMG_5397–5398, and kings/queens in IMG_5391–5392. Include both piece colors,
   light/dark and empty squares, with multiple backgrounds to separate design
   from texture. An indicative pilot is 8–12 new photos per group from several
   identified games; this is not a quantity that guarantees accuracy.
3. For moire, collect direct-reference/photo pairs of the same position, varying
   distance and angle over multiple games. Reserve separate source groups for
   validation. This helps distinguish style from optical degradation without
   moving validation photos into training.
4. Before retraining, review mixing digital training examples to preserve their
   successes. Photo v1 still has the three documented digital regressions
   (3,128/3,132 versus 3,131/3,132). Keep the digital default unchanged.

No indiscriminate new batch or immediate training is needed. These measurements
allow photographic detection/rectification work to proceed with explicit limits
on the classifier's contribution. Targeted improvements remain identified future
work; final acceptance is still pending.

## Reproduce the analysis

From the repository root with the environment activated:

```bash
python -m tools.analyze_phone_classifier
python -m pytest tests/test_phone_classifier_analysis.py tests/test_phone_inference.py -q
```

Hashes, exact photo membership, labels and orientation are checked before cached
predictions are aggregated. Models are never loaded and inference is never run.
The 19 tests cover pairing, square regressions, canonical colors and rejection of
changed/non-validation evidence. Reviewed local mosaics are in
`.cache/phone-classifier-analysis-v1/`; photos are not versioned.
