"""Inspect photographic detection only: save corners, an outline and a rectified preview."""

import argparse
import json
from pathlib import Path

from PIL import ImageDraw

from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError, read_image
from boardsnap.photo_detection import detect_photo_board
from tools.review_phone_geometry import rectify


def save_preview(image, corners, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with image.copy() as preview:
        preview.thumbnail((1200, 1200))
        points = [(x*preview.width/image.width, y*preview.height/image.height) for x, y in corners]
        draw = ImageDraw.Draw(preview)
        draw.line(points + [points[0]], fill='red', width=4)
        for i, (x, y) in enumerate(points, 1):
            draw.ellipse((x-5, y-5, x+5, y+5), fill='red')
            draw.text((x+7, y+7), str(i), fill='red')
        preview.save(destination / 'outline.jpg', quality=95)
    with rectify(image, [list(p) for p in corners]) as board:
        board.save(destination / 'rectified.png')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='Diagnostic directory inside .cache')
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if not output.is_relative_to(Path('.cache').resolve()):
        parser.error('Keep diagnostic output inside .cache.')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Choose a new or empty diagnostic directory; previous previews are preserved.')
    if args.image.resolve() in {output / name for name in ('outline.jpg', 'rectified.png', 'detection.json')}:
        parser.error('Output would overwrite the input image.')
    try:
        with read_image(args.image) as image:
            result = detect_photo_board(image)
            save_preview(image, result.corners, output)
            record = {'boardCorners': result.corners, 'cornerOrder': ['top-left', 'top-right', 'bottom-right', 'bottom-left'],
                      'imageSize': image.size, 'scope': 'Detection diagnostic only; no piece recognition or chess orientation.'}
        (output / 'detection.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record))
        return 0
    except (ImageInputError, BoardDetectionError) as error:
        print(json.dumps(error.to_dict()))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
