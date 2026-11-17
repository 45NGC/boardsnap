"""Targeted training retains whole groups and rejects validation overlap."""

from copy import deepcopy
import pytest

pytest.importorskip('torch')
from tools.train_targeted_photos import check_additions

pytestmark = pytest.mark.unit


def rows():
    old = {'split': 'validation', 'groupId': 'held-group', 'sha256': 'held-image',
           'piecePlacement': 'k7/8/8/8/8/8/8/7K', 'positionId': 'held-position',
           'configurationId': 'old', 'orientation': 'white-bottom'}
    new = {'split': 'development', 'groupId': 'new-group', 'sha256': 'new-image',
           'piecePlacement': 'k7/8/8/8/8/8/P7/7K', 'positionId': 'new-position',
           'configurationId': 'new', 'orientation': 'white-bottom', 'status': 'ok'}
    return old, new


def test_independent_reviewed_additions_do_not_mutate_old_rows():
    old, new = rows()
    snapshot = deepcopy((old, new))
    check_additions([old], [new])
    assert (old, new) == snapshot


@pytest.mark.parametrize('change', ['group', 'pixels', 'position', 'reflection', 'split', 'duplicate'])
def test_reject_invalid_training_additions(change):
    old, new = rows()
    if change == 'group': new['groupId'] = old['groupId']
    if change == 'pixels': new['sha256'] = old['sha256']
    if change == 'position': new['piecePlacement'] = old['piecePlacement']
    if change == 'reflection': new['piecePlacement'] = '7k/8/8/8/8/8/8/K7'
    if change == 'split': new['split'] = 'validation'
    if change == 'duplicate':
        new.update({k: old[k] for k in ('positionId', 'configurationId', 'orientation')})
    with pytest.raises(ValueError):
        check_additions([old], [new])
