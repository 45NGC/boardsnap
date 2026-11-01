"""Guard bounded robustness experiments against leakage and hidden regressions."""

import numpy as np
import pytest

pytest.importorskip('torch')
from tools.train_phone_robustness import augment_training, train
from tools.evaluate_photo_resampling import acceptance, cells


def test_augmentation_is_deterministic_nonmutating_and_complete():
    source = np.full((128, 64, 64, 3), 120, np.uint8)
    before = source.copy()
    result = augment_training(source, 31)
    assert result.shape == source.shape and result.dtype == source.dtype
    assert np.array_equal(source, before)
    assert np.array_equal(result, augment_training(source, 31))
    assert not np.array_equal(result, augment_training(source, 32))
    assert np.array_equal(result[0], result[63])  # board-wide capture parameters
    assert not np.array_equal(result[0], result[64])


@pytest.mark.parametrize('images', [np.zeros((63, 64, 64, 3), np.uint8), np.zeros((64, 64, 64, 3), float)])
def test_augmentation_rejects_partial_boards_and_wrong_dtype(images):
    with pytest.raises(ValueError):
        augment_training(images, 1)


def test_equal_totals_do_not_hide_lost_boards():
    result = acceptance([{'id': 'a', 'expected': [1], 'baseline': [1], 'predictions': [0]},
                         {'id': 'b', 'expected': [1], 'baseline': [0], 'predictions': [1]}])
    assert result['candidateExact'] == result['baselineExact'] == 1
    assert result['lost'] == ['a'] and result['gained'] == ['b'] and not result['passes']


def test_gain_without_regressions_passes_and_no_change_does_not():
    assert acceptance([{'id': 'a', 'expected': [1], 'baseline': [0], 'predictions': [1]}])['passes']
    assert not acceptance([{'id': 'a', 'expected': [1], 'baseline': [1], 'predictions': [1]}])['passes']
    assert not acceptance([])['passes']


def test_cells_reverse_order_without_rotating_glyphs():
    pixels = np.zeros((512, 512, 3), np.uint8)
    pixels[2, 3] = (1, 2, 3)
    pixels[-62, -61] = (4, 5, 6)
    white, black = cells(pixels, 'white-bottom'), cells(pixels, 'black-bottom')
    assert np.array_equal(white, black[::-1])
    assert black[-1, 2, 3].tolist() == [1, 2, 3]
    with pytest.raises(ValueError):
        cells(pixels, 'auto')


def test_training_rejects_evaluation_rows_before_loading_pixels(tmp_path, monkeypatch):
    from tools import train_phone_robustness as module
    monkeypatch.setattr(module, 'read_index', lambda _: ({'datasetId': 'phone-training-v1'}, [{'split': 'evaluation'}]))
    monkeypatch.setattr(module, 'load_split', lambda *a: pytest.fail('Do not load reserved arrays'))
    with pytest.raises(ValueError):
        train(tmp_path, tmp_path/'baseline.pt', tmp_path/'run')
