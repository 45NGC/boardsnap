"""Audit reviewed validation photo annotations and render their comparison gallery.

No recognition, partition assignment, training or final evaluation is performed.
This validates annotation consistency; visual correctness remains a review task.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
from html import escape
import json
from pathlib import Path

from PIL import Image

from boardsnap.output import build_result
from tools.capture_lichess import expand_placement
from tools.position_dataset import placement_family
from tools.prepare_phone_photos import ROOT, CORNER_ORDER, child, digest, validate_corners, write_json
from tools.review_phone_geometry import render_panel


def audit(data, development, *, root=ROOT, verify_files=True):
    """Reject stale reviews, wrong orientation and overlap with development."""
    if (data.get("schemaVersion") != 1 or data.get("dataRole") != "photo-validation-intake"
            or data.get("independentFinalEvaluation") is not False or not data.get("samples")):
        raise ValueError("Expected a non-final validation photo manifest.")
    confirmation = data.get("sourceSeparationConfirmation", {})
    if confirmation.get("status") != "user-confirmed-distinct-source-selection":
        raise ValueError("Source separation confirmation is missing.")
    if data.get("partitionReview", {}).get("status") != "validation-assigned":
        raise ValueError("Validation partition review is missing.")
    reference = child(root, data["referenceDevelopmentManifest"])
    if digest(reference) != data["referenceDevelopmentManifestSha256"]:
        raise ValueError("Development reference changed; review overlaps again.")
    # Ensure the supplied annotations really come from the pinned reference.
    if json.loads(reference.read_text(encoding="utf-8")) != development:
        raise ValueError("Development annotations do not match the pinned reference.")
    families = defaultdict(list)
    original_hashes, pixel_hashes, game_ids = set(), set(), set()
    for row in development["samples"]:
        placement = row.get("label", {}).get("piecePlacement")
        if placement:
            families[placement_family(placement)].append(row["id"])
        original_hashes.add(row["originalSha256"])
        pixel_hashes.add(row["pixelSha256"])
        if row["source"].get("gameId"):
            game_ids.add((row["source"]["category"], row["source"]["gameId"]))
    ids, originals, images = set(), set(), set()
    coverage = {piece: {"light": 0, "dark": 0} for piece in ["empty", *"PNBRQKpnbrqk"]}
    placements, orientations, categories = Counter(), Counter(), Counter()
    for row in data["samples"]:
        sid = row["id"]
        if not sid or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in sid):
            raise ValueError("Unsafe sample identifier.")
        if sid in ids or row["originalPath"] in originals or row["imagePath"] in images:
            raise ValueError("Duplicate photo identity or path.")
        ids.add(sid); originals.add(row["originalPath"]); images.add(row["imagePath"])
        if (row["split"] != "validation" or row["intendedSplit"] != "validation"
                or row["groupId"] != "phone-validation-batch-v1"):
            raise ValueError("The validation batch must remain together and outside training.")
        label = row["label"]
        if (label.get("status") != "visual-transcription"
                or label.get("method") != "visual-board-review"
                or not label.get("reviewedBy")
                or label.get("sourceSha256") != row["originalSha256"]):
            raise ValueError(f"Missing or stale visual transcription: {sid}")
        board = expand_placement(label["visualRows"])
        if label["orientation"] == "black-bottom":
            board = [rank[::-1] for rank in board[::-1]]
        elif label["orientation"] != "white-bottom":
            raise ValueError(f"Explicit orientation required: {sid}")
        placement = build_result([[None if p == "." else p for p in rank] for rank in board])["piecePlacement"]
        if placement != label["piecePlacement"]:
            raise ValueError(f"Visual rows and canonical orientation disagree: {sid}")
        validate_corners(row["boardCorners"], row["imageSize"])
        geometry = row.get("geometryReview", {})
        if (geometry.get("status") != "visual-reviewed"
                or geometry.get("coordinateSpace") != "normalized-image-pixels"
                or geometry.get("cornerOrder") != CORNER_ORDER
                or geometry.get("imageSha256") != row["imageSha256"]):
            raise ValueError(f"Missing or stale geometry review: {sid}")
        review = label.get("rectifiedReview", {})
        expected = {"imageSha256": row["imageSha256"], "boardCorners": row["boardCorners"],
                    "piecePlacement": placement, "orientation": label["orientation"]}
        if (review.get("outcome") != "matches-visible-pieces"
                or any(review.get(k) != v for k, v in expected.items())):
            raise ValueError(f"Missing or stale rectified review: {sid}")
        if placement_family(placement) in families:
            raise ValueError(f"Position family overlaps development: {sid}")
        if row["originalSha256"] in original_hashes or row["pixelSha256"] in pixel_hashes:
            raise ValueError(f"Photo pixels overlap development: {sid}")
        if (row["source"]["category"], row["source"].get("gameId")) in game_ids:
            raise ValueError(f"Known game overlaps development: {sid}")
        if verify_files:
            for path_key, hash_key in [("originalPath", "originalSha256"), ("imagePath", "imageSha256")]:
                if digest(child(root, row[path_key])) != row[hash_key]:
                    raise ValueError(f"Photo file changed: {sid}")
            with Image.open(child(root, row["imagePath"])) as im:
                im.load()
                if (im.mode != "RGB" or list(im.size) != row["imageSize"]
                        or hashlib.sha256(im.tobytes()).hexdigest() != row["pixelSha256"]):
                    raise ValueError(f"Normalized pixels changed: {sid}")
        for rank, cells in enumerate(board):
            for file, piece in enumerate(cells):
                coverage["empty" if piece == "." else piece]["light" if (rank + file) % 2 == 0 else "dark"] += 1
        placements[placement] += 1
        orientations[label["orientation"]] += 1
        categories[row["source"]["category"]] += 1
    return {
        "datasetId": data["datasetId"], "reviewedPhotos": len(ids),
        "reviewedPlacements": len(ids), "reviewedCornerAnnotations": len(ids),
        "distinctPlacements": len(placements), "byCategory": dict(categories),
        "orientations": dict(orientations), "labeledSquares": 64 * len(ids),
        "classBackgroundCounts": coverage, "allClassesOnBothBackgrounds": all(
            counts["light"] > 0 and counts["dark"] > 0 for counts in coverage.values()),
        "developmentPositionFamilyOverlaps": [], "developmentKnownGameOverlaps": [],
        "developmentReference": data["referenceDevelopmentManifest"],
        "developmentReferenceSha256": data["referenceDevelopmentManifestSha256"],
        "filesVerified": verify_files, "readyForSquareExport": True,
        "readyForValidation": False, "pending": ["validation square export and training-consumable index"],
        "modelInferenceRun": False, "independentFinalEvaluation": False,
        "limitations": ["Assistant visual review; not independent human verification.",
                        "Source separation is user-reported; most old game/video identities are unknown.",
                        "Overlap audit covers the pinned prior photo corpus, not every possible game position.",
                        "Known related photos stay together; 30 photos are not 30 independent sources."],
    }


def export_gallery(data, output, *, root=ROOT):
    """Render already-audited annotations; never infer or change their labels."""
    output = output.resolve()
    if not output.is_relative_to((root / ".cache").resolve()):
        raise ValueError("Keep generated review images inside .cache.")
    for row in data["samples"]:
        for key in ("originalPath", "imagePath", "jpegPath"):
            source = child(root, row[key]).resolve()
            if output.is_relative_to(source.parent) or source.is_relative_to(output):
                raise ValueError("Keep review output separate from source image directories.")
    output.mkdir(parents=True, exist_ok=True)
    cards, exports = [], []
    with Image.open(root / "src/boardsnap/assets/piece-templates.png") as atlas:
        for row in data["samples"]:
            with Image.open(child(root, row["imagePath"])) as im:
                panel, rectified = render_panel(im, row, atlas)
            sid = row["id"]
            panel.save(output / f"{sid}.jpg", quality=95)
            rectified.save(output / f"{sid}-rectified.png")
            cards.append(f'<article><h2>{escape(Path(row["originalPath"]).stem)}</h2>'
                         f'<img loading="lazy" src="{sid}.jpg" alt="{sid}">'
                         f'<p>{escape(row["label"]["orientation"])}: '
                         f'<code>{escape(row["label"]["piecePlacement"])}</code></p></article>')
            exports.append({"id": sid, "imageSha256": row["imageSha256"],
                            "boardCorners": row["boardCorners"],
                            "rectifiedSha256": digest(output / f"{sid}-rectified.png")})
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>BoardSnap validation annotations</title>'
        '<style>body{font-family:sans-serif}img{max-width:100%}code{overflow-wrap:anywhere}</style>'
        '<h1>Validation photo annotation review</h1><p>Original with grid corners, rectified photo, '
        'and transcription diagram. Assistant visual review, not model predictions or independent '
        'human verification. Corner order: image top-left, top-right, bottom-right, bottom-left. '
        'The rectified view preserves the photographed orientation.</p>' + "\n".join(cards), encoding="utf-8")
    return exports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/phone-validation-v1.json")
    parser.add_argument("--output", type=Path, help="Optional .cache directory for the gallery")
    parser.add_argument("--report", type=Path, help="Optional JSON audit report")
    args = parser.parse_args(argv)
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    development = json.loads(child(ROOT, data["referenceDevelopmentManifest"]).read_text(encoding="utf-8"))
    report = audit(data, development)
    report["manifestSha256"] = digest(args.manifest)
    if args.output:
        exports = export_gallery(data, args.output)
        write_json(args.output / "export.json", {"manifestSha256": digest(args.manifest),
                   "purpose": "annotation-review-only", "side": 512,
                   "interpolation": "opencv-linear", "orientation": "photographed-view", "exports": exports})
    if args.report:
        write_json(args.report, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
