"""Quality thresholds must reject regressions hidden by aggregate improvements."""
from copy import deepcopy

import pytest

from tools.mixed_training_policy import assess_accuracy, metrics

pytestmark=pytest.mark.unit


def record(name,wrong=None,expected=None,condition='clean'):
    target=expected or [0]*64
    predictions=target.copy()
    for index,value in (wrong or {}).items():predictions[index]=value
    return {'image':name,'expected':target,'predictions':predictions,
            'conditions':[condition], 'category':'test', 'orientation':'white-bottom',
            'appearance':'same', 'background':'plain', 'configurationId':'same'}


def baseline():
    return {'phone':[record('good'),record('bad',{0:1}),record('also-bad',{0:1,1:1})],
            'digital':[record('digital')]}


def improved():
    old=baseline();new=deepcopy(old);new['phone'][1]['predictions']=[0]*64
    return old,new


def test_identical_reference_is_safe_but_not_an_improvement():
    result=assess_accuracy(baseline(),baseline())
    assert result['safeCheckpoint'] and not result['accuracyAccepted']
    assert result['rankingKey'] is not None


def test_improvement_does_not_imply_release_or_missing_performance_pass():
    old,new=improved();result=assess_accuracy(old,new)
    assert result['accuracyAccepted']
    assert not result['promotionAllowed'] and result['pending']


def test_more_exact_boards_cannot_hide_loss_of_an_old_control():
    old,new=improved();new['phone'][0]['predictions'][0]=1
    new['phone'][2]['predictions']=[0]*64
    result=assess_accuracy(old,new)
    assert not result['safeCheckpoint'] and result['rankingKey'] is None
    assert result['domains']['phone']['lostExactBoards']==['good']


def test_photo_gain_cannot_compensate_for_digital_regression():
    old,new=improved();new['digital'][0]['predictions'][0]=12
    assert not assess_accuracy(old,new)['accuracyAccepted']


def test_false_pieces_and_missed_pieces_are_counted_separately():
    row=record('errors',{0:1,1:0},[0,7]+[0]*62)
    m=metrics([row]);assert m['falsePieces']==1 and m['missedPieces']==1
    assert m['correctSquares']==62


def test_stratum_loss_on_already_wrong_board_blocks_acceptance():
    old,new=improved()
    old['phone'][2]['conditions']=['arrow'];new['phone'][2]['conditions']=['fake']
    new['phone'][2]['predictions'][2]=1
    result=assess_accuracy(old,new)
    # Overall false-piece count is unchanged; frozen arrow grouping still detects harm.
    assert result['domains']['phone']['candidate']['falsePieces']==result['domains']['phone']['baseline']['falsePieces']
    assert result['domains']['phone']['stratumRegressions']
    assert not result['accuracyAccepted']


def test_class_recall_loss_cannot_hide_behind_net_square_gain():
    old,new=improved()
    for collection in (old,new):
        collection['phone'][2]['expected'][3]=2
        collection['phone'][2]['predictions'][3]=2
    new['phone'][2]['predictions'][3]=3
    result=assess_accuracy(old,new)
    assert any('class recall N' in r for r in result['reasons'])


def test_invalid_records_and_changed_labels_fail_closed():
    old,new=improved();new['phone'][0]['expected'][0]=1
    with pytest.raises(ValueError,match='labels'):assess_accuracy(old,new)
    with pytest.raises(ValueError):metrics([record('same'),record('same')])
    row=record('bad');row['predictions'][0]=13
    with pytest.raises(ValueError):metrics([row])
    with pytest.raises(ValueError):assess_accuracy(baseline(),baseline(),minimum_photo_gain=0)
