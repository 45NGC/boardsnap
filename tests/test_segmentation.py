"""Independent pixel expectations catch gaps, overlaps and exchanged squares."""

from contextlib import ExitStack

import numpy as np
from PIL import Image
import pytest

from boardsnap.detection import BoardBounds
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("side", [8, 24, 512])
def test_all_pixels_and_square_boundaries_in_image_order(side):
    # A deterministic pixel pattern catches even one-pixel boundary mistakes.
    pixels = np.random.default_rng(0).integers(0, 256, (side, side, 3), dtype=np.uint8)
    with ExitStack() as stack:
        image = stack.enter_context(Image.fromarray(pixels))
        squares = split_squares(image)
        assert len(squares) == 8
        assert all(len(row) == 8 for row in squares)
        assert len({id(square) for row in squares for square in row}) == 64
        step = side // 8
        rebuilt = stack.enter_context(Image.new("RGB", image.size))
        for row_index, row in enumerate(squares):
            for col_index, square in enumerate(row):
                stack.enter_context(square)
                assert square.mode == "RGB"
                assert square.size == (step, step)
                expected = pixels[row_index * step:(row_index + 1) * step,
                                  col_index * step:(col_index + 1) * step]
                np.testing.assert_array_equal(np.asarray(square), expected)
                rebuilt.paste(square, (col_index * step, row_index * step))
        assert rebuilt.tobytes() == image.tobytes()


@pytest.mark.parametrize("side", [128, 193, 584, 960])
@pytest.mark.parametrize("reversed_view", [False, True])
def test_resize_keeps_all_64_distinct_cells_in_visual_order(side, reversed_view):
    # Every square has its own color, so a transpose or reversal cannot hide.
    colors = [(20 + row * 28, 20 + col * 28, 30 + row * 8 + col)
              for row in range(8) for col in range(8)]
    if reversed_view:
        colors.reverse()
    with ExitStack() as stack:
        source = stack.enter_context(Image.new("RGB", (side + 50, side + 60), "white"))
        for row in range(8):
            for col in range(8):
                source.paste(colors[row * 8 + col],
                             (17 + round(col * side / 8), 23 + round(row * side / 8),
                              17 + round((col + 1) * side / 8), 23 + round((row + 1) * side / 8)))
        board = stack.enter_context(normalize_board(source, BoardBounds(17, 23, side, side)))
        squares = split_squares(board.image)
        for row in range(8):
            for col in range(8):
                square = stack.enter_context(squares[row][col])
                assert square.getpixel((32, 32)) == colors[row * 8 + col]


def test_crops_are_independent_and_survive_closing_board():
    with ExitStack() as stack:
        with Image.new("RGB", (16, 16), "white") as source:
            squares = split_squares(source)
            for row in squares:
                for square in row:
                    stack.enter_context(square)
            squares[0][0].putpixel((0, 0), (255, 0, 0))
            assert source.getpixel((0, 0)) == (255, 255, 255)
            source.paste("black", (0, 0, 16, 16))
        assert squares[0][0].getpixel((0, 0)) == (255, 0, 0)
        assert squares[0][1].getpixel((0, 0)) == (255, 255, 255)


@pytest.mark.parametrize("size", [(0, 0), (7, 7), (16, 24), (24, 16), (17, 17)])
def test_rejects_dimensions_that_cannot_split_evenly(size):
    with Image.new("RGB", size) as image, pytest.raises(ValueError):
        split_squares(image)


def test_requires_rgb_image():
    with pytest.raises(TypeError):
        split_squares(None)
    with Image.new("L", (16, 16)) as image, pytest.raises(ValueError):
        split_squares(image)
