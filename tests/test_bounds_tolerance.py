"""Crop stress tests preserve labels, orientation, and validation provenance."""

from dataclasses import replace

import numpy as np
from PIL import Image
import pytest

from boardsnap.detection import BoardBounds
from tools.bounds_tolerance import SCENARIOS, fixed_training_scenario, perturbed_squares
from tools.build_square_dataset import extract_squares
from tools.evaluate_tolerance import compare_records

pytestmark = pytest.mark.unit


def test_verified_only_regression_does_not_claim_pipeline_results(tmp_path, monkeypatch):
    pytest.importorskip('torch')
    from boardsnap import neural
    from tools import evaluate_marks

    class Classifier:
        def __init__(self, path):
            pass

        def predict_ids(self, pixels):
            return np.zeros(64, dtype=np.int64)

    row = dict(image='control.png', sha256='hash', positionId='p', groupId='g',
               pairId='pair', conditions=['clean'], split='evaluation')
    monkeypatch.setattr(neural, 'NeuralClassifier', Classifier)
    monkeypatch.setattr(evaluate_marks, 'read_index', lambda path: ({'sourceRoot': str(tmp_path)}, [row]))
    monkeypatch.setattr(evaluate_marks, 'digest', lambda path: 'hash')
    monkeypatch.setattr(evaluate_marks, 'load_board', lambda *args: (
        np.zeros((64, 64, 64, 3), np.uint8), np.zeros(64, np.int64)))

    def forbidden(*args, **kwargs):
        pytest.fail('Verified-only measurement must not run detection or reopen screenshots.')

    monkeypatch.setattr(evaluate_marks, 'detect_board', forbidden)
    monkeypatch.setattr(evaluate_marks.Image, 'open', forbidden)
    report = evaluate_marks.evaluate(tmp_path, tmp_path/'a.pt', tmp_path/'b.pt',
                                     'evaluation', verified_only=True)
    assert report['measuredModes'] == ['verified']
    assert not report['pipelineMeasured'] and not report['detectionMeasured']
    assert report['detection'] == report['detectionStrata'] == {}
    assert report['cleanPerformanceMaintained']
    for model in report['results'].values():
        assert set(model) == {'verified'}
        assert model['verified']['all']['exactBoards'] == 1


def board():
    pixels = np.zeros((536, 536, 3), np.uint8)
    for row in range(8):
        for col in range(8):
            pixels[12+row*64:12+(row+1)*64, 12+col*64:12+(col+1)*64] = (row*28, col*28, 100)
            # Asymmetric marker: cell reordering must not rotate piece pixels.
            pixels[15+row*64:19+row*64, 15+col*64:19+col*64] = 255
    return Image.fromarray(pixels), BoardBounds(12, 12, 512, 512)


@pytest.mark.parametrize('orientation', ['white-bottom', 'black-bottom'])
def test_reference_is_identical_to_production_normalization(orientation):
    image, bounds = board()
    before = np.asarray(image).copy()
    pixels, edges = perturbed_squares(image, bounds, orientation, SCENARIOS[0])
    assert np.array_equal(pixels, extract_squares(image, bounds, orientation))
    assert edges == bounds.as_box()
    assert np.array_equal(before, np.asarray(image))
    assert np.all(pixels[:, 3:7, 3:7] == 255)


