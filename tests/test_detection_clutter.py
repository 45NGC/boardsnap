"""Interior grid proposals must survive connected backgrounds, without relaxed gates."""

from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardDetectionError, detect_board
from tests.test_detection_structure import scene

pytestmark = pytest.mark.unit


def cluttered_board(side=384, offset=(97, 63), *, count=8, crop=None, marks=True):
    """Known geometry inside a connected network of lines and interface text."""
    board = scene(side, count=count, texture=True, marks=marks, pieces=count == 8).crop(
        (41, 29, 41 + side, 29 + side))
    if crop is not None:
        board = board.crop(crop)
    x, y = offset
    image = Image.new('RGB', (side + x + 211, side + y + 157), '#777777')
    draw = ImageDraw.Draw(image)
    # The network intersects the board's outline, so connected components alone
    # cannot isolate it. This background is not itself a checkerboard.
    for col in range(0, image.width, 47):
        draw.line((col, 0, col, image.height), fill='#222222', width=2)
    for row in range(0, image.height, 43):
        draw.line((0, row, image.width, row), fill='#eeeeee', width=2)
    draw.text((5, 5), 'Video | 12:34 | Analysis', fill='black')
    draw.text((x + side + 8, y + 25), 'Moves\n1. e4 e5\n2. Nf3 Nc6', fill='white')
    image.paste(board, offset)
    return image


@pytest.mark.parametrize('side,offset', [(128, (97, 63)), (193, (311, 29)),
                                        (384, (97, 63)), (768, (21, 105)),
                                        (1800, (97, 63))])
def test_grid_inside_connected_background_has_reviewed_geometry(side, offset):
    image = cluttered_board(side, offset)
    before = image.tobytes()
    x, y = offset
    actual = detect_board(image).as_box()
    assert max(abs(a - b) for a, b in zip(actual, (x, y, x + side, y + side))) <= 2
    assert image.tobytes() == before


def test_interior_search_is_needed_for_connected_background(monkeypatch):
    from boardsnap import detection
    image = cluttered_board()
    assert detect_board(image).as_box() == (97, 63, 481, 447)
    monkeypatch.setattr(detection, '_interior_grid_candidates', lambda *_: [])
    with pytest.raises(BoardDetectionError, match='No supported'):
        detect_board(image)


@pytest.mark.parametrize('count', [4, 6, 7, 9, 10, 12, 16])
def test_other_grid_dimensions_in_clutter_are_rejected(count):
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(cluttered_board(count=count, marks=False))
    assert caught.value.code == 'BOARD_NOT_FOUND'


@pytest.mark.parametrize('crop', [(0, 0, 336, 384), (48, 48, 384, 384),
                                  (10, 10, 374, 374)])
def test_incomplete_grid_in_clutter_is_not_reconstructed(crop):
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(cluttered_board(crop=crop))
    assert caught.value.code == 'BOARD_NOT_FOUND'


def test_clutter_without_board_is_rejected():
    image = cluttered_board()
    ImageDraw.Draw(image).rectangle((96, 62, 482, 448), fill='#888888')
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(image)
    assert caught.value.code == 'BOARD_NOT_FOUND'


def test_two_boards_connected_to_background_are_not_silently_selected():
    image = cluttered_board(256)
    other = cluttered_board(193)
    canvas = Image.new('RGB', (image.width + other.width, max(image.height, other.height)), '#777777')
    canvas.paste(image, (0, 0))
    canvas.paste(other, (image.width, 0))
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(canvas)
    assert caught.value.code == 'UNSUPPORTED_IMAGE'


def test_unrelated_axis_lines_cannot_supply_a_board():
    # Both axes have seven regular peaks, but their line segments do not form
    # a common alternating 8x8 region. Global projections only propose boxes.
    image = Image.new('RGB', (720, 720), '#dddddd')
    draw = ImageDraw.Draw(image)
    for index in range(1, 8):
        draw.line((40 + index * 40, 10, 40 + index * 40, 200), fill='black', width=2)
        draw.line((430, 330 + index * 40, 700, 330 + index * 40), fill='black', width=2)
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(image)
    assert caught.value.code == 'BOARD_NOT_FOUND'
