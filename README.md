# BoardSnap

[English](docs/en/README.md) | [Spanish](docs/es/README.md)

BoardSnap is a Python project for recognizing digital chessboards and book
diagrams and returning piece placement to the Flutter app **chess-scanner**.
**The Python pipeline and JSON CLI support three evaluated digital profiles. A book-diagram profile is experimental.**

The [profile guide](docs/en/profiles.md) records exact scope, datasets and results.
The [style inventory](docs/en/style-inventory.md) tracks backgrounds, piece designs,
interfaces and image conditions separately, with independent web/Android/iOS status.
The [position plan](docs/en/position-plan.md) fixes 80 new placements in 20 source
groups: 56 training, 12 validation and 12 final-evaluation positions.
The [configurable capture tool](docs/en/configurable-capture.md) uses this plan
for both platforms; a local 16-image training pilot verifies four new style
combinations. It does not extend recognition compatibility.
The [first clean classifier corpus](docs/en/first-clean-corpus.md) contains 3600
verified local captures: six piece sets, three backgrounds per set, both
orientations and two viewport sizes. All 80 positions keep their original
partitions. Images remain in `.cache/`; model training is still pending.
[Flutter integration](docs/en/flutter-integration.md) is documented as an HTTPS API
for Android, iOS and web; no server or Flutter client is implemented.

With the package installed, run `boardsnap image.png` (or `python -m boardsnap image.png`).
See the [CLI guide](docs/en/cli.md) for installation, errors and exit codes.

`boardsnap.detection.detect_board(image)` now combines palette proposals with
structural 8 × 8 detection for digital boards. A separate 28-image rectangle
corpus covers new backgrounds and real-use highlights/arrows; this does not
extend piece-classification compatibility. See [detection and measurements](docs/en/detection.md).
The [normalization guide](docs/en/normalization.md) explains square crops,
preserved orientation context and the `--squares` preview option.
The [orientation guide](docs/en/orientation.md) covers coordinate reading,
canonical cell ordering and explicit `--orientation white-bottom|black-bottom`
input. The default `auto` preserves coordinate reading and its White-at-the-bottom fallback.
`boardsnap.pipeline.recognize_image(path)` returns the recognized `piecePlacement`.
See [classification and measured limits](docs/en/classification.md) for the baseline,
reserved results, template provenance and `--recognition` previews.

A separate [capture utility](docs/en/capture-data.md) collects annotated lichess
screenshots for the first dataset. It does not perform image recognition.

The first dataset is included: **20 annotated PNGs** for
`lichess-cburnett-brown-v1`, split into 16 tuning and 4 evaluation images.
See the [dataset guide](docs/en/tuning-data.md) and
[collection manifest](data/manifests/lichess-cburnett-brown-v1.json).

`boardsnap.output.build_result(board)` converts an already-classified 8 × 8
matrix into the output dictionary. Its 53 unit test cases pass.

The project uses English for code, comments, configuration, and general project
files. Spanish documentation is maintained in `docs/es/`.

| Guide | English | Spanish |
| --- | --- | --- |
| Overview and installation | [Read](docs/en/README.md) | [Read](docs/es/README.md) |
| Architecture | [Read](docs/en/architecture.md) | [Read](docs/es/architecture.md) |
| Output contract | [Read](docs/en/output-contract.md) | [Read](docs/es/output-contract.md) |
| Image input | [Read](docs/en/image-input.md) | [Read](docs/es/image-input.md) |
| Board detection | [Read](docs/en/detection.md) | [Read](docs/es/detection.md) |
| Normalization and segmentation | [Read](docs/en/normalization.md) | [Read](docs/es/normalization.md) |
| Orientation | [Read](docs/en/orientation.md) | [Read](docs/es/orientation.md) |
| Piece recognition | [Read](docs/en/classification.md) | [Read](docs/es/classification.md) |
| Evaluated profiles | [Read](docs/en/profiles.md) | [Read](docs/es/profiles.md) |
| Digital style and condition inventory | [Read](docs/en/style-inventory.md) | [Read](docs/es/style-inventory.md) |
| Position plan and fixed partitions | [Read](docs/en/position-plan.md) | [Read](docs/es/position-plan.md) |
| Flutter integration design | [Read](docs/en/flutter-integration.md) | [Read](docs/es/flutter-integration.md) |
| Command-line interface | [Read](docs/en/cli.md) | [Read](docs/es/cli.md) |
| Output implementation walkthrough | [Read](docs/en/output-walkthrough.md) | [Read](docs/es/output-walkthrough.md) |
| Roadmap | [Read](docs/en/roadmap.md) | [Read](docs/es/roadmap.md) |
| Testing | [Read](docs/en/testing.md) | [Read](docs/es/testing.md) |
| Tuning data | [Read](docs/en/tuning-data.md) | [Read](docs/es/tuning-data.md) |
| First clean classifier corpus | [Read](docs/en/first-clean-corpus.md) | [Read](docs/es/first-clean-corpus.md) |
| Configurable platform captures | [Read](docs/en/configurable-capture.md) | [Read](docs/es/configurable-capture.md) |
| Capture utility | [Read](docs/en/capture-data.md) | [Read](docs/es/capture-data.md) |
| Evaluation data | [Read](docs/en/evaluation-data.md) | [Read](docs/es/evaluation-data.md) |

License: [GNU Affero General Public License v3](LICENSE).
