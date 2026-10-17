"""Raster borders must be measured before producing 64 uniformly aligned cells."""

from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board
from tests.test_detection import draw_grid

pytestmark = pytest.mark.unit


def board(size):
    image = draw_grid(size, colors=((208, 224, 234), (96, 132, 158)))
    draw = ImageDraw.Draw(image)
    # Repeated bases deliberately compete with the horizontal grid boundaries.
    cell = size / 8
    for row in range(8):
        for col in range(8):
            draw.rectangle((round((col+.15)*cell), round((row+.75)*cell),
                            round((col+.85)*cell), round((row+.9)*cell)), fill='#101010')
    return image


@pytest.mark.parametrize('size', [128, 193, 255, 384, 513])
@pytest.mark.parametrize('margins', [(0, 0, 0, 0), (0, 1, 2, 3), (3, 1, 7, 2), (1, 5, 0, 0)])
def test_asymmetric_margins_and_nonmultiple_dimensions(size, margins):
    left, top, right, bottom = margins
    image = Image.new('RGB', (size+left+right, size+top+bottom), '#555555')
    image.paste(board(size), (left, top))
    before = image.tobytes()
    actual = detect_board(image).as_box()
    assert max(abs(a-b) for a,b in zip(actual, (left, top, left+size, top+size))) <= 1
    assert image.tobytes() == before


@pytest.mark.parametrize('size', [193, 384, 513])
@pytest.mark.parametrize('side', ['left', 'top', 'right', 'bottom'])
def test_one_clipped_raster_pixel_returns_only_visible_pixels(size, side):
    box = {'left': (1, 0, size, size), 'top': (0, 1, size, size),
           'right': (0, 0, size-1, size), 'bottom': (0, 0, size, size-1)}[side]
    image = board(size).crop(box)
    assert detect_board(image) == BoardBounds(0, 0, image.width, image.height)


@pytest.mark.parametrize('side', [297, 383, 385, 401, 517])
@pytest.mark.parametrize('resampling', [Image.Resampling.BILINEAR, Image.Resampling.LANCZOS])
def test_small_scale_changes_preserve_the_eight_cell_grid(side, resampling):
    resized = board(384).resize((side, side), resampling)
    image = Image.new('RGB', (side+11, side+7), '#555555')
    image.paste(resized, (3, 5))
    assert max(abs(a-b) for a,b in zip(detect_board(image).as_box(), (3, 5, side+3, side+5))) <= 2


@pytest.mark.parametrize('cut', [3, 10, 24, 48])
@pytest.mark.parametrize('padded', [False, True])
def test_missing_border_content_is_not_padded_or_reconstructed(cut, padded):
    size = 384
    image = board(size).crop((cut, cut, size-cut, size-cut))
    if padded:
        canvas = Image.new('RGB', (size+50, size+70), '#555555')
        canvas.paste(image, (27, 31))
        image = canvas
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(image)
    assert caught.value.code == 'BOARD_NOT_FOUND'
