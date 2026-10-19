"""Rectangular grids need interior/perimeter evidence, not image-name exceptions."""

import json

import numpy as np
from PIL import Image
import pytest

from boardsnap import detection
from tools.digital_geometry_scenarios import scene, scenarios
from tools.evaluate_real_use import ROOT, load_manifest


@pytest.mark.unit
@pytest.mark.parametrize('spec',list(scenarios()),ids=lambda s:s['id'])
def test_controlled_geometry(spec):
    params={k:v for k,v in spec.items() if k not in ('id','positive')}
    image,expected=scene(**params)
    with image:
        before=image.tobytes()
        if spec['positive']:
            actual=detection.detect_board(image)
            assert max(abs(a-b) for a,b in zip(actual.as_box(),expected))<=2
        else:
            with pytest.raises(detection.BoardDetectionError) as caught:
                detection.detect_board(image)
            assert caught.value.code=='BOARD_NOT_FOUND'
        assert image.tobytes()==before


@pytest.mark.unit
def test_accepted_square_never_uses_rectangular_fallback(monkeypatch):
    image,expected=scene(384,1.,'x','clean')
    def forbidden(*args,**kwargs):
        raise AssertionError('A previously accepted digital board used the fallback.')
    monkeypatch.setattr(detection,'_rectangular_grid_candidates',forbidden)
    with image:
        assert max(abs(a-b) for a,b in zip(detection.detect_board(image).as_box(),expected))<=2


@pytest.mark.unit
@pytest.mark.parametrize('side,ratio,accepted',[
    (193,1.03,True),(401,1.045,True),(800,1.04875,True),(800,1.05125,False)])
@pytest.mark.parametrize('axis',['x','y'])
def test_additional_sizes_and_scope_boundary(side,ratio,accepted,axis):
    # Separate sizes/ratios from the initial 36-scenario development matrix.
    image,expected=scene(side,ratio,axis,'marks')
    with image:
        if accepted:
            actual=detection.detect_board(image)
            assert max(abs(a-b) for a,b in zip(actual.as_box(),expected))<=2
        else:
            with pytest.raises(detection.BoardDetectionError) as caught:
                detection.detect_board(image)
            assert caught.value.code=='BOARD_NOT_FOUND'


@pytest.mark.unit
def test_multiple_rectangular_boards_are_not_silently_selected():
    first,_=scene(257,1.04,'x','clean')
    second,_=scene(160,1.02,'y','marks')
    with first,second:
        canvas=Image.new('RGB',(first.width+second.width+20,max(first.height,second.height)),'#555555')
        with canvas:
            canvas.paste(first,(0,0));canvas.paste(second,(first.width+20,0))
            with pytest.raises(detection.BoardDetectionError) as caught:
                detection.detect_board(canvas)
            assert caught.value.code=='UNSUPPORTED_IMAGE'


@pytest.mark.integration
@pytest.mark.parametrize('number',[25,26,29])
def test_reviewed_rectangular_screenshots_and_hidden_first_file(number):
    path=ROOT/f'.cache/real-use-tests/real-use-{number}.png'
    if not path.exists():pytest.skip('Local development screenshot is unavailable.')
    data=load_manifest()
    row=next(r for r in data['samples'] if r['id']==f'real-use-{number}')
    with Image.open(path) as source, source.convert('RGB') as image:
        actual=detection.detect_board(image)
        assert max(abs(a-b) for a,b in zip(actual.as_box(),row['gridBox']))<=2
        x,y,right,bottom=row['gridBox']
        pixels=np.asarray(image).copy()
        pixels[y:bottom,x:x+14]=[51,51,51]
        with Image.fromarray(pixels) as incomplete:
            with pytest.raises(detection.BoardDetectionError) as caught:
                detection.detect_board(incomplete)
            assert caught.value.code=='BOARD_NOT_FOUND'


@pytest.mark.unit
def test_registered_positions_keep_historical_identities_and_partitions():
    # This check does not require local images or neural dependencies.
    data=json.loads((ROOT/'data/manifests/real-use-development-v1.json').read_text())
    previous=json.loads((ROOT/'data/manifests/video-development-v2.json').read_text())
    references={r['sha256']:r for r in previous['samples']}
    assert [r['id'] for r in data['samples']]==[f'real-use-{n}' for n in range(1,31)]
    assert len({r['sha256'] for r in data['samples']})==30
    assert data['independentFinalEvaluation'] is False
    assert {r['split'] for r in data['samples']}=={'development'}
    inherited=0
    for row in data['samples']:
        if row['sha256'] in references:
            inherited+=1
            assert all(row[k]==references[row['sha256']][k] for k in
                       ('positionId','sourceGroupId','split','piecePlacement','orientation'))
    assert inherited==15
