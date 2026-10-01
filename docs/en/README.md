# BoardSnap

**English** | [Spanish](../es/README.md)

`boardsnap` will be a Python engine that receives an image of a digital
chessboard or a book diagram and returns a single piece placement to the
Flutter application **chess-scanner**.

**Status: image input, first-profile detection and piece placement serialization are implemented.** The package converts
an already-classified 8 × 8 matrix into the output dictionary through
`boardsnap.output.build_result(board)`. All 53 output unit test cases pass.
Other modules will be created as their functionality is implemented.

[Image input](image-input.md) reads static PNG/JPEG files as fully loaded RGB
images and provides structured input errors through `ImageInputError`.
[Board detection](detection.md) returns grid bounds for the brown lichess profile.
Piece recognition and the recognition CLI remain pending.
The first dataset contains 20 annotated PNGs (16 tuning, 4 evaluation) for
`lichess-cburnett-brown-v1`. The JSON examples describe the output contract; they do not
represent recognition results from images.

A separate [capture utility](capture-data.md) collects screenshots and known
labels from the lichess editor. It uses the optional `capture` dependency extra.

## Scope

The engine will locate a board, crop and normalize it, split it into 64 squares,
identify pieces, and resolve orientation before serializing the position.
The output will contain only the first field of FEN:

```json
{
  "piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
}
```

There will be no interface, editor, game analysis, side to move, castling rights,
or en passant state. The engine will not return confidence scores, uncertain
squares, alternatives, or confirmation requests. Piece corrections will be
handled by the chess-scanner editor.

The [output contract](output-contract.md) defines square order, default
orientation, and structured errors. The Flutter integration mechanism requires
an explicit decision; the core will remain independent of Flutter and any web
framework.

The [output.py walkthrough](output-walkthrough.md) explains the output function
step by step, with examples of validation and empty-square compression.

## Development installation

Requires Python **3.11 or later**, `pip`, and `venv` support. From the repository
root, in a POSIX shell:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c "import boardsnap; print(boardsnap.__file__)"
```

If your Python distribution does not include `ensurepip`, install your system's
virtual environment support before creating `.venv`.

Pillow decodes images; NumPy and headless OpenCV provide board detection.
`setuptools` builds the package and the `dev` extra installs `pytest`.
PyTorch has not been added; classification remains a later stage.

## Structure

```text
src/boardsnap/
    __init__.py
    output.py            # Matrix validation and piece placement serialization
    image_input.py       # PNG/JPEG decoding, RGB normalization and input errors
    detection.py         # Grid bounds for the first brown-board profile
tools/                   # Dataset capture utility and example manifest
docs/
    en/                 # English documentation
    es/                 # Spanish documentation
data/manifests/          # Fixed collection manifest and split assignments
data/tuning/             # 16 initial tuning images and annotations
tests/
    README.md
    test_output.py       # Output specification, written before implementation
    test_dataset.py      # Image/annotation integrity and split checks
    fixtures/evaluation/ # 4 reserved evaluation images and annotations
```

The [architecture](architecture.md) describes the flow and separation of
responsibilities. Input, detection and output stages are implemented. The [roadmap](roadmap.md)
compares approaches and defines the next iterations. The [tuning data](tuning-data.md)
and [evaluation images](evaluation-data.md) guides describe the current data
partitions. Both languages contain the same documents; changes to the contract
or scope should be reflected in both versions.

Code, comments, configuration, and general project files use English. Spanish
content is limited to the documentation in `docs/es/`.

## Tests

After installing the `dev` extra:

```bash
python -m pytest
python -m pytest --collect-only
```

The 53 output tests cover serialization and internal matrix validation, not
image recognition or orientation detection. Capture validation tests also run
by default. Optional offline browser tests require explicit activation; see
the [capture guide](capture-data.md). Dataset integrity checks run by default
and can also be selected with `python -m pytest -m evaluation`; they do not
measure image recognition accuracy.

Configuration is in `pyproject.toml`. To run only the initial unit tests:

```bash
python -m pytest -m unit
```

The [test plan](testing.md) covers detection, orientation, pieces, serialization,
and errors using known positions. Evaluation images will be kept separate from
those used to tune recognition.

## Planned CLI

A later iteration will enable this interface:

```bash
boardsnap image.png
```

**This command is not registered or implemented yet.** It will produce one JSON
object per image according to the contract, independently of Flutter integration.

## Styles and limitations

Detection is implemented and tested for `lichess-cburnett-brown-v1`; see its
[measured scope and limitations](detection.md). Full piece recognition has not
been implemented for any style. Other lichess themes, chess.com and printed
diagrams remain future profiles, not implied compatibility.

Photographs of physical boards with three-dimensional pieces are out of scope.
Compatibility with every design, color, or resolution is not assumed. The first
profiles will also exclude partial boards, animations, occluded pieces, arrows,
multiple boards, and heavily skewed or degraded images. Without orientation
clues, the engine will assume White at the bottom (`a8` at the top left); an
image with Black at the bottom and no coordinates may be reversed relative to
the actual position.

## License

The repository includes the [GNU Affero General Public License v3](../../LICENSE).
