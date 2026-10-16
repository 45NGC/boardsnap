"""Parameter averaging remains a single CPU model selected without regression pixels."""

import json

import numpy as np
import pytest

torch = pytest.importorskip('torch')
from tools.average_neural import average_state, select
from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, SquareNet, load_model

pytestmark = pytest.mark.unit


def test_average_preserves_endpoints_and_does_not_modify_parents():
    left={'weight':torch.tensor([1.,3.])};right={'weight':torch.tensor([5.,7.])}
    assert torch.equal(average_state(left,right,0)['weight'],left['weight'])
    assert torch.equal(average_state(left,right,1)['weight'],right['weight'])
    assert torch.equal(average_state(left,right,.5)['weight'],torch.tensor([3.,5.]))
    assert torch.equal(left['weight'],torch.tensor([1.,3.]))
    with pytest.raises(ValueError):average_state(left,right,float('nan'))
    with pytest.raises(ValueError):average_state(left,{'weight':torch.ones(3)},.5)


def test_selection_reads_only_validation_and_saves_best_not_last(tmp_path,monkeypatch):
    from tools import average_neural
    metadata={'formatVersion':1,'architecture':ARCHITECTURE,'classOrder':list(CLASSES),
              'preprocessing':PREPROCESSING,'dataVersion':{'datasetId':'test'},'trainingConfig':{'seed':7}}
    paths=[]
    for name,value in [('left',0.),('right',1.)]:
        net=SquareNet()
        for parameter in net.parameters():parameter.data.fill_(value)
        path=tmp_path/f'{name}.pt';torch.save({'metadata':metadata,'state_dict':net.state_dict()},path)
        paths.append(path)
    (tmp_path/'dataset.json').write_text('{}')
    monkeypatch.setattr(average_neural,'read_index',lambda _: (
        {'datasetId':'test','indexes':{'verified':{'sha256':'index'}}},
        [{'split':'validation','cohort':'previous'},{'split':'evaluation','cohort':'previous'}]))
    def load(root,rows,split):
        assert split=='validation'
        return np.zeros((64,64,64,3),np.uint8),np.zeros(64,np.int64)
    monkeypatch.setattr(average_neural,'load_split',load)
    def metrics(model,images,labels,size,control_boards):
        assert control_boards.tolist()==[True]
        value=float(next(model.parameters()).detach().flatten()[0])
        return {'controlExactBoards':1,'exactBoards':1,'boards':1,'macroRecall':1.,'loss':abs(value-.5)}
    monkeypatch.setattr(average_neural,'validate',metrics)
    report=select(tmp_path,*paths,tmp_path/'run',threads=1)
    assert report['selected']['rightFraction']==.5
    model,metadata=load_model(tmp_path/'run/best.pt')
    assert float(next(model.parameters()).detach().flatten()[0])==.5
    assert metadata['parameterAverage']['rightFraction']==.5
    assert report['evaluationUsedForSelection'] is False
