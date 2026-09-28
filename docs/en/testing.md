# Test plan

**English** | [Spanish](../es/testing.md) · [Overview](README.md)

The first unit tests are in [test_output.py](../../tests/test_output.py). All
53 cases pass against `boardsnap.output.build_result(board)`, implemented in
[output.py](../../src/boardsnap/output.py). No recognition models or images
have been added.

Both `python -m pytest --collect-only` and `python -m pytest` succeed with exit
code `0`. The suite checks the actual output implementation without `skip`,
`xfail`, or simulated results.

The configuration in `pyproject.toml` limits discovery to `tests/`, uses
`importlib` import mode, and rejects unknown options or markers. Installing the
package first with `python -m pip install -e '.[dev]'` allows it to be tested
without manually adding `src/` to `sys.path`.

## Current output tests

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

`data/tuning/` will contain examples for templates, tuning, and future training.
`tests/fixtures/evaluation/` will contain held-out images with their expected
piece placements; they will not be used to tune the engine. Crops and other
variants will remain in their original image's partition. Source positions
will also be kept separate to avoid evaluating near-identical copies.

The `unit`, `integration`, and `evaluation` markers have been registered:

```bash
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m evaluation
```

The `unit` selector runs the current output tests. There are no `integration`
or `evaluation` tests yet, so those selectors exit with code `5`. Exit codes
are not altered to hide missing tests or missing functionality.
