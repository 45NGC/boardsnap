"""Freeze and package a local digital/photo preview without reading final images."""

import argparse
from email.parser import BytesParser
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile

from tools.verify_preview import sha256, verify

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = 'screen-preview-v1'
POLICY = ROOT / 'data/manifests/screen-preview-v1.json'
MODELS = {'digital': '.cache/neural-tolerance-v1-conservative/best.pt',
          'photo': '.cache/neural-phone-v1/best.pt'}


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def runtime_files(root=ROOT):
    return {p.relative_to(root).as_posix(): sha256(p)
            for p in sorted((root / 'src/boardsnap').rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'} | {
                'pyproject.toml': sha256(root / 'pyproject.toml')}


def check_frozen(policy, root=ROOT):
    if policy['runtimeSha256'] != runtime_files(root):
        raise ValueError('Runtime, installed assets or package configuration changed; freeze a new candidate.')
    for entry in policy['models'].values():
        if sha256(root / entry['source']) != entry['sha256']:
            raise ValueError('Frozen model changed.')


def freeze(path=POLICY):
    from boardsnap.neural import load_model
    from tools.evaluate_photo_detection import POLICY as geometry_policy
    previous = json.loads((ROOT / 'data/manifests/digital-acceptance-v1.json').read_text())
    models = {}
    for mode, source in MODELS.items():
        _, metadata = load_model(ROOT / source)
        models[mode] = {'source': source, 'sha256': sha256(ROOT / source), 'metadata': metadata,
                        'status': 'candidate' if mode == 'digital' else 'experimental'}
    package_version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    value = {'schemaVersion': 1, 'policyId': path.stem, 'packageVersion': package_version,
             'status': 'preview-not-accepted', 'models': models, 'runtimeSha256': runtime_files(),
             'catalogue': {'digital': previous['configurations'],
                 'digitalConditions': previous['conditions'], 'digitalLayouts': previous['layouts'],
                 'photo': {'status': 'experimental-only', 'sources': ['lichess', 'chesscom', 'video'],
                     'deviceEvidence': 'iPhone 8 photographs of screens; moderate perspective; 30 consulted validation photos',
                     'officialPieceThemesVerified': False,
                     'restrictions': ['one complete visible 8x8 board', 'explicit orientation', 'PNG/JPEG',
                                      'no guarantee for glare, blur, moire, thin pawns or occlusion']}},
             'excluded': ['books', 'physical-3d-boards', 'native-mobile-compatibility', 'automatic-photo-orientation',
                          'fully-occluded-pieces', 'arbitrary-video-layouts', 'unmeasured-styles'],
             'acceptance': {
                 'digital': {'status': 'pending-independent-evaluation', 'thresholds': previous['thresholds']},
                 'photo': {'status': 'blocked-by-current-quality',
                     'thresholds': {'minimumImages': 120, 'minimumIndependentSourceGroups': 20,
                         'minimumImagesPerSourceCategory': 30, 'minimumNegatives': 100,
                         'minimumClassSquares': 50, 'exactBoardRate': .90, 'stratumExactBoardRate': .85,
                         'classPrecision': .98, 'classRecall': .98, 'maximumDetectionMissRate': .05,
                         'maximumFalseDetectionRate': .01, 'explicitOrientationMappingRate': 1.0,
                         'minimumGeometryWithinPolicyRate': .95},
                     'geometryPolicy': geometry_policy,
                     'requiredStrata': ['source-category', 'reviewed-piece-appearance', 'background',
                                        'perspective', 'resolution', 'overlay', 'orientation'],
                     'minimumImagesPerDeclaredStratum': 10,
                     'note': 'Proposed first-version utility gates fixed before new independent photos, not fitted to 20/30. Unmeasured strata fail; no general style claim.'}},
             'cpu': {'platform': 'Linux x86_64 CPython 3.12 CPU; not mobile or HTTP',
                     'torchThreads': 4, 'opencvThreads': 1,
                     'digital': {'minimumSamples': 40, 'warmP95Ms': 1000, 'coldMs': 5000, 'peakRssMiB': 1024},
                     'photo': {'minimumSamples': 30, 'warmP95Ms': 5000, 'coldMs': 10000, 'peakRssMiB': 1024}},
             'finalDataPolicy': 'No final images read during preview preparation. Freeze source identities before acquisition; all related variants stay together. Final attempts consume the set even on failure. Consulted sets are regression only. Changing candidate or thresholds requires a new policy.',
             'evidence': {name: sha256(ROOT / name) for name in (
                 'data/reports/photo-recovery-comparison-v2.json', 'data/reports/photo-pipeline-validation-v2.json',
                 'data/reports/photo-detection-development-v2.json', 'data/reports/digital-regressions-anisotropic-candidate.json')},
             'contract': {'successFields': ['piecePlacement'], 'fenFields': 1,
                          'errors': 'existing structured errors; CLI processing exit 1, usage exit 2'},
             'distribution': 'local preview only; no publication or final acceptance'}
    write_new(path, value)
    return value


def stage(destination, policy_path=POLICY, wheelhouse=None):
    from tools.model_bundle import build_bundle
    destination = destination.absolute()
    policy = json.loads(policy_path.read_text())
    check_frozen(policy)
    if destination.exists():
        raise ValueError('Use a new release directory; never overwrite a candidate.')
    wheelhouse = wheelhouse or ROOT / '.cache/releases/digital-preview-v1/dependencies'
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.preview-', dir=destination.parent) as temporary:
        target = Path(temporary)
        dependencies = target / 'dependencies'
        dependencies.mkdir()
        for wheel in sorted(wheelhouse.glob('*.whl')):
            if not wheel.name.startswith('boardsnap-'):
                shutil.copyfile(wheel, dependencies / wheel.name)
        env = dict(os.environ, SOURCE_DATE_EPOCH='1793577600')
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-index', '--no-deps', '--no-build-isolation',
                        '--wheel-dir', str(dependencies), str(ROOT)], env=env, check=True)
        requirements = []
        for wheel in sorted(dependencies.glob('*.whl')):
            with zipfile.ZipFile(wheel) as archive:
                metadata = BytesParser().parsebytes(archive.read(next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))))
            name = metadata['Name'] + ('[ml]' if metadata['Name'] == 'boardsnap' else '')
            requirements.append(f"{name}=={metadata['Version']} --hash=sha256:{sha256(wheel)}")
        (target / 'requirements.lock').write_text('\n'.join(requirements) + '\n')
        shutil.copyfile(policy_path, target / 'policy.json')
        bundle_reports = {}
        for mode, model in policy['models'].items():
            subpolicy = target / f'{mode}-policy.json'
            write_new(subpolicy, {'policyId': f'{policy["policyId"]}-{mode}', 'modelSha256': model['sha256'],
                                 'parentPolicySha256': sha256(policy_path), 'inputType': mode})
            report = build_bundle(ROOT / model['source'], target / 'models' / mode, subpolicy)
            report['bundle'] = f'models/{mode}'
            bundle_reports[mode] = report
        write_new(target / 'model-bundles.json', bundle_reports)
        shutil.copyfile(ROOT / 'tools/verify_preview.py', target / 'verify_preview.py')
        shutil.copyfile(ROOT / 'LICENSE', target / 'LICENSE')
        shutil.copyfile(ROOT / 'data/THIRD_PARTY_NOTICES.md', target / 'THIRD_PARTY_NOTICES.md')
        source = target / 'source'
        for name in list(policy['runtimeSha256']) + ['README.md', 'LICENSE']:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        target.rename(destination)
    return destination


