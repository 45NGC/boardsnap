# Geometry robustness across 30 real-use screenshots

[Español](../es/digital-geometry-review.md) · [Home](README.md)

This review uses development/regression data only. It adds no phone-photo route,
homographies, training, distribution or independent final evaluation. Both v8 and
`neural-tolerance-v1-conservative` weights remain unchanged.

## Outcome and scope

| Measurement | Before | After |
| --- | ---: | ---: |
| Boards localized / bounds within annotation tolerance | 27/30 | 30/30 |
| Exact boards with reviewed geometry, each model | 29/30 | 29/30 |
| Correct squares with reviewed geometry, each model | 1918/1920 | 1918/1920 |
| Exact boards through the CLI, each model | 26/30 | 29/30 |
| Synthetic positives within 2 px | 0/36 | 36/36 |
| Synthetic negatives or out-of-scope controls rejected | 12/12 | 12/12 |

All 27 previously accepted rectangles retain identical bounds; no previously
correct position becomes incorrect in this set. Both models have identical
success/failure outcomes. The change recovers `real-use-25`, `real-use-26` and
`real-use-29` automatically, including the real CLI. **Not every screenshot is
recognized perfectly:** `real-use-4` retains a classification failure.

## Inventory and annotations

The [manifest](../../data/manifests/real-use-development-v1.json) records 30 current
names, hashes, dimensions, placements, orientations, visible perimeters, grid
geometry, conditions, known provenance and review status. Image bytes remain in
`.cache/real-use-tests`, outside Git. Reproduction requires that local corpus or
an identical copy.

Fifteen annotations are inherited by hash from the previous corpus, preserving
position, group and partition. `real-use-11`, `12` and `13` are variants of one
position. The fifteen new placements were visually transcribed before comparing
predictions. All thirty images were inspected; new annotations identify the
assistant as reviewer and **do not claim user confirmation**. New geometry was
reviewed against pixels/interior lines with raster uncertainty, not independently
measured with subpixel precision. This corpus allows three pixels of edge error,
consistent with the review tolerance of earlier cases.

The user cannot identify exact games/videos. Most sources are video screenshots,
some are direct page screenshots; no URLs, timestamps, theme names or games were
invented. New sources share a conservative unresolved-provenance group. Different
positions do not establish independence. The entire corpus remains development-only;
it must not subsequently be split into training, selection and acceptance without
reviewing relationships. It contains 28 distinct placements, not 30 independent
examples.

Active documentation commands use `real-use-N`. Historical identifiers, versioned
image-copy paths and `originalPath` provenance remain unchanged rather than breaking
linked hashes. They are not new execution paths. Local `rename-map.json` links old
and current names; its hash is recorded in the new manifest.

| Image | View | Reviewed grid | CLI before → after |
| --- | --- | --- | --- |
| real-use-1 | white-bottom | (19, 11, 578, 571) | OK → OK |
| real-use-2 | white-bottom | (51, 26, 1024, 992) | OK → OK |
| real-use-3 | black-bottom | (45, 25, 1013, 993) | OK → OK |
| real-use-4 | white-bottom | (18, 30, 1008, 1019) | FAIL → FAIL |
| real-use-5 | white-bottom | (44, 15, 1016, 986) | OK → OK |
| real-use-6 | white-bottom | (48, 44, 984, 981) | OK → OK |
| real-use-7 | white-bottom | (29, 28, 788, 788) | OK → OK |
| real-use-8 | white-bottom | (37, 28, 963, 953) | OK → OK |
| real-use-9 | white-bottom | (23, 10, 799, 787) | OK → OK |
| real-use-10 | white-bottom | (9, 10, 257, 258) | OK → OK |
| real-use-11 | black-bottom | (35, 17, 435, 417) | OK → OK |
| real-use-12 | black-bottom | (0, 1, 399, 401) | OK → OK |
| real-use-13 | black-bottom | (2, 2, 299, 299) | OK → OK |
| real-use-14 | black-bottom | (35, 14, 435, 414) | OK → OK |
| real-use-15 | black-bottom | (28, 8, 428, 408) | OK → OK |
| real-use-16 | white-bottom | (41, 11, 417, 387) | OK → OK |
| real-use-17 | black-bottom | (15, 13, 573, 570) | OK → OK |
| real-use-18 | black-bottom | (22, 16, 580, 573) | OK → OK |
| real-use-19 | white-bottom | (10, 24, 466, 480) | OK → OK |
| real-use-20 | white-bottom | (9, 3, 465, 459) | OK → OK |
| real-use-21 | white-bottom | (55, 23, 1143, 1111) | OK → OK |
| real-use-22 | white-bottom | (15, 11, 903, 899) | OK → OK |
| real-use-23 | white-bottom | (14, 8, 594, 586) | OK → OK |
| real-use-24 | white-bottom | (28, 14, 608, 592) | OK → OK |
| real-use-25 | white-bottom | (6, 13, 1016, 994) | FAIL → OK |
| real-use-26 | white-bottom | (3, 8, 1013, 988) | FAIL → OK |
| real-use-27 | black-bottom | (22, 22, 727, 728) | OK → OK |
| real-use-28 | black-bottom | (25, 18, 730, 724) | OK → OK |
| real-use-29 | black-bottom | (4, 11, 1015, 991) | FAIL → OK |
| real-use-30 | white-bottom | (35, 53, 859, 878) | OK → OK |

