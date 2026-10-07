"""Save development previews of board detection without changing source images."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import ImageInputError, read_image
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares
from boardsnap.orientation import detect_orientation, to_canonical
from boardsnap.classification import ClassificationError, classify_squares
from boardsnap.output import build_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", nargs="?", type=Path, default=Path("data/tuning"),
        help="Image or directory to scan recursively (default: data/tuning).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path(".cache/detection-preview"),
        help="Preview directory (default: .cache/detection-preview).",
    )
    parser.add_argument(
        "--squares", action="store_true",
        help="Also save normalized.png and 64 crops in squares/ (zero-based image order).",
    )
    parser.add_argument(
        "--orientation", action="store_true",
        help="Also save square previews, orientation.txt and canonical.png in a8-to-h1 order.",
    )
    parser.add_argument(
        "--recognition", action="store_true",
        help="Also save orientation previews and recognized piecePlacement in result.json.",
    )
    args = parser.parse_args(argv)
    source = args.input.resolve()
    output = args.output_dir.resolve()
    root = source if source.is_dir() else source.parent
    if output == root or output.is_relative_to(root) or root.is_relative_to(output):
        parser.error("Input and output directories must not overlap.")

    images = (
        sorted(path for path in source.rglob("*")
               if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"})
        if source.is_dir() else [source]
    )
    if not images:
        parser.error("No PNG or JPEG images found in the input directory.")
    destinations = [output / path.relative_to(root).with_suffix("") for path in images]
    if len(set(destinations)) != len(destinations):
        parser.error("Images with the same stem would share an output directory.")

    failures = 0
    for path, destination in zip(images, destinations, strict=True):
        try:
            destination.mkdir(parents=True, exist_ok=True)
            # Remove previous previews so a failed rerun cannot look successful.
            names = ["detection.png", "board.png", "normalized.png", "canonical.png", "orientation.txt", "result.json"]
            names.extend(f"squares/row-{row}-col-{col}.png" for row in range(8) for col in range(8))
            for name in names:
                (destination / name).unlink(missing_ok=True)
            with read_image(path) as image:
                bounds = detect_board(image)
                left, top, right, bottom = bounds.as_box()
                with image.copy() as preview:
                    ImageDraw.Draw(preview).rectangle(
                        (left, top, right - 1, bottom - 1), outline="red", width=3,
                    )
                    preview.save(destination / "detection.png")
                with image.crop(bounds.as_box()) as board:
                    board.save(destination / "board.png")
                if args.squares or args.orientation or args.recognition:
                    with ExitStack() as stack:
                        normalized = stack.enter_context(normalize_board(image, bounds))
                        normalized.image.save(destination / "normalized.png")
                        squares = split_squares(normalized.image)
                        for row in squares:
                            for square in row:
                                stack.enter_context(square)
                        (destination / "squares").mkdir(exist_ok=True)
                        for row_index, row in enumerate(squares):
                            for col_index, square in enumerate(row):
                                square.save(destination / "squares" / f"row-{row_index}-col-{col_index}.png")
                        if args.orientation or args.recognition:
                            orientation = detect_orientation(normalized)
                            canonical = to_canonical(squares, orientation)
                            with Image.new("RGB", normalized.image.size) as ordered:
                                for row_index, row in enumerate(canonical):
                                    for col_index, square in enumerate(row):
                                        ordered.paste(square, (col_index * square.width, row_index * square.height))
                                ordered.save(destination / "canonical.png")
                            (destination / "orientation.txt").write_text(orientation + "\n", encoding="utf-8")
                            if args.recognition:
                                result = build_result(to_canonical(classify_squares(squares), orientation))
                                (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"{path.name}: {bounds.as_box()} -> {destination}")
        except (ImageInputError, BoardDetectionError, ClassificationError) as error:
            failures += 1
            print(f"{path}: {error.code}: {error.message}", file=sys.stderr)
        except OSError as error:
            failures += 1
            print(f"{path}: PREVIEW_IO_ERROR: {error}", file=sys.stderr)

    print(f"Previewed {len(images) - failures}/{len(images)} images; failures: {failures}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
