"""Classify normalized cburnett squares using a small, fixed template baseline."""

from functools import lru_cache
import hashlib
from importlib.resources import files
from io import BytesIO
import json

import numpy as np
from PIL import Image


_LABELS = (None, *"PNBRQKpnbrqk")
_COLORS = np.array(((240, 217, 181), (181, 136, 99)), dtype=np.float32)


class ClassificationError(Exception):
    """Required template assets are unavailable or invalid; do not invent a board."""

    code = "PROCESSING_FAILED"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


def _square_features(square: Image.Image) -> np.ndarray:
    """Separate dark outlines/fills and light fills from the two known backgrounds."""
    pixels = np.asarray(square, dtype=np.float32)
    counts = [np.count_nonzero(np.max(np.abs(pixels - color), axis=2) < 12) for color in _COLORS]
    background = _COLORS[np.argmax(counts)].mean()
    gray = pixels.mean(axis=2)
    dark = np.maximum(background - gray, 0) / background
    light = np.maximum(gray - background, 0) / (255 - background)
    features = np.stack((dark, light), axis=2)
    # Ignore seams/shadows and the profile's upper-right/lower-left coordinate
    # regions in EVERY square, independently of square location or orientation.
    features[:2, :, :] = features[-2:, :, :] = 0
    features[:, :2, :] = features[:, -2:, :] = 0
    features[:16, -16:, :] = features[-16:, :16, :] = 0
    return features


@lru_cache(maxsize=1)
def _templates() -> tuple[np.ndarray, tuple[str | None, ...]]:
    """Load installed assets only; never consult dataset annotations at runtime."""
    try:
        assets = files("boardsnap").joinpath("assets")
        manifest = json.loads(assets.joinpath("piece-templates.json").read_text(encoding="utf-8"))
        content = assets.joinpath("piece-templates.png").read_bytes()
        if (manifest["formatVersion"] != 1 or manifest["profileId"] != "lichess-cburnett-brown-v1"
                or manifest["squareSize"] != 64
                or manifest["atlasSha256"] != hashlib.sha256(content).hexdigest()):
            raise ValueError("Incompatible piece template assets.")
        entries = manifest["templates"]
        if len(entries) != 26:
            raise ValueError("Expected all thirteen classes on both backgrounds.")
        features, labels = [], []
        with Image.open(BytesIO(content)) as atlas:
            if atlas.size != (128, 832) or atlas.mode != "RGB":
                raise ValueError("Invalid piece template atlas.")
            atlas.load()
            for index, entry in enumerate(entries):
                row, col = divmod(index, 2)
                box = (col * 64, row * 64, (col + 1) * 64, (row + 1) * 64)
                if (entry["label"] != _LABELS[row] or entry["background"] != ("light", "dark")[col]
                        or entry["atlasBox"] != list(box)):
                    raise ValueError("Invalid template label or crop mapping.")
                with atlas.crop(box) as square:
                    features.append(_square_features(square))
                labels.append(entry["label"])
        values = np.stack(features)
        values.setflags(write=False)
        return values, tuple(labels)
    except (OSError, ValueError, KeyError, TypeError, IndexError, SyntaxError) as error:
        raise ClassificationError("Could not load the piece recognition templates.") from error


def classify_square(square: Image.Image) -> str | None:
    """Choose exactly one of 13 classes for a 64x64 RGB square in image view.

    Return None for empty, or one FEN symbol from PNBRQKpnbrqk. Select the least
    mean squared feature distance across the 26 templates, with deterministic
    template-order tie breaking. No confidence, alternatives or legality checks.
    This first-profile classifier is not an unknown-style detector.

    TypeError/ValueError indicate invalid internal input; ClassificationError
    indicates missing/corrupt assets. Source pixels are not modified.
    """
    if not isinstance(square, Image.Image):
        raise TypeError("Expected a Pillow square image.")
    if square.mode != "RGB" or square.size != (64, 64):
        raise ValueError("Expected a 64x64 RGB square from the normalized board.")
    features = _square_features(square)
    templates, labels = _templates()
    distances = np.mean((templates - features) ** 2, axis=(1, 2, 3))
    return labels[int(np.argmin(distances))]


def classify_squares(squares: list[list[Image.Image]] | tuple[tuple[Image.Image, ...], ...]
                     ) -> list[list[str | None]]:
    """Classify an 8x8 list/tuple matrix, retaining image order and caller ownership."""
    if not isinstance(squares, (list, tuple)):
        raise TypeError("Squares must be a list or tuple of rows.")
    if len(squares) != 8:
        raise ValueError("Squares must contain exactly 8 rows.")
    for row in squares:
        if not isinstance(row, (list, tuple)):
            raise TypeError("Each row must be a list or tuple.")
        if len(row) != 8:
            raise ValueError("Each row must contain exactly 8 squares.")
    return [[classify_square(square) for square in row] for row in squares]
