"""Capture configurable clean datasets, or import reviewed real-use screenshots."""

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
import tempfile

from PIL import Image

from tools.position_dataset import (DEFAULT_MANIFEST, validate_manifest,
                                    validate_variants, variant_identity)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError("Expected a safe lowercase identifier")
    return value


def validate_config(config):
    required = {"id", "platform", "boardTheme", "pieceSet", "orientations", "viewport",
                "deviceScaleFactor", "conditions"}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError(f"Capture configuration must contain exactly {sorted(required)}")
    for key in ("id", "boardTheme", "pieceSet"):
        identifier(config[key])
    if config["platform"] not in ("lichess", "chesscom"):
        raise ValueError("Platform must be lichess or chesscom")
    views = config["orientations"]
    if (not isinstance(views, list) or not views
            or any(v not in ("white-bottom", "black-bottom") for v in views)
            or len(set(views)) != len(views)):
        raise ValueError("Choose distinct explicit orientations")
    viewport = config["viewport"]
    if (not isinstance(viewport, dict) or set(viewport) != {"width", "height"}
            or any(type(v) is not int or not 320 <= v <= 2560 for v in viewport.values())):
        raise ValueError("Viewport dimensions must be integers between 320 and 2560")
    if type(config["deviceScaleFactor"]) is not int or config["deviceScaleFactor"] not in (1, 2, 3):
        raise ValueError("deviceScaleFactor must be 1, 2 or 3")
    if config["conditions"] != ["clean"]:
        raise ValueError("Automated captures currently support only clean boards; markings are not implemented")


def validate_recipe(recipe, manifest):
    if not isinstance(recipe, dict) or set(recipe) != {"schemaVersion", "batchId", "positionIds", "configurations"}:
        raise ValueError("Expected schemaVersion, batchId, positionIds and configurations")
    if type(recipe["schemaVersion"]) is not int or recipe["schemaVersion"] != 1:
        raise ValueError("Expected capture recipe schemaVersion 1")
    identifier(recipe["batchId"])
    positions, configs = recipe["positionIds"], recipe["configurations"]
    if not isinstance(positions, list) or not positions or not isinstance(configs, list) or not configs:
        raise ValueError("Select at least one position and configuration")
    seen = set()
    for pid in positions:
        identifier(pid)
        variant_identity(manifest, pid)
        if pid in seen:
            raise ValueError("Duplicate positionId")
        seen.add(pid)
    seen = set()
    for config in configs:
        validate_config(config)
        if config["id"] in seen:
            raise ValueError("Duplicate configuration id")
        seen.add(config["id"])


def check_png(png, bounds, expected_size=None):
    with Image.open(BytesIO(png)) as image:
        if image.format != "PNG":
            raise ValueError("Capture must be a PNG; preserve original screenshot bytes")
        image.load()
        width, height = image.size
    if expected_size and (width, height) != tuple(expected_size):
        raise ValueError("Saved image dimensions disagree with capture configuration")
    if not isinstance(bounds, dict) or set(bounds) != {"x", "y", "width", "height"}:
        raise ValueError("Invalid board bounds")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds.values()):
        raise ValueError("Board bounds must be finite numbers")
    x, y, w, h = (bounds[k] for k in ("x", "y", "width", "height"))
    if min(w, h) < 128 or abs(w - h) > 1 or min(x, y) < 0 or x + w > width or y + h > height:
        raise ValueError("Board is clipped, too small or not square")
    return {"width": width, "height": height}


def save_sample(folder, stem, png, annotation):
    identifier(stem)
    size = check_png(png, annotation["boardBounds"])
    if annotation.get("imageSize", size) != size:
        raise ValueError("Image size does not describe the saved PNG")
    annotation = dict(annotation, image=f"{stem}.png", imageSize=size,
                      sha256=hashlib.sha256(png).hexdigest())
    folder.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "json"):
        if (folder / f"{stem}.{extension}").exists():
            raise ValueError("Refusing to overwrite a sample")
    (folder / f"{stem}.png").write_bytes(png)
    (folder / f"{stem}.json").write_text(json.dumps(annotation, indent=2) + "\n")
    return annotation


