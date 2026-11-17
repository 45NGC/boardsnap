"""Run the regular BoardSnap CLI with an explicit, checksum-verified trial model."""
import argparse
import json
import os
import subprocess
import sys

from tools.trial_config import DEFAULT_CONFIG, select_model


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--input-type', choices=('digital', 'photo'), required=True)
    parser.add_argument('--orientation', choices=('white-bottom', 'black-bottom'), required=True)
    parser.add_argument('--config', default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        model = select_model(args.config, args.input_type)
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps({'error': {'code': 'CONFIGURATION_ERROR', 'message': str(error)}}))
        return 1
    return subprocess.run([sys.executable, '-m', 'boardsnap', args.image, '--model', str(model),
                           '--input-type', args.input_type, '--orientation', args.orientation],
                          env={**os.environ, 'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4'}).returncode


if __name__ == '__main__':
    raise SystemExit(main())
