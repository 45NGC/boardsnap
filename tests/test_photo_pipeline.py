"""Photo rectification parity, orientation, routing and CLI error contracts."""

import json

import numpy as np
from PIL import Image
import pytest

from boardsnap.adapters import cli
from boardsnap.classification import ClassificationError
from boardsnap.detection import BoardDetectionError
from boardsnap.photo_detection import BoardQuadrilateral
from boardsnap.pipeline import recognize_image
from boardsnap.rectification import rectify_board
from boardsnap.segmentation import split_squares
from tools.build_phone_squares import extract_photo_squares


@pytest.mark.parametrize('orientation', ['white-bottom', 'black-bottom'])
def test_all_crops_match_training_pixels_with_perspective(orientation):
    pixels = np.random.default_rng(5).integers(0, 256, (640, 720, 3), dtype=np.uint8)
    corners = [[50, 40], [670, 90], [610, 610], [100, 590]]
    with Image.fromarray(pixels) as source:
        original = source.tobytes()
        expected = extract_photo_squares(source, corners, orientation)
        with rectify_board(source, corners) as board:
            squares = split_squares(board)
        try:
            cells = squares if orientation == 'white-bottom' else [row[::-1] for row in squares[::-1]]
            actual = np.stack([np.asarray(cell) for row in cells for cell in row])
            assert actual.shape == (64, 64, 64, 3)
            assert np.array_equal(actual, expected)
            assert source.tobytes() == original
        finally:
            for row in squares:
                for cell in row:
                    cell.close()


@pytest.mark.parametrize('corners', [
    [[-1, 0], [512, 0], [512, 512], [0, 512]],
    [[0, 0], [513, 0], [512, 512], [0, 512]],
    [[0, 0], [512, 512], [512, 0], [0, 512]],
    [[0, 0], [0, 512], [512, 512], [512, 0]],
    [[0, 0], [512, 0], [float('nan'), 512], [0, 512]],
    [[0, 0]] * 4,
])
def test_rejects_invalid_geometry_without_padding(corners):
    with Image.new('RGB', (512, 512)) as source, pytest.raises(ValueError):
        rectify_board(source, corners)


@pytest.mark.parametrize('view,expected', [
    ('white-bottom', 'R7/8/8/8/8/8/8/7k'),
    ('black-bottom', 'k7/8/8/8/8/8/8/7R'),
])
def test_photo_pipeline_orientation_and_owned_images(tmp_path, monkeypatch, view, expected):
    pytest.importorskip('torch')
    from boardsnap import neural
    path = tmp_path / 'unrelated.png'
    with Image.new('RGB', (512, 512)) as source:
        source.paste((4, 0, 0), (0, 0, 64, 64))
        source.paste((12, 0, 0), (448, 448, 512, 512))
        source.save(path)
    monkeypatch.setattr(neural.NeuralClassifier, '__init__', lambda self, path: None)
    monkeypatch.setattr(neural.NeuralClassifier, 'predict_ids', lambda self, images: images[:, 32, 32, 0])
    monkeypatch.setattr(neural, 'detect_photo_board', lambda _: BoardQuadrilateral(((0, 0), (512, 0), (512, 512), (0, 512))))
    monkeypatch.setattr(neural, 'detect_board', lambda _: pytest.fail('Digital detector must not run'))
    monkeypatch.setattr(neural, 'detect_digital_orientation', lambda _: pytest.fail('Explicit view must bypass coordinates'))
    # The pipeline must close every square after inference.
    seen = []
    original = neural.split_squares
    def split(image):
        squares = original(image)
        seen.extend(cell for row in squares for cell in row)
        return squares
    monkeypatch.setattr(neural, 'split_squares', split)
    monkeypatch.setenv('BOARDSNAP_MODEL', 'configured.pt')
    assert recognize_image(path, input_type='photo', orientation=view) == {'piecePlacement': expected}
    assert len(seen) == 64
    for cell in seen:
        with pytest.raises(ValueError):
            cell.getpixel((0, 0))


@pytest.mark.parametrize('options', [
    {'input_type': 'invalid'}, {'input_type': 'photo'},
    {'input_type': 'photo', 'orientation': 'white-bottom', 'profile': 'lichess-cburnett-brown-v1'},
])
def test_invalid_configuration_fails_before_io(options):
    with pytest.raises(ValueError):
        recognize_image('missing.png', **options)


