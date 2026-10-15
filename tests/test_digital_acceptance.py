"""Acceptance evidence must be complete, independent, immutable and fail closed."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.digital_acceptance import acceptance_gates, metric_gate, readiness
from tools.evaluate_acceptance import evaluate, start_attempt
from tools.prepare_acceptance import write_new
from tools.position_dataset import LABELS

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'data/manifests/digital-acceptance-v1.json').read_text())
pytestmark=pytest.mark.unit


def successful_summary():
    groups={'combination':[c['id'] for c in POLICY['configurations']], 'condition':POLICY['conditions'],
            'layout':POLICY['layouts'],'orientation':['white-bottom','black-bottom'],'platform':['lichess','chesscom']}
    return {'all':{'images':4560,'exactBoardRate':1.0,'classes':{
        label:{'total':1000,'precision':1.0,'recall':1.0} for label in LABELS}},
        'strata':{field:{name:{'images':1000,'exactBoardRate':1.0} for name in names} for field,names in groups.items()},
        'detection':{'missRate':0.0,'withinTwoPixelsRate':1.0},
        'negatives':{'images':240,'falseDetectionRate':0.0},'orientationMappingRate':1.0}


def test_missing_stratum_and_rare_piece_cannot_hide_behind_global_accuracy():
    summary=successful_summary()
    assert all(g['passed'] for g in acceptance_gates(POLICY,summary))
    del summary['strata']['combination']['chesscom-blue-alpha']
    summary['all']['classes']['q']['recall']=0.8
    failed=[g['name'] for g in acceptance_gates(POLICY,summary) if not g['passed']]
    assert 'class/q/recall' in failed
    assert 'combination/chesscom-blue-alpha/exact' in failed


@pytest.mark.parametrize('value',[None,float('nan'),float('inf'),True,'1'])
def test_unmeasured_or_nonfinite_metrics_never_pass(value):
    assert not metric_gate('test',value,0.99)['passed']


def test_detection_orientation_and_cpu_limits_are_separate():
    summary=successful_summary()
    summary['negatives']['falseDetectionRate']=0.02
    summary['detection']['missRate']=0.01
    summary['orientationMappingRate']=0.5
    failed={g['name'] for g in acceptance_gates(POLICY,summary) if not g['passed']}
    assert failed=={'false-detection-rate','detection-miss-rate','explicit-orientation-mapping'}


def test_readiness_reports_actual_regressions_and_does_not_consume_final_data():
    regression=json.loads((ROOT/'data/reports/neural-styles-v2-evaluation.json').read_text())
    benchmark={'modelSha256':POLICY['modelSha256'],'dataRole':'validation',
               'warm':{'samples':40,'p95Milliseconds':200},'coldMilliseconds':2000,'peakRssMiB':400}
    report=readiness(POLICY,regression,benchmark,{'passed':True,'modelSha256':POLICY['modelSha256']})
    failed={g['name']:g['actual'] for g in report['gates'] if not g['passed']}
    assert failed=={'new-regression-board-errors':2,'unresolved-detection-misses':4}
    assert report['ready'] is False and report['finalEvaluationExecuted'] is False


def test_blocked_readiness_is_checked_before_corpus_is_opened(tmp_path,monkeypatch):
    from tools import evaluate_acceptance as module
    policy=tmp_path/'policy.json'; policy.write_text(json.dumps(POLICY))
    monkeypatch.setattr(module,'check_frozen',lambda *_:None)
    def blocked(*args):raise ValueError('readiness failed')
    monkeypatch.setattr(module,'require_ready',blocked)
    with pytest.raises(ValueError,match='readiness failed'):
        evaluate(policy,tmp_path/'missing-plan',tmp_path/'model',tmp_path/'readiness',tmp_path/'missing-corpus',tmp_path/'result')
    assert not (tmp_path/'result').exists()


def test_final_attempt_and_frozen_files_cannot_be_silently_reused(tmp_path):
    start_attempt(tmp_path,'policy','model')
    with pytest.raises(FileExistsError):start_attempt(tmp_path,'policy','model')
    path=tmp_path/'frozen.json'
    write_new(path,{'first':True})
    with pytest.raises(FileExistsError):write_new(path,{'first':False})
    assert json.loads(path.read_text())=={'first':True}


def test_new_candidate_can_freeze_new_policy_without_rewriting_unobserved_plan(tmp_path,monkeypatch):
    pytest.importorskip('chess')
    from tools.prepare_acceptance import main
    plan=tmp_path/'reserved.json'
    original=(ROOT/'data/manifests/digital-acceptance-positions-v1.json').read_bytes()
    plan.write_bytes(original)
    model=tmp_path/'candidate.pt';model.write_bytes(b'new candidate identity')
    policy=tmp_path/'digital-acceptance-v2.json'
    monkeypatch.setattr('sys.argv',['prepare_acceptance','--model',str(model),'--plan',str(plan),
                                  '--policy',str(policy),'--reuse-plan'])
    main()
    assert json.loads(policy.read_text())['policyId']=='digital-acceptance-v2'
    assert plan.read_bytes()==original
    with pytest.raises(ValueError,match='Never overwrite'):main()


def test_new_sources_are_disjoint_and_every_catalogue_pair_has_both_views():
    pytest.importorskip('chess')
    from tools.acceptance_corpus import validate_plan,jobs_for
    plan=json.loads((ROOT/'data/manifests/digital-acceptance-positions-v1.json').read_text())
    validate_plan(plan)
    jobs=jobs_for(plan,POLICY)
    assert len(jobs)==240 and sum(len(j['positionIds'])*len(j['configurations'][0]['orientations']) for j in jobs)==1920
    assert all(set(j['configurations'][0]['orientations'])=={'white-bottom','black-bottom'} for j in jobs)
    changed=deepcopy(plan)
    changed['groups'][0]['source']['sourceId']=json.loads((ROOT/'data/manifests/digital-positions-v1.json').read_text())['groups'][0]['source']['sourceId']
    with pytest.raises(ValueError,match='independent'):validate_plan(changed)


def test_corrupt_model_bundle_is_rejected_before_loading(tmp_path):
    from tools.model_bundle import verify_bundle
    from tools.neural_data import digest
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'schemaVersion':1,'file':'model.pt','sha256':'expected'}))
    (tmp_path/'model.pt').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='manifest differs'):verify_bundle(tmp_path,'wrong')
    with pytest.raises(ValueError,match='checksum mismatch'):verify_bundle(tmp_path,digest(manifest))


def test_consulted_games_cannot_be_reused_by_renaming_corpus_or_ids(tmp_path):
    from tools.acceptance_history import require_unobserved
    plan=json.loads((ROOT/'data/manifests/digital-acceptance-positions-v1.json').read_text())
    history=tmp_path/'reports'
    first=tmp_path/'first'; first.mkdir()
    second=tmp_path/'renamed'; second.mkdir()
    start_attempt(first,'policy','model',plan,history)
    changed=deepcopy(plan)
    changed['groups'][0]['source']['sourceId']='renamed'
    changed['datasetId']='new-name'
    with pytest.raises(ValueError,match='already consulted'):
        start_attempt(second,'other-policy','other-model',changed,history)
    # Even taking different plies from the same source game is not independent.
    changed['positions']=[]
    with pytest.raises(ValueError,match='already consulted'):
        require_unobserved(changed,history)


def test_reserved_plan_can_render_every_required_mark_without_recognition():
    from tools.board_marks import KINDS,mark_plan
    from tools.arrow_marks import CASES,arrow_plan
    plan=json.loads((ROOT/'data/manifests/digital-acceptance-positions-v1.json').read_text())
    for config in POLICY['configurations']:
        for index,group in enumerate(plan['groups']):
            position=[p for p in plan['positions'] if p['groupId']==group['groupId']][index%4]
            for case in (*KINDS,*CASES):
                key=f"acceptance-v1:{config['id']}:{position['positionId']}:{case}"
                marks=arrow_plan(position['piecePlacement'],case,key)[0] if case in CASES else mark_plan(position['piecePlacement'],case,key)
                assert marks is not None,(config['id'],position['positionId'],case)


def test_bundle_roundtrip_preserves_metadata_and_rejects_tampered_notices(tmp_path):
    torch=pytest.importorskip('torch')
    from boardsnap.neural import ARCHITECTURE,CLASSES,PREPROCESSING,SquareNet
    from tools.model_bundle import build_bundle,verify_bundle
    from tools.neural_data import digest
    model=tmp_path/'input.pt'
    metadata={'formatVersion':1,'architecture':ARCHITECTURE,'classOrder':list(CLASSES),
              'preprocessing':PREPROCESSING,'dataVersion':{'datasetId':'unit-test'},'trainingConfig':{'seed':7}}
    torch.save({'metadata':metadata,'state_dict':SquareNet().state_dict()},model)
    policy=deepcopy(POLICY);policy['modelSha256']=digest(model)
    policy_path=tmp_path/'policy.json';policy_path.write_text(json.dumps(policy))
    destination=tmp_path/'bundle'
    report=build_bundle(model,destination,policy_path)
    data=verify_bundle(destination,report['manifestSha256'])
    assert data['metadata']==metadata and data['status']=='candidate-not-accepted'
    rejected=tmp_path/'rejected.json';rejected.write_text(json.dumps({'status':'rejected'}))
    with pytest.raises(ValueError,match='passing evidence'):
        build_bundle(model,tmp_path/'not-published',policy_path,rejected)
    (destination/'LICENSE').write_text('altered')
    with pytest.raises(ValueError,match='notice checksum'):
        verify_bundle(destination,report['manifestSha256'])


def test_accepted_bundle_contains_and_checks_its_passing_report(tmp_path,monkeypatch):
    pytest.importorskip('torch')
    from boardsnap import neural
    from tools.model_bundle import build_bundle,verify_bundle
    from tools.neural_data import digest
    monkeypatch.setattr(neural,'load_model',lambda _: (None,{'test':'metadata'}))
    model=tmp_path/'input.pt';model.write_bytes(b'test double')
    policy=deepcopy(POLICY);policy['modelSha256']=digest(model)
    policy_path=tmp_path/'policy.json';policy_path.write_text(json.dumps(policy))
    result={'status':'accepted','modelSha256':digest(model),'policySha256':digest(policy_path),
            'summary':successful_summary(),'performance':{'warm':{'samples':40,'p95Milliseconds':100},
            'coldMilliseconds':1000,'peakRssMiB':300}}
    report_path=tmp_path/'result.json';report_path.write_text(json.dumps(result))
    destination=tmp_path/'bundle'
    bundle=build_bundle(model,destination,policy_path,report_path)
    assert (destination/'acceptance-report.json').read_bytes()==report_path.read_bytes()
    (destination/'acceptance-report.json').write_text('{}')
    with pytest.raises(ValueError,match='acceptance report checksum'):
        verify_bundle(destination,bundle['manifestSha256'])
