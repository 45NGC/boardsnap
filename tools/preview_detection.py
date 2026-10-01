"""Save development previews of board detection without changing source images."""

import argparse
from pathlib import Path
import sys

from PIL import ImageDraw

from boardsnap.detection import BoardDetectionError, detect_board
from boardsnap.image_input import ImageInputError, read_image


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
            for name in ("detection.png", "board.png"):
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
            print(f"{path.name}: {bounds.as_box()} -> {destination}")
        except (ImageInputError, BoardDetectionError) as error:
            failures += 1
            print(f"{path}: {error.code}: {error.message}", file=sys.stderr)
        except OSError as error:
            failures += 1
            print(f"{path}: PREVIEW_IO_ERROR: {error}", file=sys.stderr)

    print(f"Previewed {len(images) - failures}/{len(images)} images; failures: {failures}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
