"""Offline photographic analysis must retain labels, pairing and validation scope."""

from copy import deepcopy
import json

import pytest

from tools.analyze_phone_classifier import build, digest, metrics, summarize


@pytest.fixture
def inputs():
    expected = [0] * 64
    expected[0], expected[1], expected[63] = 4, 7, 12
    photo = {'id': 'a', 'imagePath': 'a.png', 'imageSha256': 'pixels', 'split': 'validation',
             'groupId': 'one-source', 'source': {'category': 'video', 'gameId': None},
             'conditions': ['perspective', 'arrows'], 'boardCorners': [[0, 0], [512, 0], [512, 512], [0, 512]],
             'label': {'piecePlacement': 'Rp6/8/8/8/8/8/8/7k', 'orientation': 'black-bottom'},
             'captureMetadata': {'cameraModel': 'test'}}
    row = {'image': 'a.png', 'positionId': 'p1', 'groupId': 'one-source', 'category': 'video',
           'orientation': 'black-bottom', 'conditions': photo['conditions'], 'expected': expected}
    old, new = expected.copy(), expected.copy()
    old[0] = 0  # Recover rook on light a8.
    new[1] = 0  # Lose pawn on dark b8.
    report = {'split': 'validation', 'models': {'baseline': 'old', 'candidate': 'new'},
              'records': {'baseline': [dict(row, predictions=old)], 'candidate': [dict(row, predictions=new)]},
              'results': {name: {'all': {'exactBoards': 0, 'correctSquares': 63, 'totalSquares': 64}}
                          for name in ('baseline', 'candidate')}}
    manifest = {'independentFinalEvaluation': False, 'samples': [photo]}
    appearance = {'pieceAppearances': {'observed': {'officialTheme': None}}, 'samples': [
        {'photoId': 'a', 'imageSha256': 'pixels', 'pieceAppearance': 'observed', 'boardAppearance': 'plain',
         'displayedPlatform': 'unknown', 'interface': 'video'}]}
    return report, manifest, appearance


def test_pairing_recovery_losses_and_canonical_square_color(inputs):
    result = summarize(*inputs)
    assert result['squareChanges'] == {'recovered': 1, 'regressed': 1, 'netRecovered': 0}
    assert result['overall']['candidate']['classes']['p']['recall'] == 0
    assert result['overall']['candidate']['classes']['empty']['precision'] == 61 / 62
    assert result['byClassAndSquareColor']['light']['candidate']['R']['correct'] == 1
    assert result['byClassAndSquareColor']['dark']['candidate']['p']['correct'] == 0
    assert result['strata']['category']['video']['candidate']['boards'] == 1
    assert result['strata']['displayedPlatform']['unknown']['candidate']['boards'] == 1
    assert [e['square'] for e in result['photos'][0]['errors']] == ['a8', 'b8']
    assert result['photos'][0]['geometry']['oppositeEdgeRatio'] == 1
    assert result['appearanceCoverage']['observed']['status'] == 'observed-failures'
    assert result['appearanceCoverage']['observed']['generalCompatibilityEstablished'] is False


@pytest.mark.parametrize('fault', ['duplicate', 'missing-appearance', 'stale-pixels', 'labels', 'orientation',
                                  'partition', 'conditions', 'prediction', 'position', 'final'])
def test_stale_or_unpaired_evidence_is_rejected(inputs, fault):
    report, manifest, appearance = deepcopy(inputs)
    row = report['records']['candidate'][0]
    if fault == 'duplicate': report['records']['candidate'].append(deepcopy(row))
    if fault == 'missing-appearance': appearance['samples'] = []
    if fault == 'stale-pixels': appearance['samples'][0]['imageSha256'] = 'other'
    if fault == 'labels': row['expected'] = [0] * 64
    if fault == 'orientation': row['orientation'] = 'white-bottom'
    if fault == 'partition': manifest['samples'][0]['split'] = 'training'
    if fault == 'conditions': row['conditions'] = []
    if fault == 'prediction': row['predictions'][0] = -1
    if fault == 'position': row['positionId'] = 'different'
    if fault == 'final': report['split'] = 'evaluation'
    with pytest.raises(ValueError):
        summarize(report, manifest, appearance)


def test_analysis_pins_cached_report_without_loading_models(tmp_path, inputs):
    report, manifest, appearance = inputs
    paths = [tmp_path / name for name in ['report.json', 'manifest.json', 'appearance.json', 'provenance.json']]
    for path, data in zip(paths, [report, manifest]):
        path.write_text(json.dumps(data))
    appearance.update(predictionReportSha256=digest(paths[0]), manifestSha256=digest(paths[1]))
    paths[2].write_text(json.dumps(appearance))
    provenance = {'validation': {'phone': {'rawReport': {'sha256': digest(paths[0])}, 'models': report['models']},
                                'digital': {'paired': {}, 'results': {}}}}
    paths[3].write_text(json.dumps(provenance))
    result = build(*paths)
    assert result['inferenceRun'] is result['trainingRun'] is result['finalEvaluationAccessed'] is False
    paths[0].write_text(json.dumps(dict(report, split='evaluation')))
    with pytest.raises(ValueError, match='Pinned'):
        build(*paths)


def test_absent_class_has_no_invented_accuracy():
    result = metrics([{'positionId': 'one', 'expected': [0] * 64, 'predictions': [0] * 64}])
    assert result['classes']['q']['precision'] is None
    assert result['classes']['q']['recall'] is None
    assert result['exactBoards'] == 1
