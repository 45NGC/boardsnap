# Photographed board localization

**English** | [Español](../es/photo-detection.md)

An initial geometric photo detector is available as
`boardsnap.photo_detection.detect_photo_board`. It receives RGB pixels and returns
four corners of a complete 8×8 grid. It uses no neural network, expected placement,
annotation, filename or known theme palette.

The digital detector, piece models and `boardsnap` behavior are unchanged.
This stage measures **localization**, not complete recognition. Automatic connection
to the photographic classifier is documented in the subsequent [photo pipeline](photo-pipeline.md).

## Method

1. Limit the working image to 1,200 pixels per side, retaining the mapping back to
   original coordinates. The input image is unchanged.
2. Propose quadrilaterals from edges/contours. If none validates, search two line
   families with projective grid spacing; equal image-space spacing is not required.
3. Provisionally rectify each proposal and use seven interior lines per direction
   to refine geometry. Bound the displacement and require intersection consensus.
4. Check alternation in 64 cells, all fourteen interior boundaries and four complete
   outer rims. Estimate backgrounds by rank to tolerate screen illumination changes.
5. Reject off-image extrapolation and 8×8 subsets of larger grids when the checker
   pattern continues outside. Multiple distinct validated boards produce ambiguity.

Corners are floating-point coordinates in the normalized RGB image, ordered
**top-left, top-right, bottom-right, bottom-left**. This is image geometry, not
white/black chess orientation. Failures reuse `BOARD_NOT_FOUND` and
`UNSUPPORTED_IMAGE`; no confidence scores are returned.

## Measurements and policy

Before validation measurement, the geometric policy required quadrilateral IoU
≥ 0.95, maximum corner error ≤ 1% of the annotated mean side, and maximum displacement
of all 81 grid intersections ≤ 8% of a square. These are pilot geometry criteria,
not product acceptance. Manual reference corners also have limited precision.

| Dataset | Chess.com | Lichess | Videos | Total within policy |
| --- | ---: | ---: | ---: | ---: |
| Development | 52/55 | 52/53 | 28/53 | 132/161 |
| Validation | 10/10 | 10/10 | 7/10 | 27/30 |

Every returned board meets the policy; the others are rejected. Development includes
the photograph excluded from classification because its corners remain reviewed.
The 161 photographs are not presented as 161 independent sources.

Validation misses `video-img_5403`, `video-img_5406` and `video-img_5407`. The detector
was not tuned to recover those examples after measuring them. Videos remain the
main limitation; direct-page results do not imply support for arbitrary interfaces,
videos or native mobile applications.

Reports contain reference/detected corners, metrics, hashes and failures:

- [Development](../../data/reports/photo-detection-development-v1.json).
- [Validation](../../data/reports/photo-detection-validation-v1.json).
- [Negative controls](../../data/reports/photo-detection-controls-v1.json):
  18/18 correct rejections. Keep the real interface in six development photos and
  remove the board, hide 14 of 64 normalized pixels of the first file, or hide the
  entire first file. These are constructed controls, not independent natural negatives.

No reserved final evaluation was accessed and no model was retrained. Report timings
come from local runs and are not isolated mobile performance benchmarks.

## Inspect a new photo

From the repository root with `.venv` activated:

```bash
python -m tools.detect_photo ".cache/real-use-tests/my-photo.jpg" --output .cache/photo-detection/my-photo
```

Use a new or empty output directory. The command saves:

- `outline.jpg`: reduced photo with a red contour and four numbered corners.
- `rectified.png`: a 512×512 perspective-corrected inspection image.
- `detection.json`: original-image coordinates and diagnostic scope.

This JSON belongs to a **diagnostic tool**. The recognition contract remains only
`piecePlacement`. Image-read/detection failures return JSON errors and exit code 1;
invalid arguments return 2. Previous previews and original photos are preserved.
PNG/JPEG input uses existing EXIF normalization; convert HEIC first.

A checked example is available locally at
`.cache/photo-detection-v1/chesscom-5393/outline.jpg` and `rectified.png`.
For a manual development test of piece classification after new detection:

```bash
python -m tools.recognize_photo .cache/photo-detection/my-photo/rectified.png --model .cache/neural-phone-v1/best.pt --orientation white-bottom --rectified
```

Use `black-bottom` where appropriate. Correct corners do not guarantee correct
pieces; the [photographic classifier limitations](phone-classifier-analysis.md) remain.

## Tests and limits

Seventeen photo-specific tests pass: perspective, tilt, illumination, marks,
recovery without an exterior contour, multiple grids, non-boards, other grid sizes,
partial crops, the 14-pixel control, narrow input and diagnostic outputs. The combined
photo/digital regression run passes 281 tests with three skipped because local
screenshots are absent. The seventeen photo tests were rerun after guarding narrow input.

```bash
python -m pytest tests/test_photo_detection.py tests/test_detection.py tests/test_detection_structure.py tests/test_detection_bounds.py tests/test_detection_border_grid.py tests/test_detection_clutter.py tests/test_detection_anisotropic.py -m "not evaluation" -q
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-validation-v1.json --output .cache/photo-detection-validation-recheck.json
```

Scope: complete grids, roughly frontal or moderately tilted/projected, with visible
alternation and sufficient size/contrast. Proposed sides must be at least 80 working
pixels and their maximum/minimum ratio below 2. Extreme tilt, severe glare/moire,
major occlusion, low-contrast squares and lens distortion are not guaranteed.
A decorative 8×8 checkerboard can be geometrically indistinguishable from an empty
chessboard.

The [photo pipeline](photo-pipeline.md) now integrates detection and rectification
with recognition through `--input-type photo`, preserving the digital path.
Photographic acceptance has not yet been declared.
