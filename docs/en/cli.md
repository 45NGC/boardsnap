# Command-line recognition

**English** | [Spanish](../es/cli.md) · [Overview](README.md)

The CLI is a separate adapter over `boardsnap.pipeline.recognize_image`. The core
already connects image loading, board detection, normalization, segmentation,
orientation, classification and `build_result`. No recognition logic is duplicated
in the CLI, and the core does not import adapters or depend on Flutter or a web framework.

## Install and run

From the repository root, using the existing environment:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
boardsnap data/tuning/lichess-cburnett-brown-v1/pos-001-white.png
```

Reinstall once after adding the console entry point; editable installation then
reflects Python source changes. With dependencies already installed, `python -m
pip install --no-deps -e .` also registers the command. No new runtime dependency
is required. Without activating the environment, use `.venv/bin/boardsnap`.

Expected output for the example:

```json
{"piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

The equivalent module invocation is:

```bash
python -m boardsnap data/tuning/lichess-cburnett-brown-v1/pos-001-white.png
boardsnap --help
boardsnap "path with spaces/image.png"
boardsnap -- -image.png
```

Use `--` for a filename beginning with a dash. Exactly one image path is accepted;
batch processing, stdin images, HTTP and Flutter integration are not provided.
Relative paths refer to the current working directory, and installed assets work
outside the repository. The command does not write previews or modify inputs.

## Orientation option

Use `--orientation white-bottom`, `--orientation black-bottom` or `--orientation auto`.
The default is `auto`: read coordinates, then assume White at the bottom if they
are unusable. Explicit values skip coordinate reading and override contradictory
labels. This describes the image view, never the side to move. It works with
`--profile` and keeps exactly the same JSON response.

```bash
boardsnap image.png --orientation black-bottom
boardsnap image.png --profile chesscom-default-green-v1 --orientation white-bottom
```

Invalid values or a missing option value exit 2 with no JSON/stdout, before
opening the image. See [orientation semantics and tests](orientation.md).

## Streams and process status

| Invocation | stdout | stderr | Exit code |
| --- | --- | --- | --- |
| Image recognized | One success JSON object and a newline | Normally empty | 0 |
| Image/processing failure | One error JSON object and a newline | Diagnostics if applicable | 1 |
| Missing path, extra arguments or unknown option | Empty | Usage/error text | 2 |
| `--help` | Help text (not JSON) | Empty | 0 |

The response follows the [output contract](output-contract.md): only
`piecePlacement` on success, or only `error` with `code` and `message` on failure.
Only the first FEN field is returned. Missing files are processing failures
(`INPUT_READ_ERROR`, exit 1), not argument-syntax failures.

The adapter serializes known stage exceptions unchanged. Other exceptions during
recognition become `PROCESSING_FAILED` with the message `Could not recognize the
image.`; exception type/details are printed only to stderr. Python stdout writes
inside recognition are redirected to stderr so they cannot contaminate the JSON.
The core Python API still exposes its original exceptions. Process-control events
such as Ctrl+C are not converted into image errors.

```bash
boardsnap image.png > result.json 2> diagnostics.log
echo $?
```

Run `echo $?` immediately after the recognition command to inspect its exit code.
An error result contains no partial position, confidence or invented empty board.

## Coverage and tests

Select a [profile](profiles.md) using `--profile PROFILE_ID`; omission retains
brown/cburnett. The three digital profiles are evaluated on a small corpus;
the book profile is experimental with two known full-position failures.
Unknown profile IDs are usage errors (exit 2). [Flutter transport](flutter-integration.md)
is documented separately; the CLI does not start a server.

```bash
boardsnap image.png --profile chesscom-default-green-v1
```

```bash
python -m pytest tests/test_cli.py tests/test_cli_process.py
python -m pytest
```

Subprocess tests exercise both actual entry points from a different working
directory. All 16 tuning and 4 reserved captures are copied to anonymous filenames
without sidecars; output is compared exactly, including its final newline and
absence of stderr diagnostics. Cases also cover missing/directory/empty/corrupt
inputs, unsupported format, absent/multiple boards, help, invalid arguments, paths
with spaces/unicode and leading dashes. Adapter unit tests inject errors and noisy
stages to verify all error codes, unexpected failures, stream restoration and
process-control propagation; these injections do not measure recognition accuracy.

Original-profile baseline: all **74 CLI tests** passed (10 unit, 56 integration and 8
reserved-image subprocess cases). At that stage, the full suite passed **781 tests**, with
7 optional browser tests skipped. Both installed and module commands were
checked without changing the recognition templates or evaluation data.
