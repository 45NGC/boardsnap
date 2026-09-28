# BoardSnap

[English](docs/en/README.md) | [Spanish](docs/es/README.md)

BoardSnap is a Python project for recognizing digital chessboards and book
diagrams and returning piece placement to the Flutter app **chess-scanner**.
**Piece placement serialization is implemented; recognition and the CLI are pending.**

`boardsnap.output.build_result(board)` converts an already-classified 8 × 8
matrix into the output dictionary. Its 53 unit test cases pass.

The project uses English for code, comments, configuration, and general project
files. Spanish documentation is maintained in `docs/es/`.

| Guide | English | Spanish |
| --- | --- | --- |
| Overview and installation | [Read](docs/en/README.md) | [Read](docs/es/README.md) |
| Architecture | [Read](docs/en/architecture.md) | [Read](docs/es/architecture.md) |
| Output contract | [Read](docs/en/output-contract.md) | [Read](docs/es/output-contract.md) |
| Output implementation walkthrough | [Read](docs/en/output-walkthrough.md) | [Read](docs/es/output-walkthrough.md) |
| Roadmap | [Read](docs/en/roadmap.md) | [Read](docs/es/roadmap.md) |
| Testing | [Read](docs/en/testing.md) | [Read](docs/es/testing.md) |
| Tuning data | [Read](docs/en/tuning-data.md) | [Read](docs/es/tuning-data.md) |
| Evaluation data | [Read](docs/en/evaluation-data.md) | [Read](docs/es/evaluation-data.md) |

License: [GNU Affero General Public License v3](LICENSE).
