# Proposed architecture

**English** | [Spanish](../es/architecture.md) · [Overview](README.md)

This is the distribution of responsibilities. Image input, board detection,
normalization, segmentation, orientation, classification, pipeline composition and
output serialization are implemented. The CLI adapter is implemented; the future HTTPS transport is [documented](flutter-integration.md).
The initial repository contained only a README, a license, and a generic Python
`.gitignore`; there was no recognition code to preserve or migrate.

A single package, `boardsnap`, lives under `src/`. It contains `__init__.py`
and `output.py`, which validates and serializes an already-classified matrix,
plus `image_input.py`, which loads PNG/JPEG files and raises structured input errors.
`profiles.py` holds explicit profile configuration. `detection.py` locates the selected grid and returns immutable `BoardBounds`.
`normalization.py` returns a `NormalizedBoard` with resized pixels, an independent
full-resolution source copy and source bounds. `segmentation.py` returns an
8 × 8 matrix of independent crops in image order; see the
[normalization guide](normalization.md) for ownership and geometry.
`orientation.py` reads supported coordinates from the preserved source and
reorders matrix cells. Its glyph templates are installed package assets derived
only from tuning data; see [orientation](orientation.md).
`classification.py` compares square features with packaged profile-specific templates.
`pipeline.py` provides `recognize_image(path)` and owns stage resources; it returns
only piece placement and propagates structured failures. See [classification](classification.md).
The profile table is a small static configuration, not a dynamic plugin system.
The [style inventory](style-inventory.md) models board background, piece design
and interface layout as separate collection dimensions. Runtime profiles still
bundle their evaluated settings; independent inventory entries do not enable
untested combinations. Future collection metadata will record each dimension,
client and image condition separately.
All stages listed below exist; no server or additional framework is introduced.
The
[PyPA packaging guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
describes this organization and configuration through `pyproject.toml`.

The pipeline accepts `orientation="auto"` by default. Explicit `white-bottom` or
`black-bottom` skips coordinate detection and selects the canonical matrix mapping.
CLI/HTTP adapters pass the image view without adding it to the response or treating
it as the side to move. See [orientation](orientation.md).

## Recognition flow

```text
Adapter (CLI implemented; HTTPS transport documented)
    → pipeline
        → image_input → detection → normalization → segmentation
        → classification → orientation → output
    → JSON
```

Normalization preserves orientation clues in the full source copy, including
external margins and internal labels. `orientation` applies the square mapping
before output is generated; segmentation does not infer chess coordinates.

| Module | Responsibility |
| --- | --- |
| `image_input` | Read bytes or a file, decode the image, and validate its contents. Handle file orientation before analysis. |
| `detection` | Locate the boundaries of an 8 × 8 grid without changing the input pixels. |
| `normalization` | Crop the board and adjust its size and geometry while retaining the mapping to the original image. |
| `segmentation` | Produce exactly 64 crops, indexed by row and column in image view. |
| `classification` | Choose one of 13 classes per crop: empty or one of the six pieces of either color. |
| `orientation` | Use verifiable clues or the documented convention to reorder the matrix into chess coordinates. |
| `output` | Check the matrix structure, compress empty squares, and construct `piecePlacement` or the agreed error. |
| `pipeline` | Coordinate stages and propagate failures without replacing them with invented positions. |
| `adapters` | Translate external input and serialize the response; `adapters.cli` provides the JSON command. |

Image input currently returns a fully loaded RGB Pillow `Image.Image`;
`ImageInputError.to_dict()` exposes input failures for future adapters.
Other internal structures will be chosen as their stages are implemented. The core
will not import adapters or know about HTTP, Flutter, or a graphical interface.
Adapters will not contain recognition logic either.

Output validation will check piece placement syntax, not game legality. Pieces
will not be rearranged to force a legal position, nor will data such as the side
to move or castling rights be invented.

## Dependencies

Pillow decodes and normalizes image input. `setuptools` is the build backend,
`pytest` is in the development extra and Playwright is in the optional capture
extra, outside the recognition core. The license configuration includes
the existing `LICENSE` file in distributions; it requires a setuptools version
that supports `project.license-files`, as described in its
[documentation](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html).

OpenCV and NumPy implement color masks, connected regions and 8 × 8 pattern
validation for [board detection](detection.md). The [input guide](image-input.md)
specifies decoding. Only dependencies used by implemented stages are added.
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

The [CLI](cli.md) and Python API accept an explicit profile, defaulting to the
original brown style. [Evaluated profiles](profiles.md) document limits and the
experimental book baseline. The [Flutter integration design](flutter-integration.md)
proposes a separate HTTPS adapter for Android, iOS and web. It calls the same core;
no server, Flutter code or web-framework dependency is introduced in this iteration.
