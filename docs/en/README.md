# BoardSnap

**English** | [Spanish](../es/README.md)

`boardsnap` will be a Python engine that receives an image of a digital
chessboard or a book diagram and returns a single piece placement to the
Flutter application **chess-scanner**.

**Status: the Python pipeline and JSON CLI support three evaluated digital profiles.**
The [profile guide](profiles.md) describes brown/cburnett, blue/cburnett and the
captured Chess.com green style. The book profile is **experimental**: 126/128
reserved squares correct, but 0/2 full positions. The dataset has 65 images
(51 tuning, 14 reserved). [Flutter integration](flutter-integration.md) is
specified as a future HTTPS adapter for Android, iOS and web; it is not implemented.

[Image input](image-input.md) reads static PNG/JPEG files as fully loaded RGB
images and provides structured input errors through `ImageInputError`.
[Board detection](detection.md) combines known palettes with structural grid
checks. A separate 28-image rectangle corpus covers new digital styles and
real-use markings; these results do not measure piece classification.
[Normalization and segmentation](normalization.md) produce an 8 × 8 matrix of
64 × 64 RGB crops while preserving the full source for later orientation.
[Orientation](orientation.md) accepts an explicit image view through the pipeline
and CLI. The default `auto` reads coordinates and assumes White at the bottom
without usable clues; explicit values take priority.
The [classifier](classification.md) recognizes thirteen classes using tuning-only
templates. `boardsnap.pipeline.recognize_image(path)` returns piece placement.
The [recognition CLI](cli.md) exposes `boardsnap image.png` with JSON and exit codes.
The first dataset contains 20 annotated PNGs (16 tuning, 4 evaluation) for
`lichess-cburnett-brown-v1`. The JSON examples describe the output contract; they do not
represent recognition results from images.

A separate [capture utility](capture-data.md) collects screenshots and known
labels from the lichess editor. It uses the optional `capture` dependency extra.

The new [position plan](position-plan.md) contains 80 placements from 20 legal
generated sequences, split into 56 training, 12 validation and 12 evaluation
positions before capture. Its report checks coverage only.
[Configurable captures](configurable-capture.md) now use this plan for both
platforms; the local 16-image pilot verifies collection, not recognition accuracy.

The [first clean classifier corpus](first-clean-corpus.md) contains 3600 verified
captures: six piece sets on three backgrounds each, both orientations and two
viewport sizes. Its 80 positions retain the frozen training/validation/evaluation
split. The separate 36-image style check is excluded. The optional [PyTorch baseline](neural-classifier.md) is now trained and evaluated; templates remain the default.

The [labeled square dataset](square-dataset.md) provides 64 RGB crops per board,
canonical labels and inherited partitions. Verified bounds isolate classification;
detected bounds retain upstream errors for future pipeline measurements.

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
orientation, and structured errors. The [Flutter design](flutter-integration.md)
proposes HTTPS; the core remains independent of Flutter and web frameworks.

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
The optional `ml` extra installs PyTorch; see [training, saved artifacts and CPU results](neural-classifier.md).

## Structure

```text
src/boardsnap/
    __init__.py
    output.py            # Matrix validation and piece placement serialization
    image_input.py       # PNG/JPEG decoding, RGB normalization and input errors
    profiles.py          # Explicit palettes, artwork and coordinate layouts
    detection.py         # Grid bounds for the selected profile
    normalization.py     # Resize board and preserve source orientation clues
    segmentation.py      # 64 independent square crops in image order
    orientation.py       # Coordinate reading and canonical cell mapping
    assets/              # Coordinate glyph templates from tuning data
    classification.py    # Thirteen-class template baseline
    pipeline.py          # Image-to-piecePlacement Python API
    adapters/cli.py       # JSON CLI, separate from recognition logic
    __main__.py          # python -m boardsnap entry point
tools/                   # Dataset capture and detection/square previews
docs/
    en/                 # English documentation
    es/                 # Spanish documentation
data/manifests/          # Fixed collection manifest and split assignments
data/tuning/             # 51 tuning images and annotations
tests/
    README.md
    test_output.py       # Output specification, written before implementation
    test_dataset.py      # Image/annotation integrity and split checks
    fixtures/evaluation/ # 14 reserved evaluation images and annotations
```

The [architecture](architecture.md) describes the flow and separation of
responsibilities. All core stages and their composition are implemented for the initial profile. The [roadmap](roadmap.md)
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

## CLI

After installing the package:

```bash
boardsnap image.png
```

The command produces one JSON object per image, independently of Flutter integration.
`python -m boardsnap image.png` is equivalent. Reinstall the editable package once
to register the new command. See [usage, errors and exit codes](cli.md).

## Styles and limitations

The [style and condition inventory](style-inventory.md) separates backgrounds,
pieces and interface layouts, records web/Android/iOS status and orders the
remaining capture work. Listed targets are not automatically supported profiles.

See [evaluated profiles](profiles.md) for the three digital styles, the experimental
book baseline, reserved results and limitations. The original brown profile
remains the default; select another explicitly with `--profile`.

Photographs of physical boards with three-dimensional pieces are out of scope.
Compatibility with every design, color, or resolution is not assumed. The first
profiles will also exclude partial boards, animations, occluded pieces, arrows,
multiple boards, and heavily skewed or degraded images. In `auto`, without orientation
clues, the engine will assume White at the bottom (`a8` at the top left); an
image with Black at the bottom and no coordinates may be reversed relative to
the actual position.

## License

The repository includes the [GNU Affero General Public License v3](../../LICENSE).
