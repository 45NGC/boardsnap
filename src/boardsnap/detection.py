"""Locate complete grids with an explicitly selected digital or print profile."""

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from PIL import Image

from boardsnap.profiles import DEFAULT_PROFILE, get_profile


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


def _book_candidates(image: Image.Image) -> list[BoardBounds]:
    """Find framed, lightly skewed diagrams in the fixed hatched-print edition.

    The frame supplies geometry; alternating square rim brightness must also
    support eight rows/columns. This is deliberately not a generic page detector.
    """
    gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if min(width, height) < 256 or abs(width - height) > max(width, height) * .05:
            continue
        if cv2.contourArea(contour) < width * height * .8:
            continue
        dx, dy = round(width * .023), round(height * .023)
        bounds = BoardBounds(x + dx, y + dy, width - 2 * dx, height - 2 * dy)
        patch = gray[bounds.y:bounds.y + bounds.height, bounds.x:bounds.x + bounds.width]
        patch = cv2.resize(patch, (512, 512), interpolation=cv2.INTER_AREA)
        patch = cv2.GaussianBlur(patch, (0, 0), 1.3)
        values = np.empty((8, 8))
        for row in range(8):
            for col in range(8):
                cell = patch[row * 64:(row + 1) * 64, col * 64:(col + 1) * 64]
                rim = np.concatenate((cell[5:11, 5:-5].ravel(), cell[-11:-5, 5:-5].ravel(),
                                      cell[5:-5, 5:11].ravel(), cell[5:-5, -11:-5].ravel()))
                values[row, col] = np.median(rim)
        parity = np.indices((8, 8)).sum(axis=0) % 2
        light, dark = np.median(values[parity == 0]), np.median(values[parity == 1])
        middle = (light + dark) / 2
        if light - dark >= 20 and np.count_nonzero((values > middle) == (parity == 0)) >= 58:
            candidates.append(bounds)
    return candidates


def detect_board(image: Image.Image, *, profile: str = DEFAULT_PROFILE) -> BoardBounds:
    """Return one board's bounds using only a fully decoded RGB image.

    Digital profiles require complete axis-aligned boards at least 128 pixels
    per side with visible backgrounds. The experimental print profile requires
    a retained frame, at least 256 pixels per side and near-square geometry.
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

    config = get_profile(profile)
    if config.kind == "print":
        candidates = _book_candidates(image)
        if not candidates:
            raise BoardDetectionError("BOARD_NOT_FOUND", "No supported chessboard was detected in the image.")
        if len(candidates) > 1:
            raise BoardDetectionError("UNSUPPORTED_IMAGE", "Images with multiple chessboards are not supported.")
        return candidates[0]
    colors = config.colors
    tolerance = config.color_tolerance
    pixels = np.asarray(image)
    masks = [
        cv2.inRange(
            pixels,
            np.array([max(0, channel - tolerance) for channel in color], dtype=np.uint8),
            np.array([min(255, channel + tolerance) for channel in color], dtype=np.uint8),
        )
        for color in colors
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
