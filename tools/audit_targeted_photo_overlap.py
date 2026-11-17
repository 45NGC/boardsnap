"""Compare targeted photographs with existing, non-final validation annotations.

Read-only for source data, partitions and models. Unknown provenance is recorded
as unknown, never treated as evidence that two games are independent.
"""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from tools.capture_lichess import expand_placement
from tools.position_dataset import placement_family
from tools.prepare_phone_photos import ROOT, child, digest, write_json


def source_key(source):
    platform = source.get('platform', source.get('category'))
    if source.get('videoId'):
        return ('video', str(source['videoId']))
    if platform in ('chesscom', 'lichess') and source.get('gameId'):
        return (platform, str(source['gameId']))
    return None


def compare_position(session, samples):
    placement = session['label']['piecePlacement']
    family = placement_family(placement)
    flat = ''.join(expand_placement(placement))
    known = source_key(session['source'])
    exact, families, sources, distances = [], [], [], []
    for row in samples:
        other = row.get('label', {}).get('piecePlacement', row.get('piecePlacement'))
        if other:
            if other == placement:
                exact.append(row['id'])
            if placement_family(other) == family:
                families.append(row['id'])
            other_flat = ''.join(expand_placement(other))
            distances.append((sum(a != b for a, b in zip(flat, other_flat, strict=True)), row['id']))
        if known is not None and known == source_key(row.get('source', {})):
            sources.append(row['id'])
    minimum = min((n for n, _ in distances), default=None)
    return {
        'exactPositionMatches': exact, 'positionFamilyMatches': families,
        'knownSourceMatches': sources,
        'minimumDifferentSquares': minimum,
        'nearestPositionIds': [sid for n, sid in distances if n == minimum],
        'note': 'Square distance is a screening clue, not a game-identity test or move distance.',
    }


def inspect_images(rows, root):
    """Check original/normalized bytes and compute actual decoded pixel hashes."""
    checked = []
    for row in rows:
        for path, sha in (('originalPath', 'originalSha256'), ('imagePath', 'imageSha256')):
            if digest(child(root, row[path])) != row[sha]:
                raise ValueError(f'Changed input: {row["id"]}')
        with Image.open(child(root, row['imagePath'])) as image:
            if image.mode != 'RGB' or list(image.size) != row['imageSize']:
                raise ValueError(f'Changed pixels or dimensions: {row["id"]}')
            pixels = hashlib.sha256(image.tobytes()).hexdigest()
        if row.get('pixelSha256', pixels) != pixels:
            raise ValueError(f'Changed normalized pixels: {row["id"]}')
        checked.append({'id': row['id'], 'originalSha256': row['originalSha256'],
                        'imageSha256': row['imageSha256'], 'pixelSha256': pixels})
    return checked


