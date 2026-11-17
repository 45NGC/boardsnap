"""Exercise runner mechanics on tiny synthetic data, never the real training corpus."""
from copy import deepcopy

import numpy as np
import pytest
import torch
from torch import nn

from tools.train_mixed import choose_best, run_epochs, teacher_cache, teacher_mask_for, validation_predictions

pytestmark=pytest.mark.unit


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__();self.linear=nn.Linear(3,13)

    def forward(self,x):
        return self.linear(x.mean(dim=(-1,-2)))


def config():
    return {'seed':17,'epochs':3,'batchSize':13,'learningRate':.00002,'weightDecay':.0001,
            'threads':1,'distillationTemperature':2,'distillationWeight':1}


def data():
    rng=np.random.default_rng(33)
    return rng.integers(0,256,(26,64,64,3),dtype=np.uint8),np.tile(np.arange(13,dtype=np.int64),2)


def assessment(safe=True,rank=None):
    return {'safeCheckpoint':safe,'accuracyAccepted':False,'rankingKey':rank or [1,1.,64,1,64],
            'domains':{d:{'candidate':{'exactBoards':1,'boards':1}} for d in ('phone','digital')}}


def test_only_safe_epochs_rank_and_ties_keep_earliest():
    best={'epoch':1,'assessment':assessment()}
    assert not choose_best(None,assessment(False),1)
    assert choose_best(None,assessment(),1)
    assert not choose_best(best,assessment(),2)
    assert choose_best(best,assessment(rank=[2,1.,128,1,64]),2)


def test_resume_matches_uninterrupted_weights_optimizer_and_selection(tmp_path):
    torch.manual_seed(42);model=TinyModel();initial=deepcopy(model.state_dict())
    train=data();mask=np.array([True]*13+[False]*13)
    targets=np.full((26,13),1/13,np.float32);targets[~mask]=0
    metadata={'classWeights':[1.]*13,'test':'resume'}
    eval_fn=lambda _: (assessment(),{'test':'synthetic'})
    full=tmp_path/'full';full.mkdir()
    run_epochs(model,train,targets,mask,eval_fn,config(),full,metadata)
    partial=tmp_path/'partial';partial.mkdir();model=TinyModel();model.load_state_dict(initial)
    run_epochs(model,train,targets,mask,eval_fn,config(),partial,metadata,stop_after=1)
    model=TinyModel();model.load_state_dict(initial)
    result=run_epochs(model,train,targets,mask,eval_fn,config(),partial,metadata,resume=True)
    a=torch.load(full/'last.pt',weights_only=True);b=torch.load(partial/'last.pt',weights_only=True)
    assert result['complete'] and result['completedEpochs']==3 and result['selected']['epoch']==1
    for key in a['state_dict']:assert torch.equal(a['state_dict'][key],b['state_dict'][key])
    for i,state in a['optimizer']['state'].items():
        for key,value in state.items():assert torch.equal(value,b['optimizer']['state'][i][key])
    assert torch.equal(a['rngState'],b['rngState'])
    never=lambda _: (_ for _ in ()).throw(AssertionError('Completed epoch repeated'))
    run_epochs(model,train,targets,mask,never,config(),partial,metadata,resume=True)
    with pytest.raises(ValueError,match='changed'):
        run_epochs(model,train,targets,mask,never,config(),partial,dict(metadata,test='changed'),resume=True)


def test_no_eligible_epoch_never_exports_best(tmp_path):
    train=data();mask=np.ones(26,np.bool_);targets=np.full((26,13),1/13,np.float32)
    result=run_epochs(TinyModel(),train,targets,mask,lambda _: (assessment(False),{}),
                      config(),tmp_path,{'classWeights':[1.]*13},stop_after=1)
    assert result['selected'] is None and not (tmp_path/'best.pt').exists()
    assert (tmp_path/'last.pt').exists() and not result['complete']


def test_teacher_masks_only_old_training_data_and_cache_preserves_new_zeros(tmp_path):
    refs=[{'pool':'old','row':{'split':'training'}},{'pool':'new','row':{'split':'training'}}]
    mask=teacher_mask_for(refs,np.array([0]*13+[1]*13),['old'])
    targets=teacher_cache(TinyModel(),data()[0],mask,config(),tmp_path,{'test':'teacher'})
    assert np.allclose(targets[mask].sum(1),1) and not targets[~mask].any()
    class NoInference(TinyModel):
        def forward(self,x):raise AssertionError('Cache recomputed')
    assert np.array_equal(targets,teacher_cache(NoInference(),data()[0],mask,config(),tmp_path,{'test':'teacher'}))
    refs[1]['row']['split']='validation'
    with pytest.raises(ValueError):teacher_mask_for(refs,np.array([0,1]),['old'])


def test_streamed_predictions_keep_full_boards_and_drop_baseline_timings():
    pixels=np.zeros((128,64,64,3),np.uint8)
    baseline={d:[{'image':d,'expected':[0]*64,'predictions':[1]*64,'seconds':99}] for d in ('phone','digital')}
    pred=validation_predictions(TinyModel().eval(),pixels,baseline,17)
    assert all(len(v[0]['predictions'])==64 and 'seconds' not in v[0] for v in pred.values())
