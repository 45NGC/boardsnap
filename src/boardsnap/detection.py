"""Locate complete digital grids using palette proposals and structural evidence."""

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


def _structural_pattern(pixels: np.ndarray, bounds: BoardBounds) -> bool:
    """Check eight alternating rows/columns, allowing a minority of changed cells."""
    patch = pixels[bounds.y:bounds.y + bounds.height, bounds.x:bounds.x + bounds.width]
    if patch.size == 0:
        return False
    patch = cv2.resize(patch, (256, 256), interpolation=cv2.INTER_AREA).astype(np.float32)
    # Sample cell rims, not centers occupied by pieces. Median rejects thin
    # arrows/coordinates and small texture details without knowing any palette.
    values = np.empty((8, 8, 3), dtype=np.float32)
    for row in range(8):
        for col in range(8):
            cell = patch[row * 32:(row + 1) * 32, col * 32:(col + 1) * 32]
            rim = np.concatenate((cell[2:5, 2:-2].reshape(-1, 3), cell[-5:-2, 2:-2].reshape(-1, 3),
                                  cell[5:-5, 2:5].reshape(-1, 3), cell[5:-5, -5:-2].reshape(-1, 3)))
            values[row, col] = np.median(rim, axis=0)
    parity = np.indices((8, 8)).sum(axis=0) % 2
    centers = np.array([np.median(values[parity == p], axis=0) for p in (0, 1)])
    contrast = np.linalg.norm(centers[0] - centers[1])
    if contrast < 25:
        return False
    distances = np.linalg.norm(values[:, :, None] - centers, axis=3)
    own = np.take_along_axis(distances, parity[:, :, None], axis=2)[:, :, 0]
    other = np.take_along_axis(distances, (1 - parity)[:, :, None], axis=2)[:, :, 0]
    correct = (own < contrast * .65) & (other - own > contrast * .2)
    if correct.sum() < 52 or min(correct.sum(axis=0).min(), correct.sum(axis=1).min()) < 5:
        return False
    # Expected grid boundaries must carry sustained changes in both directions.
    # Sampling either side of each boundary tolerates antialiasing and grid lines.
    for array in (patch, patch.transpose(1, 0, 2)):
        support = []
        for index in range(1, 8):
            edge = index * 32
            left = np.median(array[:, edge - 3:edge - 1], axis=1)
            right = np.median(array[:, edge + 1:edge + 3], axis=1)
            support.append(np.mean(np.linalg.norm(right - left, axis=1) > max(12, contrast * .2)))
        if min(support) < .3 or np.count_nonzero(np.array(support) >= .55) < 6:
            return False
    return True


def _refine_grid(pixels: np.ndarray, bounds: BoardBounds) -> BoardBounds | None:
    """Fit seven interior boundary peaks, independently of an outer shadow/frame."""
    coordinates = []
    for axis in (0, 1):
        # axis 0 fits columns; axis 1 fits rows.
        image = pixels if axis == 0 else pixels.transpose(1, 0, 2)
        start, stop = ((bounds.x, bounds.x + bounds.width) if axis == 0
                       else (bounds.y, bounds.y + bounds.height))
        lo, hi = ((bounds.y, bounds.y + bounds.height) if axis == 0
                  else (bounds.x, bounds.x + bounds.width))
        # Bound memory on large screenshots; sample across the full board height.
        strip = image[lo:hi:max(1, (hi - lo) // 256)].astype(np.float32)
        gradient = np.mean(np.linalg.norm(np.diff(strip, axis=1), axis=2), axis=0)
        step = (stop - start) / 8
        peaks = []
        for i in range(1, 8):
            target = start + i * step
            a, b = max(0, round(target - max(2, step * .14)) - 1), min(len(gradient), round(target + max(2, step * .14)))
            if a >= b:
                return None
            peaks.append(a + int(np.argmax(gradient[a:b])) + 1)
        # A rank of pawn bases can produce a stronger peak than a grid line.
        # Fit a consensus of at least five of the seven expected boundaries,
        # then independently require the full 8x8 pattern below.
        indices = np.arange(1, 8)
        peaks = np.array(peaks)
        best = None
        for i in range(6):
            for j in range(i + 1, 7):
                slope = (peaks[j] - peaks[i]) / (j - i)
                if abs(slope - step) > step * .1:
                    continue
                intercept = peaks[i] - slope * indices[i]
                residual = abs(peaks - (intercept + slope * indices))
                inliers = residual <= max(1.5, step * .025)
                score = (int(inliers.sum()), -float(residual[inliers].sum()))
                if best is None or score > best[0]:
                    best = score, inliers
        if best is None or best[0][0] < 5:
            return None
        inliers = best[1]
        slope, intercept = np.polyfit(indices[inliers], peaks[inliers], 1)
        first, last = round(intercept), round(intercept + 8 * slope)
        if first < 0 or last > image.shape[1]:
            return None
        coordinates.extend((first, last))
    x, right, y, bottom = coordinates
    if min(right - x, bottom - y) < _MIN_BOARD_SIDE or abs((right - x) - (bottom - y)) > max(2, (right - x) * .01):
        return None
    return BoardBounds(x, y, right - x, bottom - y)


def _structural_candidates(pixels: np.ndarray) -> list[BoardBounds]:
    """Propose connected edge grids without fixed light/dark RGB values."""
    height, width = pixels.shape[:2]
    scale = min(1., 1600 / max(height, width))
    work = (pixels if scale == 1 else cv2.resize(
        pixels, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA))
    # RGB edges also retain boundaries between colors of similar luminance.
    smooth = cv2.GaussianBlur(work, (3, 3), .6).astype(np.int16)
    edges = np.zeros(work.shape[:2], np.uint8)
    edges[:, 1:] |= (np.max(np.abs(np.diff(smooth, axis=1)), axis=2) > 12).astype(np.uint8)
    edges[1:, :] |= (np.max(np.abs(np.diff(smooth, axis=0)), axis=2) > 12).astype(np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, _, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    candidates = []
    for x, y, w, h, _ in stats[1:]:
        if min(w, h) < max(24, _MIN_BOARD_SIDE * scale - 2) or abs(w - h) > max(w, h) * .08:
            continue
        left, top = round(x / scale), round(y / scale)
        right, bottom = min(width, round((x + w) / scale)), min(height, round((y + h) / scale))
        proposal = BoardBounds(left, top, right - left, bottom - top)
        refined = _refine_grid(pixels, proposal)
        if refined is not None and _structural_pattern(pixels, refined):
            candidates.append(refined)
    return candidates


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

    Digital profiles share palette-independent structural detection. Complete
    axis-aligned boards require visible alternating backgrounds and regular
    edges; a minority of highlighted/occluded cells is allowed. Known palette
    proposals retain their exact legacy bounds. Minimum side: 128 pixels.
    The experimental print profile requires
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
    for candidate in _structural_candidates(pixels):
        # Palette and edge proposals can describe the same grid. Preserve the
        # exact palette bounds when available; do not merge separate boards.
        if not any(max(abs(a - b) for a, b in zip(candidate.as_box(), known.as_box())) <= 3
                   for known in candidates):
            candidates.append(candidate)
    if not candidates:
        raise BoardDetectionError("BOARD_NOT_FOUND", "No supported chessboard was detected in the image.")
    if len(candidates) > 1:
        raise BoardDetectionError("UNSUPPORTED_IMAGE", "Images with multiple chessboards are not supported.")
    return candidates[0]