def audit(root=ROOT):
    paths = {
        'targeted': 'data/manifests/phone-targeted-intake-v1.json',
        'validation': 'data/manifests/phone-validation-v1.json',
        'development': 'data/manifests/phone-photos-v1.json',
        'digitalPositions': 'data/manifests/digital-positions-v1.json',
        'phonePartitionPlan': 'data/manifests/phone-training-v1.json',
    }
    inputs = {k: json.loads(child(root, p).read_text()) for k, p in paths.items()}
    target, validation = inputs['targeted'], inputs['validation']
    if target['independentFinalEvaluation'] or validation['independentFinalEvaluation']:
        raise ValueError('This audit must not use independent final evaluation data.')
    plan = inputs['phonePartitionPlan']
    if plan['inputs']['validationManifest']['sha256'] != digest(child(root, paths['validation'])):
        raise ValueError('Validation differs from the photographic training partition plan.')
    if any(row['split'] != 'validation' for row in validation['samples']):
        raise ValueError('Unexpected validation assignment.')
    target_images = inspect_images(target['images'], root)
    validation_images = inspect_images(validation['samples'], root)
    duplicate_matches = []
    for row in target_images:
        for other in validation_images:
            kinds = [k for k in ('originalSha256', 'imageSha256', 'pixelSha256') if row[k] == other[k]]
            if kinds:
                duplicate_matches.append({'targetId': row['id'], 'validationId': other['id'], 'matchedBy': kinds})
    groups = {g['groupId']: g for g in inputs['digitalPositions']['groups']}
    digital_validation = [dict(id=p['positionId'], piecePlacement=p['piecePlacement'], source={})
                          for p in inputs['digitalPositions']['positions']
                          if groups[p['groupId']]['split'] == 'validation']
    sessions = []
    for session in target['sessions']:
        comparisons = {
            'phoneValidation': compare_position(session, validation['samples']),
            'previousPhoneDevelopment': compare_position(session, inputs['development']['samples']),
            'generatedDigitalValidation': compare_position(session, digital_validation),
        }
        duplicates = [m for m in duplicate_matches if m['targetId'] in session['photoImageIds'] + session['referenceImageIds']]
        conflicts = bool(duplicates) or any(
            comparisons[k]['positionFamilyMatches'] or comparisons[k]['knownSourceMatches']
            for k in ('phoneValidation', 'generatedDigitalValidation'))
        sessions.append({
            'sessionId': session['id'], 'groupId': session['groupId'],
            'photoCount': len(session['photoImageIds']), 'sourceIdentity': source_key(session['source']),
            'comparisons': comparisons, 'duplicateFilesOrPixels': duplicates,
            'status': 'overlap-found' if conflicts else 'no-observed-overlap',
            'provenanceStatus': 'known-game-id' if source_key(session['source']) else 'unresolved-game-id',
        })
    return {
        'schemaVersion': 1, 'reportId': 'phone-targeted-overlap-v1',
        'scope': 'New targeted intake versus existing non-final phone validation; annotation comparisons also cover prior phone development and generated digital validation positions.',
        'inputs': {k: {'path': p, 'sha256': digest(child(root, p))} for k, p in paths.items()},
        'counts': {'targetPhotos': sum(r['kind'] == 'phone-photo' for r in target['images']),
                   'targetReferences': sum(r['kind'] == 'direct-screenshot' for r in target['images']),
                   'targetPositions': len(sessions), 'validationPhotos': len(validation['samples']),
                   'previousDevelopmentPhotos': len(inputs['development']['samples']),
                   'generatedDigitalValidationPositions': len(digital_validation),
                   'validationPhotosWithKnownSourceId': sum(source_key(r['source']) is not None for r in validation['samples']),
                   'validationPhotosWithoutKnownSourceId': sum(source_key(r['source']) is None for r in validation['samples'])},
        'imageIntegrity': {'targetedFilesAndPixelsChecked': target_images, 'validationFilesAndPixelsChecked': validation_images},
        'sessions': sessions,
        'observedOverlap': any(s['status'] == 'overlap-found' for s in sessions),
        'sourceIndependenceFullyVerified': False,
        'limitations': [
            'New Lichess series 5 and 6 have no game IDs. The user confirmed they are different from one another, not from all older sources.',
            'Twenty validation photos have no verified game/video ID. Unmatched known IDs cannot rule out a relation to those unknown sources.',
            'Different placements, pixel hashes or capture dates cannot establish different games.',
            'The digital comparison uses only validation positions from the generated plan; it is not a complete audit of every legacy or real-use corpus.',
            'This reused validation is for development/model selection, not a fresh independent acceptance evaluation.',
        ],
        'decision': 'No assignments are changed. If there is no observed overlap, keep the paired groups intact for future training assembly, recording unresolved provenance; do not claim fully verified source independence.',
        'trainingRun': False, 'partitionsChanged': False, 'finalEvaluationAccessed': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'data/reports/phone-targeted-overlap-v1.json')
    args = parser.parse_args(argv)
    report = audit()
    write_json(args.report, report)
    print(json.dumps({'counts': report['counts'], 'observedOverlap': report['observedOverlap'],
                      'sourceIndependenceFullyVerified': report['sourceIndependenceFullyVerified']}))


if __name__ == '__main__':
    main()
