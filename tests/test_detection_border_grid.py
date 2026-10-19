"""A narrow visible rim must not shift segmentation or admit missing cells."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

from boardsnap import detection
from tools.development_cases import GRID_REFERENCES, ROOT, load_grid_references
from tools.neural_data import digest
from tests.test_detection import draw_grid

REFERENCES = load_grid_references(GRID_REFERENCES)
MODELS = json.loads((ROOT/'data/reports/neural-tolerance-summary.json').read_text())
SOURCES = {r['id']: r for r in json.loads((ROOT/'data/manifests/video-development-v2.json').read_text())['samples']}


def source(case):
    return Image.open(ROOT/SOURCES[case]['path']).convert('RGB')


def grid_bounds(box):
    x,y,r,b = box
    return detection.BoardBounds(x,y,r-x,b-y)


@pytest.mark.unit
@pytest.mark.parametrize('case', REFERENCES)
def test_recovery_preserves_grid_and_validates_visible_rectangle_separately(case):
    with source(case) as image:
        before = image.tobytes()
        actual = detection.detect_board(image)
        assert actual.as_box() == tuple(REFERENCES[case]['gridBox'])
        proof = detection._recover_border_grid(np.asarray(image), actual)
        assert proof.grid == actual
        assert proof.visible.as_box() == tuple(REFERENCES[case]['visibleBox'])
        assert image.tobytes() == before


@pytest.mark.unit
@pytest.mark.parametrize('case', REFERENCES)
@pytest.mark.parametrize('turns', [0,1,2,3])
@pytest.mark.parametrize('offset', [(0,0),(47,29)])
def test_recovery_is_not_specific_to_location_or_left_border(case,turns,offset):
    with source(case) as image:
        width,height = image.size
        box = tuple(REFERENCES[case]['gridBox'])
        for _ in range(turns):
            x,y,right,bottom = box
            box = (y,width-right,bottom,width-x)
            width,height = height,width
        rotated = image.rotate(turns*90,expand=True)
    x,y = offset
    canvas = Image.new('RGB',(width+x+31,height+y+17),'#555555')
    canvas.paste(rotated,offset)
    expected = tuple(a+b for a,b in zip(box,(x,y,x,y)))
    assert detection.detect_board(canvas).as_box() == expected


@pytest.mark.unit
@pytest.mark.parametrize('case', REFERENCES)
@pytest.mark.parametrize('side',['left','top','right','bottom'])
@pytest.mark.parametrize('hidden',[8,14])
def test_partial_first_or_last_file_or_rank_remains_rejected(case,side,hidden):
    with source(case) as image:
        pixels = np.asarray(image).copy()
    x,y,right,bottom = REFERENCES[case]['gridBox']
    box = {'left':(x,y,x+hidden,bottom),'right':(right-hidden,y,right,bottom),
           'top':(x,y,right,y+hidden),'bottom':(x,bottom-hidden,right,bottom)}[side]
    l,t,r,b = box
    pixels[t:b,l:r] = (32,32,32)
    assert detection._recover_border_grid(pixels,grid_bounds(REFERENCES[case]['gridBox'])) is None
    with pytest.raises(detection.BoardDetectionError,match='No supported'):
        detection.detect_board(Image.fromarray(pixels))


@pytest.mark.unit
@pytest.mark.parametrize('hidden,accepted',[(3,True),(5,False),(8,False),(14,False)])
@pytest.mark.parametrize('edges',[1,2])
def test_palette_independent_strip_budget_and_multiple_edges(hidden,accepted,edges):
    canvas = Image.new('RGB',(536,536),'#202020')
    canvas.paste(draw_grid(456,colors=((210,222,240),(95,55,130))),(40,40))
    pixels = np.asarray(canvas).copy()
    pixels[40:496,40:40+hidden] = 32
    if edges == 2:
        pixels[40:40+hidden,40:496] = 32
    proof = detection._recover_border_grid(pixels,detection.BoardBounds(40,40,456,456))
    assert (proof is not None) == (accepted and edges==1)


@pytest.mark.unit
@pytest.mark.parametrize('case',REFERENCES)
def test_recovery_never_extrapolates_outside_a_cropped_input(case):
    with source(case) as image:
        x,y,right,bottom = REFERENCES[case]['gridBox']
        cropped = image.crop((x+8,y,right,bottom))
    with pytest.raises(detection.BoardDetectionError,match='No supported'):
        detection.detect_board(cropped)


@pytest.mark.unit
def test_accepted_grid_never_invokes_the_new_recovery(monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('Recovery must not change already accepted detections.')
    monkeypatch.setattr(detection,'_recover_border_grid',forbidden)
    with source('chesscom-video-001') as image:
        assert detection.detect_board(image).as_box() == (35,17,435,417)


@pytest.mark.unit
@pytest.mark.parametrize('fault',['source','visible','grid','lines','duplicate'])
def test_geometry_reference_rejects_drift(tmp_path,fault):
    data=json.loads(GRID_REFERENCES.read_text())
    row=data['samples'][0]
    if fault=='source': row['sourceSha256']='changed'
    elif fault=='visible':row['visibleBox'][0]+=1
    elif fault=='grid':row['gridBox'][0]=-1
    elif fault=='lines':row['verticalLines'][0]+=10
    else:data['samples'].append(deepcopy(row))
    path=tmp_path/'geometry.json';path.write_text(json.dumps(data))
    with pytest.raises(ValueError):load_grid_references(path)


@pytest.fixture(params=['baseline','candidate'])
def model(request):
    row=MODELS[request.param]
    path=ROOT/row['path']
    if not path.is_file():pytest.skip('Local reference model is not available.')
    pytest.importorskip('torch')
    assert digest(path)==row['sha256']
    yield path
    assert digest(path)==row['sha256']


@pytest.mark.integration
@pytest.mark.parametrize('case',REFERENCES)
def test_installed_cli_recovers_exact_position_without_sidecars(tmp_path,model,case):
    source_manifest=json.loads((ROOT/'data/manifests/video-development-v2.json').read_text())
    expected=next(r['piecePlacement'] for r in source_manifest['samples'] if r['id']==case)
    path=tmp_path/'unrelated screenshot.png'
    with source(case) as image:image.save(path)
    command=Path(sys.executable).parent/'boardsnap'
    result=subprocess.run([str(command),path.name,'--model',str(model),'--orientation','white-bottom'],
                          cwd=tmp_path,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr
    assert result.stderr==''
    assert result.stdout==json.dumps({'piecePlacement':expected})+'\n'


@pytest.mark.integration
def test_cli_rejects_fourteen_pixel_negative(tmp_path,model):
    case='chesscom-video-009'
    with source(case) as image:pixels=np.asarray(image).copy()
    x,y,right,bottom=REFERENCES[case]['gridBox']
    pixels[y:bottom,x:x+14]=32
    path=tmp_path/'negative.png';Image.fromarray(pixels).save(path)
    command=Path(sys.executable).parent/'boardsnap'
    result=subprocess.run([str(command),str(path),'--model',str(model),'--orientation','white-bottom'],
                          capture_output=True,text=True,timeout=60)
    assert result.returncode==1
    assert result.stderr==''
    payload=json.loads(result.stdout)
    assert set(payload)=={'error'} and payload['error']['code']=='BOARD_NOT_FOUND'