def seal(destination, report_path):
    from tools.benchmark_preview import performance_passed
    from tools.model_bundle import verify_bundle
    destination = destination.absolute()
    policy = json.loads((destination / 'policy.json').read_text())
    archive_path = destination.with_name(destination.name + '.tar.gz')
    if report_path.exists() or archive_path.exists() or (destination / 'release.json').exists():
        raise ValueError('Never overwrite a sealed release, archive or report.')
    check_frozen(policy)
    policy_hash = sha256(destination / 'policy.json')
    bundles = json.loads((destination / 'model-bundles.json').read_text())
    wheel = next((destination / 'dependencies').glob('boardsnap-*.whl'))
    for name, checksum in policy['runtimeSha256'].items():
        if sha256(destination / 'source' / name) != checksum:
            raise ValueError('Packaged source differs from frozen runtime.')
    for mode in MODELS:
        install = json.loads((destination / 'reports' / f'{mode}-installation.json').read_text())
        cpu = json.loads((destination / 'reports' / f'{mode}-cpu.json').read_text())
        if (not install['passed'] or not cpu['performancePassed']
                or not performance_passed(cpu, policy['cpu'][mode])):
            raise ValueError('Installation and CPU gates must pass before sealing the preview.')
        if install['policySha256'] != policy_hash or cpu['policySha256'] != policy_hash:
            raise ValueError('Evidence belongs to a different policy.')
        if install['modelSha256'] != policy['models'][mode]['sha256'] or cpu['modelSha256'] != policy['models'][mode]['sha256']:
            raise ValueError('Evidence belongs to different weights.')
        bundled = verify_bundle(destination / 'models' / mode, bundles[mode]['manifestSha256'])
        if bundled['sha256'] != policy['models'][mode]['sha256']:
            raise ValueError('Packaged weights differ from frozen model.')
        if mode == 'digital' and install['wheelSha256'] != sha256(wheel):
            raise ValueError('Installation belongs to another wheel.')
    if not json.loads((destination / 'reports/tests.json').read_text())['passed']:
        raise ValueError('Automatic checks must pass before sealing.')
    files = {p.relative_to(destination).as_posix(): sha256(p) for p in sorted(destination.rglob('*')) if p.is_file()}
    value = {'schemaVersion': 1, 'releaseId': policy['policyId'], 'status': 'preview-not-accepted',
             'readyForExternalTesting': True, 'finalEvaluationExecuted': False,
             'finalAcceptanceGranted': False, 'packageVersion': policy['packageVersion'],
             'policySha256': sha256(destination / 'policy.json'), 'files': files}
    write_new(destination / 'release.json', value)
    checksum = sha256(destination / 'release.json')
    verify(destination, checksum)
    with archive_path.open('xb') as output, gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for path in sorted(destination.rglob('*')):
                if not path.is_file():
                    continue
                info = archive.gettarinfo(path, arcname=f'{destination.name}/{path.relative_to(destination).as_posix()}')
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                info.mtime = 1793577600
                info.mode = 0o644
                with path.open('rb') as stream:
                    archive.addfile(info, stream)
    write_new(report_path, {'release': str(destination.relative_to(ROOT)), 'releaseManifestSha256': checksum,
                           'policySha256': value['policySha256'], 'status': value['status'],
                           'readyForExternalTesting': True, 'finalAcceptanceGranted': False,
                           'archive': str(archive_path.relative_to(ROOT)), 'archiveSha256': sha256(archive_path),
                           'files': files})
    return checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'stage', 'seal'))
    parser.add_argument('--policy', type=Path, default=POLICY)
    parser.add_argument('--directory', type=Path, default=ROOT / '.cache/releases/screen-preview-v1')
    parser.add_argument('--report', type=Path, default=ROOT / 'data/reports/screen-preview-v1.json')
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze(args.policy)
        print('Candidate and thresholds frozen; no final images read.')
    elif args.action == 'stage':
        print(stage(args.directory, args.policy))
    else:
        print(seal(args.directory, args.report))


if __name__ == '__main__':
    main()