def capture_samples(staging, manifest, recipe, headed=False):
    from playwright.sync_api import sync_playwright
    from tools.capture_sites import capture_page

    annotations = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=not headed)
        try:
            for config in recipe["configurations"]:
                context = browser.new_context(viewport=config["viewport"],
                                              device_scale_factor=config["deviceScaleFactor"],
                                              locale="en-GB", color_scheme="light")
                try:
                    page = context.new_page()
                    page.set_default_timeout(30000)
                    for pid in recipe["positionIds"]:
                        identity = variant_identity(manifest, pid)
                        for view in config["orientations"]:
                            print(f"Capturing {pid} {config['id']} {view}", file=sys.stderr, flush=True)
                            png, observed = capture_page(page, identity["piecePlacement"], config, view)
                            annotation = dict(identity, **observed, configuration=config,
                                              orientation=view, provenanceKind="automated-platform-capture")
                            annotation["source"].update(browser=f"Chromium {browser.version}",
                                                        capturedAt=datetime.now(timezone.utc).isoformat())
                            validate_variants(manifest, [annotation])
                            folder = staging / identity["split"] / config["id"]
                            stem = f"{pid}-{view}"
                            annotations.append(save_sample(folder, stem, png, annotation))
                finally:
                    context.close()
        finally:
            browser.close()
    return annotations


def import_samples(staging, manifest, specification, spec_dir):
    """Import original bytes with explicit human review, never claim DOM verification."""
    if (not isinstance(specification, dict)
            or set(specification) != {"schemaVersion", "batchId", "samples"}
            or type(specification["schemaVersion"]) is not int or specification["schemaVersion"] != 1):
        raise ValueError("Invalid real-capture specification")
    samples = specification["samples"]
    if not isinstance(samples, list) or not samples:
        raise ValueError("Real capture samples must be a nonempty list")
    annotations, seen, game_splits = [], set(), {}
    for sample in samples:
        identity = variant_identity(manifest, sample["positionId"])
        sid = identifier(sample["id"])
        if sid in seen:
            raise ValueError("Duplicate real capture id")
        seen.add(sid)
        if sample.get("orientation") not in ("white-bottom", "black-bottom"):
            raise ValueError("Real capture needs explicit orientation")
        source = sample.get("source", {})
        fields = ("url", "capturedAt", "client", "clientVersion", "sourceGroupId", "reviewedBy", "reviewedAt")
        if any(not isinstance(source.get(k), str) or not source[k].strip() for k in fields):
            raise ValueError("Real capture needs complete provenance and human review")
        if source["client"] not in ("desktop-web", "mobile-web", "android-app", "ios-app"):
            raise ValueError("Unknown capture client")
        if sample.get("reviewedPlacement") != identity["piecePlacement"] or sample.get("reviewed") is not True:
            raise ValueError("Human-reviewed placement must match the frozen position")
        origin = source["sourceGroupId"]
        if game_splits.setdefault(origin, identity["split"]) != identity["split"]:
            raise ValueError("Related real-game captures cannot cross splits")
        config = sample.get("configuration", {})
        if any(not isinstance(config.get(k), str) or not config[k] for k in ("platform", "boardTheme", "pieceSet", "layoutId")):
            raise ValueError("Real capture needs board, pieces, platform and layout")
        if config["platform"] not in ("lichess", "chesscom"):
            raise ValueError("Unsupported platform")
        conditions = config.get("conditions")
        if not isinstance(conditions, list) or not conditions or any(c not in ("clean", "arrows", "highlights", "badges") for c in conditions):
            raise ValueError("List observed image conditions explicitly")
        if "clean" in conditions and len(conditions) > 1:
            raise ValueError("A marked image cannot be labeled clean")
        png = (spec_dir / sample["image"]).read_bytes()
        if sample.get("sha256") != hashlib.sha256(png).hexdigest():
            raise ValueError("Real screenshot changed since review")
        annotation = dict(identity, orientation=sample["orientation"], configuration=config,
                          source=source, boardBounds=sample["boardBounds"],
                          provenanceKind="reviewed-real-use", verification="human-reviewed; no DOM evidence")
        validate_variants(manifest, [annotation])
        annotations.append(save_sample(staging / identity["split"] / "real-use", sid, png, annotation))
    return annotations


