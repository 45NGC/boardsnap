"""Profile isolation, provenance and regression on fixed real image groups."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import detect_orientation
from boardsnap.pipeline import recognize_image
from boardsnap.profiles import DEFAULT_PROFILE, PROFILES, get_profile

ROOT = Path(__file__).resolve().parents[1]
NEW_PROFILES = tuple(p for p in PROFILES if p != DEFAULT_PROFILE)
BOOK = 'book-strategy-hatched-v1'


def samples():
    for profile in NEW_PROFILES:
        manifest = json.loads((ROOT / f'data/manifests/{profile}.json').read_text())
        for position in manifest['positions']:
            for view in position.get('views', ('white', 'black')):
                split = position['split']
                folder = ROOT / ('data/tuning' if split == 'tuning' else 'tests/fixtures/evaluation') / profile
                path = folder / f"{position['groupId']}-{view}.png"
                yield pytest.param(profile, path, position['piecePlacement'], f'{view}-bottom',
                                   id=f"{profile}-{path.stem}",
                                   marks=pytest.mark.evaluation if split == 'evaluation' else pytest.mark.integration)


@pytest.mark.parametrize('profile,path,placement,view', list(samples()))
def test_real_profile_geometry_orientation_and_position(profile, path, placement, view):
    annotation = json.loads(path.with_suffix('.json').read_text())
    assert annotation['profileId'] == profile
    assert annotation['piecePlacement'] == placement
    assert annotation['orientation'] == view
    assert annotation['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    b = annotation['boardBounds']
    expected_box = (round(b['x']), round(b['y']), round(b['x'] + b['width']), round(b['y'] + b['height']))
    with read_image(path) as source:
        bounds = detect_board(source, profile=profile)
        # Print bounds were manually inspected and are approximate; digital
        # annotations are DOM bounds with up to two pixels of rasterization.
        tolerance = 12 if profile == BOOK else 2
        assert max(abs(a-b) for a,b in zip(bounds.as_box(), expected_box, strict=True)) <= tolerance
        with normalize_board(source, bounds) as board:
            assert detect_orientation(board, profile=profile) == view
    actual = recognize_image(path, profile=profile)
    if profile == BOOK and annotation['split'] == 'evaluation':
        # Preserve the full held-out report, including the two failed positions.
        # No expected recognition is fabricated to make the experiment pass.
        report = json.loads((ROOT / f'data/reports/{profile}-classification-evaluation.json').read_text())
        baseline = next(i for i in report['images'] if i['image'] == path.relative_to(ROOT).as_posix())
        assert actual == {'piecePlacement': baseline['actual']}
        assert actual != {'piecePlacement': placement}
    else:
        assert actual == {'piecePlacement': placement}


@pytest.mark.evaluation
@pytest.mark.parametrize('name', ['diag-003-white', 'diag-007-white'])
@pytest.mark.xfail(strict=True, reason='Experimental print baseline misclassifies one square in each held-out diagram; see measured report')
def test_book_full_position_acceptance_is_not_yet_met(name):
    path = ROOT / 'tests/fixtures/evaluation' / BOOK / f'{name}.png'
    expected = json.loads(path.with_suffix('.json').read_text())['piecePlacement']
    assert recognize_image(path, profile=BOOK) == {'piecePlacement': expected}


@pytest.mark.unit
@pytest.mark.parametrize('value', ['unknown', '../../asset', '', None, []])
def test_unknown_profile_is_not_silently_replaced(value):
    with pytest.raises(ValueError, match='Unknown recognition profile'):
        get_profile(value)


@pytest.mark.unit
@pytest.mark.parametrize('profile', NEW_PROFILES)
@pytest.mark.parametrize('kind', ['blank', 'frame', 'stripes'])
def test_profile_negatives_do_not_invent_a_position(profile, kind):
    with Image.new('RGB', (650, 650), 'white') as image:
        draw = ImageDraw.Draw(image)
        if kind == 'frame':
            draw.rectangle((10,10,640,640),outline='black',width=5)
        if kind == 'stripes':
            for col in range(8):
                draw.rectangle((col*80,0,(col+1)*80-1,639),fill=get_profile(profile).colors[col%2])
        with pytest.raises(BoardDetectionError) as error:
            detect_board(image,profile=profile)
        assert error.value.code == 'BOARD_NOT_FOUND'


@pytest.mark.integration
@pytest.mark.parametrize('profile', NEW_PROFILES)
def test_templates_and_originals_are_traced_only_to_tuning(profile):
    asset = get_profile(profile).piece_asset
    data = json.loads((ROOT / f'src/boardsnap/assets/{asset}.json').read_text())
    assert data['profileId'] == profile
    assert hashlib.sha256((ROOT / f'src/boardsnap/assets/{asset}.png').read_bytes()).hexdigest() == data['atlasSha256']
    assert {(t['label'],t['background']) for t in data['templates']} == {
        (label, background) for label in (None,*'PNBRQKpnbrqk') for background in ('light','dark')}
    for entry in data['templates']:
        path = ROOT / entry['source']['image']
        assert path.is_relative_to(ROOT / 'data/tuning' / profile)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['source']['sha256']
        annotation = path.with_suffix('.json')
        assert hashlib.sha256(annotation.read_bytes()).hexdigest() == entry['source']['annotationSha256']
        assert json.loads(annotation.read_text())['split'] == 'tuning'


@pytest.mark.integration
def test_same_positions_never_cross_partitions_between_themes_or_books():
    splits = {}
    for profile in PROFILES:
        manifest = json.loads((ROOT / f'data/manifests/{profile}.json').read_text())
        for position in manifest['positions']:
            key = position['piecePlacement']
            assert splits.setdefault(key, position['split']) == position['split']


@pytest.mark.integration
@pytest.mark.parametrize('profile', NEW_PROFILES)
def test_cli_profile_preserves_exact_json_and_empty_stderr(profile):
    name = 'diag-001-white' if profile == BOOK else 'pos-002-black'
    path = ROOT / 'data/tuning' / profile / f'{name}.png'
    expected = json.loads(path.with_suffix('.json').read_text())['piecePlacement']
    result = subprocess.run([sys.executable, '-m', 'boardsnap', '--profile', profile, str(path)],
                            capture_output=True,text=True,check=False)
    assert result.returncode == 0
    assert result.stdout == json.dumps({'piecePlacement':expected}) + '\n'
    assert result.stderr == ''


@pytest.mark.integration
def test_cli_unknown_profile_is_usage_error():
    result = subprocess.run([sys.executable,'-m','boardsnap','--profile','unknown','input.png'],
                            capture_output=True,text=True,check=False)
    assert result.returncode == 2
    assert result.stdout == ''
    assert 'invalid choice' in result.stderr


@pytest.mark.integration
@pytest.mark.parametrize('profile', NEW_PROFILES[:2])
def test_missing_coordinates_still_assume_white_bottom(profile, tmp_path):
    from boardsnap.orientation import _coordinate_boxes
    path = ROOT / 'data/tuning' / profile / 'pos-006-black.png'
    with read_image(path) as source:
        bounds = detect_board(source,profile=profile)
        draw = ImageDraw.Draw(source)
        boxes = _coordinate_boxes(bounds,profile)
        for axis, cells in enumerate(boxes):
            for i,(x1,y1,x2,y2) in enumerate(cells):
                parity = (7+i)%2 if axis == 0 or get_profile(profile).coordinates == 'lichess' else i%2
                draw.rectangle((x1,y1,x2-1,y2-1),fill=get_profile(profile).colors[parity])
        with normalize_board(source,bounds) as board:
            assert detect_orientation(board,profile=profile) == 'white-bottom'


@pytest.mark.integration
@pytest.mark.parametrize('profile', NEW_PROFILES[:2])
@pytest.mark.parametrize('scale', [.75, 1.25])
def test_digital_crops_translations_and_sizes(profile, scale, tmp_path):
    path = ROOT / 'data/tuning' / profile / 'pos-002-black.png'
    expected = json.loads(path.with_suffix('.json').read_text())['piecePlacement']
    with read_image(path) as source:
        bounds = detect_board(source,profile=profile)
        with source.crop(bounds.as_box()) as crop:
            side = round(crop.width*scale)
            with crop.resize((side,side),Image.Resampling.LANCZOS) as resized:
                with Image.new('RGB',(side+101,side+151),'#ededed') as canvas:
                    canvas.paste(resized,(37,69))
                    anonymous = tmp_path/'anonymous.png'
                    canvas.save(anonymous)
                    assert recognize_image(anonymous,profile=profile) == {'piecePlacement':expected}
