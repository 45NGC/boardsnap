"""Audit frozen preview prerequisites without inference or opening final images."""

import argparse
import json
from pathlib import Path

from tools.benchmark_preview import performance_passed
from tools.digital_acceptance import metric_gate
from tools.prepare_screen_preview import check_frozen
from tools.verify_preview import sha256, verify

ROOT = Path(__file__).resolve().parents[1]


def assess(policy, photo, digital_regression, cpu, installation):
    """Consulted evidence can block readiness but cannot grant final acceptance."""
    technical = {}
    for mode in ('digital', 'photo'):
        expected = policy['models'][mode]['sha256']
        if cpu[mode]['modelSha256'] != expected or installation[mode]['modelSha256'] != expected:
            raise ValueError('Installation/CPU evidence belongs to different weights.')
        technical[mode] = (installation[mode].get('passed') is True
                           and performance_passed(cpu[mode], policy['cpu'][mode]))
    if photo['modelSha256'] != policy['models']['photo']['sha256']:
        raise ValueError('Photo measurements belong to a different model.')
    if digital_regression['modelSha256'] != policy['models']['digital']['sha256']:
        raise ValueError('Digital regression belongs to a different model.')
    summary = photo['summary']
    count = summary['images']
    threshold = policy['acceptance']['photo']['thresholds']
    gates = [metric_gate('consulted-photo-exact-board-rate',
                         summary['automaticExactBoards']/count if count else None, threshold['exactBoardRate'])]
    for category in policy['catalogue']['photo']['sources']:
        entry = photo.get('byCategory', {}).get(category, {})
        n = entry.get('images', 0)
        gates.append(metric_gate(f'consulted-photo-source/{category}',
            entry.get('automaticExactBoards', 0)/n if n else None, threshold['stratumExactBoardRate']))
    current_py = {k: v for k, v in policy['runtimeSha256'].items() if k.endswith('.py')}
    previous = digital_regression.get('runtimeSha256', {})
    changed = sorted(k for k in set(current_py) | set(previous) if current_py.get(k) != previous.get(k))
    return {'status': 'not-finally-evaluated', 'finalEvaluationExecuted': False,
            'finalAcceptanceGranted': False, 'independentDataConsumed': False,
            'technicalChecksPassed': technical,
            'photo': {'exactBoards': summary['automaticExactBoards'], 'images': count,
                      'gatesOnConsultedData': gates,
                      'qualityReady': all(g['passed'] for g in gates),
                      'scope': 'Readiness diagnostic only; not all final gates and not independent evidence.'},
            'digital': {'previousRegressionPassed': digital_regression.get('passed') is True,
                        'runtimeFilesDifferentFromPreviousRegression': changed,
                        'currentRegressionEvidenceComplete': not changed and digital_regression.get('passed') is True,
                        'note': 'A 40-image CPU sample and clean installation do not replace full current regressions or independent acceptance.'},
            'independentCorpus': {'reviewed': False,
                'note': 'No independent corpus is supplied to this audit. Do not relabel consulted photos or screenshots.'},
            'next': ['Confirm digital-only acceptance with photos experimental, or require both modes.',
                     'Refresh digital regression evidence for the exact frozen runtime before final inference.',
                     'Photo quality must meet the frozen targets on development/validation before spending new independent photos.',
                     'Prepare and review independent source groups, labels and conditions; preserve final attempt history.']}


def audit(policy_path, release_report_path):
    policy = json.loads(policy_path.read_text())
    release_report = json.loads(release_report_path.read_text())
    if sha256(policy_path) != release_report['policySha256']:
        raise ValueError('Policy differs from the distributed preview.')
    check_frozen(policy)
    directory = ROOT / release_report['release']
    release = verify(directory, release_report['releaseManifestSha256'])
    if release['policySha256'] != sha256(policy_path):
        raise ValueError('Distributed policy changed.')
    evidence = {}

    def load_report(name, expected):
        path = ROOT / name
        if sha256(path) != expected:
            raise ValueError(f'Frozen evidence changed: {name}')
        evidence[name] = expected
        return json.loads(path.read_text())

    cpu, installation = {}, {}
    for mode in ('digital', 'photo'):
        for kind, mapping in (('cpu', cpu), ('installation', installation)):
            name = f'data/reports/screen-preview-{mode}-{kind}-v1.json'
            item = load_report(name, release['files'][f'reports/{mode}-{kind}.json'])
            if item['policySha256'] != sha256(policy_path):
                raise ValueError('Evidence refers to another policy.')
            mapping[mode] = item
    photo_name = 'data/reports/photo-pipeline-validation-v2.json'
    digital_name = 'data/reports/digital-regressions-anisotropic-candidate.json'
    photo = load_report(photo_name, policy['evidence'][photo_name])
    digital = load_report(digital_name, policy['evidence'][digital_name])
    for name, expected in photo['codeSha256'].items():
        if sha256(ROOT/name) != expected:
            raise ValueError('Photo results no longer describe the current pipeline.')
    result = assess(policy, photo, digital, cpu, installation)
    result.update(policySha256=sha256(policy_path), releaseManifestSha256=release_report['releaseManifestSha256'],
                  evidenceSha256=evidence, auditCodeSha256=sha256(Path(__file__)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, default=ROOT/'data/manifests/screen-preview-v1.json')
    parser.add_argument('--release-report', type=Path, default=ROOT/'data/reports/screen-preview-v1.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Preserve prior audits; choose a new output file.')
    result = audit(args.policy, args.release_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'photoQualityReady': result['photo']['qualityReady'],
                      'digitalRegressionCurrent': result['digital']['currentRegressionEvidenceComplete'],
                      'finalEvaluationExecuted': False}))
    return 1  # This audit never grants independent acceptance or starts inference.


if __name__ == '__main__':
    raise SystemExit(main())
