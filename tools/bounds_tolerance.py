"""Controlled whole-board crop errors; labels and source partitions never change."""

from dataclasses import dataclass

import numpy as np
from PIL import Image

from boardsnap.detection import BoardBounds
from tools.build_square_dataset import extract_squares


@dataclass(frozen=True)
class Perturbation:
    name: str
    edges: tuple[int, int, int, int] = (0, 0, 0, 0)
    scale: float = 1.0
    resampling: str = 'LANCZOS'


# Frozen before measurement. Edge offsets are input screenshot pixels, not
# normalized-square pixels. Resampling happens before production normalization.
SCENARIOS = (
    Perturbation('reference'),
    *(Perturbation(f'shift-{axis}{delta:+d}',
                  (delta, 0, delta, 0) if axis == 'x' else (0, delta, 0, delta))
      for delta in (-1, 1, -2, 2) for axis in ('x', 'y')),
    Perturbation('inset-2', (2, 2, -2, -2)),
    Perturbation('outset-2', (-2, -2, 2, 2)),
    Perturbation('asymmetric-2', (1, -2, 2, -1)),
    Perturbation('resample-85-bilinear', scale=.85, resampling='BILINEAR'),
    Perturbation('resample-115-bicubic', scale=1.15, resampling='BICUBIC'),
)


def perturbed_squares(image, bounds, orientation, scenario):
    """Return canonical crops and actual exclusive bounds, without padding.

    An out-of-frame request is invalid and must be reported, never silently
    clipped or replaced. Pieces stay upright when the board faces Black.
    """
    edges = tuple(a + b for a, b in zip(bounds.as_box(), scenario.edges, strict=True))
    left, top, right, bottom = edges
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError('Perturbed bounds leave the source image.')
    box = BoardBounds(left, top, right-left, bottom-top)
    if scenario.scale == 1:
        return extract_squares(image, box, orientation), edges
    with image.crop(edges) as crop:
        size = tuple(max(8, round(side * scenario.scale)) for side in crop.size)
        with crop.resize(size, getattr(Image.Resampling, scenario.resampling)) as resized:
            return extract_squares(resized, BoardBounds(0, 0, *size), orientation), edges


def case_name(row):
    return row.get('overlayCase', '+'.join(row.get('conditions', ['clean'])))


def fixed_training_scenario(row, seed):
    """Independent of labels, predictions, row order and other partitions."""
    import hashlib
    key = f"{seed}:{row['image']}".encode()
    value = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big')
    return SCENARIOS[1 + value % (len(SCENARIOS)-1)]


def labels_for(row):
    return np.asarray([cell['classId'] for cell in row['cells']], dtype=np.int64)
