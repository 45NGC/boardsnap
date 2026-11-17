"""Leakage guards, proportional draws and immutable prepared pixel data."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from tools.build_square_dataset import square_labels
from tools.neural_data import digest
from tools.position_dataset import LABELS
from tools.prepare_mixed_training import (
    audit_overlap, load_prepared_epoch, materialize, prepare, sample_epoch,
)

pytestmark = pytest.mark.unit


def row(placement='8/8/8/8/8/8/8/P7', split='training', group='train', **extra):
    return dict(piecePlacement=placement,split=split,groupId=group,positionId=group,
                image=group+'.png',sha256=group,**extra)


@pytest.mark.parametrize('field,value',[
    ('groupId','held'),('positionId','held'),('sha256','held'),
    ('originalSha256','held'),('pixelSha256','pixels'),
    ('source',{'platform':'chesscom','gameId':'123'}),
    ('piecePlacement','pp6/8/8/8/8/8/8/8'), # rotation + swapped colors
])
def test_leakage_in_any_identity_is_rejected(field,value):
    held=row('8/8/8/8/8/8/8/PP6','validation','held',pixelSha256='pixels',
             source={'platform':'chesscom','gameId':'123'})
    training=row(); training[field]=value
    assert audit_overlap([training],[held])


def test_unknown_source_is_not_a_conflict_or_proof_of_independence():
    assert audit_overlap([row(source={})],[row('8/8/8/8/8/8/8/PP6','validation','held',source={})])==[]
    with pytest.raises(ValueError):
        audit_overlap([row(split='validation')],[])


def boards():
    return [{'pool':pool,'eligibleIndices':[0,1,2,3],
             'row':row(group=group,configurationId=str(i))}
            for pool in ('a','b') for group in ('g1','g2') for i in range(2)]


def test_exact_quotas_reproducibility_balanced_groups_and_changed_epoch():
    refs=boards(); quotas={'a':40,'b':24}
    first=sample_epoch(refs,quotas,17)
    assert np.array_equal(first,sample_epoch(refs,quotas,17))
    assert not np.array_equal(first,sample_epoch(refs,quotas,17,1))
    assert Counter(refs[int(i)]['pool'] for i,c in first)==quotas
    for pool,total in quotas.items():
        counts=Counter(refs[int(i)]['row']['groupId'] for i,c in first if refs[int(i)]['pool']==pool)
        assert counts=={'g1':total//2,'g2':total//2}
    assert set(first[:,1])=={0,1,2,3}
    refs[0]['row']['split']='validation'
    with pytest.raises(ValueError):sample_epoch(refs,quotas,17)


def fixture_plan(root):
    name='phone-targeted-training-v1'
    source=root/'.cache'/name;source.mkdir(parents=True)
    records=[]
    for i in range(3):
        placement='8/8/8/8/8/8/8/'+('P'*(i+1))+str(7-i)
        r=row(placement,'validation' if i==2 else 'training',f'g{i}',
              configurationId=f'c{i}',photoId=f'photo{i}',orientation='white-bottom',status='ok',
              trainingAssignment='targeted',appearanceGroup='thin')
        r['cells']=square_labels(placement,'white-bottom')
        r['array']=f'{i}.npz'
        pixels=np.full((64,64,64,3),i+10,np.uint8)
        np.savez_compressed(source/r['array'],images=pixels,
                            class_ids=np.array([c['classId'] for c in r['cells']],np.uint8))
        r['arraySha256']=digest(source/r['array']); records.append(r)
    index=source/'verified.jsonl';index.write_text(''.join(json.dumps(r)+'\n' for r in records))
    meta=source/'dataset.json';meta.write_text(json.dumps({'complete':True,'classOrder':list(LABELS),
        'preprocessing':{'squareSize':64,'colorMode':'RGB'},
        'indexes':{'verified':{'path':index.name,'sha256':digest(index)}}}))
    background=root/'backgrounds.json';background.write_text('{"samples":[]}')
    return {'datasetId':'test-mix','datasets':[name],'validationDatasets':[name],
            'backgroundReview':'backgrounds.json','seed':42,'poolQuotas':{'photo-targeted':128},
            'inputs':[{'path':str(p.relative_to(root)),'sha256':digest(p)} for p in (index,meta,background)],
            'limitations':['Unknown sources remain unknown.']}, records


def test_prepare_roundtrip_keeps_pixels_labels_and_validation_then_detects_tampering(tmp_path):
    plan,rows=fixture_plan(tmp_path);dest=tmp_path/'.cache/mixed'
    result=prepare(plan,dest,root=tmp_path)
    assert result['audit']['observedConflicts']==[]
    assert result['audit']['validationBoards']==1
    assert result['trainingRun'] is False
    saved=json.loads((dest/'validation.jsonl').read_text())
    assert saved['row']==rows[2]
    images,labels=load_prepared_epoch(dest,root=tmp_path)
    assert images.shape==(128,64,64,3) and labels.shape==(128,)
    with np.load(dest/'sampling-epoch-000.npz') as sample:
        for offset,(b,c) in enumerate(zip(sample['board_indices'],sample['cell_indices'])):
            assert (images[offset]==int(b)+10).all()
            assert labels[offset]==rows[int(b)]['cells'][int(c)]['classId']
    with pytest.raises(ValueError,match='preserved'):prepare(plan,dest,root=tmp_path)
    del images,labels
    with (dest/'training-labels.npy').open('ab') as stream:stream.write(b'tamper')
    with pytest.raises(ValueError,match='artifact'):load_prepared_epoch(dest,root=tmp_path)


def test_changed_source_or_nontraining_materialization_fails(tmp_path):
    plan,_=fixture_plan(tmp_path)
    (tmp_path/'backgrounds.json').write_text('changed')
    with pytest.raises(ValueError,match='frozen'):prepare(plan,tmp_path/'.cache/mixed',root=tmp_path)
    assert not (tmp_path/'.cache/mixed').exists()


def test_pixel_overlap_blocks_assembly_even_with_different_metadata(tmp_path):
    plan,rows=fixture_plan(tmp_path)
    source=tmp_path/'.cache/phone-targeted-training-v1'
    # Simulate a mislabeled duplicate: distinct FEN/source/group and ZIP hash.
    np.savez_compressed(source/rows[0]['array'],images=np.full((64,64,64,3),12,np.uint8),
                        class_ids=np.array([c['classId'] for c in rows[0]['cells']],np.uint8))
    rows[0]['arraySha256']=digest(source/rows[0]['array'])
    index=source/'verified.jsonl';index.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    meta=source/'dataset.json';m=json.loads(meta.read_text());m['indexes']['verified']['sha256']=digest(index)
    meta.write_text(json.dumps(m))
    for entry in plan['inputs']:entry['sha256']=digest(tmp_path/entry['path'])
    with pytest.raises(ValueError,match='pixel overlap'):
        prepare(plan,tmp_path/'.cache/mixed',root=tmp_path)
    assert not (tmp_path/'.cache/mixed').exists()


def test_materialization_rejects_reserved_row(tmp_path):
    ref={'row':row(split='validation'),'eligibleIndices':[0]}
    with pytest.raises(ValueError,match='held-out'):
        materialize([ref],np.array([[0,0]]),tmp_path,tmp_path)
