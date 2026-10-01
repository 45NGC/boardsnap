# BoardSnap

[English](docs/en/README.md) | [Spanish](docs/es/README.md)

BoardSnap is a Python project for recognizing digital chessboards and book
diagrams and returning piece placement to the Flutter app **chess-scanner**.
**Image loading, first-profile board detection and piece placement serialization are implemented; piece recognition and the CLI are pending.**

`boardsnap.detection.detect_board(image)` returns grid bounds for the brown
lichess profile. See [detection scope and tests](docs/en/detection.md).

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
| Output implementation walkthrough | [Read](docs/en/output-walkthrough.md) | [Read](docs/es/output-walkthrough.md) |
| Roadmap | [Read](docs/en/roadmap.md) | [Read](docs/es/roadmap.md) |
| Testing | [Read](docs/en/testing.md) | [Read](docs/es/testing.md) |
| Tuning data | [Read](docs/en/tuning-data.md) | [Read](docs/es/tuning-data.md) |
| Capture utility | [Read](docs/en/capture-data.md) | [Read](docs/es/capture-data.md) |
| Evaluation data | [Read](docs/en/evaluation-data.md) | [Read](docs/es/evaluation-data.md) |

License: [GNU Affero General Public License v3](LICENSE).
