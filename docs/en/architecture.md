# Proposed architecture

**English** | [Spanish](../es/architecture.md) · [Overview](README.md)

This is the planned distribution of responsibilities, not an implemented API.
The initial repository contained only a README, a license, and a generic Python
`.gitignore`; there was no recognition code to preserve or migrate.

A single package, `boardsnap`, lives under `src/`. This scaffold only contains
`__init__.py`, which identifies the Python package. The modules proposed below
will be created as each responsibility is implemented; their names are
provisional. No class hierarchies, plugin registries, or services are introduced
in advance. The
[PyPA packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
describes this organization and configuration through `pyproject.toml`.

## Planned flow

```text
Adapter (CLI; Flutter integration to be decided)
    → pipeline
        → image_input → detection → normalization → segmentation
        → classification → orientation → output
    → JSON
```

Orientation clues will be preserved during input and detection. `orientation`
will apply the square mapping before output is generated.

| Module | Planned responsibility |
| --- | --- |
| `image_input` | Read bytes or a file, decode the image, and validate its contents. Handle file orientation before analysis. |
| `detection` | Locate the boundaries of an 8 × 8 grid and preserve visible margin coordinates before cropping them out. |
| `normalization` | Crop the board and adjust its size and geometry while retaining the mapping to the original image. |
| `segmentation` | Produce exactly 64 crops, indexed by row and column in image view. |
| `classification` | Choose one of 13 classes per crop: empty or one of the six pieces of either color. |
| `orientation` | Use verifiable clues or the documented convention to reorder the matrix into chess coordinates. |
| `output` | Check the matrix structure, compress empty squares, and construct `piecePlacement` or the agreed error. |
| `pipeline` | Coordinate stages and propagate failures without replacing them with invented positions. |
| `adapters` | Translate external input and serialize the response; the CLI will be the first adapter. |

Internal structures will be chosen when each stage is implemented. No public
classes or image representation tied to a library are defined yet. The core
will not import adapters or know about HTTP, Flutter, or a graphical interface.
Adapters will not contain recognition logic either.

Output validation will check piece placement syntax, not game legality. Pieces
will not be rearranged to force a legal position, nor will data such as the side
to move or castling rights be invented.

## Dependencies

The scaffold requires no runtime libraries. `setuptools` is the build backend
and `pytest` is the only development extra. The license configuration includes
the existing `LICENSE` file in distributions; it requires a setuptools version
that supports `project.license-files`, as described in its
[documentation](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html).

When working with images, Pillow will be considered for decoding and OpenCV with
NumPy for geometry and templates. Only dependencies that are used will be added.
No machine learning framework or chess rules library is introduced now to
serialize a single field.

PyTorch is a candidate for training and running a 13-class square classifier.
Its [official guide](https://docs.pytorch.org/tutorials/beginner/basics/intro.html)
describes data handling, model construction, training, and saving. In BoardSnap,
it could be combined with OpenCV to locate and normalize the board. The initial
template comparison does not need a neural network; a learned model would need
labeled data and independent evaluation. PyTorch will be selected and installed
when that experiment is undertaken.

## External integration

The future CLI will accept a path and emit JSON. It will consume the core; it
does not determine how the Flutter app will run Python. A remote service, local
process, or another approach must be chosen explicitly according to
chess-scanner's platforms and constraints. Until then, there will be no server,
endpoints, Flutter SDK, or deployment code.
