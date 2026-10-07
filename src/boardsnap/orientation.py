"""Read supported border coordinates and reorder cells into a8-to-h1 order."""

from functools import lru_cache
from importlib.resources import files
import json
from typing import Literal, TypeVar

import cv2
import numpy as np
from PIL import Image

from boardsnap.normalization import NormalizedBoard
from boardsnap.detection import BoardBounds
from boardsnap.profiles import DEFAULT_PROFILE, get_profile


Orientation = Literal["white-bottom", "black-bottom"]
_T = TypeVar("_T")


def _coordinate_boxes(bounds: BoardBounds, profile: str = DEFAULT_PROFILE) -> tuple[list[tuple[int, int, int, int]], ...]:
    """Use each digital profile's coordinate placement within border cells."""
    x, y, width, height = bounds.x, bounds.y, bounds.width, bounds.height
    sx, sy = width / 8, height / 8
    # Exclude the outer shadow without cutting off the small coordinate glyphs.
    inset_x = max(1, round(width / 584 * 2))
    inset_y = max(1, round(height / 584 * 2))
    bottom_gap = max(1, round(height / 584))
    if get_profile(profile).coordinates == "chesscom":
        return (
            [(round(x + (col + .72) * sx), round(y + height - sy * .28),
              round(x + (col + 1) * sx) - inset_x, y + height - bottom_gap) for col in range(8)],
            [(x + inset_x, round(y + row * sy) + inset_y,
              round(x + sx * .25), round(y + (row + .28) * sy)) for row in range(8)],
        )
    return (
        [(round(x + col * sx) + inset_x, round(y + height - sy * .22),
          round(x + col * sx + sx * .22), y + height - bottom_gap) for col in range(8)],
        [(round(x + width - sx * .22), round(y + row * sy) + inset_y,
          x + width - inset_x, round(y + row * sy + sy * .25)) for row in range(8)],
    )


def _glyph_mask(image: Image.Image, profile: str = DEFAULT_PROFILE) -> np.ndarray | None:
    """Extract a contrasting glyph on one of the two known square backgrounds."""
    pixels = np.asarray(image, dtype=float)
    median = np.median(pixels, axis=(0, 1))
    colors = np.asarray(get_profile(profile).colors, dtype=float)
    distances = np.linalg.norm(colors - median, axis=1)
    if distances.min() > 25:
        return None
    background = colors[distances.argmin()].mean()
    # Grayscale tolerates Chromium's colored subpixel antialiasing on text.
    gray = pixels.mean(axis=2)
    mask = gray < background - 35 if background > 180 else gray > background + 35
    ys, xs = np.where(mask)
    if len(xs) < 8:
        return None
    glyph = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if glyph.shape[0] < 6 or glyph.shape[1] < 2:
        return None
    return glyph.astype(np.uint8)


def _normalized_mask(mask: np.ndarray) -> np.ndarray:
    """Fit a glyph into a fixed canvas without changing its aspect ratio."""
    scale = min(18 / mask.shape[0], 14 / mask.shape[1])
    width = max(1, round(mask.shape[1] * scale))
    height = max(1, round(mask.shape[0] * scale))
    resized = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
    result = np.zeros((20, 16), dtype=bool)
    x, y = (16 - width) // 2, (20 - height) // 2
    result[y:y + height, x:x + width] = resized != 0
    return result


@lru_cache(maxsize=8)
def _templates(profile: str = DEFAULT_PROFILE) -> dict[str, list[np.ndarray]]:
    # Shipped package data, never runtime reads from tuning/evaluation folders.
    data = json.loads(files("boardsnap").joinpath(f"assets/{get_profile(profile).coordinate_asset}.json").read_text())
    return {
        symbol: [_normalized_mask(np.array([[int(pixel) for pixel in row] for row in bitmap],
                                          dtype=np.uint8)) for bitmap in bitmaps]
        for symbol, bitmaps in data["glyphs"].items()
    }


