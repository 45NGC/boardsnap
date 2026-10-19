# Bounded border and grid recovery

[Español](../es/border-grid-recovery.md) · [Previous diagnosis](video-009-010-diagnosis.md)

009 and 010 now work through automatic recognition with v8 and the tolerance
candidate, without changing their weights. The detector separates evidence about
the visible perimeter from the geometric rectangle needed for 64 uniform cells.

## Recovery requirements

Existing routes keep their filters and priority. Recovery runs only when none
returns a board. It requires:

1. An interior-line proposal with all seven divisions of each axis aligned and
   sufficiently strong. The five-line consensus allowed for ordinary proposals
   is not sufficient for this recovery.
2. The alternating 8 × 8 interior pattern and four visible edges passing the
   original exterior structural validation.
3. Exactly one visible edge inset by more than one pixel relative to the grid.
   Its maximum displacement is `min(6, floor(cell_side × 0.08))` input pixels:
   four pixels for these boards. Other edges may differ by only one raster pixel;
   larger outward expansion is also rejected.
4. A grid entirely inside the image, with exterior pixels available, and no
   continuation indicating a larger-than-8 × 8 grid.

`_BorderGrid` retains separate `grid` and `visible` geometry. After validating the
visible perimeter, the detector returns **grid** for normalization/segmentation.
It does not snap it back to the visible border and recreate the alignment error.
No pixels are padded, pieces reconstructed, or labels, filenames or models used
for detection. Public JSON remains exclusively `piecePlacement`, or a structured
error.

The exception tolerates a narrow exterior strip, not missing cells. It cannot
universally determine whether a few obscured pixels came from a frame, shadow
or crop. Coverage is limited to the evidence and budget above; this does not
promise arbitrary partial-board recovery or unknown-design support.

## References and results

The historical manifest remains unchanged. A separate [geometry reference](../../data/manifests/video-grid-geometry-v1.json)
records the visible border and seven lines measured before this fix. Hashes tie
it to the original images and diagnosis. Only tests and measurement tools use
these references, never the detector.

| Capture | Visible perimeter | Segmentation grid |
| --- | --- | --- |
| 009 | `(13, 23, 467, 481)` | `(10, 24, 466, 480)` |
| 010 | `(12, 2, 466, 460)` | `(9, 3, 465, 459)` |

Reports retain classification with the visible rectangle as a historical control:
uniformly splitting that rectangle still fails. They add `gridBoundsRecognition`
for classification with aligned geometry and compare detection against that same
reference. Earlier results and expected positions are not rewritten.

All [15 v8 cases](../../data/reports/video-development-v2-border-v8.json) and
[15 candidate cases](../../data/reports/video-development-v2-border-tolerance.json)
pass detection, classification with reference geometry and the full pipeline.
001/002/003 remain correct, as do the six original failures, rechecked with
[v8](../../data/reports/digital-regressions-border-v8.json) and the
[candidate](../../data/reports/digital-regressions-border-tolerance.json).

CLI tests use unrelated filenames, a foreign working directory and no screenshot
sidecars. They require exact JSON, exit 0 and empty stderr for 009/010 with both
models. The 14-pixel occlusion control requires `BOARD_NOT_FOUND`, exit 1 and empty
stderr.

## Regressions and verification scope

Tests include 8- and 14-pixel occlusions on every edge of both captures, rotated
and translated recovery, different synthetic colors, over-budget strips, multiple
obscured edges, crops escaping the frame, existing incomplete boards, other grid
dimensions, multiple boards and board-free negatives. Previously accepted
rectangles do not invoke the new recovery.

Relevant detection/CLI regressions, real cases and six original failures are
checked. **This change does not repeat neural inference over the complete
3456-image corpus**: routes that already returned a board retain their behavior.
That comprehensive pipeline run remains part of candidate closeout. Final
acceptance and distribution are not performed; old consulted datasets remain
regressions rather than independent final evidence.

The [validation record](../../data/reports/border-grid-recovery-validation.json)
links reports and hashes. The broad suite recorded 668 passing tests and two
historical visible-rectangle checks as expected failures. After converting them
to explicit perimeter/grid assertions, the final video suite passed all 118 tests
without expected failures. The broad suite includes the CLI with both models and
the negative controls described above.

## Commands

```bash
boardsnap .cache/real-use-tests/chesscom-video-009.png --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
boardsnap .cache/real-use-tests/chesscom-video-010.png --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
python -m tools.development_cases --model .cache/neural-tolerance-v1-conservative/best.pt --grid-references data/manifests/video-grid-geometry-v1.json --output .cache/border-grid-development.json
python -m pytest tests/test_detection_border_grid.py
BOARDSNAP_TEST_MODEL=.cache/neural-tolerance-v1-conservative/best.pt python -m pytest tests/test_detection*.py tests/test_video_development.py tests/test_cli.py tests/test_cli_process.py
```

To compare v8, change only `--model` or `BOARDSNAP_TEST_MODEL` to
`.cache/neural-styles-v8/best.pt`. Without `--grid-references`, the measurement tool
retains the historical visible reference; it can report geometric differences
even when the recognized position is correct.
