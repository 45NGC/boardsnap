"""Corner provenance and perspective review preserve square identity."""

from copy import deepcopy
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytest

from tools.prepare_phone_photos import audit, validate_corners
from tools.review_phone_geometry import rectify, visual_labels

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[1]


def test_perspective_review_preserves_all_64_square_centers():
    pixels = np.zeros((256, 256, 3), dtype=np.uint8)
    colors = {}
    for rank in range(8):
        for file in range(8):
            color = (20 + rank * 27, 20 + file * 27, 20 + (rank + file) * 13)
            colors[rank, file] = color
            pixels[rank * 32:(rank + 1) * 32, file * 32:(file + 1) * 32] = color
    corners = [[35, 20], [292, 47], [267, 278], [14, 245]]
    h = cv2.getPerspectiveTransform(np.float32([[0, 0], [256, 0], [256, 256], [0, 256]]),
                                    np.float32(corners))
    photo = Image.fromarray(cv2.warpPerspective(pixels, h, (320, 300)))
    original = photo.tobytes()
    result = rectify(photo, corners, 256)
    assert result.size == (256, 256)
    assert photo.tobytes() == original
    for (rank, file), color in colors.items():
        assert result.getpixel((file * 32 + 16, rank * 32 + 16)) == color


def test_diagram_uses_chess_view_but_corner_order_does_not():
    label = {"piecePlacement": "k7/8/8/8/8/8/8/6NK", "orientation": "black-bottom"}
    rows = visual_labels(label)
    assert rows[0][:2] == "KN"
    assert rows[7][7] == "k"
    label["orientation"] = "white-bottom"
    assert visual_labels(label)[0][0] == "k"
    assert visual_labels({"piecePlacement": None}) is None
    image = Image.new("RGB", (16, 16), "red")
    image.paste("blue", (0, 0, 8, 8))
    assert rectify(image, [[0, 0], [16, 0], [16, 16], [0, 16]], 16).tobytes() == image.tobytes()


@pytest.mark.parametrize("corners", [
    None, [], [[1, 2]] * 3, [[0, 0, 0]] * 4,
    [[False, 0], [20, 0], [20, 20], [0, 20]],
    [[float("nan"), 0], [20, 0], [20, 20], [0, 20]],
    [[0, 0], [float("inf"), 0], [20, 20], [0, 20]],
    [[-1, 0], [20, 0], [20, 20], [0, 20]],
    [[0, 0], [21, 0], [20, 20], [0, 20]],
    [[0, 0], [20, 20], [20, 0], [0, 20]],  # crossed
    [[0, 0], [0, 20], [20, 20], [20, 0]],  # counterclockwise
    [[20, 20], [0, 20], [0, 0], [20, 0]],  # wrong first corner
    [[0, 0], [20, 0], [5, 5], [0, 20]],  # concave
    [[0, 0], [20, 0], [20, 0], [0, 20]],
])
def test_invalid_annotations_are_rejected(corners):
    with pytest.raises(ValueError):
        validate_corners(corners, (20, 20))


@pytest.mark.parametrize("change", ["hash", "corners", "orientation", "placement", "review", "order"])
def test_stale_geometry_or_label_review_is_rejected(change):
    data = json.loads((ROOT / "data/manifests/phone-photos-v1.json").read_text())
    data["samples"] = [deepcopy(data["samples"][0])]
    row = data["samples"][0]
    if change == "hash":
        row["geometryReview"]["imageSha256"] = "changed"
    elif change == "corners":
        row["boardCorners"][0][0] += 1
    elif change == "orientation":
        row["label"]["rectifiedReview"]["orientation"] = "other"
    elif change == "placement":
        row["label"]["rectifiedReview"]["piecePlacement"] = "8/8/8/8/8/8/8/8"
    elif change == "review":
        del row["geometryReview"]
    else:
        row["geometryReview"]["cornerOrder"] = ["a8", "h8", "h1", "a1"]
    with pytest.raises(ValueError):
        audit(data, verify_files=False)
