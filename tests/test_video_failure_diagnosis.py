"""Keep diagnostic recovery distinct from production acceptance and training."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.unit


@pytest.fixture
def report():
    return json.loads((ROOT/'data/reports/video-009-010-diagnosis.json').read_text())


def test_sources_and_models_remain_development_only(report):
    manifest_path = ROOT/'data/manifests/video-development-v2.json'
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == report['manifestSha256']
    sources = {r['id']:r for r in json.loads(manifest_path.read_text())['samples']}
    assert {r['id'] for r in report['results']} == {'chesscom-video-009', 'chesscom-video-010'}
    for row in report['results']:
        assert row['split'] == 'development'
        for key in ('sha256','positionId','sourceGroupId','orientation','piecePlacement','box','gridBox'):
            assert row[key] == sources[row['id']][key]
    references = json.loads((ROOT/'data/reports/neural-tolerance-summary.json').read_text())
    assert report['models']['v8'] == references['baseline']
    assert report['models']['candidate'] == references['candidate']
    assert not any(report[k] for k in ('independentFinalEvaluation','trainingPerformed',
                                      'productionChanged','annotationsChanged'))


def test_grid_recovery_is_not_reported_as_accepted_detection(report):
    for row in report['results']:
        assert row['automaticDetection']['error']['code'] == 'BOARD_NOT_FOUND'
        assert row['interiorFitStructuralCheck']
        assert not row['interiorFitCompleteEdgesCheck']
        rejected = [t for t in row['detectorTrace'] if 'rejectedOuterEdge' in t]
        assert rejected and all(t['rejectedOuterEdge'] == 'left' for t in rejected)
        assert all(t['matchingEdgeCells'] < 6 for t in rejected)
        negative = row['partialBoardNegativeControl']
        assert negative['hiddenFirstFilePixels'] == 14
        assert negative['structuralOnly'] and not negative['completeEdges']


def test_positions_recover_with_geometry_but_not_interpolation(report):
    for row in report['results']:
        cases = row['classification']
        counts = (5,4) if row['id'].endswith('009') else (2,2)
        assert tuple(len(cases['reviewed']['models'][model]['wrongCells'])
                     for model in ('v8','candidate')) == counts
        for variant in ('interior-grid','horizontal-grid-only'):
            for model in ('v8','candidate'):
                result = cases[variant]['models'][model]
                assert result['wrongCells'] == []
                assert result['result'] == {'piecePlacement':row['piecePlacement']}
        for interpolation in row['reviewedBoundsInterpolationProbe'].values():
            assert all(interpolation[model] for model in ('v8','candidate'))


def test_grid_uses_real_pixels_without_padding(report):
    for row in report['results']:
        left,top,right,bottom = row['interiorFit']
        width,height = row['imageSize']
        assert 0 <= left < right <= width and 0 <= top < bottom <= height
        assert right-left == bottom-top == 456
        assert row['classification']['horizontal-grid-only']['box'] == [left,row['box'][1],right,row['box'][3]]
