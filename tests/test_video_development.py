"""Reviewed video variants are development regressions, never final holdouts."""

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import read_image
from tools.development_cases import GRID_REFERENCES, MANIFEST, ROOT, evaluate, load_cases, load_grid_references
from tools.neural_data import digest

DATA = json.loads(MANIFEST.read_text())
SAMPLES = DATA['samples']
GRIDS = load_grid_references(GRID_REFERENCES)


@pytest.mark.unit
def test_reviewed_images_hashes_crop_geometry_and_shared_identity():
    data = load_cases()
    assert len(data['samples']) == 15
    assert len({r['positionId'] for r in data['samples']}) == 13
    original = data['samples'][:3]
    assert len({r['positionId'] for r in original}) == 1
    assert len({r['sourceGroupId'] for r in original}) == 1
    assert {r['split'] for r in data['samples']} == {'development'}
    assert {r['orientation'] for r in data['samples']} == {'black-bottom', 'white-bottom'}
    assert SAMPLES[1]['clippedBoardPixels']['left'] == 1
    assert len({r['sourceGroupId'] for r in data['samples']}) == 2  # Conservative buckets, not two proven games.


@pytest.mark.unit
def test_expansion_preserves_original_annotations_and_historical_report():
    old_path = ROOT / 'data/manifests/video-development-v1.json'
    old = load_cases(old_path)
    assert DATA['previousManifestSha256'] == digest(old_path)
    assert DATA['samples'][:3] == old['samples']
    report = json.loads((ROOT / 'data/reports/video-development-v1-baseline.json').read_text())
    assert report['manifestSha256'] == digest(old_path)


@pytest.mark.unit
def test_coordinate_free_views_record_user_confirmation():
    samples = [r for r in SAMPLES if 'no-visible-coordinates' in r['conditions']]
    assert {r['id'] for r in samples} == {'chesscom-video-009', 'chesscom-video-010', 'chesscom-page-001'}
    assert all(r['orientation'] == 'white-bottom' and r['orientationEvidence'].startswith('user-confirmed')
               for r in samples)


@pytest.mark.unit
@pytest.mark.parametrize('fault', ['split', 'final-role', 'group', 'placement', 'hash', 'box', 'crop', 'orientation'])
def test_reviewed_cases_reject_label_drift_and_partition_changes(tmp_path, fault):
    data = deepcopy(DATA)
    row = data['samples'][1]
    if fault == 'split':
        row['split'] = 'evaluation'
    elif fault == 'final-role':
        data['independentFinalEvaluation'] = True
    elif fault == 'group':
        row['sourceGroupId'] = 'another-game'
    elif fault == 'placement':
        row['piecePlacement'] = '8/8/8/8/8/8/8/8'
    elif fault == 'hash':
        row['sha256'] = '0' * 64
    elif fault == 'box':
        row['box'][2] += 1
    elif fault == 'crop':
        row['derivedFrom']['cropBox'][0] += 1
    else:
        row['orientation'] = 'auto'
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_cases(path)


@pytest.mark.unit
@pytest.mark.parametrize('sample', SAMPLES, ids=lambda r: r['id'])
@pytest.mark.parametrize('renamed', [False, True])
def test_consulted_video_position_cannot_become_independent_acceptance(tmp_path, renamed, sample):
    from tools.acceptance_history import require_unobserved
    placement = sample['piecePlacement']
    if renamed:
        placement = placement.swapcase()  # Also reject an equivalent transformed diagram.
    plan = {'groups': [{'groupId': 'renamed-game', 'source': {
        'sourceId': 'renamed-source', 'initialPosition': 'startpos', 'moves': []}}],
        'positions': [{'positionId': 'renamed-position', 'piecePlacement': placement}]}
    with pytest.raises(ValueError, match='already consulted'):
        require_unobserved(plan, history=tmp_path)


@pytest.mark.unit
def test_related_game_positions_remain_excluded_from_acceptance(tmp_path):
    from tools.acceptance_history import require_unobserved
    plan = {'groups': [{'groupId': SAMPLES[0]['sourceGroupId'], 'source': {
        'sourceId': 'unknown', 'initialPosition': 'startpos', 'moves': []}}], 'positions': []}
    with pytest.raises(ValueError, match='Development source groups'):
        require_unobserved(plan, history=tmp_path)


@pytest.mark.integration
@pytest.mark.parametrize('sample', SAMPLES, ids=lambda r: r['id'])
def test_detector_returns_reviewed_board_bounds(sample):
    with read_image(ROOT / sample['path']) as image:
        actual = detect_board(image).as_box()
    expected = GRIDS.get(sample['id'], {}).get('gridBox', sample['box'])
    assert max(abs(a-b) for a, b in zip(actual, expected, strict=True)) <= DATA['maxEdgeErrorPixels']


