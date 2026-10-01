"""Detection on real screenshots, with tuning and held-out variants separated."""

import json
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import read_image


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / "tests/fixtures/detection/references.json").read_text())
CASES = []
for split, folder, marker in (
    ("tuning", "data/tuning", pytest.mark.integration),
    ("evaluation", "tests/fixtures/evaluation", pytest.mark.evaluation),
):
    for group in REFERENCE[split]:
        for color in ("white", "black"):
            path = ROOT / folder / REFERENCE["profileId"] / f"{group}-{color}.png"
            CASES.append(pytest.param(path, id=f"{split}-{group}-{color}", marks=marker))


@pytest.mark.parametrize("path", CASES)
@pytest.mark.parametrize("variant", ["original", "cropped", "small", "large", "relocated", "no-board"])
def test_screenshot_variants_against_reviewed_bounds(path, variant):
    image = read_image(path)
    box = tuple(REFERENCE["box"])
    expected = box
    if variant == "cropped":
        image = image.crop(box)
        expected = (0, 0, 584, 584)
    elif variant in {"small", "large"}:
        # Resize only the board, then place it at a new location. This avoids
        # treating the original screenshot's fixed location as a useful hint.
        size = 192 if variant == "small" else 960
        board = image.crop(box).resize((size, size), Image.Resampling.LANCZOS)
        image = Image.new("RGB", (size + 130, size + 180), "#dedede")
        image.paste(board, (73, 41))
        expected = (73, 41, 73 + size, 41 + size)
    elif variant == "relocated":
        canvas = Image.new("RGB", (image.width + 211, image.height + 57), "#373737")
        canvas.paste(image, (211, 57))
        image = canvas
        expected = (401, 215, 985, 799)
    elif variant == "no-board":
        # Remove the board and its shadow, leaving the actual editor interface.
        ImageDraw.Draw(image).rectangle((box[0] - 5, box[1] - 5, box[2] + 5, box[3] + 5), fill="#e8e8e8")
        with pytest.raises(BoardDetectionError) as caught:
            detect_board(image)
        assert caught.value.code == "BOARD_NOT_FOUND"
        return

    detected = detect_board(image).as_box()
    assert max(abs(a - b) for a, b in zip(detected, expected)) <= REFERENCE["maxEdgeErrorPixels"]
    if variant == "original":
        original = json.loads(path.with_suffix(".json").read_text())["boardBounds"]
        fractional_box = (original["x"], original["y"],
                          original["x"] + original["width"], original["y"] + original["height"])
        assert max(abs(a - b) for a, b in zip(detected, fractional_box)) <= REFERENCE["maxEdgeErrorPixels"]
