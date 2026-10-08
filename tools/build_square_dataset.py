"""Build traced square arrays from audited captures, without training a model."""

import argparse
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np
from PIL import Image

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board
from boardsnap.normalization import normalize_board
from boardsnap.orientation import to_canonical
from boardsnap.profiles import DEFAULT_PROFILE
from boardsnap.segmentation import split_squares
from tools.capture_lichess import expand_placement
from tools.collect_clean_corpus import DEFAULT_RECIPE, audit_corpus, build_jobs
from tools.evaluate_detection import rectangle_metrics
from tools.position_dataset import DEFAULT_MANIFEST, LABELS, SPLITS, variant_identity

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURES = ROOT / "data/reports/digital-clean-corpus-v1.json"
SQUARE_SIZE = 64


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raster_bounds(bounds):
    """Round exclusive DOM edges to nearest pixels, ties to even like Pillow."""
    if set(bounds) != {"x", "y", "width", "height"} or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in bounds.values()
    ):
        raise ValueError("Expected finite numeric board bounds.")
    x, y, w, h = (bounds[k] for k in ("x", "y", "width", "height"))
    if min(x, y) < 0 or min(w, h) <= 0:
        raise ValueError("Invalid board bounds.")
    left, top, right, bottom = map(round, (x, y, x + w, y + h))
    return BoardBounds(left, top, right - left, bottom - top)


def square_labels(placement, orientation):
    """Canonical targets with visual cell coordinates; never rotate piece pixels."""
    if orientation not in ("white-bottom", "black-bottom"):
        raise ValueError("Expected explicit capture orientation.")
    rows = expand_placement(placement)
    cells = []
    for row in range(8):
        for col in range(8):
            label = "empty" if rows[row][col] == "." else rows[row][col]
            visual_row, visual_col = ((row, col) if orientation == "white-bottom"
                                      else (7 - row, 7 - col))
            cells.append({"index": row * 8 + col, "square": f"{'abcdefgh'[col]}{8-row}",
                          "label": label, "classId": LABELS.index(label),
                          "background": "light" if (row + col) % 2 == 0 else "dark",
                          "imageRow": visual_row, "imageColumn": visual_col})
    return cells


def extract_squares(image, bounds, orientation):
    """Use production normalization/segmentation and explicit canonical ordering."""
    with ExitStack() as stack:
        board = stack.enter_context(normalize_board(image, bounds, square_size=SQUARE_SIZE))
        visual = split_squares(board.image)
        for row in visual:
            for square in row:
                stack.enter_context(square)
        canonical = to_canonical(visual, orientation)
        return np.stack([np.asarray(cell) for row in canonical for cell in row])