This table summarizes both models. JSON reports contain per-image/model outputs,
wrong squares, class metrics, groups and conditions. Categories overlap; their
denominators must not be added as independent samples.

## Diagnosis before production changes

The 30-image baseline and its 60 CLI subprocesses completed before editing
`detection.py`. Metrics were communicated and preserved in the
[real baseline](../../data/reports/real-use-geometry-before.json) and
[synthetic baseline](../../data/reports/digital-geometry-synthetic-before.json).

**Unequal scales and a narrow edge: 25, 26, 29.** Horizontal/vertical steps differ
by about 3%. Interior-line proposals already locate the region, but the near-square
filter rejects it. The visible left perimeter also starts six pixels inside the
extrapolated grid. All seven divisions on each axis and the other edges support
separating these geometries. Both models already classify these three correctly
with reviewed bounds.

| Image | Segmentation grid | Visible perimeter |
| --- | --- | --- |
| real-use-25 | (6,13,1016,994) | (12,14,1017,994) |
| real-use-26 | (3,8,1013,988) | (9,8,1014,988) |
| real-use-29 | (4,11,1015,991) | (10,11,1015,991) |

Coordinates are `(left, top, right, bottom)`, with exclusive final edges. It is
not established whether the narrow strip comes from a mask, frame or video crop.
Its origin remains unresolved; no hidden information is claimed recovered.
The grid stays inside the image and no cells are reconstructed.

**Texture classification: real-use-4.** Both models predict a black knight on
empty `a5` and `h4`. This persists with reviewed and automatic geometry, whose
bounds coincide. Wood texture and video resampling are plausible contributors;
this experiment does not isolate a unique visual cause or identify a theme name.
Changing the detector to remove these predictions is unjustified.

**Remaining 26 images.** Localization and complete recognition are correct before
and after, within the stated geometry tolerance. They include cursors, highlights,
arrows, textures, margins and video backgrounds, not universal coverage.

## Implemented change

Every existing route retains priority. Only when none finds a board does
`_rectangular_grid_candidates` run:

1. Propose extents from interior lines along both axes.
2. Fit horizontal/vertical starts and steps independently, without resizing the
   input to manufacture a square proposal.
3. Limit the larger/smaller side ratio to **1.05**. This is deliberately small
   digital anisotropy, not perspective estimation. Do not reopen near-square
   candidates rejected by previous routes.
4. Require alternation and strong evidence for **all seven boundaries on each axis**.
5. Validate the complete visible perimeter. If it differs from the grid by more
   than one pixel, require the existing narrow-rim recovery: one affected edge,
   at most `min(6, floor(smaller_cell_side × 0.08))` pixels, other edges aligned.
6. Reject continuing larger grids and retain multiple-candidate errors. Return
   validated grid geometry without snapping it back to the visible perimeter.

