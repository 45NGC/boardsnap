# Diagnosis of videos 009 and 010

[Español](../es/video-009-010-diagnosis.md) · [Development corpus](video-development.md)

**Historical diagnosis before the fix.** [Bounded recovery](border-grid-recovery.md)
now resolves both captures in the CLI. The report below preserves the earlier failure.

**Recommendation: fix geometry handling before training.** Both full positions
are recognized correctly by **v8 and the current candidate** when cropped using
the grid inferred from interior lines. This diagnosis changes neither weights,
production code nor annotations. The CLI still rejects these images; corrected-crop
results are diagnostic probes, not a deployed fix.

Two causes were reproduced: the detector rejects the left exterior strip of an
otherwise valid interior proposal, and the annotated visible rectangle is a poor
reference for uniformly dividing the 64 squares. That misalignment made the
failures look like a piece-style recognition problem.

## Inputs and references

Only the two archived PNGs in `data/development/video-cases-v2`, their reviewed
manifest labels and these weights are used:

- v8: `.cache/neural-styles-v8/best.pt`.
- Candidate: `.cache/neural-tolerance-v1-conservative/best.pt`.

The user confirmed `white-bottom` for both. The [reproducible report](../../data/reports/video-009-010-diagnosis.json)
retains hashes, detector traces, bounds, positions, square errors and interpolation
controls. No reserved final evaluation data or training are used. Both images
retain their original development group.

## Where detection stops

`detect_board` returns `BOARD_NOT_FOUND` on both images. Video-background edges
connect to the exterior, producing a component covering the image; its initial
fit does not find a regular grid. However, `_interior_grid_candidates` **does find
the seven interior lines**. Refinement places them at 57-pixel intervals:

| Capture | Vertical lines | Horizontal lines |
| --- | --- | --- |
| 009 | 67, 124, 181, 238, 295, 352, 409 | 81, 138, 195, 252, 309, 366, 423 |
| 010 | 66, 123, 180, 237, 294, 351, 408 | 60, 117, 174, 231, 288, 345, 402 |

The interior structural pattern passes, but
`_structural_pattern(..., complete_edges=True)` rejects the **left edge** before
acceptance. `_refine_grid(..., visible=True)` also cannot return a rectangle:
its local search fails to confirm that exterior transition. The problem is not
orientation or missing interior lines.
The left-edge pattern matches 5 of 8 cells in 009 and 4 of 8 in 010; the gate
requires at least 6.

## Visible rectangle versus geometric grid

Right and bottom coordinates below are exclusive.

| Capture | Current reviewed rectangle | Interior-line grid |
| --- | --- | --- |
| 009 | `(13, 23, 467, 481)` — 454 × 458 | `(10, 24, 466, 480)` — 456 × 456 |
| 010 | `(12, 2, 466, 460)` — 454 × 458 | `(9, 3, 465, 459)` — 456 × 456 |

The current manifest assigns the same rectangle to `box` and `gridBox`. That
equality does not describe these captures well: the visible left strip is offset
from the extrapolated lines. The inferred rectangles remain inside the PNG;
using them requires no invented pixels or reconstructed piece. They include some
exterior-strip pixels beside the first file.

Uniform division of the reviewed rectangle uses a horizontal step of 56.75 pixels,
starting 3 pixels right of the inferred origin. Interior-line offsets range from
2.75 to 1.25 pixels. The first square's center is displaced about 2.875 input
pixels, roughly 3.2 pixels after 64 × 64 normalization. This matters to the
framing-sensitive classifier.

The inferred geometry is supported by pixels, **not a newly approved manual
annotation**. The original manifest is preserved to expose the discrepancy.
Before changing bounds semantics, review `box` versus `gridBox`, including the
partly occluded/cropped strip. The screenshot alone cannot establish whether the
strip comes from video cropping, a shadow or compositing.

## Errors with reviewed bounds

### Capture 009

Expected placement:

```text
3rkb1r/pp2qpp1/7p/2pP4/4p1QP/2N1P1B1/PP3PP1/n1K3NR
```

| Square | Expected | v8 | Candidate |
| --- | --- | --- | --- |
| a7 | Black pawn | Empty | Empty |
| b7 | Black pawn | Empty | Empty |
| c3 | White knight | White queen | White queen |
| a2 | White pawn | Empty | Empty |
| b2 | White pawn | White rook | Correct |

v8 gets **59/64** squares correct; the candidate gets **60/64**. All remaining
squares are correct. Last-move highlighting is on c1/d1, away from these errors.

