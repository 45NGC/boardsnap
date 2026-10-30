"""Assemble a photographic training/validation dataset from a frozen split plan.

Reuse development archives byte-for-byte; extract only reviewed validation photos.
Original manifests, archives and models are never modified. No training is run.
"""

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
from html import escape
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image

from tools.build_phone_squares import contact_sheet, extract_photo_squares
from tools.build_square_dataset import square_labels, write_array
from tools.neural_data import load_board, read_index
from tools.position_dataset import LABELS, placement_family
from tools.prepare_phone_photos import ROOT, audit as audit_development, child, digest, write_json
from tools.review_phone_validation import audit as audit_validation


def assignments(development, validation):
    """Explicitly migrate the whole usable development batch, never individual cells."""
    result = {}
    for split, data in (("training", development), ("validation", validation)):
        rows = [r for r in data["samples"] if r["label"]["status"] == "visual-transcription"]
        groups = {r["groupId"] for r in rows}
        if not rows or len(groups) != 1:
            raise ValueError("Each photographic batch must retain its single source group.")
        result[split] = {"groupId": groups.pop(), "photoIds": sorted(r["id"] for r in rows)}
    return result


def checked_references(plan, root):
    paths = {}
    for name in ("developmentManifest", "validationManifest", "developmentSquaresMetadata"):
        ref = plan["inputs"][name]
        paths[name] = child(root, ref["path"])
        if digest(paths[name]) != ref["sha256"]:
            raise ValueError(f"Frozen input changed: {name}")
    return paths


def match_cached_record(record, photo):
    """A valid archive must still describe the currently reviewed photograph."""
    expected = {
        "photoId": photo["id"], "groupId": photo["groupId"], "split": "development",
        "status": "ok", "boundsMode": "reviewed-quadrilateral",
        "image": photo["imagePath"], "sha256": photo["imageSha256"],
        "originalPath": photo["originalPath"], "originalSha256": photo["originalSha256"],
        "imageSize": photo["imageSize"], "source": photo["source"],
        "conditions": photo["conditions"], "boardCorners": photo["boardCorners"],
        "geometryReview": photo["geometryReview"], "labelReview": photo["label"]["rectifiedReview"],
        "piecePlacement": photo["label"]["piecePlacement"], "orientation": photo["label"]["orientation"],
        "cells": square_labels(photo["label"]["piecePlacement"], photo["label"]["orientation"]),
    }
    if any(record.get(k) != v for k, v in expected.items()):
        raise ValueError(f"Cached record differs from reviewed annotation: {photo['id']}")


def assert_no_leakage(records):
    for key in ("groupId", "positionId", "originalSha256", "sha256", "placementFamily"):
        seen = {}
        for row in records:
            if seen.setdefault(row[key], row["split"]) != row["split"]:
                raise ValueError(f"Cross-partition leakage: {key}")


