# Test plan

**English** | [Spanish](../es/testing.md) · [Overview](README.md)

The first unit tests are in [test_output.py](../../tests/test_output.py). All
53 cases pass against `boardsnap.output.build_result(board)`, implemented in
[output.py](../../src/boardsnap/output.py). The first 20 annotated screenshots
are included; the first template baseline and full Python recognition flow are implemented.

Both `python -m pytest --collect-only` and `python -m pytest` succeed with exit
code `0`. Output and dataset checks run locally. The capture tool's seven
browser integration cases are skipped unless explicitly enabled as described
in the [capture guide](capture-data.md). Recognition accuracy tests use real pixels;
isolated policy/reporting unit tests explicitly control their inputs/outcomes.

The configuration in `pyproject.toml` limits discovery to `tests/`, uses
`importlib` import mode, and rejects unknown options or markers. Installing the
package first with `python -m pip install -e '.[dev]'` allows it to be tested
without manually adding `src/` to `sys.path`.

## Current output tests

The [CLI tests](cli.md) cover the installed command and module entry point with
exact JSON, structured errors, process exit codes and stdout/stderr separation.
Run `python -m pytest tests/test_cli.py tests/test_cli_process.py`. Reinstall the
editable package after adding/changing its console entry point before testing.

The [output contract](output-contract.md) specifies matrix values, ordering,
result shape, and validation exceptions. The suite covers:

- The starting position, an empty board, and an asymmetric position, with exact
  expected dictionaries and no additional fields.
- All twelve piece symbols and a full board, without game legality checks.
- Empty runs of lengths one through eight, leading and trailing gaps, multiple
  gaps within a rank, and resets between ranks.
- All four board corners, canonical rank/file order, tuple inputs, and an
  unchanged input matrix after serialization.
- Invalid dimensions, including ragged matrices that still contain 64 cells.
- Invalid board, row, and cell types, invalid symbols, and empty values other
  than `None`, which must raise the documented exceptions.

The handwritten expectations are independent of the production implementation.
The fixture helper only converts dots to `None`; it does not generate FEN or
simulate recognition. Canonical ordering tests do not test orientation detection
from an image.

## Cases to add with each implementation

Image input is now covered by 31 unit cases in
[test_image_input.py](../../tests/test_image_input.py). They distinguish file
access, decoding and unsupported-input failures, and check normalization,
EXIF, transparency and ownership of decoded pixels. See the
[input guide](image-input.md).

Normalization and segmentation have 39 synthetic unit cases in
`test_normalization.py` and `test_segmentation.py`, plus 16 tuning and 4 reserved
cases in `test_preprocessing_images.py`. They check exact crop boundaries, sizes,
all 64 cells in image order, reconstruction without omitted/duplicated pixels,
invalid inputs and independent preservation of the source for orientation.
See the [normalization guide](normalization.md) for commands and limitations.
Orientation adds 38 unit cases and 162 pixel/provenance cases (130 development,
32 reserved) in `test_orientation.py` and `test_orientation_images.py`. They check
readable coordinates, missing/partial/conflicting labels and exact canonical
mapping of annotated asymmetric positions. Those matrices are test inputs for
mapping, not recognized pieces. See the [orientation guide](orientation.md).
Classification adds input/asset unit checks, real square/background coverage and
full-position tests on anonymous images. Reports include exact positions and all
thirteen classes with per-background support; see [classification](classification.md).
Future learned models must use separate training, validation and evaluation groups.

| Area | Planned evidence |
| --- | --- |
| Input | Missing files, empty or corrupt content, and supported formats. |
| Detection | Complete boards with and without margins, annotated boundaries, and negative examples without a board. |
| Normalization and segmentation | Exactly 64 crops with correct boundaries and order. |
| Orientation | An asymmetric position in both views with coordinates, plus cases without clues that check the convention of `a8` at the top left. |
| Classification | All 13 classes, on light and dark squares, by profile and resolution. |
| Complete pipeline | Exact JSON equality against independently annotated placements; errors without invented positions. |
| CLI | JSON on stdout, diagnostics on stderr, and the contract's exit codes. |

Manually constructed matrices are inputs for serialization unit tests, not
substitutes for recognition evaluation. The starting position alone is
insufficient to test orientation: also use asymmetric positions and positions
that differ from the initial piece arrangement.

## Partitions and planned commands

`data/tuning/` contains 16 images for templates, tuning, and future experiments.
`tests/fixtures/evaluation/` contains four reserved images with their expected
piece placements; they will not be used to tune the engine. Crops and other
variants will remain in their original image's partition. Source positions
will also be kept separate to avoid evaluating near-identical copies.

The `unit`, `integration`, and `evaluation` markers have been registered:

```bash
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m evaluation
```

The `unit` selector runs output, image input, synthetic detection, normalization,
segmentation, orientation, classifier/report accounting and capture-manifest tests.
`integration` selects tuning-image detection/preprocessing/orientation/classification checks and
the optional offline browser tests. `evaluation` selects reserved-image
detection/preprocessing/orientation/classification checks and
[dataset integrity checks](../../tests/test_dataset.py): PNG signatures and
dimensions, hashes, annotations, bounds within images, paired orientations,
manifest consistency and disjoint positions/groups. Integrity tests alone do not
recognize pixels. Recognition tests use only images as inputs; annotations remain
expected results. Detection and classification have limited measured results in
their respective guides; the current corpus does not establish broad style support.