### Capture 010

Expected placement:

```text
8/8/8/p6p/P3K1kP/4P3/8/8
```

| Square | Expected | v8 | Candidate |
| --- | --- | --- | --- |
| a5 | Black pawn | Empty | Empty |
| a4 | White pawn | Empty | Empty |

Both models get **62/64** correct. The a4 white pawn has a yellow highlight; the
a5 black pawn does not. Highlighting affects appearance, but does not need to be
removed to recognize the position.

## Controlled comparisons

The diagnostic grid is derived automatically from pixels without using the
expected placement to select it. The tool requires a unique valid interior
proposal; it still records that production rejects its exterior-edge check.

| Crop | 009 v8 / candidate | 010 v8 / candidate |
| --- | --- | --- |
| Reviewed rectangle, usual LANCZOS | 5 / 4 errors | 2 / 2 errors |
| Interior grid, both axes | **0 / 0** | **0 / 0** |
| Correct horizontal geometry only, retain reviewed vertical bounds | **0 / 0** | **0 / 0** |
| Reviewed rectangle, nearest neighbor | 8 / 4 errors | 2 / 2 errors |
| Reviewed rectangle, bilinear | 5 / 4 errors | 2 / 2 errors |
| Reviewed rectangle, bicubic | 5 / 4 errors | 2 / 2 errors |

Horizontal correction is sufficient **for these two images**. This does not
establish that every line-derived crop is safe or that all video captures work.

- **Resolution:** about 57 pixels per square. Both models succeed with the same
  source pixels after alignment; upscaling to recover missing detail is unnecessary.
- **Style:** the piece-set identifier is unconfirmed in provenance. It cannot be
  declared absent from training; success with existing weights contradicts the
  claim that learning a new style is essential here.
- **Colors/marks:** unchanged in successful crops. Recoloring, highlight removal
  and grayscale conversion are not required.
- **Resampling:** changing interpolation alone fails. Bounds, uniform segmentation
  and resampling together change local framing.
- **Crop geometry:** directly supported by the controls and concentration of
  errors in the first files.

## Why detection was not relaxed

Removing `complete_edges=True` would be small, but unsafe. As a negative control,
**14 pixels of the first file** were covered in each image while retaining the
interior lines. The interior structural check still passes; the exterior check
rejects it. Accepting a grid solely on its interior lines would remove that
protection against partial content.

This probes the validation function, not a complete false-positive evaluation.
It is enough to reject deleting that check as a low-risk fix. No fixed three-pixel
shift or filename-specific rule was applied. No production improvement is claimed;
existing expected failures remain in place.

## Recommended next step

1. Review the two annotations, separating **visible surface**, **geometric grid**
   and any occluded strip. Preserve placement, orientation and source group.
2. Design a bounded recovery for proposals with seven consistent lines per axis
   and a narrow exterior strip: measure visible-edge versus grid disagreement,
   require evidence on other edges and reject missing cells. Set its allowance
   using validation, not just these two PNGs.
3. Preserve grid origin and spacing through normalization/segmentation. Do not
   automatically snap the grid to a visible border when that misaligns squares;
   do not invent or pad content outside the screenshot.
4. Check both models: exact positions for 009/010; retain the other 13 development
   cases, six original failures and consulted regression corpus. Include frames,
   shadows and strips of 1, 2, 4, 8 and 14 pixels, genuinely cropped boards, larger
   grids and board-free negatives. Measure visible bounds and grid alignment
   separately.

**Do not train now.** If errors remain after validated geometric correction,
prepare training additions with different positions: white/black pawns, knights,
queens and rooks on both backgrounds; highlights and clean controls; 40–80 pixels
per square and small framing/resampling variations. Keep these positions in
development and group variants by game; their current source group is conservative
and must not be treated as independent data. Risks include memorizing a style,
background or offset, and degrading clean/arrow performance. Validate by class
and complete board against untouched v8 and candidate references. This is a
contingency, not an established training requirement.

## Reproduction

```bash
python -m tools.analyze_video_failures
python -m pytest tests/test_video_failure_diagnosis.py
```

Crop sheets and bound overlays are written to `.cache/video-failure-analysis/`.
Red shows the reviewed rectangle; cyan shows the inferred grid. The tool verifies
hashes and leaves the public `piecePlacement`/structured-error contract intact.
The command now writes `current-diagnosis.json` in that cache directory using the
current detector, preserving the archived pre-fix report.
