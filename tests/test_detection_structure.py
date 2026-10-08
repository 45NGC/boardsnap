"""Independent geometry fixtures for palette-free detection, not classification."""

import numpy as np
from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board

pytestmark = pytest.mark.unit


def scene(side=384, count=8, texture=False, marks=False, pieces=False):
    """Invented artwork with a priori geometry, never sampled from reserved images."""
    rng = np.random.default_rng(1703)
    colors = np.array(((180, 225, 246), (94, 51, 131)), dtype=np.int16)
    axis = np.minimum(np.arange(side) * count // side, count - 1)
    pixels = colors[(axis[:, None] + axis[None, :]) % 2].copy()
    if texture:
        grain = rng.integers(-14, 15, size=(side, side, 1))
        bands = (7 * np.sin(np.arange(side)[:, None, None] / 2.7)).astype(int)
        pixels += grain + bands
    board = Image.fromarray(np.clip(pixels, 0, 255).astype('uint8'))
    draw = ImageDraw.Draw(board)
    if marks:
        for row, col in ((1, 2), (3, 5), (6, 4), (7, 2)):
            draw.rectangle((col*side//8, row*side//8, (col+1)*side//8-1, (row+1)*side//8-1), fill='#e4ba36')
    if pieces:
        for row in (0, 1, 6, 7):
            for col in range(8):
                x, y, cell = col*side/8, row*side/8, side/8
                draw.ellipse((x+cell*.25, y+cell*.18, x+cell*.75, y+cell*.85),
                             fill='black' if row<4 else 'white', outline='#444444')
    if marks:
        draw.line((side*.18, side*.8, side*.8, side*.2), fill='#328344', width=max(2, side//55))
        draw.polygon([(side*.8, side*.2),(side*.69,side*.23),(side*.77,side*.31)], fill='#328344')
    image = Image.new('RGB', (side + 179, side + 113), '#292b31')
    image.paste(board, (41, 29))
    return image


@pytest.mark.parametrize('side', [128, 193, 384, 768])
@pytest.mark.parametrize('texture,marks,pieces', [(False,False,False),(True,False,True),
                                               (False,True,True),(True,True,True)])
def test_structure_handles_new_colors_texture_overlays_and_sizes(side, texture, marks, pieces):
    image = scene(side, texture=texture, marks=marks, pieces=pieces)
    original = image.tobytes()
    box = detect_board(image).as_box()
    assert max(abs(a-b) for a,b in zip(box, (41,29,41+side,29+side))) <= 2
    assert image.tobytes() == original


@pytest.mark.parametrize('count', [4, 6, 7, 9, 10, 12, 16])
def test_other_grid_dimensions_with_margins_are_rejected(count):
    with pytest.raises(BoardDetectionError):
        detect_board(scene(count=count, texture=True))


@pytest.mark.parametrize('box', [(41,29,41+350,29+384),(41+48,29+48,41+384,29+384),
                                 (41+10,29+10,41+374,29+374)])
def test_incomplete_textured_grid_is_rejected(box):
    with pytest.raises(BoardDetectionError):
        detect_board(scene(texture=True).crop(box))


@pytest.mark.parametrize('kind', ['noise','square','lines','stripes','random-cells'])
def test_square_surface_or_regular_lines_are_not_enough(kind):
    rng=np.random.default_rng(42)
    image=Image.new('RGB',(500,500),'#bbbbbb')
    draw=ImageDraw.Draw(image)
    if kind=='noise':
        image=Image.fromarray(rng.integers(0,256,(500,500,3),dtype=np.uint8))
    elif kind=='square':
        draw.rectangle((40,40,439,439), fill='#73508a',outline='black',width=4)
    elif kind=='lines':
        for i in range(9):
            draw.line((40+i*50,40,40+i*50,440),fill='black',width=2)
            draw.line((40,40+i*50,440,40+i*50),fill='black',width=2)
    elif kind=='stripes':
        for i in range(8):
            draw.rectangle((40+i*50,40,89+i*50,439),fill='#73508a' if i%2 else '#8dcad6')
    else:
        for r in range(8):
            for c in range(8):
                draw.rectangle((40+c*50,40+r*50,89+c*50,89+r*50),
                               fill='#73508a' if rng.integers(2) else '#8dcad6')
    with pytest.raises(BoardDetectionError):
        detect_board(image)


def test_two_different_palettes_still_report_multiple_boards():
    from tests.test_detection import draw_grid
    image=Image.new('RGB',(750,420),'#555555')
    image.paste(draw_grid(),(5,9))
    image.paste(scene(256).crop((41,29,297,285)),(410,81))
    with pytest.raises(BoardDetectionError) as caught:
        detect_board(image)
    assert caught.value.code=='UNSUPPORTED_IMAGE'


@pytest.mark.parametrize('side', [1600, 2400])
def test_large_image_proposals_are_refined_in_original_pixel_coordinates(side):
    box=detect_board(scene(side,texture=True,marks=True,pieces=True)).as_box()
    assert max(abs(a-b) for a,b in zip(box,(41,29,41+side,29+side)))<=2


def test_rectangle_report_metrics_include_disjoint_and_shifted_boxes():
    from tools.evaluate_detection import rectangle_metrics
    assert rectangle_metrics((0,0,100,100),(0,0,100,100))=={
        'maxEdgeErrorPixels':0,'intersectionOverUnion':1.0}
    shifted=rectangle_metrics((1,0,101,100),(0,0,100,100))
    assert shifted['maxEdgeErrorPixels']==1
    assert shifted['intersectionOverUnion']==pytest.approx(9900/10100)
    assert rectangle_metrics((200,200,300,300),(0,0,100,100))['intersectionOverUnion']==0
