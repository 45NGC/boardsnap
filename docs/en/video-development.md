# Reviewed video and page development cases

**English** | [Español](../es/video-development.md) · [Overview](README.md)

The [009/010 diagnosis](video-009-010-diagnosis.md) shows both models recognize the
positions with corrected interior-grid geometry. [Subsequent bounded recovery](border-grid-recovery.md)
now recognizes them automatically, keeping perimeter and grid references separate.

The current [v2 manifest](../../data/manifests/video-development-v2.json) contains
**15 screenshots of 13 distinct positions**. The user confirmed that only
`chesscom-video-001`, `002` and `003` share a position. There are ten Chess.com video
images, three Lichess video images and one page image from each platform.
The original registration measured v8 without runtime changes. The subsequent
localization step improves detection while retaining the same model and annotations.

The original three PNGs remain in `data/development/video-cases-v1/`; the twelve
additions are unchanged copies in `data/development/video-cases-v2/`. All original
cache files remain untouched. The original [v1 manifest](../../data/manifests/video-development-v1.json)
and [three-image report](../../data/reports/video-development-v1-baseline.json)
are retained, with the earlier manifest hash recorded in v2.

## Reviewed annotations

Each sample records its checksum, original path, placement, orientation, reviewed
visible/nominal board bounds, conditions and source grouping. Piece labels were
visually transcribed before model measurement, and borders checked on pixel
scanlines rather than copied from the detector. The Lichess page's visible FEN
also corroborates its placement; no additional FEN fields are stored.
This is assistant review, not independent human annotation.

The user explicitly confirmed **White at the bottom** for coordinate-free
`chesscom-video-009`, `010` and `chesscom-page-001`. Other views were checked against
visible coordinates. Exact theme names, source URLs, timestamps and game moves
remain unknown rather than guessed.

Boxes below are `[left, top, right, bottom]`, with exclusive right/bottom edges.

| Image | View | Reviewed visible box |
| --- | --- | --- |
| chesscom-video-001 | `black-bottom` | `[35, 17, 435, 417]` |
| chesscom-video-002 | `black-bottom` | `[0, 1, 399, 401]` |
| chesscom-video-003 | `black-bottom` | `[2, 2, 299, 299]` |
| chesscom-video-004 | `black-bottom` | `[35, 14, 435, 414]` |
| chesscom-video-005 | `black-bottom` | `[28, 8, 428, 408]` |
| chesscom-video-006 | `white-bottom` | `[41, 11, 417, 387]` |
| chesscom-video-007 | `black-bottom` | `[15, 13, 573, 570]` |
| chesscom-video-008 | `black-bottom` | `[22, 16, 580, 573]` |
| chesscom-video-009 | `white-bottom` | `[13, 23, 467, 481]` |
| chesscom-video-010 | `white-bottom` | `[12, 2, 466, 460]` |
| lichess-video-001 | `white-bottom` | `[15, 11, 903, 899]` |
| lichess-video-002 | `white-bottom` | `[14, 8, 594, 586]` |
| lichess-video-003 | `white-bottom` | `[28, 14, 608, 592]` |
| chesscom-page-001 | `white-bottom` | `[9, 10, 257, 258]` |
| lichess-page-001 | `white-bottom` | `[55, 23, 1143, 1111]` |

002 is pixel-for-pixel identical to crop `[36, 16, 437, 420]` of 001. Its nominal
grid is `[-1, 1, 399, 401]`: one left-edge raster column is missing. The visible
box is `[0, 1, 399, 401]`; no pixels are reconstructed. This is a boundary stress
case, not evidence for supporting missing squares. Some new videos have slight
nonuniform scaling and texture. Lichess video 001 includes a cursor on a piece;
the Lichess page includes overlapping arrows over the queen and highlighted squares.

## Grouping and independence

All cases are **development-regression**, never independent final evaluation or
automatically imported training data. The first three retain their shared position
ID. Every new screenshot has its own position ID, as confirmed by the user.
Different positions do not prove different games: URLs/PGNs or game relationships
were not supplied. For safety, all Chess.com examples remain in the existing
`real-chesscom-video-game-001` bucket, and Lichess uses
`real-lichess-development-unresolved`. These are **two conservative platform
buckets, not a claim of two independent games**. Future related images must stay
in development; source grouping may be refined after provenance is confirmed.

The loader checks hashes, bounds, placement/group consistency and the known exact
crop relationship. Acceptance rejects these known position families even when
IDs are renamed, reflected/rotated or colors swapped, and excludes known group IDs.
Unknown related positions cannot automatically be identified without provenance.
The reserved final corpus has not been captured or evaluated.

