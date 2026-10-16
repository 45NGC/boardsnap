# Reviewed video and page development cases

**English** | [Español](../es/video-development.md) · [Overview](README.md)

The current [v2 manifest](../../data/manifests/video-development-v2.json) contains
**15 screenshots of 13 distinct positions**. The user confirmed that only
`chesscom-video-001`, `002` and `003` share a position. There are ten Chess.com video
images, three Lichess video images and one page image from each platform.
This step registers cases and measures the unchanged v8 runtime; it does not fix
localization, refine bounds or retrain the classifier.

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

## Current v8 baseline

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

## Reproduce and extend

The default manifest is now v2. For the original three cases, explicitly pass
`--manifest data/manifests/video-development-v1.json`. From the repository root:

```bash
python -m tools.development_cases --output .cache/video-detection.json
python -m tools.development_cases --model .cache/neural-styles-v8/best.pt --output .cache/video-v8.json
python -m pytest tests/test_video_development.py
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest tests/test_video_development.py
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
