"""Geometry and preservation of orientation context, independent of the corpus."""

import numpy as np
from PIL import Image
import pytest

from boardsnap.detection import BoardBounds
from boardsnap.normalization import normalize_board


pytestmark = pytest.mark.unit


def test_exact_exclusive_crop_without_resizing():
    pixels = np.arange(30 * 40 * 3, dtype=np.uint8).reshape(30, 40, 3)
    with Image.fromarray(pixels) as source:
        before = source.tobytes()
        with normalize_board(source, BoardBounds(7, 5, 16, 16), square_size=2) as board:
            assert board.image.size == (16, 16)
            assert board.image.mode == "RGB"
            np.testing.assert_array_equal(np.asarray(board.image), pixels[5:21, 7:23])
            assert board.source_bounds == BoardBounds(7, 5, 16, 16)
            assert source.tobytes() == before


@pytest.mark.parametrize("size", [(128, 128), (193, 193), (584, 584), (960, 960), (585, 584)])
def test_resize_to_default_size_without_margin_pixels(size):
    with Image.new("RGB", (size[0] + 30, size[1] + 50), "red") as source:
        source.paste((20, 70, 120), (13, 21, 13 + size[0], 21 + size[1]))
        with normalize_board(source, BoardBounds(13, 21, *size)) as board:
            assert board.image.size == (512, 512)
            assert board.image.getextrema() == ((20, 20), (70, 70), (120, 120))


def test_context_preserves_internal_and_external_clues_after_source_changes_and_closes():
    with Image.new("RGB", (100, 110), "white") as source:
        # Distinct stand-ins for labels outside and inside the board.
        source.putpixel((8, 50), (11, 12, 13))
        source.putpixel((14, 80), (21, 22, 23))
        original = source.tobytes()
        board = normalize_board(source, BoardBounds(10, 20, 80, 80))
        source.paste("black", (0, 0, 100, 110))
    with board:
        assert board.source_image.size == (100, 110)
        assert board.source_image.tobytes() == original
        assert board.source_image.getpixel((8, 50)) == (11, 12, 13)
        assert board.source_image.getpixel((14, 80)) == (21, 22, 23)
        board.image.putpixel((0, 0), (255, 0, 0))
        assert board.source_image.tobytes() == original
    for image in (board.image, board.source_image):
        with pytest.raises(ValueError):
            image.getpixel((0, 0))


@pytest.mark.parametrize("bounds,exception", [
    ((0, 0, 16, 16), TypeError),
    (BoardBounds(0.5, 0, 16, 16), TypeError),
    (BoardBounds(True, 0, 16, 16), TypeError),
    (BoardBounds(-1, 0, 16, 16), ValueError),
    (BoardBounds(0, -1, 16, 16), ValueError),
    (BoardBounds(0, 0, 0, 16), ValueError),
    (BoardBounds(0, 0, 16, -1), ValueError),
    (BoardBounds(1, 0, 16, 16), ValueError),
    (BoardBounds(0, 1, 16, 16), ValueError),
])
def test_invalid_bounds_are_rejected_instead_of_padded(bounds, exception):
    with Image.new("RGB", (16, 16)) as source, pytest.raises(exception):
        normalize_board(source, bounds)


@pytest.mark.parametrize("size,exception", [(0, ValueError), (-1, ValueError), (1.5, TypeError), (True, TypeError)])
def test_invalid_target_size(size, exception):
    with Image.new("RGB", (16, 16)) as source, pytest.raises(exception):
        normalize_board(source, BoardBounds(0, 0, 16, 16), square_size=size)


def test_requires_rgb_image():
    with pytest.raises(TypeError):
        normalize_board("image.png", BoardBounds(0, 0, 16, 16))
    with Image.new("L", (16, 16)) as source, pytest.raises(ValueError):
        normalize_board(source, BoardBounds(0, 0, 16, 16))
