"""Render annotated photographic boards beside their visual transcription.

Offline annotation QA only: no detector, classifier, training or partition changes.
The rectified image retains the photographed view; only diagram square order is
reversed for black-bottom. Piece glyphs are never rotated upside down.
"""

import argparse
from html import escape
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tools.capture_lichess import expand_placement
from tools.prepare_phone_photos import (
    ROOT, audit, child, digest, validate_corners, write_json, write_review_index,
)


def rectify(image, corners, side=512):
    """Map annotated grid boundaries to [0, side] without changing chess view."""
    validate_corners(corners, image.size)
    if type(side) is not int or side < 8 or side % 8:
        raise ValueError("Review side must be a positive multiple of eight, at least eight.")
    transform = cv2.getPerspectiveTransform(
        np.float32(corners), np.float32([[0, 0], [side, 0], [side, side], [0, side]]),
    )
    return Image.fromarray(cv2.warpPerspective(
        np.asarray(image.convert("RGB")), transform, (side, side), flags=cv2.INTER_LINEAR,
    ))


def visual_labels(label):
    if label["piecePlacement"] is None:
        return None
    board = expand_placement(label["piecePlacement"])
    if label["orientation"] == "black-bottom":
        return [rank[::-1] for rank in board[::-1]]
    if label["orientation"] != "white-bottom":
        raise ValueError("Review requires an explicit orientation.")
    return board


def render_panel(image, row, atlas):
    name = Path(row["originalPath"]).stem
    rectified = rectify(image, row["boardCorners"])
    panel = Image.new("RGB", (1400, 595), "#eeeeee")
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default(size=18)
    draw.text((8, 5), f"{name} | {row['label']['orientation']}", font=font, fill="black")
    thumb = image.copy()
    thumb.thumbnail((350, 510))
    points = [(x * thumb.width / image.width, y * thumb.height / image.height)
              for x, y in row["boardCorners"]]
    outline = ImageDraw.Draw(thumb)
    outline.line(points + [points[0]], fill="red", width=2)
    for index, (x, y) in enumerate(points):
        outline.ellipse((x - 3, y - 3, x + 3, y + 3), fill="red")
        outline.text((x + 3, y + 3), str(index + 1), fill="red")
    panel.paste(thumb, (0, 40))
    panel.paste(rectified, (365, 40))
    for k in range(1, 8):
        for a, b in [((365 + k * 64, 40), (365 + k * 64, 47)),
                     ((365 + k * 64, 544), (365 + k * 64, 551)),
                     ((365, 40 + k * 64), (372, 40 + k * 64)),
                     ((870, 40 + k * 64), (877, 40 + k * 64))]:
            draw.line((a, b), fill="red")
    board = visual_labels(row["label"])
    if board is None:
        draw.text((900, 200), "AMBIGUOUS: excluded from classification", font=font, fill="red")
    else:
        for rank in range(8):
            for file in range(8):
                index = [".", *"PNBRQKpnbrqk"].index(board[rank][file])
                color = (rank + file) % 2
                tile = atlas.crop((color * 64, index * 64, (color + 1) * 64, (index + 1) * 64))
                panel.paste(tile, (885 + file * 64, 40 + rank * 64))
    draw.text((8, 565), "1: TL, 2: TR, 3: BR, 4: BL", font=font, fill="black")
    draw.text((365, 565), "Rectified photograph (visual order)", font=font, fill="black")
    draw.text((885, 565), "Transcription diagram (not a prediction)", font=font, fill="black")
    return panel, rectified


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/phone-photos-v1.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/phone-photos-v1/geometry")
    args = parser.parse_args(argv)
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = audit(data)
    if report["reviewedCornerAnnotations"] != len(data["samples"]):
        raise ValueError("Annotate and review every board before exporting the geometry gallery.")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".cache"):
        raise ValueError("Keep generated review images inside .cache.")
    for row in data["samples"]:
        for key in ("originalPath", "imagePath"):
            source = child(ROOT, row[key]).resolve()
            if output.is_relative_to(source.parent) or source.is_relative_to(output):
                raise ValueError("Keep review output separate from source image directories.")
    output.mkdir(parents=True, exist_ok=True)
    cards, exports = [], []
    with Image.open(ROOT / "src/boardsnap/assets/piece-templates.png") as atlas:
        for row in data["samples"]:
            with Image.open(child(ROOT, row["imagePath"])) as image:
                panel, rectified = render_panel(image.convert("RGB"), row, atlas)
            name = row["id"]
            panel.save(output / f"{name}.jpg", quality=94)
            rectified.save(output / f"{name}-rectified.png")
            title = escape(Path(row["originalPath"]).stem)
            cards.append(f'<article id="{name}"><h2>{title}</h2>'
                         f'<a href="{name}.jpg"><img loading="lazy" src="{name}.jpg" alt="{title}"></a>'
                         f'<p>{escape(row["label"]["piecePlacement"] or "Ambiguous: excluded")}</p></article>')
            exports.append({"id": name, "imageSha256": row["imageSha256"],
                            "boardCorners": row["boardCorners"],
                            "rectifiedSha256": digest(output / f"{name}-rectified.png")})
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>BoardSnap geometry review</title>'
        '<style>body{font-family:sans-serif}img{max-width:100%}p{overflow-wrap:anywhere}</style>'
        '<h1>Photographic annotation review</h1><p>Original with corners, rectified image, '
        'and label diagram. Assistant visual review; not independent human verification. '
        'Development data only. Rectified copies are review artifacts, not a training split.</p>'
        + "\n".join(cards), encoding="utf-8")
    write_json(output / "export.json", {
        "manifestSha256": digest(args.manifest), "purpose": "annotation-review-only",
        "side": 512, "interpolation": "opencv-linear", "orientation": "photographed-view",
        "exports": exports,
    })
    # Refresh the existing intake page when using its conventional output folder.
    if output == ROOT / ".cache/phone-photos-v1/geometry":
        write_review_index(output.parent, data["samples"])
    print(json.dumps({"reviewedPhotos": len(exports), "index": str(output / "index.html")}))


if __name__ == "__main__":
    main()
