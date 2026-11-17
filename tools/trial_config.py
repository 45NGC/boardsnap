"""Explicit local trial model selection, independent of production defaults."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / 'data/manifests/local-trial-v1.json'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def select_model(config_path, mode, root=ROOT):
    if mode not in ('digital', 'photo'):
        raise ValueError('Choose digital or photo explicitly.')
    data = json.loads(Path(config_path).read_text())
    if data['schemaVersion'] != 1 or data['status'] != 'local-trial-not-accepted':
        raise ValueError('Unsupported trial configuration.')
    row = data['models'][mode]
    path = (root / row['path']).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or sha256(path) != row['sha256']:
        raise ValueError('Trial model is missing, outside the repository or has a different checksum.')
    return path
