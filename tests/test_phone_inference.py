"""Manual photo inference and validation-only comparison contracts."""

import json

import numpy as np
from PIL import Image
import pytest

pytest.importorskip('torch')
from tools import compare_validation, recognize_photo


@pytest.fixture
def board(tmp_path, monkeypatch):
    pixels = np.zeros((512, 512, 3), np.uint8)
    pixels[:64, :64, 0] = 4  # White rook at photographed top left.
    pixels[-64:, -64:, 0] = 12  # Black king at photographed bottom right.
    path = tmp_path / 'board.png'
    Image.fromarray(pixels).save(path)

    class PixelClassifier:
        def __init__(self, path):
            pass

        def predict_ids(self, images):
            assert images.shape == (64, 64, 64, 3)
            return images[:, 32, 32, 0]

    monkeypatch.setattr(recognize_photo, 'NeuralClassifier', PixelClassifier)
    return path


@pytest.mark.parametrize('orientation,placement', [
    ('white-bottom', 'R7/8/8/8/8/8/8/7k'),
    ('black-bottom', 'k7/8/8/8/8/8/8/7R'),
])
def test_manual_corners_and_rectified_views_agree(board, orientation, placement):
    expected = {'piecePlacement': placement}
    assert recognize_photo.recognize_photo(board, 'unused', orientation=orientation, rectified=True) == expected
    assert recognize_photo.recognize_photo(board, 'unused', orientation=orientation,
        corners=[[0, 0], [512, 0], [512, 512], [0, 512]]) == expected


def test_photo_cli_json_and_missing_file(board, capsys):
    assert recognize_photo.main([str(board), '--model', 'unused', '--orientation', 'white-bottom', '--rectified']) == 0
    out = capsys.readouterr()
    assert json.loads(out.out) == {'piecePlacement': 'R7/8/8/8/8/8/8/7k'}
    assert not out.err
    assert recognize_photo.main([str(board.parent / 'missing.jpg'), '--model', 'unused',
                                 '--orientation', 'white-bottom', '--rectified']) == 1
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'INPUT_READ_ERROR'


def test_photo_cli_rejects_invalid_corners_and_rectified_aspect(board, capsys):
    assert recognize_photo.main([str(board), '--model', 'unused', '--orientation', 'black-bottom',
                                 '--corners', '0', '0', '512', '0', '512', '999', '0', '512']) == 1
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'INVALID_GEOMETRY'
    Image.new('RGB', (512, 400)).save(board)
    with pytest.raises(ValueError, match='square'):
        recognize_photo.recognize_photo(board, 'unused', orientation='white-bottom', rectified=True)


def test_validation_pairing_counts_losses_even_with_equal_totals():
    base = [{'image': 'a', 'expected': [1], 'predictions': [1]},
            {'image': 'b', 'expected': [2], 'predictions': [1]}]
    new = [{'image': 'a', 'expected': [1], 'predictions': [2]},
           {'image': 'b', 'expected': [2], 'predictions': [2]}]
    assert compare_validation.paired_changes(base, new) == {'gainedExactBoards': ['b'], 'lostExactBoards': ['a']}
    with pytest.raises(ValueError, match='same ordered'):
        compare_validation.paired_changes(base, new[::-1])


def test_comparison_opens_validation_arrays_only(tmp_path, monkeypatch):
    rows = [dict(split=split, image=split, positionId=split, groupId=split,
                 orientation='white-bottom', configurationId='test')
            for split in ('training', 'validation', 'evaluation')]
    monkeypatch.setattr(compare_validation, 'read_index', lambda _: ({'datasetId': 'test',
        'indexes': {'verified': {'sha256': 'test'}}}, rows))
    monkeypatch.setattr(compare_validation, 'digest', lambda _: 'test')
    calls = []

    def load_board(_, row):
        assert row['split'] == 'validation'
        calls.append(row['image'])
        return np.zeros((64, 64, 64, 3), np.uint8), np.zeros(64, np.int64)

    class EmptyClassifier:
        def __init__(self, path):
            pass

        def predict_ids(self, images):
            return np.zeros(64, np.int64)

    monkeypatch.setattr(compare_validation, 'load_board', load_board)
    monkeypatch.setattr(compare_validation, 'NeuralClassifier', EmptyClassifier)
    result = compare_validation.compare(tmp_path, tmp_path / 'a', tmp_path / 'b')
    assert calls == ['validation', 'validation']  # warmup + paired measurement
    assert result['results']['candidate']['all']['exactBoards'] == 1
    assert result['paired'] == {'gainedExactBoards': [], 'lostExactBoards': []}
