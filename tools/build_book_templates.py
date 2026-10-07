"""Build a bounded multi-example baseline from the five tuning book diagrams."""

from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

from PIL import Image

from boardsnap.detection import BoardBounds
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.output import build_result
from boardsnap.profiles import get_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'book-strategy-hatched-v1'
LABELS = (None, *'PNBRQKpnbrqk')


def build_templates(root=ROOT):
    folder = root / 'data/tuning' / PROFILE
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['profileId'] != PROFILE or any(p['split'] != 'tuning' for p in manifest['positions']):
        raise ValueError('Book templates require the fixed tuning split')
    entries, counts = [], Counter()
    with ExitStack() as stack:
        atlas = stack.enter_context(Image.new('RGB', (128, 3328)))
        for position in sorted(manifest['positions'], key=lambda p: p['groupId']):
            path = folder / f"{position['groupId']}-white.png"
            annotation = json.loads(path.with_suffix('.json').read_text())
            if (annotation['split'] != 'tuning' or annotation['profileId'] != PROFILE
                    or annotation['piecePlacement'] != position['piecePlacement']
                    or annotation['orientation'] != 'white-bottom'):
                raise ValueError('Inconsistent book annotation')
            labels = [[p for t in rank for p in ([None] * int(t) if t.isdigit() else [t])]
                      for rank in position['piecePlacement'].split('/')]
            if build_result(labels)['piecePlacement'] != position['piecePlacement']:
                raise ValueError('Noncanonical tuning placement')
            b = annotation['boardBounds']
            bounds = BoardBounds(b['x'], b['y'], b['width'], b['height'])
            with read_image(path) as source, normalize_board(source, bounds) as board:
                for row in range(8):
                    for col in range(8):
                        label, background = labels[row][col], ('light','dark')[(row+col)%2]
                        key = label, background
                        if counts[key] == 4:
                            continue
                        counts[key] += 1
                        ar, ac = divmod(len(entries), 2)
                        box = [ac*64, ar*64, (ac+1)*64, (ar+1)*64]
                        with board.image.crop((col*64,row*64,(col+1)*64,(row+1)*64)) as square:
                            atlas.paste(square, tuple(box))
                        entries.append(dict(label=label,background=background,atlasBox=box,source={
                            'image':path.relative_to(root).as_posix(),
                            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'annotationSha256':hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest(),
                            'row':row,'column':col,'orientation':'white-bottom','bounds':list(bounds.as_box())}))
        if set(counts) != {(p,b) for p in LABELS for b in ('light','dark')}:
            raise ValueError('Tuning data must cover all classes on both backgrounds')
        asset = get_profile(PROFILE).piece_asset
        destination = root / 'src/boardsnap/assets'
        atlas_path = destination / f'{asset}.png'
        with atlas.crop((0,0,128,64*((len(entries)+1)//2))) as compact:
            compact.save(atlas_path)
        data = dict(formatVersion=2,profileId=PROFILE,squareSize=64,
                    selection='First four samples per class/background; tuning diagrams only.',
                    atlasSha256=hashlib.sha256(atlas_path.read_bytes()).hexdigest(),templates=entries)
        (destination/f'{asset}.json').write_text(json.dumps(data,indent=2)+'\n')
    print(f'Wrote {len(entries)} book templates')


if __name__ == '__main__':
    build_templates()
