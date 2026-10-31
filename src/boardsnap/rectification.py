"""Rectify image-space grid boundaries without changing chess orientation."""

import cv2
import numpy as np
from PIL import Image


def rectify_board(image: Image.Image, corners, *, side: int = 512) -> Image.Image:
    """Return an owned RGB square using the photographic training interpolation.

    Corners are TL/TR/BR/BL in EXIF-normalized input coordinates. Boundaries
    map to [0, side]; no extra margin, sharpening, rotation or cell reordering.
    Invalid geometry is rejected rather than filling absent board regions.
    """
    if not isinstance(image, Image.Image):
        raise TypeError("Expected a Pillow image.")
    if image.mode != "RGB":
        raise ValueError("Expected RGB pixels; normalize the input first.")
    if type(side) is not int or side < 8 or side % 8:
        raise ValueError("Board side must be a positive multiple of eight.")
    points = np.asarray(corners, dtype=np.float64)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError("Expected four finite corner coordinates.")
    if np.any(points < 0) or np.any(points > (image.width, image.height)):
        raise ValueError("Board corners must stay inside the input image.")
    edges = np.roll(points, -1, axis=0) - points
    following = np.roll(edges, -1, axis=0)
    if np.any(edges[:, 0] * following[:, 1] - edges[:, 1] * following[:, 0] <= 0):
        raise ValueError("Corners must form a convex clockwise quadrilateral.")
    tl, tr, br, bl = points
    if not (tl[0] < tr[0] and bl[0] < br[0] and tl[1] < bl[1] and tr[1] < br[1]):
        raise ValueError("Corners must follow image TL/TR/BR/BL order.")
    transform = cv2.getPerspectiveTransform(
        points.astype(np.float32), np.float32([[0, 0], [side, 0], [side, side], [0, side]]),
    )
    return Image.fromarray(cv2.warpPerspective(
        np.asarray(image), transform, (side, side), flags=cv2.INTER_LINEAR,
    ))
