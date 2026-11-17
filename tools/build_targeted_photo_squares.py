"""Export visually reviewed paired photographs, preserving development groups.

This offline adapter consumes the targeted intake schema. It never annotates,
assigns training splits, runs recognition, or modifies source photographs.
"""

import argparse
from collections import Counter
import hashlib
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile

from PIL import Image

from tools.build_phone_squares import contact_sheet, extract_photo_squares
from tools.build_square_dataset import square_labels, write_array
from tools.position_dataset import LABELS
from tools.prepare_phone_photos import CORNER_ORDER, ROOT, child, digest, validate_corners, write_json
from tools.review_phone_geometry import render_panel, visual_labels


def review_fingerprint(photo, session, reference):
    """Bind visual approval to the exact geometry, labels, grouping and pair."""
    payload = {
        "photoId": photo["id"], "imageSha256": photo["imageSha256"],
        "originalSha256": photo["originalSha256"], "imageSize": photo["imageSize"],
        "boardCorners": photo["boardCorners"], "sessionId": session["id"],
        "referenceImageId": reference["id"], "referenceSha256": reference["imageSha256"],
        "label": session["label"], "groupId": session["groupId"], "split": session["split"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(data, root):
    """Reject missing/stale reviews, broken pairs, changed files and split changes."""
    if (data.get("schemaVersion") != 1
            or data.get("dataRole") != "paired-photographic-development-intake"
            or data.get("independentFinalEvaluation") is not False):
        raise ValueError("Expected a paired development intake.")
    images = {r["id"]: r for r in data["images"]}
    sessions = {s["id"]: s for s in data["sessions"]}
    if (not images or not sessions or len(images) != len(data["images"])
            or len(sessions) != len(data["sessions"])):
        raise ValueError("Missing or duplicate identities.")
    assigned = []
    for session in sessions.values():
        label = session["label"]
        if session["split"] != "development" or not session["groupId"]:
            raise ValueError("Keep source groups in development until training assignment is reviewed.")
        if (label.get("status") != "visual-transcription" or not label.get("reviewedBy")
                or label.get("method") != "direct-screenshot-transcription-and-photo-comparison"
                or label.get("visualRows") != visual_labels(label)):
            raise ValueError("Expected consistent visually transcribed labels.")
        for field, kind in (("photoImageIds", "phone-photo"), ("referenceImageIds", "direct-screenshot")):
            if not session[field]:
                raise ValueError("Each session needs photos and references.")
            for identity in session[field]:
                if (identity not in images or images[identity]["session"] != session["id"]
                        or images[identity]["kind"] != kind):
                    raise ValueError("Image membership does not match its session.")
                assigned.append(identity)
        if label.get("referenceImageSha256") not in [images[i]["imageSha256"] for i in session["referenceImageIds"]]:
            raise ValueError("Label reference is not part of this session.")
    if sorted(assigned) != sorted(images):
        raise ValueError("Every image must belong to exactly one session.")
    rows = []
    for photo in images.values():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", photo["id"]):
            raise ValueError("Unsafe image identity.")
        for key, checksum in (("originalPath", "originalSha256"), ("imagePath", "imageSha256")):
            if digest(child(root, photo[key])) != photo[checksum]:
                raise ValueError(f"Changed source bytes: {photo['id']}.")
        with Image.open(child(root, photo["imagePath"])) as image:
            if image.mode != "RGB" or list(image.size) != photo["imageSize"]:
                raise ValueError("Changed source image size or mode.")
        if photo["kind"] != "phone-photo":
            continue
        session = sessions[photo["session"]]
        reference = images.get(photo["referenceImageId"])
        if reference is None or reference["id"] not in session["referenceImageIds"]:
            raise ValueError("Photograph reference must belong to the same session.")
        validate_corners(photo["boardCorners"], photo["imageSize"])
        review = photo.get("geometryReview", {})
        if (photo.get("cornerAnnotationStatus") != "visual-reviewed"
                or review.get("status") != "visual-reviewed"
                or review.get("coordinateSpace") != "normalized-image-pixels"
                or review.get("cornerOrder") != CORNER_ORDER
                or not review.get("reviewedBy") or not review.get("reviewedOn")
                or review.get("outcome") != "complete-grid-aligned-and-labels-match-reference"
                or review.get("fingerprint") != review_fingerprint(photo, session, reference)):
            raise ValueError(f"Missing or stale geometry/label review: {photo['id']}.")
        rows.append((photo, session, reference))
    return rows


def build(manifest, destination, *, root=ROOT):
    root, destination = root.resolve(), destination.resolve()
    if not destination.is_relative_to(root / ".cache") or destination.exists():
        raise ValueError("Use a new destination inside .cache.")
    manifest_hash = digest(manifest)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    rows = validate(data, root)
    for image in data["images"]:
        for key in ("originalPath", "imagePath"):
            source = child(root, image[key]).resolve()
            if destination.is_relative_to(source.parent) or source.is_relative_to(destination):
                raise ValueError("Keep output separate from source directories.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    coverage = {label: {"light": 0, "dark": 0} for label in LABELS}
    records, cards = [], []
    with tempfile.TemporaryDirectory(prefix=".targeted-squares-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        (stage / "previews").mkdir()
        with Image.open(ROOT / "src/boardsnap/assets/piece-templates.png") as atlas:
            for photo, session, reference in rows:
                label, identity = session["label"], photo["id"]
                payload = child(root, photo["imagePath"]).read_bytes()
                if hashlib.sha256(payload).hexdigest() != photo["imageSha256"]:
                    raise ValueError("Photograph changed during export.")
                with Image.open(BytesIO(payload)) as image:
                    pixels = extract_photo_squares(image, photo["boardCorners"], label["orientation"])
                    panel, rectified = render_panel(image, photo | {"label": label}, atlas)
                cells = square_labels(label["piecePlacement"], label["orientation"])
                array = f"development/{identity}.npz"
                checksum = write_array(stage / array, pixels, cells)
                preview = f"previews/{identity}-squares.jpg"
                with contact_sheet(pixels, cells) as sheet:
                    sheet.save(stage / preview, quality=94)
                panel_path = f"previews/{identity}-geometry.jpg"
                rectified_path = f"previews/{identity}-rectified.png"
                panel.save(stage / panel_path, quality=94)
                rectified.save(stage / rectified_path)
                panel.close(); rectified.close()
                record = {
                    "photoId": identity, "positionId": "photo-position-" + hashlib.sha256(label["piecePlacement"].encode()).hexdigest()[:16],
                    "configurationId": identity, "sessionId": session["id"],
                    "groupId": session["groupId"], "split": session["split"], "source": session["source"],
                    "appearanceGroup": session["appearanceGroup"], "boardAppearance": session["boardAppearance"],
                    "status": "ok", "boundsMode": "reviewed-quadrilateral", "image": photo["imagePath"],
                    "sha256": photo["imageSha256"], "originalPath": photo["originalPath"],
                    "originalSha256": photo["originalSha256"], "imageSize": photo["imageSize"],
                    "referenceImageId": reference["id"], "referenceImage": reference["imagePath"],
                    "referenceSha256": reference["imageSha256"], "conditions": photo["conditions"],
                    "boardCorners": photo["boardCorners"], "geometryReview": photo["geometryReview"],
                    "piecePlacement": label["piecePlacement"], "orientation": label["orientation"],
                    "cells": cells, "array": array, "arraySha256": checksum, "preview": preview,
                    "rectified": rectified_path, "rectifiedSha256": digest(stage / rectified_path),
                }
                records.append(record)
                for cell in cells:
                    coverage[cell["label"]][cell["background"]] += 1
                ref_link = escape(os.path.relpath(child(root, reference["imagePath"]), destination), quote=True)
                cards.append(f'<article><h2>{escape(identity)} | {label["orientation"]}</h2>'
                             f'<img loading="lazy" src="{panel_path}" alt="Original, rectified photograph and transcription">'
                             f'<p><a href="{ref_link}">Direct reference</a> · <a href="{rectified_path}">Rectified PNG</a></p>'
                             f'<a href="{preview}"><img loading="lazy" src="{preview}" alt="64 labeled canonical squares"></a></article>')
        if digest(manifest) != manifest_hash:
            raise ValueError("Manifest changed during export.")
        (stage / "verified.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        report = {
            "schemaVersion": 1, "datasetId": "phone-targeted-squares-v1", "complete": True,
            "dataRole": "photo-development-squares", "readyForTraining": False,
            "sourceManifestSha256": manifest_hash, "writtenBoards": len(records), "squareCount": len(records) * 64,
            "groups": dict(Counter(r["groupId"] for r in records)),
            "splitCounts": {"development": len(records), "training": 0, "validation": 0, "evaluation": 0},
            "classOrder": list(LABELS), "classBackgroundCounts": coverage,
            "distinctPlacements": len({r["piecePlacement"] for r in records}),
            "preprocessing": {"boardSize": 512, "squareSize": 64, "colorMode": "RGB", "dtype": "uint8",
                "interpolation": "opencv-linear", "ordering": "a8..h1; reorder cells, never rotate glyphs"},
            "independentFinalEvaluation": False, "trainingRun": False, "balancingApplied": False,
            "review": "Assistant visual check of all rectified boards, grid boundaries and paired references; not independent human verification or detector accuracy measurement.",
            "pending": "Assign training membership after cross-corpus source/position overlap review; preserve existing groups and partitions.",
            "indexes": {"verified": {"path": "verified.jsonl", "sha256": digest(stage / "verified.jsonl")}},
            "codeSha256": {name: digest(ROOT / name) for name in (
                "tools/build_targeted_photo_squares.py", "tools/build_phone_squares.py",
                "tools/review_phone_geometry.py", "tools/build_square_dataset.py")},
        }
        write_json(stage / "dataset.json", report)
        (stage / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>BoardSnap targeted photo squares</title>'
            '<style>body{font-family:sans-serif}img{max-width:100%}article{margin-bottom:3em}</style>'
            '<h1>Targeted photographic squares</h1><p>Assistant visual review. Development only; '
            'groups unchanged. Labels come from paired references, not predictions.</p>' + "\n".join(cards), encoding="utf-8")
        if destination.exists():
            raise ValueError("Destination appeared during export.")
        stage.rename(destination)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/phone-targeted-intake-v1.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/phone-targeted-squares-v1")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = build(args.manifest, args.output)
    if args.report:
        write_json(args.report, report)
    print(json.dumps({"boards": report["writtenBoards"], "squares": report["squareCount"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
