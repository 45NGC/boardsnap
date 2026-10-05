"""Split a normalized board into 64 independent crops in image order."""

from PIL import Image


def split_squares(image: Image.Image) -> list[list[Image.Image]]:
    """Return eight rows of eight RGB squares, top-to-bottom and left-to-right.

    Each crop owns its pixels. No pixels are skipped, repeated, resized or
    reordered; the caller owns the returned images and may close them after use.
    The top-left crop is [0][0], not necessarily a8: chess orientation is pending.
    Invalid internal inputs raise TypeError or ValueError.
    """
    if not isinstance(image, Image.Image):
        raise TypeError("Expected a normalized Pillow image.")
    if image.mode != "RGB":
        raise ValueError("Expected a normalized RGB board.")
    if image.width != image.height or image.width < 8 or image.width % 8:
        raise ValueError("Expected a square board with a positive side divisible by eight.")

    side = image.width // 8
    return [
        [image.crop((col * side, row * side, (col + 1) * side, (row + 1) * side))
         for col in range(8)]
        for row in range(8)
    ]
