"""Training inventory must preserve partitions and distinguish actual mark coverage."""
import json

import pytest

from tools.inventory_training_coverage import cell_features, finish, new_stat, record, training_rows
from tools.build_square_dataset import square_labels
from tools.neural_data import digest
from tools.position_dataset import LABELS

pytestmark = pytest.mark.unit


def arrow(start, end):
    return {'kind':'arrow', 'from':start, 'to':end, 'path':'straight',
            'width':.14, 'rgba':[30,160,65,192]}


def test_mark_tags_use_canonical_coordinates_for_black_bottom():
    features = cell_features({'orientation':'black-bottom', 'marks':[
        arrow('a8','c8'), {'kind':'circle','squares':['c8'], 'rgba':[30,160,65,192]}]})
    assert 'arrow-start' in features[0]
    assert 'arrow-tip' in features[2]
    assert 'arrow-with-other-mark' in features[2]
    assert not features[63]


def test_crossing_requires_overlap_pixels_not_just_shared_square():
    features = cell_features({'marks':[arrow('b4','f4'),arrow('d6','d2')]})
    assert 'arrow-crossing' in features[35]  # d4
    assert 'arrow-crossing' not in features[33]  # b4
    features = cell_features({'marks':[arrow('a8','b8'),arrow('b7','b8')]})
    # Tips meet at b8: shared arrow pixels, not a board-level scenario guess.
    assert 'arrow-crossing' in features[1]


def test_photo_board_condition_does_not_mark_all_cells_or_imply_clean():
    assert all(not x for x in cell_features({'conditions':['arrows','wood-texture']}))
    assert all(not x for x in cell_features({}))
    assert all('clean-control' in x for x in cell_features({'conditions':['clean']}))


def test_stats_separate_occurrences_from_groups_and_class_colors():
    row = {'arraySha256':'archive','positionId':'pos','groupId':'group', 'image':'img',
           'array':'x.npz','cells':square_labels('8/8/8/8/8/8/8/P7','white-bottom')}
    stat = new_stat()
    record(stat,row,[0,56],{0})
    record(stat,row,[0,56],{0})
    summary=finish(stat)
    assert summary['squares']==4 and summary['uniqueBoardArchives']==1
    assert summary['groups']==1 and summary['emptySquares']==2
    assert summary['byClassAndSquareColor']=={'P|dark':2,'empty|light':2}
    assert summary['cellsRetainedByExistingTrainingSelector']==2


def test_loader_skips_reserved_annotations_and_detects_changed_index(tmp_path):
    row={'split':'training','status':'ok','piecePlacement':'8/8/8/8/8/8/8/8',
         'orientation':'white-bottom','cells':square_labels('8/8/8/8/8/8/8/8','white-bottom')}
    index=tmp_path/'verified.jsonl'
    index.write_text('\n'.join(json.dumps(r) for r in [row,{'split':'evaluation'}, {'split':'validation'}]))
    meta={'complete':True,'classOrder':list(LABELS),'indexes':{'verified':{'path':index.name,'sha256':digest(index)}}}
    (tmp_path/'dataset.json').write_text(json.dumps(meta))
    assert training_rows(tmp_path)[0]==[row]
    index.write_text(index.read_text()+'\n')
    with pytest.raises(ValueError,match='changed'):
        training_rows(tmp_path)