def build(plan_path, destination, *, root=ROOT):
    root, destination = root.resolve(), destination.resolve()
    if not destination.is_relative_to(root / ".cache"):
        raise ValueError("Keep derived datasets inside .cache.")
    if destination.exists():
        raise ValueError("Destination already exists; use a new version.")
    plan_hash = digest(plan_path)
    plan = json.loads(plan_path.read_text())
    if (plan.get("schemaVersion") != 1 or plan.get("dataRole") != "photo-training-partition-plan"
            or plan.get("independentFinalEvaluation") is not False):
        raise ValueError("Expected a frozen, non-final photographic partition plan.")
    paths = checked_references(plan, root)
    development = json.loads(paths["developmentManifest"].read_text())
    validation = json.loads(paths["validationManifest"].read_text())
    summary = audit_development(development, root=root)
    if (summary["reviewedCornerAnnotations"] != len(development["samples"])
            or summary["placementsReviewedAfterRectification"] != summary["labels"].get("visual-transcription", 0)):
        raise ValueError("All development labels and corners must have rectified reviews.")
    audit_validation(validation, development, root=root)
    if plan["assignments"] != assignments(development, validation):
        raise ValueError("Frozen assignments differ from reviewed batches.")
    excluded = sorted(r["id"] for r in development["samples"] if r["label"]["status"] != "visual-transcription")
    if plan["excludedPhotoIds"] != excluded:
        raise ValueError("Frozen exclusions differ from reviewed annotations.")
    old_root = paths["developmentSquaresMetadata"].parent
    if destination.is_relative_to(old_root) or old_root.is_relative_to(destination):
        raise ValueError("Keep the new dataset separate from the existing square export.")
    for photo in development["samples"] + validation["samples"]:
        for key in ("originalPath", "imagePath"):
            source = child(root, photo[key]).resolve()
            if destination.is_relative_to(source.parent) or source.is_relative_to(destination):
                raise ValueError("Keep square output separate from source images.")
    old_meta = json.loads(paths["developmentSquaresMetadata"].read_text())
    if (not old_meta.get("complete") or old_meta.get("dataRole") != "photo-development-squares"
            or old_meta["classOrder"] != list(LABELS)
            or old_meta["preprocessing"]["squareSize"] != 64
            or old_meta["preprocessing"]["colorMode"] != "RGB"
            or old_meta["sourceManifestSha256"] != digest(paths["developmentManifest"])):
        raise ValueError("Incompatible or stale development square export.")
    index = child(old_root, old_meta["indexes"]["verified"]["path"])
    if digest(index) != old_meta["indexes"]["verified"]["sha256"]:
        raise ValueError("Development square index changed.")
    cached = [json.loads(line) for line in index.read_text().splitlines()]
    cached_ids = [r["photoId"] for r in cached]
    if sorted(cached_ids) != plan["assignments"]["training"]["photoIds"]:
        raise ValueError("Development archives are missing, duplicated or unexpected.")
    by_id = {r["id"]: r for r in development["samples"]}
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = []
    coverage = {s: {c: {"light": 0, "dark": 0} for c in LABELS} for s in ("training", "validation")}
    with tempfile.TemporaryDirectory(prefix=".phone-training-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        (stage / "previews").mkdir()
        for split, items in (("training", cached), ("validation", validation["samples"])):
            for item in items:
                if split == "training":
                    photo = by_id[item["photoId"]]
                    match_cached_record(item, photo)
                    pixels, _ = load_board(old_root, item)
                    row = deepcopy(item)
                else:
                    photo = item
                    payload = child(root, photo["imagePath"]).read_bytes()
                    if hashlib.sha256(payload).hexdigest() != photo["imageSha256"]:
                        raise ValueError("Validation photograph changed after audit.")
                    with Image.open(BytesIO(payload)) as image:
                        pixels = extract_photo_squares(image, photo["boardCorners"], photo["label"]["orientation"])
                    row = {"photoId": photo["id"], "configurationId": photo["id"],
                           "groupId": photo["groupId"], "status": "ok", "boundsMode": "reviewed-quadrilateral",
                           "image": photo["imagePath"], "sha256": photo["imageSha256"],
                           **{k: photo[k] for k in ("originalPath", "originalSha256", "imageSize", "source",
                                                   "conditions", "boardCorners", "geometryReview")},
                           "labelReview": photo["label"]["rectifiedReview"],
                           "piecePlacement": photo["label"]["piecePlacement"], "orientation": photo["label"]["orientation"],
                           "cells": square_labels(photo["label"]["piecePlacement"], photo["label"]["orientation"])}
                row.update(split=split, sourceSplit=photo["split"],
                           positionId="photo-position-" + hashlib.sha256(row["piecePlacement"].encode()).hexdigest()[:16],
                           placementFamily=placement_family(row["piecePlacement"]),
                           array=f"{split}/{photo['id']}.npz", preview=f"previews/{photo['id']}.jpg")
                if split == "training":
                    target = stage / row["array"]
                    target.parent.mkdir(exist_ok=True)
                    shutil.copyfile(child(old_root, item["array"]), target)
                    if digest(target) != item["arraySha256"]:
                        raise ValueError("Reused archive changed during copy.")
                    row["reusedFrom"] = {"dataset": str(old_root.relative_to(root)),
                                         "array": item["array"], "sha256": item["arraySha256"]}
                else:
                    row["arraySha256"] = write_array(stage / row["array"], pixels, row["cells"])
                load_board(stage, row)
                with contact_sheet(pixels, row["cells"]) as sheet:
                    sheet.save(stage / row["preview"], quality=94)
                for cell in row["cells"]:
                    coverage[split][cell["label"]][cell["background"]] += 1
                records.append(row)
        assert_no_leakage(records)
        indexes = {}
        for name in ("verified", "training", "validation"):
            selected = records if name == "verified" else [r for r in records if r["split"] == name]
            path = stage / f"{name}.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in selected))
            indexes[name] = {"path": path.name, "sha256": digest(path), "boards": len(selected)}
        write_json(stage / "partition-plan.json", plan)
        report = {"schemaVersion": 1, "datasetId": plan["datasetId"], "dataRole": "photo-training-validation-squares",
                  "complete": True, "readyForTraining": True, "readyForValidation": True,
                  "independentFinalEvaluation": False, "classOrder": list(LABELS),
                  "preprocessing": old_meta["preprocessing"], "indexes": indexes,
                  "partitionPlan": {"path": "partition-plan.json", "sha256": digest(stage / "partition-plan.json"),
                                    "sourceSha256": plan_hash},
                  "inputs": plan["inputs"], "sourceRoot": str(root), "outputRoot": str(destination),
                  "splitCounts": {"training": len(cached), "validation": len(validation["samples"]), "evaluation": 0},
                  "squareCounts": {s: indexes[s]["boards"] * 64 for s in ("training", "validation")},
                  "reusedTrainingArchives": len(cached), "newValidationArchives": len(validation["samples"]),
                  "exclusions": old_meta["exclusions"], "classBackgroundCounts": coverage,
                  "categories": {s: dict(Counter(r["source"]["category"] for r in records if r["split"] == s))
                                 for s in ("training", "validation")},
                  "balancing": {"applied": False, "augmentationApplied": False, "policy": "All 64 cells retained; only future training may be balanced or augmented."},
                  "classificationEvaluated": False, "automaticDetectionEvaluated": False, "trainingRun": False,
                  "checks": {"archivesLoaded": len(records), "crossPartitionOverlap": False,
                             "sourceManifestsModified": False, "existingSquareExportModified": False},
                  "limitations": ["Reviewed geometry isolates classification; no automatic photo detection is measured.",
                                  "Source separation is user-reported, with conservative batch groups.",
                                  "Only the two photo manifests are compared; this is not permission to mix arbitrary digital datasets.",
                                  "This is a photographic pilot dataset, not a final independent evaluation."],
                  "codeSha256": {p: digest(ROOT / p) for p in ("tools/build_phone_training_dataset.py", "tools/build_phone_squares.py", "tools/neural_data.py")}}
        write_json(stage / "dataset.json", report)
        read_index(stage)
        cards = [f'<article><h2>{escape(Path(r["originalPath"]).stem)} — {r["split"]}</h2>'
                 f'<img loading="lazy" src="{r["preview"]}" alt="64 labeled squares"></article>' for r in records]
        (stage / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Photographic training dataset</title>'
            '<style>body{font-family:sans-serif}img{max-width:100%}</style><h1>Photographic training and validation crops</h1>'
            '<p>All 64 cells in canonical a8..h1 order. Reviewed geometry; no recognition or training results.</p>' + "\n".join(cards))
        checked_references(plan, root)
        if digest(plan_path) != plan_hash or digest(index) != old_meta["indexes"]["verified"]["sha256"]:
            raise ValueError("Frozen plan or source index changed during export.")
        if destination.exists():
            raise ValueError("Destination appeared during export.")
        stage.rename(destination)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "data/manifests/phone-training-v1.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/phone-training-v1")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = build(args.plan, args.output)
    if args.report:
        write_json(args.report, report)
    print(json.dumps({"output": report["outputRoot"], "boards": report["splitCounts"],
                      "squares": report["squareCounts"], "readyForTraining": True, "trainingRun": False}))


if __name__ == "__main__":
    main()
