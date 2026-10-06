"""Rebuild coordinate glyph assets from the two empty tuning boards only."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path

from boardsnap.detection import BoardBounds
from boardsnap.image_input import read_image
from boardsnap.orientation import _coordinate_boxes, _glyph_mask


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    glyphs = defaultdict(list)
    sources = []
    bounds = BoardBounds(190, 158, 584, 584)
    for view, alphabets in (
        ("white", ("abcdefgh", "87654321")),
        ("black", ("hgfedcba", "12345678")),
    ):
        relative = Path(f"data/tuning/lichess-cburnett-brown-v1/pos-004-{view}.png")
        path = ROOT / relative
        sources.append({"path": relative.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        with read_image(path) as image:
            for boxes, alphabet in zip(_coordinate_boxes(bounds), alphabets, strict=True):
                for box, symbol in zip(boxes, alphabet, strict=True):
                    with image.crop(box) as patch:
                        mask = _glyph_mask(patch)
                    if mask is None:
                        raise ValueError(f"Could not extract tuning coordinate {symbol!r} from {relative}.")
                    glyphs[symbol].append(["".join(str(int(pixel)) for pixel in row) for row in mask])
    data = {
        "profileId": "lichess-cburnett-brown-v1", "sources": sources,
        "sourceBounds": [bounds.x, bounds.y, bounds.width, bounds.height],
        "glyphs": dict(sorted(glyphs.items())),
    }
    destination = ROOT / "src/boardsnap/assets/coordinate-glyphs.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote 32 coordinate glyph masks to {destination}")


if __name__ == "__main__":
    main()
