"""Classifier input, background handling and failure contract."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

import boardsnap.classification as classification
from boardsnap.classification import ClassificationError, classify_square, classify_squares


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("color", [(240, 217, 181), (181, 136, 99)])
@pytest.mark.parametrize("labels", [False, True])
def test_empty_squares_and_coordinate_regions(color, labels):
    with Image.new("RGB", (64, 64), color) as square:
        if labels:
            # These are distracting marks, not simulated piece recognition.
            draw = ImageDraw.Draw(square)
            draw.rectangle((53, 3, 60, 12), fill="white")
            draw.rectangle((3, 53, 12, 60), fill="black")
        before = square.tobytes()
        assert classify_square(square) is None
        assert square.tobytes() == before


@pytest.mark.parametrize("mode,size", [("L", (64, 64)), ("RGBA", (64, 64)),
                                       ("RGB", (63, 64)), ("RGB", (32, 32)), ("RGB", (0, 0))])
def test_requires_normalized_rgb_square(mode, size):
    with Image.new(mode, size) as square, pytest.raises(ValueError):
        classify_square(square)


@pytest.mark.parametrize("value", [None, "square.png", [[0] * 64] * 64])
def test_requires_pillow_image(value):
    with pytest.raises(TypeError):
        classify_square(value)


@pytest.mark.parametrize("value,exception", [
    (None, TypeError), ("abcdefgh" * 8, TypeError), ([], ValueError),
    ([[None] * 8] * 7, ValueError), ([None] * 8, TypeError),
    ([[None] * 7] * 8, ValueError), ([[None] * 9] * 8, ValueError),
    ([[None] * 7, [None] * 9] + [[None] * 8] * 6, ValueError),
    ([[None] * 8] * 8, TypeError),
])
def test_invalid_matrix_does_not_produce_partial_labels(value, exception):
    with pytest.raises(exception):
        classify_squares(value)


def test_tuple_matrix_keeps_input_images_open_and_unchanged():
    with Image.new("RGB", (64, 64), (240, 217, 181)) as square:
        squares = tuple(tuple(square for _ in range(8)) for _ in range(8))
        before = square.tobytes()
        assert classify_squares(squares) == [[None] * 8 for _ in range(8)]
        assert square.tobytes() == before


@pytest.mark.parametrize("failure", ["missing", "hash", "classes", "mapping", "corrupt", "mode"])
def test_unavailable_templates_raise_structured_processing_error(tmp_path, monkeypatch, failure):
    original = Path(__file__).resolve().parents[1] / "src/boardsnap/assets"
    target = tmp_path / "assets"
    target.mkdir()
    data = json.loads((original / "piece-templates.json").read_text())
    content = (original / "piece-templates.png").read_bytes()
    if failure == "hash":
        data["atlasSha256"] = "incorrect"
    elif failure == "classes":
        data["templates"].pop()
    elif failure == "mapping":
        data["templates"][0]["label"] = "K"
    elif failure == "corrupt":
        content = b"not a PNG"
        data["atlasSha256"] = hashlib.sha256(content).hexdigest()
    elif failure == "mode":
        with Image.new("RGBA", (128, 832)) as image:
            image.save(target / "piece-templates.png")
        content = (target / "piece-templates.png").read_bytes()
        data["atlasSha256"] = hashlib.sha256(content).hexdigest()
    if failure != "missing":
        (target / "piece-templates.json").write_text(json.dumps(data))
        (target / "piece-templates.png").write_bytes(content)
    classification._templates.cache_clear()
    monkeypatch.setattr(classification, "files", lambda package: tmp_path)
    try:
        with Image.new("RGB", (64, 64), (240, 217, 181)) as square:
            with pytest.raises(ClassificationError) as caught:
                classify_square(square)
        assert caught.value.to_dict() == {
            "error": {"code": "PROCESSING_FAILED", "message": "Could not load the piece recognition templates."}
        }
    finally:
        classification._templates.cache_clear()
