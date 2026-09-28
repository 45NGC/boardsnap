# Tests

`test_output.py` verifies `boardsnap.output.build_result(board)`. All 53 unit
test cases pass against the implementation in `src/boardsnap/output.py`.

```bash
python -m pytest --collect-only -q
python -m pytest -m unit
```

There are no image recognition or integration tests yet. Read the
[test plan in English](../docs/en/testing.md).

A [Spanish version of the test plan](../docs/es/testing.md) is also available.
