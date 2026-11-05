# Current photographic error inventory

**English** | [Español](../es/photo-error-inventory.md)

**Step 1 complete:** reproducible comparison of the 30 consulted validation photos,
using photo v1 and the recovered v2 detector. No inference, training or preprocessing
experiments were run. Frozen candidate, weights, labels and partitions are unchanged.

- [Error and control CSV](../../data/reports/photo-error-inventory-v1.csv).
- [Complete JSON report, including all 30 photos](../../data/reports/photo-error-inventory-v1.json).
- [Development detection-gap annex](../../data/reports/photo-error-inventory-v1-development.csv).

## Comparable summary

| Measurement | Result |
| --- | ---: |
| Detected photos | 29/30 |
| Exact positions with annotated corners | 19/30 |
| Exact positions through automatic CLI | 20/30 |
| Correct through both paths | 18/30 |
| Current full-pipeline failures | 10 |
| Table: at least one path fails | 12 |
| Annotated-corner square errors, **same 29 detected photos** | 47/1,856 |
| Automatic-crop square errors, **same 29 photos** | 32/1,856 |

Across all 30 photos there are 49 annotated-corner errors: two belong to the photo
that automatic detection rejects. Do not compare that total directly with 32 as
if the cohorts matched. A rejected photo has no automatic square predictions;
its square-error count is **unknown**, not zero, and its complete position fails.

## Per-photo table

`square expected→predicted`; uppercase = white, lowercase = black,
`P/N/B/R/Q/K` = pawn/knight/bishop/rook/queen/king; `∅` = empty. Squares always use
canonical chess coordinates, including black-bottom views. **All** photos have
annotated perspective and moire; conditions below list additional factors.
Appearance IDs are local visual groups, not verified official theme names.
“Annotated” means predictions with reviewed corners, not erroneous piece labels.

| Photo / view | Appearance / background | Additional conditions | Errors with annotated corners | Automatic errors | Interpretation |
| --- | --- | --- | --- | --- | --- |
| `chesscom-img_5395` / black-bottom | `cc-flat` / `plain-green` | arrows, highlights | `e5 p→∅` | `e5 p→∅` | Fails with both geometries |
| `chesscom-img_5396` / black-bottom | `cc-flat` / `plain-green` | highlights | `e5 b→B` | **OK** | Control: automatic crop recovers |
| `chesscom-img_5397` / white-bottom | `cc-shaded` / `wood-texture` | arrows, textured-board, highlights | `d8 q→p`; `f8 b→B`; `a5 ∅→n`; `f5 b→B`; `f3 N→∅`; `a1 R→∅`; `b1 N→∅` | `d8 q→p`; `f8 b→B`; `a1 R→B`; `b1 N→∅` | Fails with both geometries |
| `chesscom-img_5398` / white-bottom | `cc-shaded` / `wood-texture` | textured-board, highlights | `e6 p→∅`; `b2 ∅→n`; `a1 R→∅` | `a1 R→B` | Fails with both geometries |
| `chesscom-img_5399` / white-bottom | `cc-flat` / `plain-blue` | highlights | `f8 b→B` | **OK** | Control: automatic crop recovers |
| `chesscom-img_5401` / white-bottom | `cc-thin-stem` / `plain-purple` | — | `a7 p→∅`; `b7 p→∅`; `c7 p→∅`; `f7 p→∅`; `g7 p→∅`; `h7 p→∅`; `e6 p→∅`; `f6 n→N`; `e5 n→N`; `g3 P→R`; `a2 P→∅`; `b2 P→R`; `c2 P→∅`; `f2 P→R`; `h2 P→R` | `a7 p→∅`; `b7 p→∅`; `c7 p→∅`; `f7 p→∅`; `g7 p→∅`; `h7 p→∅`; `e6 p→∅`; `f6 n→N`; `e5 n→N`; `a2 P→∅`; `c2 P→∅` | Fails with both geometries |
| `chesscom-img_5402` / white-bottom | `cc-thin-stem` / `plain-purple` | — | `c7 p→∅`; `a6 p→∅`; `g6 p→∅`; `h6 p→∅`; `g4 p→∅`; `g3 P→R`; `a2 P→∅`; `c2 P→∅` | `c7 p→∅`; `a6 p→∅`; `g6 p→∅`; `h6 p→∅`; `g4 p→∅`; `a2 P→∅`; `c2 P→∅` | Fails with both geometries |
| `lichess-img_5391` / black-bottom | `lc-rounded-king` / `wood-texture` | textured-board, highlights | `d8 q→b`; `f6 n→N`; `e1 K→N` | `d8 q→b`; `f6 n→N`; `e1 K→N` | Fails with both geometries |
| `lichess-img_5392` / black-bottom | `lc-rounded-king` / `wood-texture` | textured-board, highlights | `d4 q→Q`; `d2 K→N` | `d4 q→Q`; `d2 K→N` | Fails with both geometries |
| `video-img_5403` / black-bottom | `video-flat-brown` / `plain-brown` | strong-moire, highlights | `d8 q→n`; `d1 R→∅` | **Not detected** | Detection + classification gap |
| `video-img_5404` / white-bottom | `video-flat-green` / `plain-green` | strong-moire, physical-board-in-background-scene, highlights | `f8 b→q`; `c4 B→∅`; `d4 P→N`; `c2 P→∅`; `e2 ∅→P`; `d1 Q→∅` | `c5 ∅→R`; `e1 ∅→B` | Fails with both geometries |
| `video-img_5406` / white-bottom | `video-classic-a` / `plain-blue` | arrows, additional-board-thumbnails, highlights | **OK** | `h8 ∅→n` | Crop-sensitive failure |


