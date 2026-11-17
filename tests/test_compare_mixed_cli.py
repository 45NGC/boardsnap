"""CLI comparison must validate bytes and detect trades hidden by totals."""
import json
import subprocess

import pytest

from tools.compare_mixed_cli import check_contract, paired_summary


def process(result, code=0, stderr=''):
    return subprocess.CompletedProcess([],code,json.dumps(result)+'\n',stderr)


def test_success_and_structured_error_contract():
    assert check_contract(process({'piecePlacement':'8/8/8/8/8/8/8/8'}))
    assert check_contract(process({'error':{'code':'BOARD_NOT_FOUND','message':'Missing board.'}},1))


@pytest.mark.parametrize('result,code,stderr',[
    ({'piecePlacement':'8/8/8/8/8/8/8/8','confidence':1},0,''),
    ({'piecePlacement':'8/8/8/8/8/8/8/8'},1,''),
    ({'piecePlacement':'8/8/8/8/8/8/8/8'},0,'debug'),
    ({'error':{'code':'x'}},1,''),
])
def test_contract_violations_rejected(result,code,stderr):
    with pytest.raises(ValueError):check_contract(process(result,code,stderr))


def test_equal_totals_do_not_hide_lost_boards_or_detection_errors():
    correct={'piecePlacement':'8/8/8/8/8/8/8/8'}
    wrong={'piecePlacement':'p7/8/8/8/8/8/8/8'}
    error={'error':{'code':'BOARD_NOT_FOUND','message':'Missing.'}}
    rows=[{'id':'a','expected':correct['piecePlacement'],'baseline':correct,'candidate':wrong},
          {'id':'b','expected':correct['piecePlacement'],'baseline':wrong,'candidate':correct},
          {'id':'c','expected':correct['piecePlacement'],'baseline':error,'candidate':error}]
    result=paired_summary(rows)
    assert result['baseline']['images']==3 and result['baseline']['detected']==2
    assert result['baseline']['exactBoards']==result['candidate']['exactBoards']==1
    assert result['lostExactBoards']==['a'] and result['gainedExactBoards']==['b']
