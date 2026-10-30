"""Photographic crops preserve pixel orientation, labels and unresolved groups."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from tools.build_phone_squares import build, extract_photo_squares, partition_plan
from tools.neural_data import load_board, read_index
from tools.prepare_phone_photos import CORNER_ORDER, prepare, write_json

pytestmark = pytest.mark.unit


def corpus(tmp_path):
    source = tmp_path / 'originals' / 'chesscom-photos'
    source.mkdir(parents=True)
    image = Image.new('RGB', (320, 300), 'gray')
    for row in range(8):
        for col in range(8):
            x, y = 32 + col * 32, 16 + row * 32
            image.paste((row * 30, col * 30, 100), (x, y, x + 32, y + 32))
            image.paste((255, 0, 255), (x + 1, y + 1, x + 5, y + 5))
    image.save(source / 'test.png')
    manifest = tmp_path / 'manifest.json'
    data = prepare(source.parent, tmp_path / 'review', manifest, root=tmp_path)
    row = data['samples'][0]
    row['source']['gameId'] = 'observed-game'
    row['boardCorners'] = [[32, 16], [288, 16], [288, 272], [32, 272]]
    row['geometryReview'] = dict(status='visual-reviewed', imageSha256=row['imageSha256'],
        coordinateSpace='normalized-image-pixels', cornerOrder=CORNER_ORDER,
        reviewedBy='test', reviewedOn='2026-10-28')
    row['label'].update(status='visual-transcription', piecePlacement='k7/8/8/8/8/8/8/6NK',
        orientation='black-bottom', method='visual-board-review', reviewedBy='test',
        sourceSha256=row['originalSha256'])
    row['label']['rectifiedReview'] = dict(imageSha256=row['imageSha256'],
        boardCorners=deepcopy(row['boardCorners']), piecePlacement=row['label']['piecePlacement'],
        orientation='black-bottom', reviewedBy='test', reviewedOn='2026-10-28',
        outcome='matches-visible-pieces')
    write_json(manifest, data)
    return manifest, data


def test_export_all_cells_in_canonical_order_without_rotating_glyphs(tmp_path):
    manifest, data = corpus(tmp_path)
    output = tmp_path / '.cache/squares'
    original = Path(tmp_path / data['samples'][0]['originalPath']).read_bytes()
    report = build(manifest, output, root=tmp_path)
    row = json.loads((output / 'verified.jsonl').read_text())
    images, labels = load_board(output, row)
    assert images.shape == (64, 64, 64, 3)
    for r in range(8):
        for c in range(8):
            assert images[r * 8 + c, 32, 32].tolist() == [(7 - r) * 30, (7 - c) * 30, 100]
            assert images[r * 8 + c, 4, 4].tolist() == [255, 0, 255]
    assert row['cells'][0]['square'] == 'a8'
    assert row['cells'][0]['label'] == 'k'
    assert row['cells'][0]['imageRow'] == row['cells'][0]['imageColumn'] == 7
    assert row['cells'][-1]['label'] == 'K'
    assert row['groupId'] == data['samples'][0]['groupId']
    assert report['squareCount'] == 64
    assert report['splitCounts'] == dict(development=1, training=0, validation=0, evaluation=0)
    assert sum(sum(counts.values()) for counts in report['classBackgroundCounts'].values()) == 64
    assert report['readyForTraining'] is False
    assert original == Path(tmp_path / data['samples'][0]['originalPath']).read_bytes()
    assert (output / row['preview']).is_file()
    with pytest.raises(ValueError, match='Invalid split'):
        read_index(output)  # Cannot silently train on development data.
    with pytest.raises(ValueError, match='already exists'):
        build(manifest, output, root=tmp_path)


def test_ambiguous_photo_has_no_crops(tmp_path):
    manifest, data = corpus(tmp_path)
    ambiguous = deepcopy(data['samples'][0])
    ambiguous['id'] = 'ambiguous'
    source = tmp_path / ambiguous['originalPath']
    copy = source.with_name('ambiguous.png')
    copy.write_bytes(source.read_bytes())
    ambiguous['originalPath'] = str(copy.relative_to(tmp_path))
    ambiguous['label'].update(status='ambiguous', piecePlacement=None)
    ambiguous['label']['rectifiedReview'].update(piecePlacement=None, outcome='ambiguous-excluded')
    data['samples'].append(ambiguous)
    write_json(manifest, data)
    output = tmp_path / '.cache/squares'
    report = build(manifest, output, root=tmp_path)
    assert report['sourcePhotoCount'] == 2 and report['writtenBoards'] == 1
    assert report['exclusions'][0]['id'] == 'ambiguous'
    assert not (output / 'development/ambiguous.npz').exists()


@pytest.mark.parametrize('change', ['review', 'split', 'pixels'])
def test_invalid_inputs_do_not_publish_crops(tmp_path, change):
    manifest, data = corpus(tmp_path)
    row = data['samples'][0]
    if change == 'review':
        del row['label']['rectifiedReview']
    elif change == 'split':
        row['split'] = 'validation'
    else:
        (tmp_path / row['imagePath']).write_bytes(b'changed')
    write_json(manifest, data)
    output = tmp_path / '.cache/squares'
    with pytest.raises(ValueError):
        build(manifest, output, root=tmp_path)
    assert not output.exists()


def test_provenance_clues_do_not_create_independent_groups(tmp_path):
    manifest, data = corpus(tmp_path)
    plan = partition_plan(data, 'manifest-hash')
    assert len(plan['groups']) == 1
    assert plan['groups'][0]['observedGameIds'] == ['chesscom:observed-game']
    assert plan['groups'][0]['split'] == 'development'
    assert plan['status'] == 'awaiting-independent-validation-sources'


def test_unknown_orientation_is_not_assumed():
    with pytest.raises(ValueError, match='explicit orientation'):
        extract_photo_squares(Image.new('RGB', (64, 64)), [[0, 0], [64, 0], [64, 64], [0, 64]], 'auto')
