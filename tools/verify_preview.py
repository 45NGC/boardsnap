"""Verify a portable preview using only the Python standard library."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(folder, expected_sha256):
    folder = Path(folder).resolve()
    manifest = folder / 'release.json'
    if sha256(manifest) != expected_sha256:
        raise ValueError('Release manifest differs from the independently recorded checksum.')
    data = json.loads(manifest.read_text())
    if data.get('schemaVersion') != 1 or data.get('status') != 'preview-not-accepted':
        raise ValueError('Unsupported preview manifest.')
    if not data.get('files'):
        raise ValueError('Empty release inventory.')
    for name, expected in data['files'].items():
        path = folder / name
        if Path(name).is_absolute() or not path.resolve().is_relative_to(folder) or path.is_symlink():
            raise ValueError('Release path escapes its directory.')
        if sha256(path) != expected:
            raise ValueError(f'Checksum mismatch: {name}')
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != set(data['files']) | {'release.json'}:
        raise ValueError('Unlisted or missing release files.')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--sha256', required=True, help='release.json checksum from a separate trusted record')
    args = parser.parse_args()
    data = verify(args.folder, args.sha256)
    print(f"Verified {data['releaseId']}: {len(data['files'])} files; preview, not final acceptance.")


if __name__ == '__main__':
    main()
