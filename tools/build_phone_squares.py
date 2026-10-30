"""Export reviewed phone-photo squares while retaining unresolved source groups.

This produces development data, not a training/validation partition. References
come from visually reviewed corners and placements, never model predictions.
"""

import argparse
from collections import Counter
from io import BytesIO
from html import escape
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw

from tools.build_square_dataset import square_labels, write_array
from tools.position_dataset import LABELS
from tools.prepare_phone_photos import ROOT, audit, child, digest, write_json
from tools.review_phone_geometry import rectify


def extract_photo_squares(image, corners, orientation):
    """Rectify once and reorder whole cells to a8..h1 without rotating glyphs."""
    if orientation not in ("white-bottom", "black-bottom"):
        raise ValueError("Photographic squares require an explicit orientation.")
    with rectify(image, corners) as board:
        pixels = np.asarray(board)
        visual = pixels.reshape(8, 64, 8, 64, 3).transpose(0, 2, 1, 3, 4)
        if orientation == "black-bottom":
            visual = visual[::-1, ::-1]
        return np.ascontiguousarray(visual.reshape(64, 64, 64, 3))


def contact_sheet(pixels, cells):
    """Show every unchanged crop with its square and label outside its pixels."""
    sheet = Image.new("RGB", (640, 640), "#dddddd")
    draw = ImageDraw.Draw(sheet)
    for index, cell in enumerate(cells):
        x, y = index % 8 * 80, index // 8 * 80
        sheet.paste(Image.fromarray(pixels[index]), (x + 8, y))
        draw.text((x + 4, y + 65), f"{cell['square']}: {cell['label']}", fill="black")
    return sheet


def partition_plan(data, manifest_hash):
    """Record existing assignments and clues without inventing independence."""
    groups = {}
    for row in data["samples"]:
        group = groups.setdefault(row["groupId"], {
            "groupId": row["groupId"], "split": "development", "samples": [],
            "observedGameIds": set(),
        })
        group["samples"].append(row["id"])
        source = row["source"]
        if source.get("gameId"):
            group["observedGameIds"].add(f"{source['category']}:{source['gameId']}")
    for group in groups.values():
        group["observedGameIds"] = sorted(group["observedGameIds"])
    return {
        "schemaVersion": 1, "sourceManifestSha256": manifest_hash,
        "status": "awaiting-independent-validation-sources",
        "independentFinalEvaluation": False, "groups": list(groups.values()),
        "policy": "Keep unresolved sources together in development, including duplicate positions, all views and related games. Visible game IDs are clues, not permission to separate them from unresolved sources.",
        "validationRequirements": [
            "Collect new identified games/videos and record source IDs before taking variants.",
            "Assign whole games/videos to validation before cropping or tuning; never split photographs or squares randomly.",
            "Check source IDs and identical/equivalent placements against development and existing corpora; merge related groups and keep overlaps out of independent validation.",
            "Review placement, orientation and four corners; version the approved partition manifest before training.",
            "Cover target platforms, piece designs, perspectives and marks in validation; retain natural frequencies.",
        ],
    }