def test_photo_requires_explicit_model_configuration(monkeypatch, capsys):
    monkeypatch.delenv('BOARDSNAP_MODEL', raising=False)
    with pytest.raises(ClassificationError, match='require a model'):
        recognize_image('missing.png', input_type='photo', orientation='white-bottom')
    assert cli.main(['missing.png', '--input-type', 'photo', '--orientation', 'white-bottom']) == 1
    output = capsys.readouterr()
    assert json.loads(output.out)['error']['code'] == 'PROCESSING_FAILED'
    assert output.err == ''


@pytest.mark.parametrize('args', [[], ['--orientation', 'auto'], ['--orientation', 'white-bottom', '--profile', 'lichess-cburnett-brown-v1']])
def test_photo_cli_rejects_ambiguous_configuration(args, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(['missing.png', '--input-type', 'photo', *args])
    assert error.value.code == 2
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('failure', [False, True])
def test_photo_cli_routing_json_and_diagnostics(monkeypatch, capsys, failure):
    def recognize(path, **options):
        assert options == {'input_type': 'photo', 'orientation': 'black-bottom', 'model': 'model.pt'}
        print('diagnostic')
        if failure:
            raise BoardDetectionError('BOARD_NOT_FOUND', 'No complete grid.')
        return {'piecePlacement': 'k7/8/8/8/8/8/8/7R'}
    monkeypatch.setattr(cli, 'recognize_image', recognize)
    assert cli.main(['photo.jpg', '--input-type', 'photo', '--model', 'model.pt', '--orientation', 'black-bottom']) == int(failure)
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert output.out == json.dumps(result) + '\n'
    assert set(result) == ({'error'} if failure else {'piecePlacement'})
    assert output.err == 'diagnostic\n'


@pytest.mark.parametrize('failure,code', [('missing', 'INPUT_READ_ERROR'), ('corrupt', 'INVALID_IMAGE'), ('plain', 'BOARD_NOT_FOUND')])
def test_photo_input_errors_reach_cli(tmp_path, monkeypatch, capsys, failure, code):
    pytest.importorskip('torch')
    from boardsnap import neural
    monkeypatch.setattr(neural, 'load_model', lambda _: (None, {}))
    path = tmp_path / 'input.png'
    if failure == 'corrupt':
        path.write_bytes(b'invalid png')
    elif failure == 'plain':
        with Image.new('RGB', (512, 512), 'white') as image:
            image.save(path)
    assert cli.main([str(path), '--input-type', 'photo', '--model', 'test.pt', '--orientation', 'white-bottom']) == 1
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result['error']['code'] == code
    assert output.out == json.dumps(result) + '\n' and output.err == ''


def test_invalid_photo_model_is_structured(tmp_path, capsys):
    pytest.importorskip('torch')
    assert cli.main(['photo.png', '--input-type', 'photo', '--model', str(tmp_path / 'missing.pt'),
                     '--orientation', 'white-bottom']) == 1
    output = capsys.readouterr()
    assert json.loads(output.out)['error']['code'] == 'PROCESSING_FAILED'
    assert output.err == ''


@pytest.mark.parametrize('case', ['final', 'training', 'stale-detector', 'missing-records'])
def test_photo_comparison_rejects_unreserved_scope_or_stale_geometry(tmp_path, case):
    pytest.importorskip('torch')
    from tools.evaluate_photo_pipeline import compare
    from tools.evaluate_photo_detection import DETECTOR, digest
    manifest = tmp_path / 'manifest.json'
    detection = tmp_path / 'detection.json'
    data = {'independentFinalEvaluation': case == 'final',
            'samples': [{'id': 'x', 'split': 'training' if case == 'training' else 'validation'}]}
    manifest.write_text(json.dumps(data))
    report = {'manifestSha256': digest(manifest), 'detectorSha256': digest(DETECTOR), 'records': []}
    if case == 'stale-detector':
        report['detectorSha256'] = 'changed'
    detection.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        compare(manifest, detection, tmp_path / 'never-load-model.pt')
