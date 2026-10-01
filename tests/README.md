# Tests

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

There are no piece classification tests yet. Read the
[test plan in English](../docs/en/testing.md).

`test_dataset.py` verifies the 20 committed PNGs and their annotations, hashes,
bounds, canonical placements, paired orientations and fixed partition inventory.
Run these checks with `python -m pytest -m evaluation`. They check dataset
integrity, not recognition accuracy, and do not access the browser or network.

A [Spanish version of the test plan](../docs/es/testing.md) is also available.