The 5% limit bounds scope; **it does not independently prove completeness**.
It is smaller than a whole missing rank/file (12.5%), but much smaller crops must
still be rejected using interior/exterior evidence. The rim allowance was not
increased to fit these screenshots. There are no filename, platform, position or
resolution exceptions. Existing normalization already maps valid rectangles to
512×512; classifier and cell extraction are unchanged.

## Validation and regressions

The controlled matrix contains 36 images: base sizes 160, 257 and 512; 2%/4%
scale differences on either axis; clean, highlight/arrow, and textured JPEG-82
scenes. It uses asymmetric margins, bilinear/bicubic resampling and independent
artificial drawings. It measures geometry, not classification of those drawings.
Twelve controls cover 14-pixel occlusion, 14-pixel cropping, a missing file, 7×7/9×9
grids and 8%/15% deformation outside the new route's scope.

Eight additional checks use different sizes/ratios: 193 at 3%, 401 at 4.5%, and
800 with 839/841-pixel opposite dimensions, along both axes. These check alignment
below 5% and rejection above it. They are not final evaluation or independent
photographic evidence. Real 25/26/29 controls with 14 pixels hidden from the first
file also remain rejected.

Existing negative surfaces, lines, other grids and previous geometry cases are
covered by `tests/test_detection*.py`. All six original failures pass again with
[v8](../../data/reports/digital-regressions-anisotropic-v8.json) and the
[candidate](../../data/reports/digital-regressions-anisotropic-candidate.json).
Real CLI subprocesses ran for every image and model before/after: 120 invocations.
Checks cover a single JSON output, exit code, empty stderr and agreement with
the Python pipeline, including initial structured failures.

[After results](../../data/reports/real-use-geometry-after.json),
[synthetic controls](../../data/reports/digital-geometry-synthetic-after.json) and
the [verification summary](../../data/reports/digital-geometry-summary.json)
record hashes and outcomes. The summary details the broad suite and additional
tests; overlapping runs are not added as distinct tests.

The broad suite completed with **845 passing tests**, no failures or skips.
All eight additional checks added after that suite was collected also passed.
The initial 54 focused tests are included in the 845.

## Reproduction

From the repository root with the existing environment and both models. Choose
fresh report names: tools refuse to overwrite earlier reports.

```bash
source .venv/bin/activate
python -m tools.evaluate_real_use --cli --output .cache/geometry-recheck.json
python -m tools.digital_geometry_scenarios --output .cache/geometry-controls.json
BOARDSNAP_TEST_MODEL=.cache/neural-tolerance-v1-conservative/best.pt \
  python -m pytest tests/test_detection*.py tests/test_video_development.py \
  tests/test_cli.py tests/test_cli_process.py tests/test_normalization.py \
  tests/test_segmentation.py tests/test_output.py tests/test_image_input.py -q
boardsnap .cache/real-use-tests/real-use-25.png \
  --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
boardsnap .cache/real-use-tests/real-use-29.png \
  --model .cache/neural-tolerance-v1-conservative/best.pt --orientation black-bottom
```

`--image-root PATH` accepts a corpus copy with identical filenames and hashes.
Names load evaluation labels, never inform recognition. The baseline uses the
detector at `e38df0ed8e3058afe5e98a3108a7469933cd6145`. To reproduce it, use an
isolated copy of that code with the new evaluation tools and identical data;
do not revert the current working directory. Usually reusing its report and
verifying hashes is sufficient; avoid rerunning unchanged inputs. Recheck the
six cases using `python -m tools.recheck_digital_regressions --model PATH --output REPORT`
with each model.

## Limitations and next step

This **bounded digital geometry extension** can be closed while preserving its
regressions, then the photographic pilot can proceed. This does not accept a
general product release. Outstanding items are:

- `real-use-4` texture confusion, separate from detection.
- Full neural pipeline replay of the 3,456 consulted images. Earlier verified-bound
  classification is not presented as an automatic pipeline evaluation.
- Exact new-source provenance and external confirmation of new transcriptions;
  do not create new partitions without reviewing relationships.
- Rotation, perspective, paper and photographic degradation, outside this change.
- A narrow covered background rim cannot universally be distinguished from a
  tiny crop. The exception is bounded and never promises recovery of hidden pieces.

Legacy datasets named `evaluation` used by regression tests were already consulted.
The independent final dataset has not been opened or evaluated.
