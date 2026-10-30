"""Test the photo classifier with manual corners or an already rectified board.

Development tool, not automatic photographic board detection. Coordinates use
the EXIF-oriented image, in TL/TR/BR/BL order. No annotations or labels are read.
"""

import argparse
from contextlib import redirect_stdout
import json
import sys

import torch

from boardsnap.classification import ClassificationError
from boardsnap.image_input import ImageInputError, read_image
from boardsnap.neural import CLASSES, NeuralClassifier
from boardsnap.output import build_result
from tools.build_phone_squares import extract_photo_squares


def recognize_photo(path, model, *, orientation, corners=None, rectified=False):
    if (corners is None) == (not rectified):
        raise ValueError('Choose manual corners or an already rectified board.')
    with read_image(path) as image:
        if rectified:
            if image.width != image.height or image.width < 128:
                raise ValueError('A rectified input must be square, at least 128 pixels, with no margins.')
            corners = [[0, 0], [image.width, 0], [image.width, image.height], [0, image.height]]
        pixels = extract_photo_squares(image, corners, orientation)
    predictions = NeuralClassifier(model).predict_ids(pixels)
    labels = [None if value == 0 else CLASSES[value] for value in predictions]
    return build_result([labels[start:start + 8] for start in range(0, 64, 8)])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', help='PNG or JPEG photograph or rectified board')
    parser.add_argument('--model', required=True)
    parser.add_argument('--orientation', choices=('white-bottom', 'black-bottom'), required=True)
    geometry = parser.add_mutually_exclusive_group(required=True)
    geometry.add_argument('--corners', type=float, nargs=8, metavar='COORD', help='x1 y1 x2 y2 x3 y3 x4 y4 (TL/TR/BR/BL)')
    geometry.add_argument('--rectified', action='store_true', help='Input is already a square board without margins or perspective')
    args = parser.parse_args(argv)
    status = 0
    with redirect_stdout(sys.stderr):
        try:
            torch.set_num_threads(4)
            corners = [args.corners[i:i + 2] for i in range(0, 8, 2)] if args.corners else None
            result = recognize_photo(args.image, args.model, orientation=args.orientation,
                                     corners=corners, rectified=args.rectified)
        except (ImageInputError, ClassificationError) as error:
            result, status = error.to_dict(), 1
        except ValueError as error:
            result, status = {'error': {'code': 'INVALID_GEOMETRY', 'message': str(error)}}, 1
    print(json.dumps(result))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
