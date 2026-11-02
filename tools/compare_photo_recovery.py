"""Compare frozen photo recovery measurements without running inference again."""

import argparse
import json
from pathlib import Path

import numpy as np

from tools.evaluate_photo_detection import ROOT, digest


def matched(before, after):
    old = {row['id']: row for row in before}
    if len(old) != len(before) or len(after) != len(before) or {row['id'] for row in after} != set(old):
        raise ValueError('Reports must describe the same unique images.')
    pairs = [(old[row['id']], row) for row in after]
    for a, b in pairs:
        for key in ('imageSha256', 'groupId', 'split'):
            if a[key] != b[key]:
                raise ValueError('Image identity or partition changed.')
        if a['split'] not in ('development', 'training', 'validation'):
            raise ValueError('Reserved evaluation is not part of this comparison.')
    return pairs


def compare():
    paths = {f'{kind}{version}': ROOT/f'data/reports/photo-{kind}-v{version}.json'
             for kind in ('detection-development', 'detection-validation', 'detection-controls', 'pipeline-validation')
             for version in (1, 2)}
    reports = {key: json.loads(path.read_text()) for key, path in paths.items()}
    geometry = {}
    for cohort in ('development', 'validation'):
        before, after = (reports[f'detection-{cohort}{version}'] for version in (1, 2))
        if before['manifestSha256'] != after['manifestSha256'] or before['policy'] != after['policy']:
            raise ValueError('Geometry inputs or acceptance policy changed.')
        pairs = matched(before['records'], after['records'])
        old_valid = [(a, b) for a, b in pairs if 'detectedCorners' in a]
        lost = [a['id'] for a, b in old_valid if 'detectedCorners' not in b]
        changed = [a['id'] for a, b in old_valid if 'detectedCorners' in b and
                   not np.array_equal(a['detectedCorners'], b['detectedCorners'])]
        geometry[cohort] = {'before': before['summary'], 'after': after['summary'],
                            'lostDetections': lost, 'changedExistingCorners': changed,
                            'newDetections': [b['id'] for a, b in pairs if 'detectedCorners' not in a and 'detectedCorners' in b]}
    old, new = (reports[f'pipeline-validation{v}'] for v in (1, 2))
    if old['modelSha256'] != new['modelSha256'] or old['manifestSha256'] != new['manifestSha256']:
        raise ValueError('Model or photo manifest changed.')
    pairs = matched(old['records'], new['records'])
    lost_boards = [a['id'] for a, b in pairs if a['automaticExact'] and not b['automaticExact']]
    gained_boards = [b['id'] for a, b in pairs if not a['automaticExact'] and b['automaticExact']]
    changed_success = [a['id'] for a, b in pairs if a['cliExitCode'] == 0 and a['cliResult'] != b['cliResult']]
    controls = reports['detection-controls2']
    accepted = (all(not r['lostDetections'] and not r['changedExistingCorners'] and not r['after']['outOfTolerance']
                    for r in geometry.values()) and not lost_boards and not changed_success
                and bool(gained_boards) and controls['rejected'] == controls['images'])
    for key, report in reports.items():
        if key.endswith('2') and 'detectorSha256' in report:
            if report['detectorSha256'] != digest(ROOT/'src/boardsnap/photo_detection.py'):
                raise ValueError('Recovery report is stale.')
    for path, sha in new['codeSha256'].items():
        if digest(ROOT/path) != sha:
            raise ValueError('Full-pipeline report is stale.')
    if digest(ROOT/new['model']) != new['modelSha256']:
        raise ValueError('Photo weights changed after measurement.')
    return {'schemaVersion': 1, 'scope': 'Consulted development/validation, not independent final acceptance.',
            'codeSha256': digest(Path(__file__)), 'finalEvaluationAccessed': False, 'modelChanged': False,
            'inputs': {key: {'path': str(path.relative_to(ROOT)), 'sha256': digest(path)} for key, path in paths.items()},
            'accepted': accepted, 'geometry': geometry, 'controls': {'images': controls['images'], 'rejected': controls['rejected']},
            'pipeline': {'before': old['summary'], 'after': new['summary'], 'gainedExactBoards': gained_boards,
                         'lostExactBoards': lost_boards, 'changedPreviouslyReturnedPositions': changed_success},
            'remaining': ['video-img_5403 remains undetected.',
                          'video-img_5406 is detected within geometry tolerance but has a false black knight on h8.',
                          'Photographic style/moire classification gaps remain; no new training was run.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Choose a new report path.')
    result = compare()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'accepted': result['accepted'], 'pipeline': result['pipeline']}))


if __name__ == '__main__':
    main()