def plan_hash(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def check_real_isolation(dataset_root, annotations, manifest):
    """Check prior plan hashes and identities before publishing any batch."""
    hashes, sources = {}, {}
    previous = []
    for path in dataset_root.glob("*/batch.json"):
        batch = json.loads(path.read_text())
        if batch["positionPlanSha256"] != plan_hash(manifest):
            raise ValueError("Position plan changed for this dataset; use a separately reviewed dataset ID")
        previous.extend(batch["samples"])
    for item in [*previous, *annotations]:
        identity = (item["groupId"], item["split"], item["piecePlacement"])
        if hashes.setdefault(item["sha256"], identity) != identity:
            raise ValueError("Identical images cannot have conflicting identities or partitions")
        if item["provenanceKind"] == "reviewed-real-use":
            source = (item["configuration"]["platform"], item["source"]["sourceGroupId"])
            if sources.setdefault(source, item["split"]) != item["split"]:
                raise ValueError("A real-game source already exists in a different partition")


def run_batch(manifest, specification, output_root, *, mode="capture", spec_dir=Path("."), headed=False):
    validate_manifest(manifest)
    dataset_root = output_root / identifier(manifest["datasetId"])
    target = dataset_root / identifier(specification["batchId"])
    if target.exists():
        raise ValueError("Batch destination exists; choose a new batchId or output root")
    if mode == "capture":
        validate_recipe(specification, manifest)
    elif mode != "import-real":
        raise ValueError("Unknown capture mode")
    check_real_isolation(dataset_root, [], manifest)
    dataset_root.mkdir(parents=True, exist_ok=True)
    # A per-dataset exclusive lock prevents concurrent publication across splits.
    lock = dataset_root / ".capture.lock"
    with lock.open("x"):
        try:
            with tempfile.TemporaryDirectory(prefix=".capture-", dir=dataset_root) as tmp:
                staging = Path(tmp)
                annotations = (capture_samples(staging, manifest, specification, headed) if mode == "capture"
                               else import_samples(staging, manifest, specification, spec_dir))
                check_real_isolation(dataset_root, annotations, manifest)
                (staging / "batch.json").write_text(json.dumps({
                    "schemaVersion": 1, "datasetId": manifest["datasetId"],
                    "positionPlanSha256": plan_hash(manifest),
                    "positionPlanHashEncoding": "json.dumps(sort_keys=True), UTF-8",
                    "recipe": specification, "samples": annotations,
                }, indent=2) + "\n")
                if target.exists():
                    raise ValueError("Batch destination appeared during capture")
                staging.rename(target)
        finally:
            lock.unlink()
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "import-real"))
    parser.add_argument("specification", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text())
        specification = json.loads(args.specification.read_text())
        validate_manifest(manifest)
        identifier(specification["batchId"])
        if args.mode == "capture":
            validate_recipe(specification, manifest)
        target = args.output_root / manifest["datasetId"] / specification["batchId"]
        if target.exists():
            raise ValueError("Batch destination exists")
        check_real_isolation(target.parent, [], manifest)
        if args.validate_only:
            if args.mode == "import-real":
                with tempfile.TemporaryDirectory() as temporary:
                    annotations = import_samples(Path(temporary), manifest, specification, args.specification.parent)
                    check_real_isolation(target.parent, annotations, manifest)
            print("Valid capture request; no dataset published")
            return 0
        target = run_batch(manifest, specification, args.output_root, mode=args.mode,
                           spec_dir=args.specification.parent, headed=args.headed)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(f"Capture request failed: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"Browser capture failed: {error}", file=sys.stderr)
        return 1
    print(f"Saved verified batch: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