## Attribution and limits

- **Detection:** `5403` is the only validation rejection. With annotated geometry
  it also misclassifies d8's queen and misses d1's rook; recovering detection alone
  does not guarantee an exact complete position.
- **Classification with reviewed geometry:** eight photos fail with both crops.
  This establishes errors that do not depend solely on automatic detection.
  Design, background, optics and preprocessing can interact; these reports cannot
  isolate a single cause for every confusion.
- **Crop sensitivity:** `5406` changes from correct to a false black knight on h8.
  Maximum corner error is 8.69 original-image pixels and maximum grid displacement
  is .0293 cells, within policy. All 29 detected boards meet geometry policy.
  A difference from annotation does not automatically mean incorrect detection.
- **Mixed changes:** `5404` recovers six squares but introduces false pieces on c5
  and e1. In `5397–5398`, a1 remains wrong but changes from a missing rook to a rook
  classified as a bishop. These changed wrong labels are retained, not counted
  as recovered squares.
- **Required positive controls:** `5396` and `5399` are correct with automatic
  geometry. Fixing sensitivity must preserve these gains.

On the same 29 photos, automatic crops **recover 18 squares and introduce three
new errors**: c5/e1 in `5404`, h8 in `5406`. This supports measuring both geometries,
not replacing either indiscriminately. Manual corners also have limited precision.

## Priorities for the catalogue and new data

1. **`cc-thin-stem`, `5401–5402`: 18/32 automatic errors**, two wrong positions.
   Twelve black pawns and four white pawns disappear; two black knights become
   white. Neither photo has annotated arrows or highlights. The previous visual
   training audit did not find the same pawn design among representative examples,
   making this a concrete priority.
2. **`cc-shaded`, `5397–5398`: five errors**, two positions. Prioritize shaded
   pieces on wood, rooks, knights and piece color. Similar training examples exist;
   the entire family is not claimed absent.
3. **`lc-rounded-king`, `5391–5392`: five errors**, two positions. Kings/queens
   and knights need targeted examples. These three groups account for **28/32
   errors**, which are related observations, not 28 independent cases.
4. **Cropping and moire:** retain `5404`/`5406` and controls `5396`/`5399` to measure
   geometric robustness without sacrificing current successes.
5. **Marks:** `5395` misses e5's pawn where arrows overlap. This earlier visual
   hypothesis does not establish causation or justify erasing arrows.
6. **Remaining geometry:** `5403` and the development annex, kept separate from
   cases measured only for classification.

Conditions overlap: automatic exact positions are 9/12 with arrows, 18/26 with
highlights, 6/10 with textures and 1/3 with strong moire. These ratios do not
isolate each condition's effect. No controlled evidence attributes specific
errors to defocus or glare. Pixels and piece transcriptions were not visually
reviewed again in this step.

## Development and previous experiments

The development cohort has 134/161 detections within policy and 27 rejections.
The annex preserves IDs, original filenames, conditions and groups. These reports
lack a paired classification comparison for that cohort: no piece errors or styles
are invented and its totals are not pooled with the 30-photo validation batch.
The 161 examples are not independent sources either.

The three rejected resampling experiments and `neural-phone-robustness-v2` remain
rejected because they lost previous successes. JSON records their source reports
and historical decisions. Their metrics used v1 geometry and are not presented as
new v2 detector measurements. None of the experiments was repeated.

## Reproduction

```bash
python -m tools.consolidate_photo_errors --output-prefix .cache/photo-error-review
python -m pytest tests/test_photo_error_inventory.py -q
```

The command writes JSON, paired CSV and development-geometry CSV. It rejects
existing outputs, duplicate identities, changed labels/views/partitions,
inconsistent geometry and predictions from different code or weights. It opens
only JSON and source code for hash checks; photos and weight files are unnecessary.
The 18 tests cover this restriction, canonical coordinates, unavailable predictions
versus zero errors, and current totals.

Next, **fix the initial photographic catalogue** around these priorities. There is
no need to retrain or collect an untargeted batch yet. Final evaluation stays reserved.