def _read_coordinate(image: Image.Image, alphabet: str, profile: str = DEFAULT_PROFILE) -> str | None:
    mask = _glyph_mask(image, profile)
    if mask is None:
        return None
    glyph = _normalized_mask(mask)
    scores = []
    for symbol in alphabet:
        score = max(np.count_nonzero(glyph & template) / np.count_nonzero(glyph | template)
                    for template in _templates(profile)[symbol])
        scores.append((score, symbol))
    scores.sort(reverse=True)
    # Internal template similarity gates, never confidence fields in the result.
    if scores[0][0] < .78 or scores[0][0] - scores[1][0] < .05:
        return None
    return scores[0][1]


def detect_orientation(board: NormalizedBoard, *, profile: str = DEFAULT_PROFILE) -> Orientation:
    """Read selected-profile coordinates from preserved source pixels.

    At least four readable labels must agree on one direction, with no readable
    contradictions across either axis. Missing, unreadable or conflicting clues
    deterministically fall back to white-bottom. No piece/layout assumptions,
    metadata, filenames or annotations are used. This does not rotate images.

    Lichess uses bottom-file/right-rank labels; Chess.com uses bottom-file/left-rank.
    The print profile has no coordinates and always uses the documented fallback.
    Invalid internal arguments raise TypeError/ValueError, not a guessed position.
    """
    if not isinstance(board, NormalizedBoard):
        raise TypeError("Expected a NormalizedBoard with preserved source pixels.")
    image, bounds = board.source_image, board.source_bounds
    if not isinstance(image, Image.Image) or not isinstance(bounds, BoardBounds):
        raise TypeError("Expected a Pillow source image and BoardBounds.")
    if image.mode != "RGB":
        raise ValueError("Expected an RGB source image.")
    if any(type(value) is not int for value in (bounds.x, bounds.y, bounds.width, bounds.height)):
        raise TypeError("Board bounds must contain integers.")
    if (min(bounds.x, bounds.y) < 0 or min(bounds.width, bounds.height) <= 0
            or bounds.x + bounds.width > image.width or bounds.y + bounds.height > image.height):
        raise ValueError("Board bounds must lie entirely inside the source image.")
    if get_profile(profile).coordinates == "none" or min(bounds.width, bounds.height) < 256:
        return "white-bottom"

    directions: list[str] = []
    for boxes, expected in zip(_coordinate_boxes(bounds, profile), ("abcdefgh", "87654321"), strict=True):
        for index, box in enumerate(boxes):
            with image.crop(box) as patch:
                symbol = _read_coordinate(patch, expected, profile)
            if symbol is None:
                continue
            if symbol == expected[index]:
                directions.append("white-bottom")
            elif symbol == expected[7 - index]:
                directions.append("black-bottom")
            else:
                return "white-bottom"
    if len(directions) >= 4 and all(direction == "black-bottom" for direction in directions):
        return "black-bottom"
    return "white-bottom"


def to_canonical(matrix: list[list[_T]] | tuple[tuple[_T, ...], ...],
                 orientation: Orientation) -> list[list[_T]]:
    """Copy row containers into a8-to-h1 order without changing or copying cells.

    Accept an 8x8 list/tuple matrix of labels or square images in image order.
    Black-bottom reverses both axes; piece drawings are never rotated. Cells
    remain owned by the caller; this function neither validates nor classifies them.
    """
    if orientation not in ("white-bottom", "black-bottom"):
        raise ValueError("Orientation must be white-bottom or black-bottom.")
    if not isinstance(matrix, (list, tuple)):
        raise TypeError("Matrix must be a list or tuple of rows.")
    if len(matrix) != 8:
        raise ValueError("Matrix must contain exactly 8 rows.")
    for row in matrix:
        if not isinstance(row, (list, tuple)):
            raise TypeError("Each row must be a list or tuple.")
        if len(row) != 8:
            raise ValueError("Each row must contain exactly 8 cells.")
    if orientation == "black-bottom":
        return [list(reversed(row)) for row in reversed(matrix)]
    return [list(row) for row in matrix]
