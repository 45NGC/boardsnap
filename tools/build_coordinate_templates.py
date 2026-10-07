"""Rebuild coordinate glyph assets from the two empty tuning boards only."""

import argparse
from contextlib import ExitStack
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from PIL import Image

from boardsnap.detection import BoardBounds
from boardsnap.image_input import read_image
from boardsnap.orientation import _coordinate_boxes, _glyph_mask
from boardsnap.profiles import DEFAULT_PROFILE, PROFILES, get_profile


ROOT = Path(__file__).resolve().parents[1]


def build_templates(profile: str = DEFAULT_PROFILE) -> None:
    glyphs = defaultdict(list)
    sources = []
    if get_profile(profile).coordinates == "none":
        raise ValueError("This profile uses the orientation convention, not coordinate templates.")
    for view, alphabets in (
        ("white", ("abcdefgh", "87654321")),
        ("black", ("hgfedcba", "12345678")),
    ):
        relative = Path(f"data/tuning/{profile}/pos-004-{view}.png")
        path = ROOT / relative
        annotation = json.loads(path.with_suffix(".json").read_text())
        if annotation["split"] != "tuning" or annotation["profileId"] != profile:
            raise ValueError("Coordinates must come from the selected tuning profile")
        b = annotation["boardBounds"]
        bounds = BoardBounds(round(b["x"]), round(b["y"]), round(b["width"]), round(b["height"]))
        sources.append({"path": relative.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        with ExitStack() as stack:
            image = stack.enter_context(read_image(path))
            variants = [(image, bounds)]
            if profile == "lichess-cburnett-blue-v1":
                cropped = stack.enter_context(image.crop(bounds.as_box()))
                for scale in (.75, 1.25):
                    side = round(cropped.width * scale)
                    resized = stack.enter_context(cropped.resize((side, side), Image.Resampling.LANCZOS))
                    variants.append((resized, BoardBounds(0, 0, side, side)))
            for pixels, variant_bounds in variants:
                for boxes, alphabet in zip(_coordinate_boxes(variant_bounds, profile), alphabets, strict=True):
                    for box, symbol in zip(boxes, alphabet, strict=True):
                        with pixels.crop(box) as patch:
                            mask = _glyph_mask(patch, profile)
                        if mask is None and pixels is not image:
                            continue  # Too-small augmented glyphs also remain unreadable at runtime.
                        if mask is None:
                            raise ValueError(f"Could not extract tuning coordinate {symbol!r} from {relative}.")
                        glyphs[symbol].append(["".join(str(int(pixel)) for pixel in row) for row in mask])

    data = {
        "profileId": profile, "sources": sources,
        "sourceBounds": [bounds.x, bounds.y, bounds.width, bounds.height],
        "glyphs": dict(sorted(glyphs.items())),
    }
    if profile == "lichess-cburnett-blue-v1":
        data["augmentation"] = "Original source plus board-only crops resized with LANCZOS to 75% and 125%; tuning only."
    destination = ROOT / f"src/boardsnap/assets/{get_profile(profile).coordinate_asset}.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {sum(map(len, glyphs.values()))} coordinate glyph masks to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(p for p, c in PROFILES.items() if c.coordinates != "none"), default=DEFAULT_PROFILE)
    build_templates(parser.parse_args().profile)
