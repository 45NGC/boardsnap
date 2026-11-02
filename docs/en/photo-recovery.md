# Photographic geometry recovery

**English** | [Español](../es/photo-recovery.md)

A bounded photographic detector correction is accepted: it recovers two validation
photos and one additional complete position while preserving previous results.
**Photo v1 weights and the digital candidate are retained.** No training was
repeated and none of the rejected experiments from the [quality review](photo-quality.md)
were adopted.

## Cause and correction

`video-img_5406` had supported geometric proposals, but intersection refinement
shifted the bottom boundary into the interface. If no result from the original
path is accepted, a measured proposal can now be recovered when refinement moved
it by at most **one tenth of a cell**. The original proposal must independently
pass all grid, boundary and exterior-continuation checks.

In `video-img_5407`, the light frame blends into light squares, leaving outer-edge
segments approximately one cell long. After previous methods fail, an additional
line search admits shorter proposal segments. Interior refinement and all
acceptance checks remain in place. Missing boundaries are not reconstructed and
neither filenames nor expected positions select the result.

Recovery only runs when the original path has no accepted board. Digital
detection, rectification, classification, orientation, labels and partitions
remain unchanged.

## Recorded measurements

| Check | Before | After |
| --- | ---: | ---: |
| Development: detections within geometry policy | 132/161 | 134/161 |
| Consulted validation: detections within geometry policy | 27/30 | 29/30 |
| Consulted validation: exact positions through CLI | 19/30 | 20/30 |
| Constructed negative controls rejected | 18/18 | 18/18 |

The [comparison report](../../data/reports/photo-recovery-comparison-v2.json) checks
image identity, groups, partitions, policies and code/model hashes. All previously
returned corners are identical. All 27 previously returned CLI positions are
unchanged, including the 19 correct positions. No new detection violates policy:
IoU ≥ .95, corner error ≤ 1% of board side and maximum grid displacement ≤ 8% of
a cell.

There are now **1,824/1,856 correct squares** among the 29 detected photos. Previously
this was 1,697/1,728 among 27: these denominators differ and must not be compared
as if they described the same images. Annotated-corner classification remains
1,871/1,920 squares and 19/30 complete positions. The pipeline report includes
per-class results.

Verification: 355 regression tests passed, with three skipped for missing older
local screenshots; another 11 new detector tests and eight comparison tests
passed. Checks cover both recovered photos, rejection after hiding 14/64 of their
first file, other incomplete outer rims, 7×7/9×9 grids and bounded recovery.
All 30 photos ran through the actual CLI with JSON, stderr and exit-code checks.

Additional search increases the cost of some rejections. Development detection
times were .61 s median and 5.15 s p95 while other checks were running: these are
diagnostic timings, not an isolated acceptance benchmark.

## Remaining limits and next step

- `video-img_5407` now returns the complete correct position automatically.
- `video-img_5406` is detected within tolerance but produces a false black knight
  on **h8**; its annotated-corner classification was correct.
- `video-img_5403` remains undetected. Thin pawns, shaded pieces/textures and some
  photos with moire or overlays still cause errors.

General tolerance to blur, glare, arrows or occlusion is not claimed. Targeted
examples of missing styles and measured class confusions remain the next priority,
keeping the current model as a reference. This improves the available pipeline,
but **20/30 does not establish photographic version acceptance**.

This previously consulted batch was used to develop the correction. Independent
final evaluation remains untouched; the improvement is not a new independent test.

## Usage and reproduction

The command is unchanged:

```bash
boardsnap "my-photo.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

Use `black-bottom` when appropriate. Successful output still contains only
`piecePlacement`; structured errors remain unchanged.

V1 reports are preserved. V2 reports are new measurements, not new models. Compare
existing reports without inference or training:

```bash
python -m tools.compare_photo_recovery --output .cache/photo-recovery-comparison.json
```

To deliberately repeat measurements, choose new output paths:

```bash
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-photos-v1.json --output .cache/photo-development-recheck.json
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-validation-v1.json --output .cache/photo-validation-recheck.json
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-photos-v1.json --controls-only --output .cache/photo-controls-recheck.json
python -m tools.evaluate_photo_pipeline --detection-report .cache/photo-validation-recheck.json --model .cache/neural-phone-v1/best.pt --output .cache/photo-pipeline-recheck.json
```
