"""Audit saved mixed-training errors and teacher targets without model inference."""

import argparse
import hashlib
from collections import Counter
from html import escape
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.analyze_targeted_regressions import changes
from tools.mixed_training_policy import DEFAULT_PLAN, reference_records
from tools.neural_data import digest, load_board
from tools.position_dataset import LABELS
from tools.prepare_phone_photos import ROOT, write_json


OBSERVATIONS = {
    ('chesscom-img_5397', 'e3'): 'Empty dark wood with moire and small arrow fragments at left corners; no piece body.',
    ('lichess-img_5390', 'd8'): 'Empty dark wood with vertical grain and photographic bands; no overlay in this cell.',
    ('lichess-img_5392', 'a7'): 'Complete shaded black pawn, centered; head, collar and base remain visible.',
    ('lichess-img_5392', 'c5'): 'Empty dark wood with diagonal photographic bands; no piece or overlay in this cell.',
    ('video-img_5404', 'e4'): 'Empty light cell with strong coloured screen interference; nearby pieces remain inside their cells.',
    ('video-img_5404', 'e3'): 'Empty dark green cell with strong periodic screen interference; no piece body.',
}


def audit_teacher(labels, targets, board_ids, cell_ids, refs, teacher_pools):
    """Count repeated exposures separately from distinct annotated training cells."""
    labels = np.asarray(labels)
    if (targets.shape != (len(labels), len(LABELS)) or len(board_ids) != len(labels)
            or len(cell_ids) != len(labels) or not np.isfinite(targets).all()):
        raise ValueError('Invalid teacher arrays.')
    if any(r['row']['split'] != 'training' for r in refs):
        raise ValueError('Teacher audit accepts training records only.')
    for b, c, label in zip(board_ids, cell_ids, labels, strict=True):
        if not 0 <= int(b) < len(refs) or not 0 <= int(c) < 64:
            raise ValueError('Invalid sampled cell index.')
        if refs[int(b)]['row']['cells'][int(c)]['classId'] != int(label):
            raise ValueError('Training label differs from annotation.')
    pools = np.array([refs[int(b)]['pool'] for b in board_ids])
    mask = np.isin(pools, teacher_pools)
    if not np.allclose(targets[mask].sum(axis=1), 1, atol=1e-5):
        raise ValueError('Teacher probabilities do not sum to one.')
    predicted = targets.argmax(axis=1)
    counts = Counter(zip(map(int, board_ids), map(int, cell_ids)))
    representatives = {}
    for i, key in enumerate(zip(map(int, board_ids), map(int, cell_ids))):
        if key in representatives:
            prior = representatives[key]
            if labels[i] != labels[prior] or not np.array_equal(targets[i], targets[prior]):
                raise ValueError('Repeated training cell has inconsistent targets.')
        representatives[key] = i
    conflicts = []
    for (b, c), i in representatives.items():
        if not mask[i] or labels[i] == predicted[i]:
            continue
        row = refs[b]['row']
        if row['cells'][c]['classId'] != labels[i]:
            raise ValueError('Training label differs from annotation.')
        conflicts.append({'boardIndex': b, 'cellIndex': c, 'image': row['image'],
                          'originalPath': row.get('originalPath'), 'square': row['cells'][c]['square'],
                          'pool': refs[b]['pool'], 'expected': LABELS[int(labels[i])],
                          'teacher': LABELS[int(predicted[i])], 'exposures': counts[b, c],
                          'teacherExpectedProbabilityAtTemperature2': float(targets[i, labels[i]])})
    coverage = []
    for pool in sorted(set(pools)):
        chosen = pools == pool
        empty = chosen & (labels == 0)
        coverage.append({'pool': pool, 'samples': int(chosen.sum()), 'emptySamples': int(empty.sum()),
                         'distinctEmptyCells': len(set(zip(board_ids[empty].tolist(), cell_ids[empty].tolist()))),
                         'boards': len(set(board_ids[chosen].tolist())),
                         'teacherConflictingSamples': int((chosen & mask & (predicted != labels)).sum()),
                         'teacherFalsePieceSamples': int((empty & mask & (predicted != 0)).sum())})
    return {'teacherSamples': int(mask.sum()), 'conflictingSamples': sum(c['exposures'] for c in conflicts),
            'distinctConflictingCells': len(conflicts),
            'falsePieceSamples': sum(c['exposures'] for c in conflicts if c['expected'] == 'empty'),
            'distinctFalsePieceCells': sum(c['expected'] == 'empty' for c in conflicts),
            'coverage': coverage, 'conflicts': conflicts}


