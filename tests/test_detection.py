"""Geometry and negative cases with independent, explicitly placed grid bounds."""

from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board


pytestmark = pytest.mark.unit


def draw_grid(size=256, count=8, colors=((240, 217, 181), (181, 136, 99))):
    image = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(image)
    for row in range(count):
        for col in range(count):
            draw.rectangle(
                (round(col * size / count), round(row * size / count),
                 round((col + 1) * size / count) - 1, round((row + 1) * size / count) - 1),
                fill=colors[(row + col) % 2],
            )
    return image


@pytest.mark.parametrize("size", [128, 193, 256, 584, 1024])
@pytest.mark.parametrize("offset", [(0, 0), (37, 91), (290, 21)])
def test_detects_grid_at_known_bounds(size, offset):
    board = draw_grid(size)
    x, y = offset
    if offset == (0, 0):
        image = board
    else:
        image = Image.new("RGB", (size + x + 47, size + y + 53), "#e8e8e8")
        image.paste(board, offset)
    original = image.tobytes()
    assert detect_board(image) == BoardBounds(x, y, size, size)
    assert image.tobytes() == original


def test_allows_piece_like_occlusions_without_returning_a_large_distractor():
    image = Image.new("RGB", (1000, 640), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((450, 20, 949, 519), fill=(240, 217, 181))
    board = draw_grid()
    pieces = ImageDraw.Draw(board)
    for row in range(8):
        for col in range(8):
            pieces.ellipse((col * 32 + 9, row * 32 + 5, col * 32 + 24, row * 32 + 28), fill="black")
    image.paste(board, (31, 59))
    assert detect_board(image) == BoardBounds(31, 59, 256, 256)


@pytest.mark.parametrize("color", ["white", "black", (240, 217, 181), (181, 136, 99)])
def test_rejects_uniform_images(color):
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(Image.new("RGB", (400, 400), color))
    assert caught.value.code == "BOARD_NOT_FOUND"
    assert caught.value.to_dict() == {"error": {"code": "BOARD_NOT_FOUND", "message": str(caught.value)}}


@pytest.mark.parametrize("count", [4, 6, 7, 9, 10, 12, 16])
def test_rejects_other_checker_grid_dimensions(count):
    with pytest.raises(BoardDetectionError, match="No supported"):
        detect_board(draw_grid(384, count=count))


def test_rejects_stripes():
    image = Image.new("RGB", (256, 256), (240, 217, 181))
    draw = ImageDraw.Draw(image)
    for col in (1, 3, 5, 7):
        draw.rectangle((col * 32, 0, col * 32 + 31, 255), fill=(181, 136, 99))
    with pytest.raises(BoardDetectionError):
        detect_board(image)


@pytest.mark.parametrize("box", [(0, 0, 224, 256), (32, 32, 256, 256)])
def test_rejects_incomplete_boards(box):
    with pytest.raises(BoardDetectionError):
        detect_board(draw_grid().crop(box))


def test_detects_previously_unsupported_palette():
    assert detect_board(draw_grid(colors=((255, 255, 255), (0, 0, 0)))) == BoardBounds(0, 0, 256, 256)


@pytest.mark.parametrize('size', [128, 193, 384, 513])
def test_tight_crop_with_repeated_piece_bases_retains_exact_bounds(size):
    # Strong repeated bases near grid lines can extrapolate the interior peak
    # fit beyond the image. This uses real pixels, without patching the fitter.
    image = draw_grid(size, colors=((208, 224, 234), (96, 132, 158)))
    draw = ImageDraw.Draw(image)
    cell = size / 8
    for row in range(8):
        for col in range(8):
            draw.rectangle((round((col+.15)*cell), round((row+.75)*cell),
                            round((col+.85)*cell), round((row+.9)*cell)), fill='#101010')
    assert detect_board(image) == BoardBounds(0, 0, size, size)


@pytest.mark.parametrize('count', [6, 7, 9, 10])
def test_full_frame_proposal_still_rejects_wrong_grid_size(monkeypatch, count):
    from boardsnap import detection
    monkeypatch.setattr(detection, '_refine_grid', lambda *_, **__: None)
    with pytest.raises(BoardDetectionError, match='No supported'):
        detect_board(draw_grid(384, count=count, colors=((208, 224, 234), (96, 132, 158))))


@pytest.mark.parametrize('margin', [4, 8])
def test_nearly_full_frame_grid_prefers_fitted_bounds_to_image_boundary(margin):
    board = draw_grid(384, colors=((208, 224, 234), (96, 132, 158)))
    image = Image.new('RGB', (384+2*margin, 384+2*margin), '#999999')
    image.paste(board, (margin, margin))
    assert detect_board(image) == BoardBounds(margin, margin, 384, 384)


def test_multiple_boards_are_an_explicit_error():
    image = Image.new("RGB", (600, 300), "white")
    image.paste(draw_grid(), (10, 10))
    image.paste(draw_grid(), (320, 10))
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(image)
    assert caught.value.code == "UNSUPPORTED_IMAGE"


def test_requires_normalized_rgb_input():
    with pytest.raises(TypeError):
        detect_board("image.png")
    with pytest.raises(ValueError):
        detect_board(Image.new("L", (256, 256)))


def test_small_image_has_no_supported_board():
    with pytest.raises(BoardDetectionError):
        detect_board(draw_grid(64))


def test_box_uses_exclusive_edges():
    assert BoardBounds(10, 20, 200, 200).as_box() == (10, 20, 210, 220)
