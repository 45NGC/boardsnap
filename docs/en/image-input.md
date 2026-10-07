# Image input

**English** | [Spanish](../es/image-input.md) · [Overview](README.md)

`boardsnap.image_input.read_image(path)` accepts a string or text `os.PathLike`
(such as `pathlib.Path`) and returns a fully decoded Pillow `Image.Image` in
RGB mode, with eight bits per channel. Pillow is a runtime dependency, installed
by `python -m pip install -e '.[dev]'`.

```python
from boardsnap.image_input import ImageInputError, read_image

try:
    with read_image("data/tuning/lichess-cburnett-brown-v1/pos-001-white.png") as image:
        print(image.mode, image.size)  # RGB (1280, 1000)
except ImageInputError as error:
    print(error.to_dict())
```

The image owns its pixels and keeps no source file open. The function never
edits the input file, prints output, resizes, crops or constructs a position.
Pixel coordinates start at the top-left: `(x, y)` means column and row.

## Formats and normalization

- Only static PNG and JPEG are accepted, identified by content, not extension.
  Decoding a format does not establish recognition support for it.
- Binary, grayscale, grayscale with alpha, palette, RGB, RGBA and CMYK modes
  become RGB. High-bit-depth grayscale modes are explicitly rejected.
- Alpha, palette transparency and transparent color keys are composited on
  white. The returned image has no alpha channel.
- EXIF rotation/reflection is applied; dimensions may change accordingly.
  This follows display metadata, not White/Black chess orientation. No square
  coordinates are inferred.
- Source metadata is discarded after normalization. Embedded ICC profiles are
  not used for color-managed conversion.
- Multi-frame PNG and identified formats outside PNG/JPEG are unsupported.
- Pillow's active decompression pixel guard remains enabled; its warnings and
  errors become `UNSUPPORTED_IMAGE` without changing the global limit.

The file is read once. Its bytes are verified and then reopened in memory for
full decoding. Thus decoder errors cannot be mistaken for file-read failures.
[Pillow opening is lazy](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open),
so opening a header alone is insufficient. Metadata orientation uses
[ImageOps.exif_transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose).

## Failures

Expected failures raise `ImageInputError` with `code`, `message` and `to_dict()`.
Messages are English; callers should depend on the code rather than exact text.

| Code | Cases |
| --- | --- |
| `INPUT_READ_ERROR` | Missing file, directory, permission failure or another inability to read bytes |
| `INVALID_IMAGE` | Empty or unidentified content, corrupt checksums, truncated pixels or decoding failure |
| `UNSUPPORTED_IMAGE` | Identified unsupported format, animation, pixel mode or decoder pixel limit |

Content Pillow cannot identify is `INVALID_IMAGE`, including formats unknown to
its decoder. An identified unsupported format is rejected before full integrity
validation. Incorrect argument types raise `TypeError`; unexpected programming
errors are not silently converted into input errors.

`error.to_dict()` produces the [error contract](output-contract.md), for example:

```json
{"error": {"code": "INVALID_IMAGE", "message": "The image file is empty."}}
```

The CLI adapter encodes this dictionary as JSON. No `piecePlacement` is
returned on failure. [Detection](detection.md) consumes this image representation;
the [CLI](cli.md) is implemented and Flutter integration remains undecided.

## Tests

```bash
python -m pytest tests/test_image_input.py
python -m pytest
```

The 31 cases use temporary images, without the browser, network or evaluation
dataset. They check valid formats, channel/pixel order, detached results, modes,
transparency, CMYK, EXIF, access errors, readable-but-truncated headers, corrupt
checksums, unsupported formats/conditions and pixel limits.
