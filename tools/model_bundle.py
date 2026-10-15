"""Create and verify a local, versioned model bundle; no downloads or publishing."""

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import tempfile

from tools.neural_data import digest


def verify_bundle(folder, expected_manifest_sha256):
    manifest = folder/'manifest.json'
    if digest(manifest) != expected_manifest_sha256:
        raise ValueError('Bundle manifest differs from its independently recorded checksum.')
    data = json.loads(manifest.read_text())
    if data.get('schemaVersion') != 1 or data.get('file') != 'model.pt':
        raise ValueError('Unsupported bundle manifest.')
    if digest(folder/'model.pt') != data['sha256']:
        raise ValueError('Model checksum mismatch.')
    if set(data.get('notices',{})) != {'LICENSE','THIRD_PARTY_NOTICES.md'}:
        raise ValueError('Bundle notices are missing.')
    for name, checksum in data['notices'].items():
        if digest(folder/name)!=checksum:raise ValueError('Bundle notice checksum mismatch.')
    if data.get('status') == 'accepted-for-declared-scope':
        if digest(folder/'acceptance-report.json') != data.get('acceptanceReportSha256'):
            raise ValueError('Bundle acceptance report checksum mismatch.')
    elif data.get('status') != 'candidate-not-accepted':
        raise ValueError('Unsupported bundle acceptance status.')
    from boardsnap.neural import load_model
    _, metadata = load_model(folder/'model.pt')
    if metadata != data['metadata']:
        raise ValueError('Bundle metadata differs from the weights.')
    return data


def build_bundle(model, destination, policy_path, acceptance_report=None):
    from boardsnap.neural import load_model
    _, metadata = load_model(model)
    policy = json.loads(policy_path.read_text())
    if digest(model) != policy['modelSha256']:
        raise ValueError('Model differs from the frozen candidate.')
    status='candidate-not-accepted'
    if acceptance_report is not None:
        from tools.digital_acceptance import acceptance_gates, performance_gates
        result=json.loads(acceptance_report.read_text())
        if (result.get('status')!='accepted' or result.get('modelSha256')!=digest(model)
                or result.get('policySha256')!=digest(policy_path)
                or not all(g['passed'] for g in acceptance_gates(policy,result['summary'])+performance_gates(policy,result['performance']))):
            raise ValueError('An accepted release requires passing evidence for this exact model and policy.')
        status='accepted-for-declared-scope'
    if destination.exists():
        raise ValueError('Bundle destination exists; use a new version.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.bundle-') as temporary:
        stage = Path(temporary)
        shutil.copyfile(model, stage/'model.pt')
        root=Path(__file__).resolve().parents[1]
        shutil.copyfile(root/'LICENSE',stage/'LICENSE')
        shutil.copyfile(root/'data/THIRD_PARTY_NOTICES.md',stage/'THIRD_PARTY_NOTICES.md')
        if acceptance_report is not None:
            shutil.copyfile(acceptance_report, stage/'acceptance-report.json')
        data = {'schemaVersion': 1, 'bundleId': policy['policyId'], 'status': status,
                'boardsnapVersion': version('boardsnap'), 'file': 'model.pt', 'sha256': digest(stage/'model.pt'),
                'policySha256': digest(policy_path), 'metadata': metadata,
                'notices':{name:digest(stage/name) for name in ('LICENSE','THIRD_PARTY_NOTICES.md')},
                'acceptanceReportSha256':digest(acceptance_report) if acceptance_report else None,
                'licenseNotice': 'See project LICENSE and data/THIRD_PARTY_NOTICES.md; this bundle grants no additional third-party artwork rights.'}
        (stage/'manifest.json').write_text(json.dumps(data, indent=2)+'\n')
        manifest_hash = digest(stage/'manifest.json')
        (stage/'SHA256SUMS').write_text(''.join(
            f'{digest(path)}  {path.name}\n' for path in sorted(stage.iterdir()) if path.is_file()))
        (stage/'README.md').write_text(f'# BoardSnap digital model\n\nStatus: {status}. Copy this directory intact.\n'
            'Verify manifest.json against the checksum recorded separately in the installation report.\n'
            'Install the matching BoardSnap wheel with its ml extra, then configure BOARDSNAP_MODEL\n'
            'with the absolute path to model.pt. Requests contain image and explicit orientation.\n'
            'Weights, class order, preprocessing and source data version are recorded in manifest.json.\n')
        verify_bundle(stage, manifest_hash)
        stage.rename(destination)
    return {'bundle': str(destination), 'manifestSha256': manifest_hash, 'modelSha256': data['sha256'],
            'policySha256': digest(policy_path), 'status': data['status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--model', type=Path, required=True)
    build.add_argument('--policy', type=Path, required=True)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--report', type=Path, required=True)
    build.add_argument('--acceptance-report',type=Path,help='Optional passing final report for an accepted bundle; otherwise candidate only')
    check = commands.add_parser('verify')
    check.add_argument('bundle', type=Path)
    check.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        verify_bundle(args.bundle, args.manifest_sha256)
        print('Bundle integrity and model metadata verified.')
    else:
        report = build_bundle(args.model, args.output, args.policy,args.acceptance_report)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