## Historical v8 baseline before the localization change

The [15-image report](../../data/reports/video-development-v2-baseline.json)
records **5/15 accurate detections** and **5/15 complete-pipeline successes**.
Nine images return `BOARD_NOT_FOUND`; 002 returns bounds with 3-pixel maximum
error. With reviewed visible bounds, classification succeeds on **13/15 images**.
009 and 010 still have incorrect pieces, so the expanded corpus does not justify
a detection-only diagnosis. Geometry/resampling and classification robustness
need separate follow-up measurements.

| Image | Detection within 2 px | Classification with reviewed bounds | Complete pipeline |
| --- | --- | --- | --- |
| chesscom-video-001 | Fails | Correct | Fails |
| chesscom-video-002 | Fails | Correct | Fails |
| chesscom-video-003 | Correct | Correct | Correct |
| chesscom-video-004 | Fails | Correct | Fails |
| chesscom-video-005 | Fails | Correct | Fails |
| chesscom-video-006 | Fails | Correct | Fails |
| chesscom-video-007 | Correct | Correct | Correct |
| chesscom-video-008 | Correct | Correct | Correct |
| chesscom-video-009 | Fails | Fails | Fails |
| chesscom-video-010 | Fails | Fails | Fails |
| lichess-video-001 | Correct | Correct | Correct |
| lichess-video-002 | Fails | Correct | Fails |
| lichess-video-003 | Fails | Correct | Fails |
| chesscom-page-001 | Correct | Correct | Correct |
| lichess-page-001 | Fails | Correct | Fails |

## Step 2: localization inside complex backgrounds

The [new report](../../data/reports/video-development-v2-localization.json) uses
the same 15 images, labels and v8 weights. The detector now proposes rectangles
from regular interior lines even when edge components merge with surrounding
graphics. It keeps the existing geometric/alternation checks and additionally
checks complete outer cells and rejects visible continuation into larger grids.
See [detection](detection.md) for the algorithm and bounded-search limitations.

| Measurement | Before | After |
| --- | ---: | ---: |
| Rectangles within 2 pixels | 5/15 | 11/15 |
| Exact placement with reviewed bounds | 13/15 | 13/15 |
| Exact placement through the full pipeline | 5/15 | 12/15 |

`chesscom-video-001` is localized at `[35, 17, 435, 418]` (maximum edge error
1 pixel) and returns the expected placement. 003 retains its exact rectangle and
placement. 004, 005, 006, Lichess video 002 and the Lichess page also gain accurate
localization and correct placement. All five previous working cases stay correct.

At the end of step 2, remaining work was explicit: 002 still used the imprecise full-frame fallback;
Lichess video 003 now returns the correct placement but has a 3-pixel rectangle
error. Chess.com videos 009/010 still fail localization and also fail classification
with reviewed bounds. These are separate geometry/classification follow-ups,
not reasons to change annotations to match predictions. Strict expected failures
now track those four rectangle cases, two reviewed-bound classification cases,
and three full-pipeline cases. The following step updates this status.

The [older detection corpus recheck](../../data/reports/digital-detection-v3-localization-regression.json)
retains all 28 rectangles and rejects all 28 board-removal negatives. Tests also
reject the 15 video/page backgrounds after removing their boards, test resized
and translated copies of 001, and exercise connected synthetic backgrounds with
text, multiple boards, other grid sizes and incomplete boards. These controls do
not establish a zero false-positive rate on arbitrary future screenshots.

All reports remain development/regression evidence. No final holdout was opened,
no classifier was retrained, and the public recognition JSON is unchanged.

The complete test suite with the local v8 artifact passes **1490 tests**, with
36 optional browser tests skipped and 11 expected failures (the nine development
checks listed above and two experimental book-diagram cases).

The [complete v8 regression recheck](../../data/reports/neural-styles-v8-localization-regression.json)
preserves **3456/3456 exact boards and 221184/221184 correct squares**, with both
verified and detected bounds. All 3456 rectangles remain within two pixels.
These are variants of 12 previously consulted source positions, not independent
final evidence. Dataset/model hashes and all aggregate candidate metrics match
the historical v8 report; the new report records the updated detector hash.

## Step 3: visible-boundary refinement

The [bounds report](../../data/reports/video-development-v2-bounds.json) records
**13/15 accurate detections and 13/15 exact full-pipeline positions**, compared
with 11/15 and 12/15 after step 2. Reviewed-bound classification remains 13/15:
the weights, labels, input images and classifier preprocessing are unchanged.

