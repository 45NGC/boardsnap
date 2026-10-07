"""Classify normalized squares using installed, profile-specific templates."""

from functools import lru_cache
import hashlib
from importlib.resources import files
from io import BytesIO
import json

import cv2
import numpy as np
from PIL import Image

from boardsnap.profiles import DEFAULT_PROFILE, get_profile


_LABELS = (None, *"PNBRQKpnbrqk")


class ClassificationError(Exception):
    """Required template assets are unavailable or invalid; do not invent a board."""

    code = "PROCESSING_FAILED"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


def _square_features(square: Image.Image, profile: str = DEFAULT_PROFILE) -> np.ndarray:
    """Separate dark outlines/fills and light fills from the two known backgrounds."""
    pixels = np.asarray(square, dtype=np.float32)
    if get_profile(profile).kind == "print":
        # Suppress the edition's fine diagonal hatch while retaining piece shape.
        gray = cv2.GaussianBlur(pixels.mean(axis=2), (0, 0), 1.3)
        rim = np.concatenate((gray[3:9, 3:-3].ravel(), gray[-9:-3, 3:-3].ravel(),
                              gray[3:-3, 3:9].ravel(), gray[3:-3, -9:-3].ravel()))
        background = float(np.median(rim))
        features = np.stack((np.maximum(background - gray, 0) / max(background, 1),
                             np.maximum(gray - background, 0) / max(255 - background, 1)), axis=2)
        features[:4] = features[-4:] = 0
        features[:, :4] = features[:, -4:] = 0
        return features
    colors = np.asarray(get_profile(profile).colors, dtype=np.float32)
    counts = [np.count_nonzero(np.max(np.abs(pixels - color), axis=2) < 12) for color in colors]
    background = colors[np.argmax(counts)].mean()
    gray = pixels.mean(axis=2)
    dark = np.maximum(background - gray, 0) / background
    light = np.maximum(gray - background, 0) / (255 - background)
    features = np.stack((dark, light), axis=2)
    # Ignore seams/shadows and the profile's upper-right/lower-left coordinate
    # regions in EVERY square, independently of square location or orientation.
    features[:2, :, :] = features[-2:, :, :] = 0
    features[:, :2, :] = features[:, -2:, :] = 0
    if get_profile(profile).coordinates == "chesscom":
        features[:16, :16, :] = features[-16:, -16:, :] = 0
    else:
        features[:16, -16:, :] = features[-16:, :16, :] = 0
    return features


@lru_cache(maxsize=8)
def _templates(profile: str = DEFAULT_PROFILE) -> tuple[np.ndarray, tuple[str | None, ...]]:
    """Load installed assets only; never consult dataset annotations at runtime."""
    try:
        config = get_profile(profile)
        assets = files("boardsnap").joinpath("assets")
        manifest = json.loads(assets.joinpath(f"{config.piece_asset}.json").read_text(encoding="utf-8"))
        content = assets.joinpath(f"{config.piece_asset}.png").read_bytes()
        book = config.kind == "print"
        if (manifest["formatVersion"] != (2 if book else 1) or manifest["profileId"] != profile
                or manifest["squareSize"] != 64
                or manifest["atlasSha256"] != hashlib.sha256(content).hexdigest()):
            raise ValueError("Incompatible piece template assets.")
        entries = manifest["templates"]
        if (not book and len(entries) != 26) or (book and not 26 <= len(entries) <= 104):
            raise ValueError("Expected all thirteen classes on both backgrounds.")
        features, labels = [], []
        with Image.open(BytesIO(content)) as atlas:
            if atlas.size != (128, 64 * ((len(entries) + 1) // 2)) or atlas.mode != "RGB":
                raise ValueError("Invalid piece template atlas.")
            atlas.load()
            for index, entry in enumerate(entries):
                row, col = divmod(index, 2)
                box = (col * 64, row * 64, (col + 1) * 64, (row + 1) * 64)
                valid_label = (entry["label"] in _LABELS and entry["background"] in ("light", "dark")
                               if book else entry["label"] == _LABELS[row]
                               and entry["background"] == ("light", "dark")[col])
                if not valid_label or entry["atlasBox"] != list(box):
                    raise ValueError("Invalid template label or crop mapping.")
                with atlas.crop(box) as square:
                    features.append(_square_features(square, profile))
                labels.append(entry["label"])
        if {(e["label"], e["background"]) for e in entries} != {
                (label, background) for label in _LABELS for background in ("light", "dark")}:
            raise ValueError("Missing template classes or backgrounds.")
        values = np.stack(features)
        values.setflags(write=False)
        return values, tuple(labels)
    except (OSError, ValueError, KeyError, TypeError, IndexError, SyntaxError) as error:
        raise ClassificationError("Could not load the piece recognition templates.") from error


def classify_square(square: Image.Image, *, profile: str = DEFAULT_PROFILE) -> str | None:
    """Choose exactly one of 13 classes for a 64x64 RGB square in image view.

    Return None for empty, or one FEN symbol from PNBRQKpnbrqk. Select the least
    mean squared feature distance across the profile templates, with deterministic
    template-order tie breaking. No confidence, alternatives or legality checks.
    This classifier is not an unknown-style detector.

    TypeError/ValueError indicate invalid internal input; ClassificationError
    indicates missing/corrupt assets. Source pixels are not modified.
    """
    if not isinstance(square, Image.Image):
        raise TypeError("Expected a Pillow square image.")
    if square.mode != "RGB" or square.size != (64, 64):
        raise ValueError("Expected a 64x64 RGB square from the normalized board.")
    features = _square_features(square, profile)
    templates, labels = _templates(profile)
    distances = np.mean((templates - features) ** 2, axis=(1, 2, 3))
    if get_profile(profile).kind == "print":
        # A few pixels of printing/alignment variation should not change a class.
        distances = np.full(len(labels), np.inf)
        for dy in (-3, 0, 3):
            for dx in (-3, 0, 3):
                shifted = features[7 + dy:57 + dy, 7 + dx:57 + dx]
                values = np.mean((templates[:, 7:57, 7:57] - shifted) ** 2, axis=(1, 2, 3))
                distances = np.minimum(distances, values)
    return labels[int(np.argmin(distances))]


def classify_squares(squares: list[list[Image.Image]] | tuple[tuple[Image.Image, ...], ...],
                     *, profile: str = DEFAULT_PROFILE) -> list[list[str | None]]:
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
    return [[classify_square(square, profile=profile) for square in row] for row in squares]
