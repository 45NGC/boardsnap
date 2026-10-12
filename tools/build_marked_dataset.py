"""Derive paired controlled-mark screenshots from the audited clean square corpus."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile

from tools.board_marks import KINDS, RENDERER, mark_plan, mark_png
from tools.build_square_dataset import build_dataset
from tools.neural_data import child, digest, read_index
from tools.position_dataset import DEFAULT_MANIFEST, validate_manifest


def select_sources(rows):
    """One existing view/size per position/appearance, selected without pixels or predictions."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["positionId"], row["configurationId"].rsplit("-", 1)[0]].append(row)
    return [min(values, key=lambda r: hashlib.sha256(
        f"marks-v1:{r['positionId']}:{r['configurationId']}:{r['orientation']}".encode()).hexdigest())
        for _, values in sorted(groups.items())]


def build_marked_captures(dataset, destination):
    """Keep all clean controls; mark a fixed pilot spanning every position and style.

    Publish PNGs and annotation pairs atomically. Every derived sample inherits
    the exact original position/group/split and records its original image hash.
    """
    if destination.exists():
        raise ValueError("Marked capture destination exists.")
    metadata, original = read_index(dataset)
    source_root = Path(metadata["sourceRoot"])
    selected = select_sources(original)
    selected_keys = {(r['positionId'], r['configurationId'], r['orientation']) for r in selected}
    records, coverage = [], defaultdict(Counter)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".marks-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        for number, row in enumerate(original, 1):
            path = child(source_root, row["image"])
            if digest(path) != row["sha256"]:
                raise ValueError("Clean source changed since audit.")
            base = {key: deepcopy(row[key]) for key in ("image", "sha256", "datasetId", "positionId", "groupId",
                    "split", "piecePlacement", "configurationId", "orientation", "boardBounds", "imageSize")}
            base.update(conditions=["clean"], baseConfigurationId=row["configurationId"],
                        pairId=f"{row['positionId']}:{row['configurationId']}:{row['orientation']}")
            target = stage / "clean" / row["image"]
            target.parent.mkdir(parents=True, exist_ok=True)
            # Copy bytes rather than hardlink: editing an output can never mutate a clean source.
            png = path.read_bytes()
            target.write_bytes(png)
            base["image"] = str(target.relative_to(stage))
            target.with_suffix(".json").write_text(json.dumps(base, indent=2) + "\n")
            records.append(base)
            if (row['positionId'], row['configurationId'], row['orientation']) not in selected_keys:
                continue
            for kind in KINDS:
                marks = mark_plan(row["piecePlacement"], kind, f"{row['positionId']}:{row['configurationId']}:{kind}")
                marked, evidence = mark_png(png, row["boardBounds"], row["orientation"], marks, row["piecePlacement"])
                variant = dict(base, configurationId=f"{row['configurationId']}-{kind}", conditions=[kind],
                               marks=marks, augmentation=evidence, provenanceKind="controlled-mark-variant")
                target = stage / kind / row["image"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(marked)
                variant.update(image=str(target.relative_to(stage)), sha256=digest(target))
                target.with_suffix(".json").write_text(json.dumps(variant, indent=2) + "\n")
                records.append(variant)
                marked_squares = {s for mark in marks for s in mark["squares"]}
                for cell in row["cells"]:
                    if cell["square"] in marked_squares:
                        coverage[f"{row['split']}/{kind}"][f"{cell['label']}:{cell['background']}"] += 1
            if number % 100 == 0:
                print(f"Marked capture sources {number}/{len(original)}", flush=True)
        report = {"schemaVersion": 1, "renderer": RENDERER, "complete": True,
                  "cleanDatasetSha256": digest(dataset / "dataset.json"),
                  "cleanIndexSha256": metadata["indexes"]["verified"]["sha256"],
                  "rendererSha256": digest(Path(__file__).with_name("board_marks.py")),
                  "selection": "all clean controls; one recorded view/size per position/appearance, minimum SHA256 marks-v1 key",
                  "selectedSourceBoards": len(selected), "cleanBoards": len(original),
                  "markedBoards": len(records)-len(original), "images": records,
                  "markedClassBackgroundCounts": dict(coverage),
                  "realUseClassificationIncluded": False,
                  "limitations": ["Synthetic overlays are not native platform rendering.",
                                  "Check indicators are king-specific; other marks are sampled across class/background buckets.",
                                  "No arrows; no legal move or check semantics are asserted."]}
        (stage / "captures.json").write_text(json.dumps(report, indent=2) + "\n")
        if destination.exists():
            raise ValueError("Destination appeared during build.")
        stage.rename(destination)
    return report


def corpus_summary(captures, dataset):
    """Small committable report; PNGs, arrays and the full capture index stay local."""
    capture_path = captures / "captures.json"
    captured = json.loads(capture_path.read_text())
    metadata, rows = read_index(dataset)
    if metadata["sourceCaptureReportSha256"] != digest(capture_path) or len(rows) != len(captured["images"]):
        raise ValueError("Marked square dataset does not match its capture report.")
    result = {key: value for key, value in captured.items() if key != "images"}
    result.update(squareDatasetSha256=digest(dataset / "dataset.json"),
                  captureReportSha256=digest(capture_path), indexes=metadata["indexes"],
                  splits={split: {"boards": sum(r["split"] == split for r in rows),
                                  "conditions": dict(Counter(c for r in rows if r["split"] == split for c in r["conditions"]))}
                          for split in ("training", "validation", "evaluation")})
    result["missingMarkedClassBackgrounds"] = {}
    for key, counts in captured["markedClassBackgroundCounts"].items():
        labels = "Kk" if key.endswith("/check") else ["empty", *"PNBRQKpnbrqk"]
        result["missingMarkedClassBackgrounds"][key] = [f"{label}:{color}" for label in labels
                for color in ("light", "dark") if not counts.get(f"{label}:{color}")]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-dataset", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text())
    validate_manifest(manifest)
    if args.output.exists():
        raise ValueError("Square destination exists.")
    report = build_marked_captures(args.clean_dataset, args.captures)
    build_dataset(args.captures.resolve(), report["images"], manifest, args.output,
                  provenance={"datasetId": "digital-marked-squares-v1",
                              "sourceCaptureReportSha256": digest(args.captures / "captures.json"),
                              "augmentationRenderer": RENDERER,
                              "augmentationRendererSha256": report["rendererSha256"]})
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(corpus_summary(args.captures, args.output), indent=2) + "\n")


if __name__ == "__main__":
    main()