002 now returns visible bounds **`[0, 1, 399, 401]`** and the correct placement with
v8 automatically. Its missing left raster column is not reconstructed. 001 and
003 still return the identical expected placement; adding asymmetric margins to
all three also preserves it. Lichess video 003 now matches its reviewed rectangle
`[28, 14, 608, 592]`. Video 003 from Chess.com remains within one pixel of its
annotation (`[2, 2, 298, 299]` detected), without changing the reference to fit it.

The nearly square frame is no longer accepted solely because its overall pattern
resembles an 8x8 grid. It must yield an interior-line fit, visible outer boundaries
and alignment with all eight rows/columns. The same refinement checks the final
selected rectangle. See [detection](detection.md#visible-bounds-before-segmentation)
for limits, including the single-raster-pixel allowance and optional refinement of
already validated proposals.

Chess.com videos **009/010 remain unresolved** in detection and reviewed-bound
classification. Six strict expected-failure checks retain these distinctions;
no new training or broad video-compatibility claim is made. The
[older detection corpus](../../data/reports/digital-detection-v4-bounds-regression.json)
still passes 28/28 rectangles and rejects 28/28 board-removal negatives. The six
original arrow/cropped-board failures also retain their correct placements.

The complete suite with v8 now passes **1552 tests**, with 36 optional browser
tests skipped and eight expected failures (six checks for videos 009/010 and two
experimental book-diagram cases). The new geometry tests exercise all four
single-pixel crop directions, reject larger cuts with/without surrounding margins,
and check nonmultiple sizes and two resampling methods. Nine neural checks confirm
the shared position across 001/002/003 and three margin configurations.

The [complete recognition regression](../../data/reports/neural-styles-v8-bounds-regression.json)
preserves **3456/3456 exact boards and 221184/221184 correct squares**, both with
reviewed bounds and with detected bounds. All 3456 detected rectangles remain
within two pixels, including clean images, simple marks and arrows. These are
variants of 12 previously consulted positions, not independent final evidence.
Model and dataset hashes, and all aggregate candidate metrics, match the step 2
report; the runtime hashes identify the updated detector.

```bash
python -m tools.development_cases --model .cache/neural-styles-v8/best.pt --output .cache/bounds-step3/video-recheck.json
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest tests/test_detection_bounds.py tests/test_video_development.py
python -m tools.preview_detection data/development/video-cases-v1/chesscom-video-002.png --output-dir .cache/bounds-step3/preview --squares
boardsnap .cache/real-use-tests/chesscom-video-002.png --model .cache/neural-styles-v8/best.pt --orientation black-bottom
```

To reproduce the complete recognition regression:

```bash
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v8/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --regression --output .cache/bounds-step3/corpus-recheck.json
```

The development-cases command still exits 1 because 009/010 fail; `boardsnap`
returns only the correct `piecePlacement`. These remain consulted development/regression samples.
The independent final acceptance set is untouched.

## Reproduce and extend

The default manifest is now v2. For the original three cases, explicitly pass
`--manifest data/manifests/video-development-v1.json`. From the repository root:

```bash
python -m tools.development_cases --output .cache/video-detection.json
python -m tools.development_cases --model .cache/neural-styles-v8/best.pt --output .cache/video-v8.json
python -m pytest tests/test_video_development.py
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest tests/test_video_development.py
# Connected-background synthetic controls and the complete suite
python -m pytest tests/test_detection_clutter.py
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest
# View the fixed 001 rectangle and square crops (local ignored output)
python -m tools.preview_detection data/development/video-cases-v1/chesscom-video-001.png --output-dir .cache/localization-step2/preview --squares
# Recheck the already consulted recognition corpus with unchanged models
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v8/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --regression --output .cache/localization-step2/corpus-recheck.json
```

The evaluator exits **1 while any measured case fails**. Without `--model` it
measures detection without Torch. With a model it separately measures reviewed-bound
classification and the production pipeline; expected bounds never guide production
detection. Reports pin dataset, model, runtime and tool hashes.
Known desired-behavior failures use strict `xfail`: improvements cause `XPASS`,
requiring explicit removal of the marks. Neural tests require `BOARDSNAP_TEST_MODEL`;
an explicitly supplied invalid path fails instead of being silently skipped.

No additional screenshots are required to start the detector fixes. Keep any new
originals in `.cache/real-use-tests/`, with source URL/timestamp or game link when
possible. Original frames and crops remain related variants; ordinary positive
examples should retain all board edges. Keep working controls alongside failures.
For example: `chesscom-video-game-002-frame-001-original.png` and
`chesscom-video-game-002-frame-001-crop.png`. New files are pending review, never
automatically promoted to a final evaluation set.
