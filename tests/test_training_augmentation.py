"""Extra arrow examples cannot move reserved positions into training."""

from copy import deepcopy

import numpy as np
import pytest

from tools.build_arrowhead_training import arrow_to, choose_sources
from tools.board_marks import validate_marks
from tools.position_dataset import LABELS
from tools.training_augmentation import add_training_variants, validate_additions

pytestmark = pytest.mark.unit


def source_row():
    return dict(image='source.png', sha256='source-hash', split='training',
                positionId='position', groupId='game', piecePlacement='8/8/8/8/8/8/8/8',
                orientation='white-bottom', style={'combination': 'test', 'layout': 'lichess-editor'})


def extra_row():
    return dict(source_row(), image='variant.png', sourceImage='source.png',
                sourceSha256='source-hash')


@pytest.mark.parametrize('key,value', [
    ('split', 'evaluation'), ('split', 'validation'), ('sourceImage', 'unknown.png'),
    ('sourceSha256', 'changed'), ('positionId', 'different'), ('groupId', 'different'),
    ('piecePlacement', '8/8/8/8/8/8/8/K7'), ('orientation', 'black-bottom'),
    ('style', {'combination': 'held-out'}),
])
def test_rejects_mislabeled_or_reserved_variants(key, value):
    row = extra_row()
    row[key] = value
    with pytest.raises(ValueError):
        validate_additions([source_row()], [row])


@pytest.mark.parametrize('split', ['validation', 'evaluation'])
def test_relabeling_reserved_source_as_training_is_rejected(split):
    base = dict(source_row(), split=split)
    with pytest.raises(ValueError):
        validate_additions([base], [extra_row()])


def test_additions_load_training_only_and_preserve_base_arrays(tmp_path, monkeypatch):
    from tools import training_augmentation as module
    (tmp_path / 'dataset.json').write_text('{}')
    monkeypatch.setattr(module, 'read_index', lambda _: (
        {'indexes': {'verified': {'sha256': 'index-hash'}}}, [extra_row()]))
    def load(root, rows, split, *, marked_cells_only):
        assert split == 'training'
        assert marked_cells_only is True
        return np.full((2, 64, 64, 3), 123, np.uint8), np.array([1, 2])
    monkeypatch.setattr(module, 'load_split', load)
    base = np.zeros((1, 64, 64, 3), np.uint8), np.array([0])
    combined, evidence = add_training_variants(tmp_path, [source_row()], base, marked_cells_only=True)
    assert combined[1].tolist() == [0, 1, 2]
    assert not base[0].any()
    assert evidence['trainingSquares'] == 2
    assert evidence['validationChanged'] is False
    assert evidence['evaluationArraysLoaded'] is False


def coverage_rows():
    cells = [dict(label=label, background=bg, square=f'{"ab"[b]}{i % 8 + 1}')
             for i, label in enumerate(LABELS) for b, bg in enumerate(('light', 'dark'))]
    return [dict(source_row(), image=f'{view}.png', orientation=view,
                 conditions=['clean'], cells=cells)
            for view in ('white-bottom', 'black-bottom')]


def test_arrow_source_selection_covers_all_classes_and_ignores_reserved_images():
    rows = coverage_rows()
    reserved = [dict(row, split='evaluation', image='reserved-' + row['image']) for row in rows]
    selected = choose_sources(rows + reserved)
    assert len(selected) == 13 * 2 * 2
    assert all(item[2]['split'] == 'training' for item in selected)
    assert selected == choose_sources(list(reversed(rows + reserved)))
    incomplete = deepcopy(rows)
    incomplete[0]['cells'].pop()
    with pytest.raises(ValueError, match='coverage'):
        choose_sources(incomplete)


@pytest.mark.parametrize('target', ['a1', 'a8', 'h1', 'h8', 'd4'])
def test_arrowheads_reach_requested_square_with_valid_deterministic_geometry(target):
    arrow = arrow_to(target, 'seed')
    assert arrow == arrow_to(target, 'seed')
    assert arrow['to'] == target
    assert arrow['from'] != target
    validate_marks([arrow], '8/8/8/8/8/8/8/8')
