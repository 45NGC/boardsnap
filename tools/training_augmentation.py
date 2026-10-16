"""Append audited variants of existing training positions, without touching validation."""

import numpy as np

from tools.neural_data import digest, load_split, read_index


def validate_additions(base_rows, extra_rows):
    sources = {r['image']: r for r in base_rows}
    if not extra_rows:
        raise ValueError('Additional training variants are empty.')
    for row in extra_rows:
        source = sources.get(row.get('sourceImage'))
        if source is None or source['split'] != 'training' or row['split'] != 'training':
            raise ValueError('Additional variants must originate in existing training images only.')
        if row.get('sourceSha256') != source['sha256']:
            raise ValueError('Augmentation source pixels changed.')
        for key in ('positionId', 'groupId', 'piecePlacement', 'orientation', 'style'):
            if row.get(key) != source.get(key):
                raise ValueError('Augmentation identity differs from the training source.')


def add_training_variants(root, base_rows, train, *, marked_cells_only=False):
    metadata, rows = read_index(root)
    validate_additions(base_rows, rows)
    extra = load_split(root, rows, 'training', marked_cells_only=marked_cells_only)
    combined = tuple(np.concatenate((a, b)) for a, b in zip(train, extra, strict=True))
    provenance = {'datasetSha256': digest(root/'dataset.json'),
                  'indexSha256': metadata['indexes']['verified']['sha256'],
                  'trainingBoards': len(rows), 'trainingSquares': len(extra[1]),
                  'validationChanged': False, 'evaluationArraysLoaded': False}
    return combined, provenance
