# Automatic photographic recognition

**English** | [Español](../es/photo-pipeline.md)

The photo path now connects RGB input, four-corner detection, perspective
rectification, 64 crops, the neural classifier and canonical piece placement.
It is experimental and explicitly selected; the digital path stays the default.
No manual corners or annotation files are read during recognition.

## Run a photograph

With the virtual environment and the existing photographic model:

```bash
boardsnap ".cache/real-use-tests/my-photo.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

Use `black-bottom` when appropriate. Orientation describes the board view, not
the side to move. Photo mode requires an explicit orientation: coordinate reading
under perspective has not been validated. It rejects `auto` and `--profile` as
invalid invocations. `BOARDSNAP_MODEL` can supply the model if `--model` is omitted;
no model is downloaded or selected from local cache automatically. Choose the
photographic model deliberately; this work does not replace the digital model.
PNG/JPEG and EXIF normalization use the existing image input; convert HEIC first.

Python callers use:

```python
from boardsnap.pipeline import recognize_image

result = recognize_image("photo.jpg", input_type="photo",
                         model=".cache/neural-phone-v1/best.pt",
                         orientation="black-bottom")
```

Success still contains only `piecePlacement`. Input, detection and model failures
use existing structured errors and exit code 1. Invalid CLI arguments exit 2 on
stderr; processing diagnostics also go to stderr, never into the JSON on stdout.
The Python API raises stage exceptions, or `ValueError` for invalid configuration.

## Geometry and preprocessing

`rectify_board` lives in the installable core, independent of development tools.
It maps TL/TR/BR/BL boundaries to a 512×512 RGB image with OpenCV bilinear
interpolation, matching training. It rejects nonfinite, inverted, degenerate and
out-of-image corners instead of padding missing squares. It preserves the view
and glyph direction. Only the classified **cell order** is reversed for black
at the bottom; individual piece images are never rotated upside down.

Tests compare all 64 crops byte-for-byte with the original annotation/export
implementation for both orientations and perspective. The source is unchanged;
photo inference releases its owned images and square crops even on failure.

The [detector diagnostic](photo-detection.md) remains available for outlines and
rectified previews. Its JSON is separate from the recognition output contract.

## Validation and limits

The comparison report is [photo-pipeline-validation-v1.json](../../data/reports/photo-pipeline-validation-v1.json).
It runs all 30 previously consulted validation photos through the actual CLI and
compares with classification using reviewed corners. It reuses the frozen
geometry report for crop comparisons, checking detector, manifest and image
hashes, and requires CLI predictions to agree. Model and source hashes are recorded.
This is validation, not independent final acceptance; the model was not retrained.

| Source | Detected | Exact boards with annotated corners | Exact boards through CLI |
| --- | ---: | ---: | ---: |
| Chess.com | 10/10 | 3/10 | 5/10 |
| Lichess | 10/10 | 8/10 | 8/10 |
| Videos | 7/10 | 8/10 | 6/10 |
| Total | 27/30 | 19/30 | 19/30 |

Equal totals conceal different cases: automatic crops recover `chesscom-img_5396`
and `chesscom-img_5399`; detection rejects `video-img_5406` and `video-img_5407`,
which were correct with annotated corners. The third rejection, `video-img_5403`,
already had classification errors. Among the 27 detected images, no previously
exact position is lost and those two are gained. Neither the detector nor the
model was tuned using these results.

Annotated geometry yields 1,871/1,920 correct squares (97.45%). Automatic crops
yield 1,697/1,728 (98.21%) **only among the 27 detected images**; the denominators
cover different sets and the percentages alone do not establish an improvement.
The report includes per-class metrics and pixel differences between crops.

Verification: 184 integration/regression tests passed (eight evaluation tests
deselected); 48 targeted classifier/photo-path checks passed, followed by 27 photo
tests after completing the comparison-tool guards. These test sets overlap.
The installed `boardsnap` command was also checked against a known photo position.

To reproduce deliberately with a new report path:

```bash
python -m tools.evaluate_photo_pipeline --model .cache/neural-phone-v1/best.pt --output .cache/photo-pipeline-recheck.json
python -m pytest tests/test_photo_pipeline.py tests/test_photo_detection.py tests/test_cli.py tests/test_orientation_input.py tests/test_phone_inference.py tests/test_phone_geometry.py tests/test_phone_squares.py tests/test_cli_process.py -m "not evaluation" -q
```

Detection and classification are separate sources of error. A successful command
means processing completed, not that all pieces are correct. Moderate perspective
and a complete visible grid remain required; severe glare, occlusion, distortion
and some video photographs are not covered. The [classifier diagnosis](phone-classifier-analysis.md)
still applies. Final acceptance, model distribution and Flutter integration are
separate work; the reserved final set has not been used.
