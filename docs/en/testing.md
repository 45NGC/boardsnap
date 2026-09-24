# Test plan

**English** | [Spanish](../es/testing.md) · [Overview](README.md)

This iteration only configures pytest. There are no implemented tests or images;
`python -m pytest` and `python -m pytest --collect-only` will exit with code `5`
until real cases are added.

The configuration in `pyproject.toml` limits discovery to `tests/`, uses
`importlib` import mode, and rejects unknown options or markers. Installing the
package first with `python -m pip install -e '.[dev]'` allows it to be tested
without manually adding `src/` to `sys.path`.

## Cases to add with each implementation

| Area | Planned evidence |
| --- | --- |
| Input | Missing files, empty or corrupt content, and supported formats. |
| Detection | Complete boards with and without margins, annotated boundaries, and negative examples without a board. |
| Normalization and segmentation | Exactly 64 crops with correct boundaries and order. |
| Orientation | An asymmetric position in both views with coordinates, plus cases without clues that check the convention of `a8` at the top left. |
| Classification | All 13 classes, on light and dark squares, by profile and resolution. |
| Piece placement | Starting position, empty and mixed ranks, compression of empty runs, and rank/file order; absence of the other FEN fields. |
| Complete pipeline | Exact JSON equality against independently annotated placements; errors without invented positions. |
| CLI | JSON on stdout, diagnostics on stderr, and the contract's exit codes. |

Manually constructed matrices will be inputs for serialization and orientation
unit tests, not substitutes for recognition evaluation. The starting position
alone is insufficient to test orientation: also use asymmetric positions and
positions that differ from the initial piece arrangement.

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

These selectors are ready for future tests; they do not currently select any
cases either. Exit codes are not altered to hide that absence.
