# Tests

`test_cli.py` checks adapter error and stream handling. `test_cli_process.py`
executes both `boardsnap` and `python -m boardsnap` with real images, compares
exact JSON, checks exit codes and ensures diagnostics stay outside stdout.
The console command must be registered first: `python -m pip install -e '.[dev]'`.
See the [CLI guide](../docs/en/cli.md).

`test_classification.py` checks classifier inputs, empty/background handling and
asset failures. `test_classification_images.py` checks all thirteen classes on both
backgrounds, template provenance, each real square and complete pixel-to-position
recognition with anonymous inputs. Tuning and evaluation keep separate markers.
`test_classification_report.py` checks metric denominators with controlled outcomes,
not recognition accuracy. See the [baseline and evaluation](../docs/en/classification.md).

`test_orientation.py` tests fallback/consistency policy and canonical cell mapping.
`test_orientation_images.py` reads real coordinate pixels with separate tuning
and evaluation markers, including absent, partial and conflicting labels.
Annotated piece matrices test the mapping only; they do not simulate measured
piece recognition. See the [orientation guide](../docs/en/orientation.md).

`test_normalization.py` and `test_segmentation.py` check cropping, resizing,
preserved orientation context and all 64 squares with exact ordering/coverage.
`test_preprocessing_images.py` runs input through segmentation on real captures:
16 tuning cases (`integration`) and 4 reserved cases (`evaluation`). These checks
do not classify pieces or resolve chess orientation. See the
[normalization guide](../docs/en/normalization.md).

`test_detection.py` covers exact synthetic grid geometry and negative cases.
`test_detection_images.py` compares real screenshot variants with reviewed
bounds: tuning cases use `integration`, held-out cases use `evaluation`.
See the [detection guide](../docs/en/detection.md) for scope and measurements.

`test_image_input.py` covers PNG/JPEG decoding, RGB normalization, EXIF,
transparency and the three structured input error codes using temporary images.
Run it with `python -m pytest tests/test_image_input.py`.

`test_output.py` verifies `boardsnap.output.build_result(board)`. All 53 unit
test cases pass against the implementation in `src/boardsnap/output.py`.

```bash
python -m pytest --collect-only -q
python -m pytest -m unit
```

`test_capture_lichess.py` checks manifest validation, partition separation and
overwrite protection. Its optional offline Chromium integration tests check
screenshots and annotations without contacting lichess. See the
[capture guide](../docs/en/capture-data.md) for installation and commands.

Piece classification and full-position checks are now implemented. Read the
[test plan in English](../docs/en/testing.md).

`test_dataset.py` verifies the 20 committed PNGs and their annotations, hashes,
bounds, canonical placements, paired orientations and fixed partition inventory.
Run these checks with `python -m pytest -m evaluation`. They check dataset
integrity, not recognition accuracy, and do not access the browser or network.

A [Spanish version of the test plan](../docs/es/testing.md) is also available.

`test_profiles.py` adds regression, provenance, split isolation and CLI checks
for additional styles. The experimental book profile has two strict expected
full-position failures (`xfail`), not two accepted positions. Results and scope
are recorded in the [profile guide](../docs/en/profiles.md).