def build(manifest, destination, *, root=ROOT):
    root = root.resolve()
    destination = destination.resolve()
    if not destination.is_relative_to(root / ".cache"):
        raise ValueError("Keep derived photographic squares inside .cache.")
    if destination.exists():
        raise ValueError("Destination already exists; use a new version.")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_hash = digest(manifest)
    summary = audit(data, root=root)
    if (summary["reviewedCornerAnnotations"] != len(data["samples"])
            or summary["placementsReviewedAfterRectification"] != summary["labels"].get("visual-transcription", 0)):
        raise ValueError("All corners and valid placements must be reviewed after rectification.")
    for row in data["samples"]:
        for key in ("originalPath", "imagePath"):
            source = child(root, row[key]).resolve()
            if destination.is_relative_to(source.parent) or source.is_relative_to(destination):
                raise ValueError("Keep square output separate from originals and review images.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    coverage = {label: {"light": 0, "dark": 0} for label in LABELS}
    categories = Counter()
    records, exclusions = [], []
    with tempfile.TemporaryDirectory(prefix=".phone-squares-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        (stage / "previews").mkdir()
        for row in data["samples"]:
            if row["label"]["status"] != "visual-transcription":
                exclusions.append({"id": row["id"], "originalPath": row["originalPath"],
                                   "reason": row["label"].get("note", row["label"]["status"])})
                continue
            payload = child(root, row["imagePath"]).read_bytes()
            if hashlib.sha256(payload).hexdigest() != row["imageSha256"]:
                raise ValueError("Photograph changed after audit.")
            label = row["label"]
            with Image.open(BytesIO(payload)) as image:
                pixels = extract_photo_squares(image, row["boardCorners"], label["orientation"])
            cells = square_labels(label["piecePlacement"], label["orientation"])
            relative = f"development/{row['id']}.npz"
            array_hash = write_array(stage / relative, pixels, cells)
            preview = f"previews/{row['id']}.jpg"
            with contact_sheet(pixels, cells) as sheet:
                sheet.save(stage / preview, quality=94)
            records.append({
                "photoId": row["id"], "positionId": "photo-position-" + hashlib.sha256(label["piecePlacement"].encode()).hexdigest()[:16],
                "configurationId": row["id"], "groupId": row["groupId"], "split": row["split"],
                "status": "ok", "boundsMode": "reviewed-quadrilateral",
                "image": row["imagePath"], "sha256": row["imageSha256"],
                "originalPath": row["originalPath"], "originalSha256": row["originalSha256"],
                "imageSize": row["imageSize"], "source": row["source"],
                "conditions": row["conditions"], "boardCorners": row["boardCorners"],
                "geometryReview": row["geometryReview"], "labelReview": label["rectifiedReview"],
                "piecePlacement": label["piecePlacement"], "orientation": label["orientation"],
                "cells": cells, "array": relative, "arraySha256": array_hash, "preview": preview,
            })
            categories[row["source"]["category"]] += 1
            for cell in cells:
                coverage[cell["label"]][cell["background"]] += 1
        if not records:
            raise ValueError("No reviewed classification photographs available.")
        if digest(manifest) != manifest_hash:
            raise ValueError("Source manifest changed during square extraction.")
        (stage / "verified.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        plan = partition_plan(data, manifest_hash)
        write_json(stage / "partition-plan.json", plan)
        report = {
            "schemaVersion": 1, "datasetId": "phone-squares-v1", "dataRole": "photo-development-squares",
            "complete": True, "readyForTraining": False, "sourceManifestSha256": manifest_hash,
            "sourceRoot": str(root), "outputRoot": str(destination), "classOrder": list(LABELS),
            "sourcePhotoCount": len(data["samples"]), "writtenBoards": len(records),
            "squareCount": len(records) * 64, "categories": dict(categories), "exclusions": exclusions,
            "splitCounts": {"development": len(records), "training": 0, "validation": 0, "evaluation": 0},
            "classBackgroundCounts": coverage,
            "preprocessing": {"squareSize": 64, "colorMode": "RGB", "dtype": "uint8",
                "rectification": "reviewed full-image quadrilateral to 512x512, OpenCV INTER_LINEAR",
                "ordering": "a8 to h1; reorder cells for black-bottom without rotating pixels",
                "orientation": "explicit reviewed view; no automatic orientation or detection"},
            "balancing": {"applied": False, "policy": "retain all 64 cells from every valid board"},
            "classificationEvaluated": False, "automaticDetectionEvaluated": False,
            "indexes": {"verified": {"path": "verified.jsonl", "sha256": digest(stage / "verified.jsonl")}},
            "partitionPlan": {"path": "partition-plan.json", "sha256": digest(stage / "partition-plan.json"),
                              "status": plan["status"]},
            "codeSha256": {name: digest(ROOT / name) for name in (
                "tools/build_phone_squares.py", "tools/review_phone_geometry.py", "tools/build_square_dataset.py")},
        }
        write_json(stage / "dataset.json", report)
        cards = [f'<article><h2>{escape(Path(r["originalPath"]).stem)}</h2>'
                 f'<a href="{r["preview"]}"><img loading="lazy" src="{r["preview"]}" alt="64 labeled squares"></a>'
                 f'<p>{escape(r["groupId"])} | development</p></article>' for r in records]
        (stage / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>BoardSnap photographic squares</title>'
            '<style>body{font-family:sans-serif}img{max-width:100%}</style>'
            '<h1>Reviewed photographic squares</h1><p>64 crops per board in a8..h1 order. '
            'Development only; no independent validation split yet. Labels are assistant visual references.</p>'
            + "\n".join(cards), encoding="utf-8")
        if destination.exists():
            raise ValueError("Destination appeared during build.")
        stage.rename(destination)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/phone-photos-v1.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/phone-squares-v1")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = build(args.manifest, args.output)
    if args.report:
        write_json(args.report, report)
    print(json.dumps({"boards": report["writtenBoards"], "squares": report["squareCount"],
                      "readyForTraining": False, "output": report["outputRoot"]}))


if __name__ == "__main__":
    main()
