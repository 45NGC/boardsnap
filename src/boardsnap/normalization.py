"""Crop and resize a board while preserving pixels needed for orientation."""

from dataclasses import dataclass
from typing import Self

from PIL import Image

from boardsnap.detection import BoardBounds


@dataclass(frozen=True)
class NormalizedBoard:
    """Own the resized board and a full-resolution copy of the decoded input.

    Bounds refer to source_image, after input EXIF normalization. Images remain
    mutable despite the frozen fields. Use as a context manager or call close().
    """

    image: Image.Image
    source_image: Image.Image
    source_bounds: BoardBounds

    def close(self) -> None:
        """Release both owned images; separately extracted squares stay valid."""
        self.image.close()
        self.source_image.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def normalize_board(
    image: Image.Image, bounds: BoardBounds, *, square_size: int = 64,
) -> NormalizedBoard:
    """Return an RGB board of size (8 * square_size) on each side.

    Crop exclusive right/bottom bounds and resize with LANCZOS. Preserve image
    view: do not rotate, mirror, remove internal labels or infer chess orientation.
    Retain the entire source at original resolution so margin/internal coordinate
    labels remain available even after the caller closes or changes the input.

    Invalid internal arguments raise TypeError or ValueError. Reject out-of-image
    bounds instead of allowing Pillow to pad an invalid crop with black pixels.
    This stage does not detect a grid or correct perspective.
    """
    if not isinstance(image, Image.Image):
        raise TypeError("Expected a Pillow image from read_image().")
    if image.mode != "RGB":
        raise ValueError("Expected RGB pixels; use read_image() to normalize the input.")
    if not isinstance(bounds, BoardBounds):
        raise TypeError("Expected BoardBounds from detect_board().")
    if any(type(value) is not int for value in (bounds.x, bounds.y, bounds.width, bounds.height)):
        raise TypeError("Board bounds must contain integers.")
    if type(square_size) is not int:
        raise TypeError("Square size must be an integer.")
    if square_size <= 0:
        raise ValueError("Square size must be positive.")
    if bounds.x < 0 or bounds.y < 0 or bounds.width <= 0 or bounds.height <= 0:
        raise ValueError("Board bounds must have nonnegative coordinates and positive dimensions.")
    if bounds.x + bounds.width > image.width or bounds.y + bounds.height > image.height:
        raise ValueError("Board bounds must lie entirely inside the input image.")

    side = square_size * 8
    with image.crop(bounds.as_box()) as cropped:
        normalized = cropped.resize((side, side), Image.Resampling.LANCZOS)
    try:
        source = image.copy()
    except Exception:
        normalized.close()
        raise
    return NormalizedBoard(normalized, source, bounds)
