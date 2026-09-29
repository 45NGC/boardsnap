# Tests

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

There are no image recognition tests yet. Read the
[test plan in English](../docs/en/testing.md).

A [Spanish version of the test plan](../docs/es/testing.md) is also available.
