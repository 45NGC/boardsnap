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
`neural.py` provides the optional PyTorch classifier, shared preprocessing and
validated CPU model loading. `pipeline.py` chooses it from `model=PATH` or
`BOARDSNAP_MODEL`; an explicit profile selects legacy templates instead.
`pipeline.py` provides `recognize_image(path)` and owns stage resources; it returns
only piece placement and propagates structured failures. See [classification](classification.md).
The profile table is a small static configuration, not a dynamic plugin system.
The [style inventory](style-inventory.md) models board background, piece design
and interface layout as separate collection dimensions. Legacy profiles still
bundle their evaluated settings. The neural flow needs no user-selected profile;
its corpus records each dimension, client and condition separately. Independent
inventory entries do not enable untested combinations; see [measured expansion](style-expansion.md).
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
        → classification (templates) or neural (model) → orientation → output
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
| `neural` | Provide an optional learned classifier with the same 13 classes and a validated model/preprocessing contract. |
| `orientation` | Use verifiable clues or the documented convention to reorder the matrix into chess coordinates. |
| `output` | Check the matrix structure, compress empty squares, and construct `piecePlacement` or the agreed error. |
| `pipeline` | Coordinate stages and propagate failures without replacing them with invented positions. |
| `adapters` | Translate external input and serialize the response; `adapters.cli` provides the JSON command. |

Image input currently returns a fully loaded RGB Pillow `Image.Image`;
`ImageInputError.to_dict()` exposes input failures for future adapters.
The core does not import adapters or know about HTTP, Flutter, or a graphical
interface. Adapters do not contain recognition logic either.

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

OpenCV and NumPy implement palette proposals, connected RGB edges, regular
boundary fitting and robust 8 × 8 alternation checks for [board detection](detection.md). The [input guide](image-input.md)
specifies decoding. Only dependencies used by implemented stages are added.
Output generation itself uses neither a machine learning framework nor chess rules.

Outside the core, the optional `dataset` extra pins `chess==1.11.2` for generating
and replaying legal source moves in the [position plan](position-plan.md).
Structural coverage/split checks use the standard library. This dependency is
not used for inference, legality correction or app output.

PyTorch is installed through the optional `ml` extra and is used for training and
CPU inference of the 13-class square classifier. The default pipeline imports it
only when a model is selected. OpenCV detection remains independent of the model.
Training, capture and evaluation tools live in `tools/`, outside runtime inference;
see the [model guide](neural-classifier.md) and [current expansion](style-expansion.md).

## External integration

The [CLI](cli.md) and Python API accept image and orientation with a model configured
once. Explicit profiles retain legacy templates; only an unconfigured installation
defaults to the original brown style. [Evaluated profiles](profiles.md) document limits and the
experimental book baseline. The [Flutter integration design](flutter-integration.md)
proposes a separate HTTPS adapter for Android, iOS and web. It calls the same core;
no server, Flutter code or web-framework dependency is introduced in this iteration.
