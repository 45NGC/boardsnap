"""Verify both preview modes using the isolated wheel, outside the checkout."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image

from tools.check_installation import check_installation
from tools.model_bundle import verify_bundle
from tools.verify_preview import sha256

ROOT = Path(__file__).resolve().parents[1]


def check_photos(python, release):
    bundles = json.loads((release/'model-bundles.json').read_text())
    bundle = release/'models/photo'
    metadata = verify_bundle(bundle, bundles['photo']['manifestSha256'])
    policy = json.loads((release/'policy.json').read_text())
    source = ROOT/'data/reports/photo-pipeline-validation-v2.json'
    if sha256(source) != policy['evidence'][str(source.relative_to(ROOT))]:
        raise ValueError('Photo installation references changed.')
    report = json.loads(source.read_text())
    selected = {}
    for row in report['records']:
        if row['split'] != 'validation':
            raise ValueError('Only consulted validation is allowed.')
        if row['automaticExact']:
            selected.setdefault((row['category'], row['orientation']), row)
    if {row['orientation'] for row in selected.values()} != {'white-bottom', 'black-bottom'}:
        raise ValueError('Both photo views must be exercised.')
    env = dict(os.environ, OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
    env.pop('PYTHONPATH', None)
    env.pop('BOARDSNAP_MODEL', None)
    checks = []
    with tempfile.TemporaryDirectory(prefix='boardsnap-photo-installed-', dir='/tmp') as name:
        directory = Path(name)
        def run(label, image, *, orientation='white-bottom', model=bundle/'model.pt', expected=None, error=None, usage=False, module=False):
            command = ([str(python), '-I', '-m', 'boardsnap'] if module else [str(python.parent/'boardsnap')])
            process = subprocess.run(command + [str(image), '--input-type', 'photo', '--model', str(model),
                '--orientation', orientation], cwd=directory, env=env, text=True, capture_output=True, timeout=60)
            if usage:
                passed = process.returncode == 2 and not process.stdout and bool(process.stderr)
            else:
                try:
                    actual = json.loads(process.stdout)
                    contract = actual == {'piecePlacement': expected} if expected is not None else (
                        set(actual) == {'error'} and set(actual['error']) == {'code', 'message'}
                        and actual['error']['code'] == error and bool(actual['error']['message']))
                    passed = contract and not process.stderr and process.returncode == (0 if expected is not None else 1)
                except (ValueError, TypeError, KeyError):
                    passed = False
            checks.append(dict(check=label, passed=passed, returnCode=process.returncode,
                               stdout=process.stdout, stderr=process.stderr))
        for index, row in enumerate(selected.values()):
            image = ROOT/row['image']
            if sha256(image) != row['imageSha256']:
                raise ValueError('Photo changed.')
            local = directory/f'photo-{index}.png'
            shutil.copyfile(image, local)
            run(row['id'], local, orientation=row['orientation'], expected=row['expected'], module=index == 0)
        blank = directory/'blank.png'
        with Image.new('RGB', (512, 512), 'white') as image:
            image.save(blank)
        empty = directory/'empty.png'
        empty.touch()
        run('photo without board', blank, error='BOARD_NOT_FOUND')
        run('empty image', empty, error='INVALID_IMAGE')
        run('missing image', directory/'absent.png', error='INPUT_READ_ERROR')
        run('photo auto orientation is rejected', blank, orientation='auto', usage=True)
        run('missing weights', blank, model=directory/'missing.pt', error='PROCESSING_FAILED')
    return {'passed': all(c['passed'] for c in checks), 'modelSha256': metadata['sha256'],
            'scope': 'installed photo CLI and python -I -m boardsnap outside checkout; consulted validation only',
            'referenceSha256': sha256(source), 'policySha256': sha256(release/'policy.json'),
            'checks': checks, 'verificationCodeSha256': sha256(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--release', type=Path, required=True)
    args = parser.parse_args()
    release = args.release.absolute()
    python = args.python.absolute()  # Keep the venv path rather than resolving its symlink.
    reports = release/'reports'
    reports.mkdir(exist_ok=True)
    for mode in ('digital', 'photo'):
        if (reports/f'{mode}-installation.json').exists():
            raise ValueError('Do not overwrite installation evidence.')
    bundles = json.loads((release/'model-bundles.json').read_text())
    digital = check_installation(python, next((release/'dependencies').glob('boardsnap-*.whl')),
        release/'models/digital', bundles['digital']['manifestSha256'], ROOT/'.cache/digital-style-squares-v2')
    digital['policySha256'] = sha256(release/'policy.json')
    photo = check_photos(python, release)
    for mode, data in [('digital', digital), ('photo', photo)]:
        (reports/f'{mode}-installation.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps({'digitalPassed': digital['passed'], 'photoPassed': photo['passed']}))
    return 0 if digital['passed'] and photo['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