@pytest.mark.parametrize('scenario', SCENARIOS, ids=lambda s:s.name)
def test_all_variants_have_64_canonical_cells_and_correct_edge_offsets(scenario):
    image, bounds = board()
    white, edges = perturbed_squares(image, bounds, 'white-bottom', scenario)
    black, _ = perturbed_squares(image, bounds, 'black-bottom', scenario)
    assert white.shape == (64, 64, 64, 3) and white.dtype == np.uint8
    assert np.array_equal(white[::-1], black)
    assert edges == tuple(a+b for a,b in zip(bounds.as_box(), scenario.edges))
    for index, cell in enumerate(white):
        assert tuple(cell[32,32]) == (index//8*28, index%8*28, 100)


@pytest.mark.parametrize('edges', [(-1,0,0,0),(0,-1,0,0),(0,0,1,0),(0,0,0,1)])
def test_no_padding_or_silent_clipping(edges):
    image = Image.new('RGB',(512,512))
    with pytest.raises(ValueError, match='leave'):
        perturbed_squares(image, BoardBounds(0,0,512,512), 'white-bottom', replace(SCENARIOS[0],edges=edges))


def test_training_choices_are_stable_and_label_independent():
    row = dict(image='source.png', split='training', piecePlacement='8/8/8/8/8/8/8/8')
    assert fixed_training_scenario(row, 10) == fixed_training_scenario(dict(row,piecePlacement='different'),10)
    assert fixed_training_scenario(row, 10).name != 'reference'
    assert len({fixed_training_scenario(dict(row,image=str(i)),10).name for i in range(100)}) > 10


def test_paired_metrics_do_not_hide_regressions_behind_other_improvements():
    def row(image, scenario, guess):
        return dict(image=image,positionId=image,case='clean',scenario=scenario,
                    expected=[0]*64,predictions=[guess]+[0]*63)
    report = compare_records([row('a','reference',0), row('b','reference',1),
                              row('a','shift',1), row('b','shift',0)])
    assert report['reference']['all']['exactBoards'] == report['shift']['all']['exactBoards'] == 1
    assert report['shift']['previouslyCorrectBoardsLost'] == ['a']
    assert report['shift']['all']['classes']['empty']['total'] == 128


def test_training_sampling_excludes_other_partitions():
    from tools.train_tolerance import selected_for_augmentation
    rows = [dict(image=f'{i}.png',split='training') for i in range(100)]
    assert any(map(selected_for_augmentation,rows))
    for split in ('validation','evaluation'):
        assert not any(selected_for_augmentation(dict(r,split=split)) for r in rows)


def test_edge_boards_get_an_applicable_challenge_without_synthetic_padding():
    from tools.train_tolerance import choose_valid_scenario
    row = dict(image='edge.png',boardBounds={'x':0,'y':0,'width':512,'height':512})
    scenario = choose_valid_scenario(row,(512,512))
    assert scenario.name in ('inset-2','resample-85-bilinear','resample-115-bicubic')


def test_preparation_keeps_original_validation_and_never_loads_evaluation(tmp_path,monkeypatch):
    import json
    from tools import train_tolerance as module
    from tools.neural_data import digest
    image,bounds = board()
    sources = tmp_path/'sources'
    sources.mkdir()
    image.save(sources/'source.png')
    image.save(sources/'validation.png')
    sha = digest(sources/'source.png')
    from tools.build_square_dataset import square_labels
    placement = '8/8/8/8/8/8/8/8'
    base = dict(image='source.png',sha256=sha,positionId='train-pos',groupId='train-game',
                split='training',piecePlacement=placement,orientation='black-bottom',style={},
                boardBounds=dict(x=12,y=12,width=512,height=512),cells=square_labels(placement,'black-bottom'))
    validation = dict(base,image='validation.png',split='validation',positionId='val-pos',groupId='val-game')
    evaluation = dict(base,image='evaluation.png',split='evaluation',positionId='eval-pos',groupId='eval-game')
    extra = dict(base,image='extra.png',sourceImage='source.png',sourceSha256=sha)
    dataset,additional = tmp_path/'base',tmp_path/'extra'
    for root in (dataset,additional):
        root.mkdir()
        (root/'dataset.json').write_text('{}')
    metadata = {'sourceRoot':str(sources),'indexes':{'verified':{'sha256':'test-index'}}}
    monkeypatch.setattr(module,'read_index',lambda root: (metadata,[extra] if root==additional else [base,validation,evaluation]))
    monkeypatch.setattr(module,'selected_for_augmentation',lambda r:r['split']=='training')
    loaded = []
    def load(root,row):
        assert row['split'] != 'evaluation'
        loaded.append(row['split'])
        return np.full((64,64,64,3),42,np.uint8),np.zeros(64,np.int64)
    monkeypatch.setattr(module,'load_board',load)
    cache = tmp_path/'prepared'
    report = module.prepare(dataset,additional,cache)
    assert loaded == ['training','training','validation']
    assert report['originalTrainingSquares'] == 128
    assert report['augmentedTrainingBoards'] == report['originalValidationBoards'] == 1
    assert report['evaluationArraysLoaded'] is False and report['validationUsedForTraining'] is False
    pixels = np.load(cache/'validation-images.npy')
    assert np.all(pixels[:64] == 42)
    assert not np.all(pixels[64:] == 42)
    variants = json.loads((cache/'variants.json').read_text())
    assert [(r['positionId'],r['split']) for r in variants] == [('train-pos','training'),('val-pos','validation')]
    assert module.prepare(dataset,additional,cache) == report
    (cache/'variants.json').write_text('tampered')
    with pytest.raises(ValueError,match='changed'):
        module.prepare(dataset,additional,cache)


def test_inapplicable_crops_are_not_classification_losses():
    reference = dict(image='a',positionId='a',case='clean',scenario='reference',expected=[0]*64,predictions=[0]*64)
    invalid = dict(reference,scenario='shift',predictions=[-1]*64,error='outside image')
    result = compare_records([reference,invalid])['shift']
    assert result['invalidCrops'] == ['a']
    assert result['previouslyCorrectBoardsLost'] == []
    assert result['applicable']['images'] == 0
    assert result['all']['confusionRowsExpectedColumnsPredicted'][0][-1] == 64


def test_validation_gate_requires_paired_preservation_and_improvement():
    from copy import deepcopy
    from tools.evaluate_tolerance import validation_gate
    def row(scenario,guess):
        return dict(image='a',positionId='a',case='clean',scenario=scenario,expected=[0]*64,predictions=[guess]+[0]*63)
    baseline = compare_records([row('reference',0),row('shift',1)])
    candidate = compare_records([row('reference',0),row('shift',0)])
    paired = {'reference':{'baselineCorrectCandidateWrong':[]}}
    gate = validation_gate({'v8':baseline,'candidate':candidate},paired)
    assert gate['passed'] and gate['perturbedExactBoardsGain'] == 1
    assert not validation_gate({'v8':baseline,'candidate':baseline},paired)['passed']
    assert not validation_gate({'v8':baseline,'candidate':candidate},
                               {'reference':{'baselineCorrectCandidateWrong':['a']}})['passed']
    changed = deepcopy(candidate)
    changed['shift']['invalidCrops'] = ['a']
    assert not validation_gate({'v8':baseline,'candidate':changed},paired)['passed']


def test_selection_rejects_exchanged_board_errors_even_when_totals_match():
    pytest.importorskip('torch')
    from tools.select_tolerance import preserves_reference
    baseline = np.ones((2,64),dtype=bool)
    baseline[1,0] = False
    improved = np.ones((2,64),dtype=bool)
    exchanged = np.ones((2,64),dtype=bool)
    exchanged[0,0] = False
    assert preserves_reference(baseline,improved)
    assert preserves_reference(baseline,baseline)
    assert not preserves_reference(baseline,exchanged)
    worse = baseline.copy()
    worse[1,1] = False
    assert not preserves_reference(baseline,worse)


def test_parameter_selection_saves_a_loadable_model_and_excludes_regressing_fractions(tmp_path):
    import json
    torch = pytest.importorskip('torch')
    from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, NeuralClassifier, SquareNet
    from tools.neural_data import digest
    from tools.select_tolerance import select
    torch.set_num_threads(1)
    cache = tmp_path/'cache'
    cache.mkdir()
    np.save(cache/'validation-images.npy',np.zeros((128,64,64,3),np.uint8))
    np.save(cache/'validation-labels.npy',np.zeros(128,np.int64))
    manifest = {'complete':True,'validationUsedForTraining':False,'evaluationArraysLoaded':False,
                'originalValidationBoards':1,
                'files':{p.name:digest(p) for p in cache.iterdir()}}
    (cache/'dataset.json').write_text(json.dumps(manifest))
    data_version = {'preparedDatasetSha256':digest(cache/'dataset.json')}
    model = SquareNet()
    for parameter in model.parameters():
        parameter.data.zero_()
    metadata = {'formatVersion':1,'architecture':ARCHITECTURE,'classOrder':list(CLASSES),
                'preprocessing':PREPROCESSING,'dataVersion':data_version,'trainingConfig':{'seed':1}}
    paths = []
    for name,label in (('baseline',0),('trained',1)):
        root = tmp_path/name
        root.mkdir()
        model.layers[-1].bias.data.zero_()
        model.layers[-1].bias.data[label] = 8
        path = root/'best.pt'
        torch.save({'metadata':metadata,'state_dict':model.state_dict()},path)
        (root/'training.json').write_text(json.dumps({'complete':True,'metadata':metadata,'weightsSha256':digest(path)}))
        paths.append(path)
    run = tmp_path/'selected'
    result = select(cache,*paths,run,threads=1)
    assert result['selected']['trainedFraction'] == 0
    assert result['history'][-1]['referencePreserved'] is False
    assert result['evaluationUsedForSelection'] is False
    assert not NeuralClassifier(run/'best.pt').predict_ids(np.zeros((64,64,64,3),np.uint8)).any()
    (cache/'validation-labels.npy').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Training and selection|pixels/labels changed'):
        select(cache,*paths,tmp_path/'rejected',threads=1)


def test_comparison_cli_returns_failure_when_validation_gate_fails(monkeypatch,tmp_path):
    from tools import evaluate_tolerance as module
    monkeypatch.setattr(module,'evaluate',lambda *args:{'validationGate':{'passed':False}})
    args = ['--dataset',str(tmp_path),'--model','baseline.pt','--model','candidate.pt',
            '--output',str(tmp_path/'report.json')]
    assert module.main(args) == 1
    monkeypatch.setattr(module,'evaluate',lambda *args:{'validationGate':{'passed':True}})
    assert module.main(args) == 0
    monkeypatch.setattr(module,'evaluate',lambda *args:{})
    assert module.main(['--dataset',str(tmp_path),'--model','baseline.pt','--output',str(tmp_path/'baseline.json')]) == 0
