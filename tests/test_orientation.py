"""Orientation fallback/consistency policy and independent canonical mapping."""

from contextlib import ExitStack
from unittest.mock import patch

from PIL import Image
import pytest

from boardsnap.detection import BoardBounds
from boardsnap.normalization import NormalizedBoard, normalize_board
from boardsnap.orientation import detect_orientation, to_canonical


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("labels,expected", [
    (list("abcdefgh87654321"), "white-bottom"),
    (list("hgfedcba12345678"), "black-bottom"),
    ([None] * 16, "white-bottom"),
    (list("hgfe") + [None] * 12, "black-bottom"),
    (list("hgf") + [None] * 13, "white-bottom"),
    ([None] * 8 + list("12345678"), "black-bottom"),
    (list("hgfedcba") + [None] * 8, "black-bottom"),
    (list("hgfedcba87654321"), "white-bottom"),
    (list("abcdefgh12345678"), "white-bottom"),
    (list("ggfedcba12345678"), "white-bottom"),
])
def test_coordinate_evidence_policy_in_isolation(labels, expected):
    # This is a decision-policy unit test, not an OCR or recognition measurement.
    with Image.new("RGB", (584, 584)) as image:
        with normalize_board(image, BoardBounds(0, 0, 584, 584)) as board:
            with patch("boardsnap.orientation._read_coordinate", side_effect=labels):
                assert detect_orientation(board) == expected


@pytest.mark.parametrize("size", [128, 256, 584])
@pytest.mark.parametrize("color", ["white", "black", (181, 136, 99), (240, 217, 181)])
def test_real_pixels_without_coordinates_fall_back(size, color):
    with Image.new("RGB", (size, size), color) as image:
        with normalize_board(image, BoardBounds(0, 0, size, size)) as board:
            assert detect_orientation(board) == "white-bottom"


@pytest.mark.parametrize("orientation", ["white-bottom", "black-bottom"])
@pytest.mark.parametrize("container", [list, tuple])
def test_every_cell_maps_to_canonical_order_without_mutation(orientation, container):
    canonical = [[f"{file}{rank}" for file in "abcdefgh"] for rank in range(8, 0, -1)]
    if orientation == "white-bottom":
        visual = container(container(row) for row in canonical)
    else:
        visual = container(container(f"{file}{rank}" for file in "hgfedcba") for rank in range(1, 9))
    before = [list(row) for row in visual]
    result = to_canonical(visual, orientation)
    assert result == canonical
    assert [list(row) for row in visual] == before
    result[0][0] = "changed"
    assert [list(row) for row in visual] == before


def test_reorders_square_objects_without_rotating_their_pixels():
    with ExitStack() as stack:
        visual = [[stack.enter_context(Image.new("RGB", (8, 8))) for _ in range(8)] for _ in range(8)]
        visual[7][7].putpixel((1, 2), (255, 0, 0))
        result = to_canonical(visual, "black-bottom")
        assert result[0][0] is visual[7][7]
        assert result[0][0].getpixel((1, 2)) == (255, 0, 0)
        assert result[0][0].getpixel((6, 5)) == (0, 0, 0)


@pytest.mark.parametrize("matrix,exception", [
    (None, TypeError), ("abcdefgh" * 8, TypeError),
    ([], ValueError), ([[None] * 8] * 7, ValueError),
    ([None] * 8, TypeError), (["abcdefgh"] * 8, TypeError),
    ([[None] * 7] * 8, ValueError), ([[None] * 9] * 8, ValueError),
    ([[None] * 7, [None] * 9] + [[None] * 8] * 6, ValueError),
])
def test_rejects_invalid_matrix(matrix, exception):
    with pytest.raises(exception):
        to_canonical(matrix, "white-bottom")


def test_rejects_invalid_orientation():
    with pytest.raises(ValueError):
        to_canonical([[None] * 8 for _ in range(8)], "sideways")


def test_rejects_invalid_context():
    with pytest.raises(TypeError):
        detect_orientation(None)
    with Image.new("RGB", (584, 584)) as rgb, Image.new("L", (584, 584)) as gray:
        with pytest.raises(ValueError):
            detect_orientation(NormalizedBoard(rgb, gray, BoardBounds(0, 0, 584, 584)))
        with pytest.raises(ValueError):
            detect_orientation(NormalizedBoard(rgb, rgb, BoardBounds(-1, 0, 584, 584)))
        with pytest.raises(TypeError):
            detect_orientation(NormalizedBoard(rgb, rgb, BoardBounds(.5, 0, 584, 584)))
