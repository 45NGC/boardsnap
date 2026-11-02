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


@pytest.mark.parametrize('drift,recover', [(5, True), (14, False)])
def test_measured_boundary_recovery_is_bounded(monkeypatch, drift, recover):
    from boardsnap import photo_detection as detector
    corners = np.float32([[100, 100], [612, 100], [612, 612], [100, 612]])
    monkeypatch.setattr(detector, '_contour_candidates', lambda _: [corners])
    monkeypatch.setattr(detector, '_line_candidates', lambda _, **kwargs: [])
    monkeypatch.setattr(detector, '_refine', lambda pixels, q: q + np.float32([0, drift]))
    with grid(pieces=False) as board, photograph(board, corners, (712, 712), clutter=False) as image:
        if recover:
            assert np.array_equal(detect_photo_board(image).corners, corners)
        else:
            with pytest.raises(BoardDetectionError):
                detect_photo_board(image)


def test_recovery_keeps_original_success_and_skips_fragment_pass(monkeypatch):
    from boardsnap import photo_detection as detector
    def unexpected(*args, **kwargs):
        pytest.fail('Do not run recovery after a supported contour result.')
    monkeypatch.setattr(detector, '_line_candidates', unexpected)
    corners = [[140, 80], [650, 110], [620, 650], [90, 590]]
    with grid() as board, photograph(board, corners) as image:
        assert geometry_metrics(detect_photo_board(image).corners, corners)['withinPolicy']


def test_fragmented_edges_still_require_complete_grid(monkeypatch):
    from boardsnap import photo_detection as detector
    corners = np.float32([[140, 80], [650, 110], [620, 650], [90, 590]])
    calls = []
    monkeypatch.setattr(detector, '_contour_candidates', lambda _: [])
    def proposals(pixels, *, fragmented_edges=False):
        calls.append(fragmented_edges)
        return [corners] if fragmented_edges else []
    monkeypatch.setattr(detector, '_line_candidates', proposals)
    with grid() as board, photograph(board, corners) as image:
        assert geometry_metrics(detect_photo_board(image).corners, corners)['withinPolicy']
    assert calls == [False, True]
    calls.clear()
    with grid() as board:
        ImageDraw.Draw(board).rectangle((0, 0, 13, 511), fill='#343b42')
        with photograph(board, corners) as image, pytest.raises(BoardDetectionError):
            detect_photo_board(image)
    assert calls == [False, True]


@pytest.mark.integration
@pytest.mark.parametrize('photo_id', ['video-img_5406', 'video-img_5407'])
def test_reviewed_photo_recovery_and_hidden_file(photo_id):
    import hashlib
    import json
    from pathlib import Path
    from boardsnap.image_input import read_image
    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root/'data/manifests/phone-validation-v1.json').read_text())['samples']
    row = next(r for r in rows if r['id'] == photo_id)
    path = root/row['imagePath']
    if not path.is_file():
        pytest.skip('Local consulted photo validation image is unavailable.')
    assert row['split'] == 'validation'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['imageSha256']
    with read_image(path) as image:
        found = detect_photo_board(image)
        assert geometry_metrics(found.corners, row['boardCorners'])['withinPolicy']
        transform = cv2.getPerspectiveTransform(np.float32([[0, 0], [512, 0], [512, 512], [0, 512]]),
                                                np.float32(row['boardCorners']))
        hidden = cv2.perspectiveTransform(np.float32([[[0, 0], [14, 0], [14, 512], [0, 512]]]), transform)
        pixels = np.array(image)
        cv2.fillConvexPoly(pixels, np.rint(hidden[0]).astype(np.int32), (52, 59, 66))
        with Image.fromarray(pixels) as incomplete, pytest.raises(BoardDetectionError) as error:
            detect_photo_board(incomplete)
        assert error.value.code == 'BOARD_NOT_FOUND'


@pytest.mark.parametrize('count', [7, 9])
def test_recovery_rejects_near_eight_grid_sizes(count):
    corners = [[140, 80], [650, 110], [620, 650], [90, 590]]
    with grid(count, pieces=False) as board, photograph(board, corners) as image, pytest.raises(BoardDetectionError):
        detect_photo_board(image)


@pytest.mark.parametrize('box', [(498, 0, 511, 511), (0, 0, 511, 13), (0, 498, 511, 511)])
def test_recovery_rejects_other_incomplete_rims(box):
    corners = [[140, 80], [650, 110], [620, 650], [90, 590]]
    with grid() as board:
        ImageDraw.Draw(board).rectangle(box, fill='#343b42')
        with photograph(board, corners) as image, pytest.raises(BoardDetectionError):
            detect_photo_board(image)
