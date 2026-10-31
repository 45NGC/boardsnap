"""Expose one-image recognition as a JSON command-line interface."""

import argparse
from contextlib import redirect_stdout
import json
import sys

from boardsnap.classification import ClassificationError
from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError
from boardsnap.pipeline import recognize_image
from boardsnap.profiles import PROFILES


def main(argv: list[str] | None = None) -> int:
    """Emit one JSON line for a processed image, returning 0 on success or 1 on failure.

    argparse handles help (0) and invalid invocations (2) before recognition.
    Python diagnostics from recognition are redirected to stderr. Unexpected
    processing exceptions become PROCESSING_FAILED only at this adapter boundary;
    the Python core continues to expose its original exceptions to developers.
    """
    parser = argparse.ArgumentParser(prog="boardsnap", description="Recognize a chessboard image as piece placement JSON.")
    parser.add_argument("image", help="Path to a PNG or JPEG image.")
    backend = parser.add_mutually_exclusive_group()
    backend.add_argument("--profile", choices=tuple(PROFILES),
                        help="Use legacy templates for this profile, overriding BOARDSNAP_MODEL.")
    backend.add_argument("--model", help="Multi-style neural model path (otherwise BOARDSNAP_MODEL; unconfigured legacy fallback).")
    parser.add_argument("--orientation", choices=("white-bottom", "black-bottom", "auto"), default="auto",
                        help="Image view, not side to move; explicit values override coordinates (default: auto).")
    parser.add_argument("--input-type", choices=("digital", "photo"), default="digital",
                        help="Use photo for automatic perspective correction; requires a model and explicit orientation.")
    args = parser.parse_args(argv)
    if args.input_type == "photo" and (args.orientation == "auto" or args.profile is not None):
        parser.error("--input-type photo requires --orientation white-bottom or black-bottom and cannot use --profile.")

    exit_code = 0
    with redirect_stdout(sys.stderr):
        try:
            options = {"orientation": args.orientation}
            if args.input_type == "photo":
                options["input_type"] = "photo"
            if args.profile:
                options["profile"] = args.profile
            if args.model is not None:
                options["model"] = args.model
            result = recognize_image(args.image, **options)
        except (ImageInputError, BoardDetectionError, ClassificationError) as error:
            result = error.to_dict()
            exit_code = 1
        except Exception as error:
            result = {"error": {"code": "PROCESSING_FAILED", "message": "Could not recognize the image."}}
            print(f"boardsnap: {type(error).__name__}: {error}", file=sys.stderr)
            exit_code = 1
    print(json.dumps(result))
    return exit_code
