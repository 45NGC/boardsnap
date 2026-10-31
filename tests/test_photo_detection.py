"""Photographic grid geometry is independent of piece labels and neural weights."""

import cv2
import numpy as np
from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardDetectionError
from boardsnap.photo_detection import detect_photo_board
from tools.evaluate_photo_detection import geometry_metrics


def grid(count=8, *, pieces=True):
    image = Image.new('RGB', (512, 512))
    draw = ImageDraw.Draw(image)
    for row in range(count):
        for col in range(count):
            x, y = col*512/count, row*512/count
            draw.rectangle((x, y, (col+1)*512/count, (row+1)*512/count),
                           fill=(210, 218, 170) if (row+col) % 2 == 0 else (80, 110, 130))
            if pieces and count == 8 and (row in (0, 1, 6, 7) or (row, col) == (3, 4)):
                draw.ellipse((x+20, y+14, x+44, y+52), fill='black' if row < 4 else 'white')
    return image


def photograph(board, corners, size=(800, 760), *, clutter=True):
    transform = cv2.getPerspectiveTransform(np.float32([[0, 0], [512, 0], [512, 512], [0, 512]]), np.float32(corners))
    pixels = cv2.warpPerspective(np.asarray(board), transform, size)
    mask = cv2.warpPerspective(np.full((512, 512), 255, np.uint8), transform, size)
    background = Image.new('RGB', size, '#343b42')
    if clutter:
        draw = ImageDraw.Draw(background)
        draw.rectangle((15, 10, size[0]-15, size[1]-15), outline='#e8e8e8', width=5)
        for y in range(30, size[1]-20, 35):
            draw.text((20, y), 'Interface - 01:15  MOVES', fill='white')
    array = np.array(background)
    array[mask > 200] = pixels[mask > 200]
    return Image.fromarray(array)


@pytest.mark.parametrize('corners', [
    [[140, 80], [650, 110], [620, 650], [90, 590]],
    [[210, 90], [650, 60], [700, 650], [110, 680]],
    [[80, 160], [670, 70], [650, 580], [170, 660]],
])
def test_moderate_perspective_rotation_and_interface(corners):
    with grid() as board, photograph(board, corners) as image:
        before = image.tobytes()
        found = np.array(detect_photo_board(image).corners)
        assert np.max(np.linalg.norm(found - corners, axis=1)) < 6
        assert before == image.tobytes()


def test_illumination_and_marked_cells():
    with grid() as board:
        draw = ImageDraw.Draw(board)
        draw.rectangle((3*64, 3*64, 4*64-1, 4*64-1), fill=(230, 210, 40))
        draw.line((40, 100, 420, 390), fill=(200, 120, 30), width=8)
        pixels = np.asarray(board).astype(float)
        pixels *= np.linspace(1, .65, 512)[:, None, None]
        corners = [[110, 70], [660, 100], [610, 650], [160, 630]]
        with Image.fromarray(pixels.astype(np.uint8)) as shaded, photograph(shaded, corners) as image:
            found = np.array(detect_photo_board(image).corners)
        assert np.max(np.linalg.norm(found - corners, axis=1)) < 6


@pytest.mark.parametrize('variant', ['plain', 'noise', 'frame', 'six', 'ten', 'hidden14', 'missing-file', 'cut-off'])
def test_incomplete_boards_and_non_boards_are_rejected(variant):
    corners = [[130, 80], [650, 100], [620, 650], [100, 620]]
    if variant in ('six', 'ten'):
        board = grid(6 if variant == 'six' else 10, pieces=False)
    elif variant == 'noise':
        board = Image.fromarray(np.random.default_rng(14).integers(0, 256, (512, 512, 3), dtype=np.uint8))
    elif variant in ('plain', 'frame'):
        board = Image.new('RGB', (512, 512), '#c5c5c5')
        if variant == 'frame':
            draw = ImageDraw.Draw(board)
            for inset in (1, 20, 40): draw.rectangle((inset, inset, 511-inset, 511-inset), outline='black', width=4)
    else:
        board = grid()
        if variant == 'hidden14':
            ImageDraw.Draw(board).rectangle((0, 0, 13, 511), fill='#343b42')
        elif variant == 'missing-file':
            ImageDraw.Draw(board).rectangle((0, 0, 63, 511), fill='#343b42')
    image = photograph(board, corners)
    if variant == 'cut-off':
        image = image.crop((180, 0, 800, 760))
    with board, image, pytest.raises(BoardDetectionError) as error:
        detect_photo_board(image)
    assert error.value.code == 'BOARD_NOT_FOUND'


def test_two_complete_boards_are_ambiguous():
    with grid() as board:
        first = photograph(board, [[40, 40], [440, 50], [450, 480], [50, 470]], (1000, 520), clutter=False)
        second = photograph(board, [[540, 40], [940, 50], [950, 480], [550, 470]], (1000, 520), clutter=False)
        pixels = np.asarray(first).copy()
        pixels[:, 500:] = np.asarray(second)[:, 500:]
        with Image.fromarray(pixels) as image, pytest.raises(BoardDetectionError) as error:
            detect_photo_board(image)
        first.close()
        second.close()
        assert error.value.code == 'UNSUPPORTED_IMAGE'


def test_input_contract():
    with pytest.raises(TypeError): detect_photo_board(None)
    with Image.new('L', (512, 512)) as image, pytest.raises(ValueError): detect_photo_board(image)
    with Image.new('RGB', (40, 30)) as image, pytest.raises(BoardDetectionError): detect_photo_board(image)
    with Image.new('RGB', (1, 3000)) as image, pytest.raises(BoardDetectionError): detect_photo_board(image)


def test_line_fallback_without_an_exterior_contour(monkeypatch):
    from boardsnap import photo_detection
    monkeypatch.setattr(photo_detection, '_contour_candidates', lambda _: [])
    corners = [[140, 80], [650, 110], [620, 650], [90, 590]]
    with grid() as board, photograph(board, corners) as image:
        found = detect_photo_board(image)
    assert geometry_metrics(found.corners, corners)['withinPolicy']


def test_geometry_metrics_detect_a_shift_even_with_high_overlap():
    expected = [[100, 100], [612, 100], [612, 612], [100, 612]]
    assert geometry_metrics(expected, expected)['withinPolicy']
    metrics = geometry_metrics(np.array(expected)+[10, 0], expected)
    assert metrics['intersectionOverUnion'] > .95
    assert metrics['maxCornerErrorPixels'] == 10
    assert metrics['maxGridErrorCellFraction'] == 10/64
    assert not metrics['withinPolicy']


def test_diagnostic_cli_saves_only_detection_outputs(tmp_path, monkeypatch, capsys):
    import json
    from tools.detect_photo import main
    monkeypatch.chdir(tmp_path)
    corners = [[140, 80], [650, 110], [620, 650], [90, 590]]
    with grid() as board, photograph(board, corners) as image:
        image.save('photo.png')
    output = '.cache/photo'
    assert main(['photo.png', '--output', output]) == 0
    result = json.loads(capsys.readouterr().out)
    assert 'boardCorners' in result and 'piecePlacement' not in result
    assert geometry_metrics(result['boardCorners'], corners)['withinPolicy']
    with Image.open(tmp_path / output / 'rectified.png') as board:
        assert board.size == (512, 512)
    assert (tmp_path / output / 'outline.jpg').exists()
    with pytest.raises(SystemExit) as error:
        main(['photo.png', '--output', output])
    assert error.value.code == 2
    capsys.readouterr()
    assert main(['missing.jpg', '--output', '.cache/missing']) == 1
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'INPUT_READ_ERROR'
