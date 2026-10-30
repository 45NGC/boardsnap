"""Partition migration reuses archives and rejects stale or leaking annotations."""

from copy import deepcopy
import json

import numpy as np
from PIL import Image
import pytest

from tools.build_phone_squares import build as build_development, extract_photo_squares
from tools.build_phone_training_dataset import assignments, build
from tools.capture_lichess import expand_placement
from tools.neural_data import load_board, load_split, read_index
from tools.prepare_phone_photos import CORNER_ORDER, digest, prepare, write_json


def photo_manifest(tmp_path, name, placement, color):
    source = tmp_path / name / 'originals' / 'chesscom-photos'
    source.mkdir(parents=True)
    image = Image.new('RGB', (256, 256), color)
    image.paste('red', (1, 1, 12, 12))
    image.save(source / 'photo.png')
    manifest = tmp_path / name / 'manifest.json'
    data = prepare(source.parent, tmp_path / name / 'review', manifest, root=tmp_path)
    row = data['samples'][0]
    row['boardCorners'] = [[0, 0], [256, 0], [256, 256], [0, 256]]
    row['geometryReview'] = dict(status='visual-reviewed', imageSha256=row['imageSha256'],
        coordinateSpace='normalized-image-pixels', cornerOrder=CORNER_ORDER,
        reviewedBy='test', reviewedOn='2026-10-30')
    # Both fixture photos use black-bottom; visual rows are distinct from canonical.
    from boardsnap.output import build_result
    visual = [r[::-1] for r in expand_placement(placement)[::-1]]
    visual_fen = build_result([[None if p == '.' else p for p in r] for r in visual])['piecePlacement']
    row['label'].update(status='visual-transcription', piecePlacement=placement, visualRows=visual_fen,
        orientation='black-bottom', method='visual-board-review', reviewedBy='test',
        sourceSha256=row['originalSha256'])
    row['label']['rectifiedReview'] = dict(imageSha256=row['imageSha256'],
        boardCorners=deepcopy(row['boardCorners']), piecePlacement=placement,
        orientation='black-bottom', reviewedBy='test', reviewedOn='2026-10-30',
        outcome='matches-visible-pieces')
    write_json(manifest, data)
    return manifest, data


@pytest.fixture
def prepared(tmp_path):
    dev_path, dev = photo_manifest(tmp_path, 'dev', 'k7/8/8/8/8/8/8/6NK', 'tan')
    old = tmp_path / '.cache/old'
    build_development(dev_path, old, root=tmp_path)
    val_path, val = photo_manifest(tmp_path, 'val', 'k7/8/8/8/8/8/8/5BNK', 'green')
    val.update(dataRole='photo-validation-intake', referenceDevelopmentManifest=str(dev_path.relative_to(tmp_path)),
        referenceDevelopmentManifestSha256=digest(dev_path),
        sourceSeparationConfirmation={'status':'user-confirmed-distinct-source-selection'},
        partitionReview={'status':'validation-assigned'})
    val['samples'][0].update(split='validation', intendedSplit='validation', groupId='phone-validation-batch-v1')
    write_json(val_path, val)
    inputs = {'developmentManifest':dev_path, 'validationManifest':val_path,
              'developmentSquaresMetadata':old/'dataset.json'}
    plan = dict(schemaVersion=1, datasetId='phone-training-test', dataRole='photo-training-partition-plan',
        independentFinalEvaluation=False, inputs={k:{'path':str(p.relative_to(tmp_path)), 'sha256':digest(p)} for k,p in inputs.items()},
        assignments=assignments(dev,val), excludedPhotoIds=[])
    plan_path=tmp_path/'plan.json'
    write_json(plan_path,plan)
    return plan_path, plan, old, dev_path, val_path


def test_reuse_and_export_load_with_actual_training_loader(tmp_path, prepared):
    plan_path, _, old, dev_path, val_path = prepared
    before = {p: digest(p) for p in [dev_path,val_path,old/'dataset.json',old/'verified.jsonl']}
    old_row=json.loads((old/'verified.jsonl').read_text())
    output=tmp_path/'.cache/train'
    report=build(plan_path,output,root=tmp_path)
    meta, rows=read_index(output)
    assert report['splitCounts']=={'training':1,'validation':1,'evaluation':0}
    assert report['reusedTrainingArchives']==report['newValidationArchives']==1
    assert meta['readyForTraining'] and not meta['trainingRun']
    assert (output/rows[0]['array']).read_bytes()==(old/old_row['array']).read_bytes()
    for split in ('training','validation'):
        _, subset=read_index(output,split)
        assert len(subset)==1 and subset[0]['split']==split
        pixels, labels=load_split(output,rows,split)
        assert pixels.shape==(64,64,64,3) and labels.shape==(64,)
    val=json.loads(val_path.read_text())['samples'][0]
    with Image.open(tmp_path/val['imagePath']) as image:
        expected=extract_photo_squares(image,val['boardCorners'],val['label']['orientation'])
    actual,_=load_board(output,rows[1])
    assert np.array_equal(actual,expected)
    assert all(digest(p)==h for p,h in before.items())
    with pytest.raises(ValueError,match='already exists'):
        build(plan_path,output,root=tmp_path)


@pytest.mark.parametrize('change', ['archive','index','plan','review','assignment','overlap'])
def test_invalid_inputs_never_publish_dataset(tmp_path, prepared, change):
    plan_path,plan,old,dev_path,val_path=prepared
    if change=='archive':
        row=json.loads((old/'verified.jsonl').read_text())
        (old/row['array']).write_bytes(b'corrupt archive')
    elif change=='index':
        (old/'verified.jsonl').write_text('')
    elif change=='plan':
        plan['inputs']['validationManifest']['sha256']='0'*64
    elif change=='assignment':
        plan['assignments']['training']['photoIds']=[]
    else:
        val=json.loads(val_path.read_text())
        if change=='review':
            val['samples'][0]['boardCorners'][0][0]+=1
        else:
            # A consistently labeled copy of a development position still leaks.
            old_label=json.loads(dev_path.read_text())['samples'][0]['label']
            label=val['samples'][0]['label']
            label['piecePlacement']=old_label['piecePlacement']
            label['visualRows']=old_label['visualRows']
            label['rectifiedReview']['piecePlacement']=old_label['piecePlacement']
        write_json(val_path,val)
        plan['inputs']['validationManifest']['sha256']=digest(val_path)
    write_json(plan_path,plan)
    output=tmp_path/'.cache/train'
    with pytest.raises(ValueError):
        build(plan_path,output,root=tmp_path)
    assert not output.exists()