def validate_records(records, manifest):
    """Never permit image variants, positions or source groups to cross splits."""
    seen, groups, positions, hashes = set(), {}, {}, {}
    for record in records:
        identity = variant_identity(manifest, record["positionId"])
        if any(record.get(k) != v for k, v in identity.items()):
            raise ValueError("Source identity differs from frozen position plan.")
        path = Path(record["image"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe source path.")
        key = (record["positionId"], record["configurationId"], record["orientation"])
        if key in seen:
            raise ValueError("Duplicate source variant.")
        seen.add(key)
        for mapping, name in ((groups, "groupId"), (positions, "positionId"), (hashes, "sha256")):
            if mapping.setdefault(record[name], record["split"]) != record["split"]:
                raise ValueError("Source data crosses partitions.")
        square_labels(record["piecePlacement"], record["orientation"])


def audited_sources(report_path, manifest, recipe):
    recorded = json.loads(report_path.read_text())
    output_root = Path(recorded["outputRoot"])
    if not output_root.is_absolute():
        output_root = ROOT / output_root
    actual = audit_corpus(manifest, recipe, build_jobs(manifest, recipe), output_root)
    for field in ("complete", "positionPlanSha256", "baseRecipeSha256", "imageCount", "images"):
        if recorded[field] != actual[field]:
            raise ValueError(f"Capture report does not match audited sources: {field}")
    validate_records(actual["images"], manifest)
    return output_root / manifest["datasetId"], actual["images"]


def new_statistics():
    return {split: {"sourceBoards": 0, "writtenBoards": 0, "failedBoards": 0,
                    "squares": 0, "withinOnePixelBoards": 0,
                    "classes": {label: {color: 0 for color in ("light", "dark")} for label in LABELS},
                    "configurations": {}, "uniquePositions": set(), "sourceGroups": set(),
                    "classPositions": {label: {color: set() for color in ("light", "dark")}
                                       for label in LABELS}}
            for split in SPLITS}


def add_coverage(stat, record, cells):
    stat["writtenBoards"] += 1
    stat["squares"] += 64
    stat["uniquePositions"].add(record["positionId"])
    stat["sourceGroups"].add(record["groupId"])
    config = stat["configurations"].setdefault(record["configurationId"],
        {label: {color: 0 for color in ("light", "dark")} for label in LABELS})
    for cell in cells:
        label, color = cell["label"], cell["background"]
        stat["classes"][label][color] += 1
        config[label][color] += 1
        stat["classPositions"][label][color].add(record["positionId"])


def finish_statistics(stats):
    for stat in stats.values():
        stat["uniquePositions"] = len(stat["uniquePositions"])
        stat["sourceGroups"] = len(stat["sourceGroups"])
        stat["classPositions"] = {label: {color: len(ids) for color, ids in colors.items()}
                                  for label, colors in stat["classPositions"].items()}
        stat["missingClassBackgrounds"] = [f"{label}:{color}" for label in LABELS
            for color in ("light", "dark") if not stat["classes"][label][color]]
    return stats


def training_weights(stats):
    """Optional inverse-frequency weights from verified training only; not applied."""
    counts = stats["training"]["classes"]
    total = stats["training"]["squares"]
    return {label: {color: (total / (26 * count) if count else None)
                    for color, count in colors.items()} for label, colors in counts.items()}


def write_array(path, pixels, cells):
    labels = np.asarray([cell["classId"] for cell in cells], dtype=np.uint8)
    if pixels.shape != (64, SQUARE_SIZE, SQUARE_SIZE, 3) or pixels.dtype != np.uint8:
        raise ValueError("Expected exactly 64 normalized RGB squares.")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, images=pixels, class_ids=labels)
    # Verify the serialized arrays, not just the in-memory representation.
    with np.load(path, allow_pickle=False) as saved:
        if set(saved.files) != {"images", "class_ids"} or not np.array_equal(saved["images"], pixels) or not np.array_equal(saved["class_ids"], labels):
            raise ValueError("Saved square arrays differ from their labels/pixels.")
    return sha256(path)


def build_dataset(source_root, records, manifest, destination, modes=("verified",),
                  detector=detect_board, provenance=None):
    """Publish a whole build atomically; detected failures stay in the denominator.

    Verified bounds are used only in the classifier-isolation branch and to
    measure detection afterwards. The detector receives the source pixels alone.
    Wrong detected bounds are retained, never repaired using the annotation.
    """
    validate_records(records, manifest)
    if not modes or len(set(modes)) != len(modes) or any(m not in ("verified", "detected") for m in modes):
        raise ValueError("Choose verified and/or detected mode.")
    if destination.exists():
        raise ValueError("Destination already exists; use a new build directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    statistics = {mode: new_statistics() for mode in modes}
    with tempfile.TemporaryDirectory(prefix=".squares-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        with ExitStack() as stack:
            indexes = {mode: stack.enter_context((staging / f"{mode}.jsonl").open("w")) for mode in modes}
            for number, record in enumerate(records, 1):
                source = source_root / record["image"]
                png = source.read_bytes()
                if hashlib.sha256(png).hexdigest() != record["sha256"]:
                    raise ValueError("Source PNG changed after capture audit.")
                with Image.open(BytesIO(png)) as decoded, decoded.convert("RGB") as image:
                    if list(image.size) != [record["imageSize"]["width"], record["imageSize"]["height"]]:
                        raise ValueError("Source dimensions changed.")
                    reference = raster_bounds(record["boardBounds"])
                    cells = square_labels(record["piecePlacement"], record["orientation"])
                    for mode in modes:
                        stat = statistics[mode][record["split"]]
                        stat["sourceBoards"] += 1
                        row = dict(record, boundsMode=mode, cells=cells, status="ok")
                        try:
                            bounds = reference if mode == "verified" else detector(image)
                        except BoardDetectionError as error:
                            stat["failedBoards"] += 1
                            row.update(status="detection-failed", error=error.to_dict()["error"], cells=[])
                        else:
                            row["cropBounds"] = asdict(bounds)
                            if mode == "detected":
                                row["detectionMetrics"] = rectangle_metrics(bounds.as_box(), reference.as_box())
                                stat["withinOnePixelBoards"] += row["detectionMetrics"]["maxEdgeErrorPixels"] <= 1
                            pixels = extract_squares(image, bounds, record["orientation"])
                            relative = (Path(mode) / record["split"] / record["configurationId"]
                                        / f"{record['positionId']}-{record['orientation']}.npz")
                            row.update(array=str(relative), arraySha256=write_array(staging / relative, pixels, cells))
                            add_coverage(stat, record, cells)
                        indexes[mode].write(json.dumps(row, separators=(",", ":")) + "\n")
                if number % 100 == 0 or number == len(records):
                    print(f"Prepared {number}/{len(records)} boards", flush=True)
        finished = {mode: finish_statistics(stats) for mode, stats in statistics.items()}
        report = {"schemaVersion": 1, "datasetId": "digital-squares-v1", "complete": True,
                  "sourceBoardCount": len(records), "classOrder": list(LABELS),
                  "preprocessing": {"squareSize": 64, "colorMode": "RGB", "dtype": "uint8",
                    "range": [0, 255], "resize": "Pillow LANCZOS whole board to 512x512",
                    "ordering": "a8 to h1; reorder cells for black-bottom without rotating pixels",
                    "boundsRounding": "nearest exclusive edges; ties to even",
                    "orientation": "explicit verified capture view; automatic reading not evaluated"},
                  "sourceRoot": str(source_root), "outputRoot": str(destination), "modes": finished,
                  "detectorProfile": DEFAULT_PROFILE, "classificationEvaluated": False,
                  "balancing": {"applied": False, "policy": "preserve every source square in every split"},
                  "indexes": {mode: {"path": f"{mode}.jsonl", "sha256": sha256(staging / f"{mode}.jsonl")}
                              for mode in modes},
                  "codeSha256": {name: sha256(ROOT / name) for name in (
                    "tools/build_square_dataset.py", "src/boardsnap/normalization.py",
                    "src/boardsnap/segmentation.py", "src/boardsnap/orientation.py", "src/boardsnap/detection.py")}}
        report.update(provenance or {})
        if "verified" in finished:
            report["balancing"]["optionalTrainingClassBackgroundWeights"] = training_weights(finished["verified"])
        (staging / "dataset.json").write_text(json.dumps(report, indent=2) + "\n")
        if destination.exists():
            raise ValueError("Destination appeared during build.")
        staging.rename(destination)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, default=DEFAULT_CAPTURES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mode", choices=("verified", "detected", "both"), default="verified")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text())
        recipe = json.loads(args.recipe.read_text())
        if args.output_root.exists():
            raise ValueError("Destination already exists; use a new build directory.")
        print("Auditing capture PNGs, annotations and partitions...", flush=True)
        source_root, records = audited_sources(args.captures, manifest, recipe)
        modes = ("verified", "detected") if args.mode == "both" else (args.mode,)
        report = build_dataset(source_root, records, manifest, args.output_root, modes,
                               provenance={"sourceCaptureReportSha256": sha256(args.captures),
                                           "positionManifestSha256": sha256(args.manifest)})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Completed square dataset: {args.output_root}")
        return 0
    except Exception as error:
        print(f"Square dataset build failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
