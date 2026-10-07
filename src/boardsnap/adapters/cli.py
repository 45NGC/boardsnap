"""Expose one-image recognition as a JSON command-line interface."""

import argparse
from contextlib import redirect_stdout
import json
import sys

from boardsnap.classification import ClassificationError
from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError
from boardsnap.pipeline import recognize_image


def main(argv: list[str] | None = None) -> int:
    """Emit one JSON line for a processed image, returning 0 on success or 1 on failure.

    argparse handles help (0) and invalid invocations (2) before recognition.
    Python diagnostics from recognition are redirected to stderr. Unexpected
    processing exceptions become PROCESSING_FAILED only at this adapter boundary;
    the Python core continues to expose its original exceptions to developers.
    """
    parser = argparse.ArgumentParser(prog="boardsnap", description="Recognize a chessboard image as piece placement JSON.")
    parser.add_argument("image", help="Path to a PNG or JPEG image (initial brown/cburnett profile).")
    args = parser.parse_args(argv)

    exit_code = 0
    with redirect_stdout(sys.stderr):
        try:
            result = recognize_image(args.image)
        except (ImageInputError, BoardDetectionError, ClassificationError) as error:
            result = error.to_dict()
            exit_code = 1
        except Exception as error:
            result = {"error": {"code": "PROCESSING_FAILED", "message": "Could not recognize the image."}}
            print(f"boardsnap: {type(error).__name__}: {error}", file=sys.stderr)
            exit_code = 1
    print(json.dumps(result))
    return exit_code
