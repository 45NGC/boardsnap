"""Paired photo exports require current visual reviews and preserve source groups."""

from copy import deepcopy
import json

import numpy as np
from PIL import Image
import pytest

from tools.build_targeted_photo_squares import build, review_fingerprint
from tools.prepare_phone_photos import CORNER_ORDER, digest, write_json
from tools.review_phone_geometry import visual_labels

pytestmark = pytest.mark.unit


def corpus(root, orientation):
    source = root / 'sources'
    source.mkdir()
    image = Image.new('RGB', (300, 300), 'gray')
    for r in range(8):
        for c in range(8):
            x, y = 16 + c * 32, 16 + r * 32
            image.paste((r * 30, c * 30, 100), (x, y, x + 32, y + 32))
            image.paste((255, 0, 255), (x + 2, y + 2, x + 6, y + 6))
    images = []
    for identity, kind in [('photo', 'phone-photo'), ('reference', 'direct-screenshot')]:
        path = source / f'{identity}.png'
        image.save(path)
        images.append(dict(id=identity, kind=kind, session='position1',
            imagePath=str(path.relative_to(root)), originalPath=str(path.relative_to(root)),
            originalSha256=digest(path), imageSha256=digest(path), imageSize=[300, 300]))
    photo, reference = images
    label = dict(status='visual-transcription', piecePlacement='k7/8/8/8/8/8/8/6NK',
        orientation=orientation, method='direct-screenshot-transcription-and-photo-comparison',
        reviewedBy='test', referenceImageSha256=reference['imageSha256'])
    label['visualRows'] = visual_labels(label)
    session = dict(id='position1', groupId='game-1', split='development', label=label,
        photoImageIds=['photo'], referenceImageIds=['reference'], source={'platform': 'chesscom'},
        appearanceGroup='test-pieces', boardAppearance='test-background')
    photo.update(referenceImageId='reference', conditions=['perspective'],
        boardCorners=[[16, 16], [272, 16], [272, 272], [16, 272]],
        cornerAnnotationStatus='visual-reviewed')
    photo['geometryReview'] = dict(status='visual-reviewed', reviewedBy='test', reviewedOn='2026-11-13',
        coordinateSpace='normalized-image-pixels', cornerOrder=CORNER_ORDER,
        outcome='complete-grid-aligned-and-labels-match-reference',
        fingerprint=review_fingerprint(photo, session, reference))
    data = dict(schemaVersion=1, dataRole='paired-photographic-development-intake',
        independentFinalEvaluation=False, sessions=[session], images=images)
    manifest = root / 'manifest.json'
    write_json(manifest, data)
    return manifest, data


@pytest.mark.parametrize('orientation', ['white-bottom', 'black-bottom'])
def test_canonical_crops_labels_group_and_originals_preserved(tmp_path, orientation):
    manifest, data = corpus(tmp_path, orientation)
    output = tmp_path / '.cache/squares'
    original_hashes = [digest(tmp_path / r['originalPath']) for r in data['images']]
    report = build(manifest, output, root=tmp_path)
    row = json.loads((output / 'verified.jsonl').read_text())
    with np.load(output / row['array'], allow_pickle=False) as saved:
        assert saved['images'].shape == (64, 64, 64, 3)
        for r in range(8):
            for c in range(8):
                vr, vc = (r, c) if orientation == 'white-bottom' else (7-r, 7-c)
                assert saved['images'][r*8+c, 32, 32].tolist() == [vr*30, vc*30, 100]
                assert saved['images'][r*8+c, 6, 6].tolist() == [255, 0, 255]
        assert saved['class_ids'].tolist() == [cell['classId'] for cell in row['cells']]
    assert row['cells'][0]['square'] == 'a8' and row['cells'][0]['label'] == 'k'
    assert row['cells'][-1]['square'] == 'h1' and row['cells'][-1]['label'] == 'K'
    assert row['groupId'] == 'game-1' and row['split'] == 'development'
    assert row['referenceImageId'] == 'reference'
    assert report['writtenBoards'] == 1 and report['squareCount'] == 64
    assert report['readyForTraining'] is False
    assert sum(sum(v.values()) for v in report['classBackgroundCounts'].values()) == 64
    assert original_hashes == [digest(tmp_path / r['originalPath']) for r in data['images']]
    assert (output / row['preview']).exists() and (output / 'index.html').exists()
    with pytest.raises(ValueError, match='new destination'):
        build(manifest, output, root=tmp_path)


@pytest.mark.parametrize('change', [
    'corners', 'orientation', 'label', 'group', 'split', 'pixels', 'reference-pixels',
    'reference-pair', 'unreviewed', 'duplicate', 'missing-member', 'cross-session',
])
def test_stale_or_invalid_inputs_never_publish_export(tmp_path, change):
    manifest, data = corpus(tmp_path, 'white-bottom')
    photo, reference = data['images']
    session = data['sessions'][0]
    if change == 'corners':
        photo['boardCorners'][0][0] += 2
    elif change == 'orientation':
        session['label']['orientation'] = 'black-bottom'
        session['label']['visualRows'] = visual_labels(session['label'])
    elif change == 'label':
        session['label']['piecePlacement'] = '8/8/8/8/8/8/8/8'
        session['label']['visualRows'] = visual_labels(session['label'])
    elif change == 'group':
        session['groupId'] = 'another-game'
    elif change == 'split':
        session['split'] = 'validation'
    elif change in ('pixels', 'reference-pixels'):
        row = photo if change == 'pixels' else reference
        (tmp_path / row['imagePath']).write_bytes(b'changed')
    elif change == 'reference-pair':
        photo['referenceImageId'] = 'photo'
    elif change == 'unreviewed':
        del photo['geometryReview']
    elif change == 'duplicate':
        data['images'].append(deepcopy(photo))
    elif change == 'missing-member':
        session['photoImageIds'] = []
    elif change == 'cross-session':
        reference['session'] = 'other-session'
    write_json(manifest, data)
    output = tmp_path / '.cache/squares'
    with pytest.raises(ValueError):
        build(manifest, output, root=tmp_path)
    assert not output.exists()