@pytest.mark.integration
@pytest.mark.parametrize('sample', SAMPLES, ids=lambda r: r['id'])
def test_video_background_without_board_is_rejected(sample):
    with read_image(ROOT / sample['path']) as image:
        x, y, right, bottom = sample['box']
        ImageDraw.Draw(image).rectangle((x - 5, y - 5, right + 5, bottom + 5), fill='#cccccc')
        with pytest.raises(BoardDetectionError) as caught:
            detect_board(image)
    assert caught.value.code == 'BOARD_NOT_FOUND'


@pytest.mark.integration
@pytest.mark.parametrize('scale,offset', [(1, (0, 0)), (.75, (139, 47)),
                                         (1.5, (19, 83)), (2, (211, 13))])
def test_first_video_localizes_after_resizing_and_translation(scale, offset):
    sample = SAMPLES[0]
    with read_image(ROOT / sample['path']) as image:
        resized = image.resize((round(image.width * scale), round(image.height * scale)),
                               Image.Resampling.LANCZOS)
    x, y = offset
    canvas = Image.new('RGB', (resized.width + x + 37, resized.height + y + 21), '#555555')
    canvas.paste(resized, offset)
    expected = tuple(round(v * scale) + delta
                     for v, delta in zip(sample['box'], (x, y, x, y)))
    assert max(abs(a - b) for a, b in zip(detect_board(canvas).as_box(), expected)) <= 2


@pytest.fixture(scope='module')
def neural_report():
    model = os.environ.get('BOARDSNAP_TEST_MODEL')
    if not model:
        pytest.skip('Set BOARDSNAP_TEST_MODEL to test a local neural artifact.')
    pytest.importorskip('torch')
    return evaluate(model=Path(model), grid_references=GRID_REFERENCES)


@pytest.mark.integration
@pytest.mark.parametrize('sample', SAMPLES, ids=lambda r: r['id'])
def test_classification_with_reviewed_grid_matches_position(neural_report, sample):
    result = next(r for r in neural_report['results'] if r['id'] == sample['id'])
    assert result.get('gridBoundsRecognition', result['reviewedBoundsRecognition'])['correct']


@pytest.mark.integration
@pytest.mark.parametrize('sample_id', GRIDS)
def test_visible_rectangle_is_not_silently_used_as_uniform_grid(neural_report, sample_id):
    result = next(r for r in neural_report['results'] if r['id'] == sample_id)
    assert not result['reviewedBoundsRecognition']['correct']
    assert result['gridBoundsRecognition']['correct']
    assert result['visibleBoundary']['maxEdgeErrorPixels'] == 0


@pytest.mark.integration
@pytest.mark.parametrize('sample', SAMPLES, ids=lambda r: r['id'])
def test_complete_pipeline_matches_reviewed_position(neural_report, sample):
    result = next(r for r in neural_report['results'] if r['id'] == sample['id'])
    assert result['fullPipeline']['correct']


@pytest.fixture(scope='module')
def neural_classifier():
    model = os.environ.get('BOARDSNAP_TEST_MODEL')
    if not model:
        pytest.skip('Set BOARDSNAP_TEST_MODEL to test a local neural artifact.')
    torch = pytest.importorskip('torch')
    from boardsnap.neural import NeuralClassifier
    torch.set_num_threads(4)
    return NeuralClassifier(Path(model))


@pytest.mark.integration
@pytest.mark.parametrize('sample', SAMPLES[:3], ids=lambda r: r['id'])
@pytest.mark.parametrize('margins', [(0, 0, 0, 0), (3, 5, 9, 2), (11, 1, 4, 7)])
def test_same_video_position_with_asymmetric_margins(tmp_path, neural_classifier, sample, margins):
    left, top, right, bottom = margins
    with read_image(ROOT / sample['path']) as original:
        image = Image.new('RGB', (original.width+left+right, original.height+top+bottom), '#555555')
        image.paste(original, (left, top))
    expected = tuple(a+b for a,b in zip(sample['box'], (left, top, left, top)))
    assert max(abs(a-b) for a,b in zip(detect_board(image).as_box(), expected)) <= 2
    path = tmp_path / 'padded.png'
    image.save(path)
    assert neural_classifier.recognize_image(path, orientation=sample['orientation']) == {
        'piecePlacement': sample['piecePlacement']}


@pytest.mark.unit
def test_detector_only_measurement_does_not_claim_classification():
    report = evaluate(grid_references=GRID_REFERENCES)
    assert report['passed'] == all(r['detection']['correct'] for r in report['results'])
    assert report['modelSha256'] is None
    assert report['images'] == 15 and report['positions'] == 13
    assert report['sourceGroups'] == 2  # Do not interpret unresolved groups as a game count.
    assert [r['expectedBox'] for r in report['results']] == [GRIDS.get(r['id'], {}).get('gridBox',r['box']) for r in SAMPLES]
    assert [r['expectedVisibleBox'] for r in report['results']] == [r['box'] for r in SAMPLES]
    assert all('fullPipeline' not in r for r in report['results'])
