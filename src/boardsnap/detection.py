"""Locate complete, axis-aligned 8 by 8 boards in the lichess brown profile."""

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from PIL import Image


# RGB colors of the first profile, not coordinates from the screenshot corpus.
_COLORS = ((240, 217, 181), (181, 136, 99))
_COLOR_TOLERANCE = 12
_MIN_BOARD_SIDE = 128


@dataclass(frozen=True)
class BoardBounds:
    """Integer bounds in input-image pixels, with exclusive right/bottom edges."""

    x: int
    y: int
    width: int
    height: int

    def as_box(self) -> tuple[int, int, int, int]:
        """Return the (left, top, right, bottom) box used by Pillow crops."""
        return self.x, self.y, self.x + self.width, self.y + self.height


class BoardDetectionError(Exception):
    """An expected failure to select one supported board."""

    def __init__(
        self,
        code: Literal["BOARD_NOT_FOUND", "UNSUPPORTED_IMAGE"],
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


def _has_checker_pattern(masks: list[np.ndarray], bounds: BoardBounds) -> bool:
    """Require the two background colors to alternate in every cell.

    Ignore a thin cell border for antialiasing/coordinate labels. Piece pixels
    are allowed to cover the center, but each cell must retain background.
    """
    xs = np.linspace(bounds.x, bounds.x + bounds.width, 9).round().astype(int)
    ys = np.linspace(bounds.y, bounds.y + bounds.height, 9).round().astype(int)
    fractions = np.empty((8, 8, 2), dtype=float)
    for row in range(8):
        for col in range(8):
            inset = max(1, min(xs[col + 1] - xs[col], ys[row + 1] - ys[row]) // 16)
            left, right = xs[col] + inset, xs[col + 1] - inset
            top, bottom = ys[row] + inset, ys[row + 1] - inset
            for index, mask in enumerate(masks):
                cell = mask[top:bottom, left:right]
                fractions[row, col, index] = np.count_nonzero(cell) / cell.size
    # Either parity may start at the top left; this does not resolve chess view.
    for first_color in (0, 1):
        valid = True
        for row in range(8):
            for col in range(8):
                expected = (row + col + first_color) % 2
                correct, wrong = fractions[row, col, expected], fractions[row, col, 1 - expected]
                if correct < 0.25 or wrong > 0.10:
                    valid = False
                    break
            if not valid:
                break
        if valid:
            return True
    return False


def detect_board(image: Image.Image) -> BoardBounds:
    """Return one board's bounds using only a fully decoded RGB image.

    Supports the brown two-color profile, complete axis-aligned boards at least
    128 pixels per side, with enough background visible in every square.
    Does not modify pixels, crop, infer orientation, or recognize pieces.

    Raises:
        BoardDetectionError: No supported grid, or multiple supported grids.
        TypeError: Input is not a Pillow image.
        ValueError: Input is not RGB (normalize it with image_input first).
    """
    if not isinstance(image, Image.Image):
        raise TypeError("Expected a Pillow image from read_image().")
    if image.mode != "RGB":
        raise ValueError("Expected RGB pixels; use read_image() to normalize the input.")
    if min(image.size) < _MIN_BOARD_SIDE:
        raise BoardDetectionError("BOARD_NOT_FOUND", "No supported chessboard was detected in the image.")

    pixels = np.asarray(image)
    masks = [
        cv2.inRange(
            pixels,
            np.array([channel - _COLOR_TOLERANCE for channel in color], dtype=np.uint8),
            np.array([min(255, channel + _COLOR_TOLERANCE) for channel in color], dtype=np.uint8),
        )
        for color in _COLORS
    ]
    background = cv2.bitwise_or(*masks)
    # Close tiny antialiased seams without filling the piece-sized holes.
    connected = cv2.morphologyEx(background, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, _, stats, _ = cv2.connectedComponentsWithStats(connected, connectivity=8)
    candidates = []
    for x, y, width, height, area in stats[1:]:
        if min(width, height) < _MIN_BOARD_SIDE:
            continue
        if abs(int(width) - int(height)) > max(2, max(width, height) * 0.01):
            continue
        if area < width * height * 0.25:
            continue
        bounds = BoardBounds(int(x), int(y), int(width), int(height))
        if _has_checker_pattern(masks, bounds):
            candidates.append(bounds)
    if not candidates:
        raise BoardDetectionError("BOARD_NOT_FOUND", "No supported chessboard was detected in the image.")
    if len(candidates) > 1:
        raise BoardDetectionError("UNSUPPORTED_IMAGE", "Images with multiple chessboards are not supported.")
    return candidates[0]
