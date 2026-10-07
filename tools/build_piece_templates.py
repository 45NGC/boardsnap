"""Rebuild the first piece baseline from the fixed tuning split, never evaluation."""

from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

from PIL import Image

from boardsnap.detection import BoardBounds
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.output import build_result


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "lichess-cburnett-brown-v1"
LABELS = (None, *"PNBRQKpnbrqk")


def build_templates(root: Path = ROOT) -> None:
    """Select the first sample of each class/background in stable filename order."""
    folder = root / "data/tuning" / PROFILE
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["profileId"] != PROFILE or any(p["split"] != "tuning" for p in manifest["positions"]):
        raise ValueError("Only the fixed tuning profile can supply templates.")
    selected = {}
    coverage = Counter()
    with ExitStack() as stack:
        atlas = stack.enter_context(Image.new("RGB", (128, 832)))
        for position in sorted(manifest["positions"], key=lambda value: value["groupId"]):
            for view in ("black", "white"):
                path = folder / f"{position['groupId']}-{view}.png"
                annotation_path = path.with_suffix(".json")
                annotation = json.loads(annotation_path.read_text())
                if (annotation["split"] != "tuning" or annotation["profileId"] != PROFILE
                        or annotation["orientation"] != f"{view}-bottom"
                        or annotation["piecePlacement"] != position["piecePlacement"]):
                    raise ValueError(f"Inconsistent tuning annotation: {annotation_path}")
                labels = [[p for token in rank for p in ([None] * int(token) if token.isdigit() else [token])]
                          for rank in annotation["piecePlacement"].split("/")]
                if build_result(labels)["piecePlacement"] != annotation["piecePlacement"]:
                    raise ValueError("Tuning placement must use canonical run encoding.")
                if view == "black":
                    labels = [row[::-1] for row in labels[::-1]]
                annotated = annotation["boardBounds"]
                x, y = round(annotated["x"]), round(annotated["y"])
                bounds = BoardBounds(x, y, round(annotated["x"] + annotated["width"]) - x,
                                     round(annotated["y"] + annotated["height"]) - y)
                with read_image(path) as source, normalize_board(source, bounds) as board:
                    for row in range(8):
                        for col in range(8):
                            label = labels[row][col]
                            background = ("light", "dark")[(row + col) % 2]
                            key = label, background
                            coverage[key] += 1
                            if key in selected:
                                continue
                            target_row, target_col = LABELS.index(label), (row + col) % 2
                            atlas_box = [target_col * 64, target_row * 64,
                                         (target_col + 1) * 64, (target_row + 1) * 64]
                            with board.image.crop((col * 64, row * 64, (col + 1) * 64, (row + 1) * 64)) as square:
                                atlas.paste(square, tuple(atlas_box))
                            selected[key] = {
                                "label": label, "background": background, "atlasBox": atlas_box,
                                "source": {"image": path.relative_to(root).as_posix(),
                                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                           "annotationSha256": hashlib.sha256(annotation_path.read_bytes()).hexdigest(),
                                           "row": row, "column": col, "orientation": annotation["orientation"],
                                           "bounds": list(bounds.as_box())},
                            }
        keys = [(label, background) for label in LABELS for background in ("light", "dark")]
        if set(selected) != set(keys):
            raise ValueError("Tuning data must cover all thirteen classes on both backgrounds.")
        destination = root / "src/boardsnap/assets"
        destination.mkdir(parents=True, exist_ok=True)
        atlas_path = destination / "piece-templates.png"
        atlas.save(atlas_path)
        data = {
            "formatVersion": 1, "profileId": PROFILE, "squareSize": 64,
            "selection": "First sample per class/background in filename and image row/column order; tuning only.",
            "atlasSha256": hashlib.sha256(atlas_path.read_bytes()).hexdigest(),
            "templates": [dict(selected[key], tuningCount=coverage[key]) for key in keys],
        }
        (destination / "piece-templates.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote 26 templates from {sum(coverage.values())} tuning squares to {destination}")


if __name__ == "__main__":
    build_templates()
