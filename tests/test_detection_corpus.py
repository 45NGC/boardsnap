"""Reviewed rectangles for new themes and real-use marked screenshots."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardDetectionError, detect_board

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'data/manifests/digital-detection-v1.json').read_text())
CASES = [pytest.param(item, id=item['id'], marks=(pytest.mark.evaluation if item['split']=='evaluation'
                                               else pytest.mark.integration))
         for item in MANIFEST['samples']]


@pytest.mark.unit
def test_detection_dataset_hashes_bounds_and_group_isolation():
    groups, hashes = {}, set()
    for item in MANIFEST['samples']:
        assert groups.setdefault(item['sourceGroupId'],item['split']) == item['split']
        path = ROOT / item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        assert item['sha256'] not in hashes
        hashes.add(item['sha256'])
        with Image.open(path) as image:
            image.load()
            assert list(image.size)==item['imageSize']
            x,y,right,bottom=item['box']
            assert 0<=x<right<=image.width and 0<=y<bottom<=image.height
            assert right-x==bottom-y
    assert len(MANIFEST['samples'])==28
    assert sum(s['split']=='evaluation' for s in MANIFEST['samples'])==8
    assert MANIFEST['classificationLabelsAvailable'] is False


@pytest.mark.parametrize('sample',CASES)
@pytest.mark.parametrize('variant',['original','cropped','small','relocated','no-board'])
def test_detection_geometry_without_classifying_pieces(sample,variant):
    with Image.open(ROOT / sample['path']) as source:
        image = source.convert('RGB')
    box = tuple(sample['box'])
    expected = box
    if variant == 'cropped':
        image = image.crop(box)
        expected = (0,0,image.width,image.height)
    elif variant == 'small':
        board = image.crop(box).resize((256,256),Image.Resampling.LANCZOS)
        image = Image.new('RGB',(471,399),'#3c3d43')
        image.paste(board,(101,57))
        expected = (101,57,357,313)
    elif variant == 'relocated':
        canvas = Image.new('RGB',(image.width+180,image.height+110),'#e2e4e7')
        canvas.paste(image,(137,41))
        image = canvas
        expected = tuple(a+b for a,b in zip(box,(137,41,137,41)))
    elif variant == 'no-board':
        x,y,right,bottom=box
        ImageDraw.Draw(image).rectangle((x-5,y-5,right+5,bottom+5),fill='#cccccc')
        with pytest.raises(BoardDetectionError) as caught:
            detect_board(image)
        assert caught.value.code=='BOARD_NOT_FOUND'
        return
    detected = detect_board(image).as_box()
    assert max(abs(a-b) for a,b in zip(detected,expected))<=MANIFEST['maxEdgeErrorPixels']
