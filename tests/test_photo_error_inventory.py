"""Consolidation uses recorded predictions and preserves paired geometry evidence."""

from copy import deepcopy
import csv
import json
from pathlib import Path

import pytest

from tools.consolidate_photo_errors import INPUTS, compare_cells, consolidate, development_gaps, generate, write_outputs

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    return {key: json.loads((ROOT/path).read_text()) for key, path in INPUTS.items()}


def test_current_totals_and_failure_roles(data):
    result = consolidate(data)
    assert result['summary'] == {
        'images': 30, 'detected': 29, 'annotatedExactBoards': 19, 'automaticExactBoards': 20,
        'annotatedSquareErrors': 49, 'automaticSquareErrorsOnDetectedOnly': 32, 'failureTableRows': 12,
        'stages': {'both-correct': 18, 'classification-fails-with-both-geometries': 8,
                   'automatic-crop-recovers-position': 2, 'detection-failed': 1, 'crop-sensitive-failure': 1},
        'introducedSquares': 3, 'recoveredSquares': 18}
    rows = {r['id']: r for r in result['photos']}
    assert result['pairedDetectedMetrics'] == {
        'images': 29, 'squares': 1856, 'annotatedSquareErrors': 47, 'automaticSquareErrors': 32}
    assert rows['chesscom-img_5395']['orientation'] == 'black-bottom'
    assert rows['chesscom-img_5395']['wrongSquares'][0]['square'] == 'e5'
    missing = rows['video-img_5403']
    assert missing['automaticErrorCount'] is None
    assert missing['automaticPlacement'] is None
    assert missing['annotatedErrorCount'] == 2
    assert missing['recoveredSquares'] == []  # A missing prediction never counts as recovery.
    shifted = rows['video-img_5406']
    assert shifted['geometryMetrics']['withinPolicy'] is True
    assert shifted['introducedSquares'] == ['h8']
    assert shifted['annotatedErrorCount'] == 0
    assert shifted['automaticErrorCount'] == 1
    assert [rows[k]['stage'] for k in ('chesscom-img_5396', 'chesscom-img_5399')] == ['automatic-crop-recovers-position']*2


def test_canonical_coordinates_empty_and_piece_colors():
    expected = 'n7/8/8/8/8/8/8/7K'
    wrong = compare_cells(expected, 'k7/8/8/8/8/8/8/7K', 'n7/8/8/8/8/8/8/8')
    assert [(r['square'], r['expected'], r['annotated'], r['automatic']) for r in wrong] == [
        ('a8', 'n', 'k', 'n'), ('h1', 'K', 'K', 'empty')]
    assert all(r['squareColor'] == 'light' for r in wrong)
    with pytest.raises(ValueError):
        compare_cells('8/8', expected, expected)


@pytest.mark.parametrize('change', ['duplicate', 'missing-style', 'image-hash', 'group', 'split', 'orientation',
                                    'target', 'corners', 'geometry', 'flag', 'model', 'non-detection-error', 'final'])
def test_stale_or_inconsistent_evidence_fails(data, change):
    row = data['pipeline']['records'][0]
    if change == 'duplicate':
        data['pipeline']['records'].append(deepcopy(row))
    elif change == 'missing-style':
        data['appearances']['samples'].pop()
    elif change == 'image-hash':
        row['imageSha256'] = 'changed'
    elif change == 'group':
        row['groupId'] = 'another-game'
    elif change == 'split':
        row['split'] = 'evaluation'
    elif change == 'orientation':
        row['orientation'] = 'black-bottom'
    elif change == 'target':
        row['expected'] = '8/8/8/8/8/8/8/8'
    elif change == 'corners':
        data['detection']['records'][0]['expectedCorners'][0][0] += 1
    elif change == 'geometry':
        row['automaticCorners'][0][0] += 1
    elif change == 'flag':
        row['automaticExact'] = False
    elif change == 'model':
        data['pipeline']['modelSha256'] = 'another-model'
    elif change == 'non-detection-error':
        failure = next(r for r in data['pipeline']['records'] if r['cliExitCode'])
        failure['cliResult']['error']['code'] = 'PROCESSING_FAILED'
    else:
        data['manifest']['independentFinalEvaluation'] = True
    with pytest.raises(ValueError):
        consolidate(data)


def test_development_gaps_are_not_invented_classification_errors(data):
    gaps = development_gaps(data)
    assert gaps['summary']['detected'] == 134
    assert len(gaps['gaps']) == 27
    assert all(r['classificationComparisonAvailable'] is False and r['pieceAppearance'] is None for r in gaps['gaps'])


def test_csv_roundtrip_and_no_overwrite(tmp_path, data):
    report = consolidate(data)
    report['developmentGeometryOnly'] = development_gaps(data)
    prefix = tmp_path/'inventory'
    write_outputs(prefix, report)
    with prefix.with_suffix('.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 12
    assert next(r for r in rows if r['id'] == 'video-img_5403')['automaticErrors'] == 'NOT_DETECTED'
    with pytest.raises(ValueError, match='never overwrite'):
        write_outputs(prefix, report)


def test_generation_does_not_open_images_or_weights(monkeypatch):
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path.suffix not in ('.png', '.jpg', '.jpeg', '.HEIC', '.pt', '.npy')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    report = generate()
    assert report['inferenceRun'] is False and report['trainingRun'] is False
    assert report['finalEvaluationAccessed'] is False
    assert not report['previousExperimentsNotRepeated']['trainingExperiment']['accepted']