def panel(output, name, pixels, cells, title):
    """Render canonical existing crops; the export never changes training pixels."""
    canvas = Image.new('RGB', (max(750, 530 + 190 * len(cells)), 550), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((5, 5), title, fill='black')
    for i, cell in enumerate(pixels):
        canvas.paste(Image.fromarray(cell), (i % 8 * 64, 30 + i // 8 * 64))
    for j, cell in enumerate(cells):
        i = cell['index']
        draw.rectangle((i % 8 * 64, 30 + i // 8 * 64, i % 8 * 64 + 63, 30 + i // 8 * 64 + 63),
                       outline='red', width=2)
        canvas.paste(Image.fromarray(pixels[i]).resize((176, 176), Image.Resampling.NEAREST), (530 + j * 190, 70))
        draw.text((530 + j * 190, 40), cell['text'], fill='black')
    path = output / f'{name}.png'
    canvas.save(path)
    return path.name


def analyze(output, root=ROOT):
    output.mkdir(parents=True, exist_ok=True)
    plan = json.loads((root / DEFAULT_PLAN.relative_to(ROOT)).read_text())
    run = root / plan['runDirectory']
    history = json.loads((run / 'training.json').read_text())
    if not history['complete'] or history['completedEpochs'] != 12:
        raise ValueError('Expected the completed bounded attempt.')
    baseline = reference_records(plan, root)
    epochs = []
    inputs = {}
    for item in history['history']:
        path = run / item['predictions']
        if digest(path) != item['predictionsSha256']:
            raise ValueError('Saved prediction hash changed.')
        prediction = json.loads(path.read_text())
        for domain, records in baseline.items():
            for old, new in zip(records, prediction['records'][domain], strict=True):
                if old['image'] != new['image'] or old['expected'] != new['expected']:
                    raise ValueError('Unaligned saved predictions.')
        epochs.append(prediction)
        inputs[str(path.relative_to(root))] = digest(path)
    data = root / '.cache/mixed-training-v1'
    refs = [json.loads(line) for line in (data / 'training-boards.jsonl').read_text().splitlines()]
    validation = {r['row']['image']: r for r in map(json.loads, (data / 'validation.jsonl').read_text().splitlines())}
    labels = np.load(data / 'training-labels.npy', allow_pickle=False)
    with np.load(data / 'sampling-epoch-000.npz', allow_pickle=False) as sample:
        board_ids, cell_ids = sample['board_indices'], sample['cell_indices']
    target_path = run / 'teacher-targets.npy'
    target_meta = json.loads((run / 'teacher-cache.json').read_text())
    signature = json.loads((run / 'execution.json').read_text())
    if signature['planSha256'] != digest(root / DEFAULT_PLAN.relative_to(ROOT)):
        raise ValueError('Frozen plan changed.')
    if signature['datasetSha256'] != digest(data / 'dataset.json'):
        raise ValueError('Prepared dataset changed.')
    dataset = json.loads((data / 'dataset.json').read_text())
    for name, entry in dataset['artifacts'].items():
        if digest(data / name) != entry['sha256']:
            raise ValueError('Prepared artifact changed.')
    mask = np.asarray([refs[int(b)]['pool'] in plan['loss']['teacherPools'] for b in board_ids], dtype=np.bool_)
    if target_meta['signature'] != dict(signature, maskSha256=hashlib.sha256(mask.tobytes()).hexdigest()):
        raise ValueError('Teacher cache belongs to another execution.')
    if digest(target_path) != target_meta['sha256']:
        raise ValueError('Teacher cache hash changed.')
    targets = np.load(target_path, mmap_mode='r', allow_pickle=False)
    teacher = audit_teacher(labels, targets, board_ids, cell_ids, refs, plan['loss']['teacherPools'])
    cases, delta, cards = [], [], []
    for n, (old, new) in enumerate(zip(baseline['phone'], epochs[-1]['records']['phone'], strict=True)):
        edits = changes(old['expected'], old['predictions'], new['predictions'])
        delta.extend(dict(image=old['image'], **edit) for edit in edits)
        regressions = [e for e in edits if e['change'] == 'regression']
        if not regressions:
            continue
        ref = validation[old['image']]
        if ref['row']['split'] != 'validation':
            raise ValueError('Unexpected split.')
        pixels, expected = load_board(root / ref['sourceDataset'], ref['row'])
        if expected.tolist() != old['expected']:
            raise ValueError('Saved predictions do not match crop labels.')
        for c in regressions:
            c['epochPredictions'] = [LABELS[e['records']['phone'][n]['predictions'][c['index']]] for e in epochs]
            c['background'] = ref['row']['cells'][c['index']]['background']
            c['visualReview'] = OBSERVATIONS[(Path(old['image']).stem, c['square'])]
        preview = panel(output, Path(old['image']).stem, pixels,
                        [{'index': c['index'], 'text': f"{c['square']}: {c['expected']} -> {c['candidate']}"} for c in regressions],
                        Path(old['image']).name)
        cards.append((preview, old['image']))
        cases.append({'image': old['image'], 'arraySha256': ref['row']['arraySha256'],
                      'boundsMode': ref['row']['boundsMode'], 'conditions': ref['row'].get('conditions'),
                      'regressions': regressions, 'preview': preview})
    # Visual checks are limited to the seven conflicting empty cells, not all teacher errors.
    for n, c in enumerate(x for x in teacher['conflicts'] if x['expected'] == 'empty'):
        ref = refs[c['boardIndex']]
        pixels, expected = load_board(root / ref['sourceDataset'], ref['row'])
        if expected[c['cellIndex']] != 0:
            raise ValueError('Expected an empty annotated training cell.')
        preview = panel(output, f'teacher-empty-{n+1}', pixels,
                        [{'index': c['cellIndex'], 'text': f"{c['square']}: empty -> {c['teacher']}"}],
                        Path(c['originalPath']).name)
        cards.append((preview, c['originalPath']))
        c['preview'] = preview
    for path in (data / 'training-boards.jsonl', data / 'validation.jsonl', data / 'training-labels.npy',
                 data / 'sampling-epoch-000.npz', target_path, root / DEFAULT_PLAN.relative_to(ROOT), run / 'training.json'):
        inputs[str(path.relative_to(root))] = digest(path)
    weights = np.asarray(plan['loss']['classWeights'])
    counts = np.bincount(labels, minlength=13)
    if counts.tolist() != plan['loss']['classCounts']:
        raise ValueError('Frozen class counts differ.')
    mass = counts * weights
    report = {'schemaVersion': 1, 'inputs': inputs, 'analysisCodeSha256': digest(Path(__file__)),
              'scope': 'Saved predictions, sampled training targets and existing verified crops only.',
              'trainingRun': False, 'inferenceRun': False, 'finalEvaluationAccessed': False,
              'changes': dict(Counter(c['change'] for c in delta)), 'allChangedCells': delta,
              'regressionCases': cases, 'teacher': teacher,
              'lossContext': {'emptySampleFraction': float(counts[0] / counts.sum()),
                              'emptyNominalWeightMassFraction': float(mass[0] / mass.sum()),
                              'queenBlackToEmptyWeightRatio': float(weights[11] / weights[0]),
                              'note': 'Nominal summed CE weights, not observed gradient magnitudes. Batch weighted-mean normalization and KL also matter.'},
              'digitalChangedCellsAtLastEpoch': sum(a != b for old, new in zip(baseline['digital'], epochs[-1]['records']['digital'], strict=True)
                                                     for a, b in zip(old['predictions'], new['predictions'], strict=True)),
              'recommendation': 'Keep phone-v1. Propose one future isolated ablation excluding the 19 sampled exposures of seven visually checked empty cells from KL when the teacher predicts a piece; retain CE for every sample and all other KL targets. Use a label-based rule, not validation IDs. Do not train in this review.',
              'limitations': ['No causal proof that teacher conflicts explain validation regressions.',
                              'No automatic detector rerun; geometric claims limited to visual review of existing verified crops.',
                              'Old photo provenance is partly unknown; different placements do not prove unrelated games.',
                              'No claim that current CNN capacity is insufficient.',
                              'Validation has already been consulted and is not independent final evaluation.']}
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Mixed training review</title>'
        '<style>body{font-family:sans-serif}img{max-width:100%}</style><h1>Saved crops: validation and training</h1>'
        + ''.join(f'<h2>{escape(title)}</h2><img src="{escape(preview)}">' for preview, title in cards))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.cache/mixed-review-v1')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / '.cache'):
        raise ValueError('Keep previews inside .cache.')
    report = analyze(args.output)
    write_json(ROOT / 'data/reports/mixed-training-review-v1.json', report)
    print(json.dumps({'changes': report['changes'], 'teacherConflictingSamples': report['teacher']['conflictingSamples'],
                      'teacherDistinctFalsePieces': report['teacher']['distinctFalsePieceCells']}))


if __name__ == '__main__':
    main()
