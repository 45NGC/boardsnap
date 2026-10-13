"""Extend clean/simple-mark controls with traced full-image arrow variants."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile

from tools.arrow_marks import CASES, RENDERER, arrow_plan
from tools.board_marks import mark_conditions, mark_png
from tools.build_marked_dataset import select_sources
from tools.build_square_dataset import build_dataset
from tools.neural_data import child, digest, read_index
from tools.position_dataset import DEFAULT_MANIFEST, validate_manifest


def build_captures(dataset, destination):
    if destination.exists():
        raise ValueError("Arrow capture destination exists.")
    metadata, rows = read_index(dataset)
    source_root = Path(metadata["sourceRoot"])
    clean = [r for r in rows if r.get("conditions") == ["clean"]]
    if not clean or any("arrow" in r.get("conditions", []) for r in rows):
        raise ValueError("Expected clean/simple-mark controls, without previous arrow variants.")
    selected = select_sources(clean)
    records, skipped, coverage = [], [], defaultdict(Counter)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".arrows-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        for row in rows:
            source = child(source_root, row["image"])
            if digest(source) != row["sha256"]:
                raise ValueError("Control PNG changed after audit.")
            target = stage / "controls" / row["image"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            record = {key: value for key, value in row.items() if key not in (
                "array", "arraySha256", "boundsMode", "cropBounds", "cells", "status", "detectionMetrics")}
            record.update(image=str(target.relative_to(stage)), overlayCase="+".join(row["conditions"]))
            target.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
            records.append(record)
        for number, row in enumerate(selected, 1):
            png = child(source_root, row["image"]).read_bytes()
            base = {key: value for key, value in row.items() if key not in (
                "array", "arraySha256", "boundsMode", "cropBounds", "cells", "status")}
            for case in CASES:
                marks, details = arrow_plan(row["piecePlacement"], case,
                                           f"arrows-v1:{row['pairId']}:{case}")
                if marks is None:
                    skipped.append(dict(details, positionId=row["positionId"], pairId=row["pairId"], split=row["split"]))
                    continue
                marked, evidence = mark_png(png, row["boardBounds"], row["orientation"], marks, row["piecePlacement"])
                target = stage / case / row["image"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(marked)
                record = dict(base, image=str(target.relative_to(stage)), sha256=digest(target),
                    configurationId=f"{row['configurationId']}-{case}", conditions=mark_conditions(marks),
                    marks=marks, overlayCase=case, arrowCoverage=details, augmentation=evidence,
                    provenanceKind="controlled-arrow-variant")
                target.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
                records.append(record)
                for index in details["arrowCoveredIndices"]:
                    cell = row["cells"][index]
                    coverage[f"{row['split']}/{case}"][f"{cell['label']}:{cell['background']}"] += 1
            if number % 100 == 0 or number == len(selected):
                print(f"Arrow sources {number}/{len(selected)}", flush=True)
        report = {"schemaVersion": 1, "complete": True, "renderer": RENDERER,
                  "parentDatasetSha256": digest(dataset / "dataset.json"),
                  "parentIndexSha256": metadata["indexes"]["verified"]["sha256"],
                  "rendererCodeSha256": {name: digest(Path(__file__).with_name(name)) for name in ("arrow_marks.py", "board_marks.py")},
                  "controlBoards": len(rows), "selectedCleanSources": len(selected),
                  "arrowBoards": len(records)-len(rows), "skippedUnavailableRoutes": skipped,
                  "coveredClassBackgroundCounts": dict(coverage), "images": records,
                  "realClassificationIncluded": False, "removalOrMaskingApplied": False,
                  "policy": "retain all controls and source partitions; generate four arrow cases on marks-v1 pilot sources",
                  "limits": "Synthetic overlays only; no recovery guarantee for fully obscured distinguishing piece information."}
        (stage / "captures.json").write_text(json.dumps(report, indent=2) + "\n")
        if destination.exists():
            raise ValueError("Destination appeared during build.")
        stage.rename(destination)
    return report


def summary(captures, dataset):
    report = json.loads((captures / "captures.json").read_text())
    metadata, rows = read_index(dataset)
    if metadata["sourceCaptureReportSha256"] != digest(captures / "captures.json") or len(rows) != len(report["images"]):
        raise ValueError("Capture and square indexes disagree.")
    output = {key: value for key, value in report.items() if key != "images"}
    output.update(squareDatasetSha256=digest(dataset / "dataset.json"), indexes=metadata["indexes"],
                  splits={s: {"cases": dict(Counter(r["overlayCase"] for r in rows if r["split"] == s)),
                              "geometries": dict(Counter(g for r in rows if r["split"] == s
                                                        for g in r.get("arrowCoverage", {}).get("geometries", []))),
                              "positions": len({r["positionId"] for r in rows if r["split"] == s}),
                              "groups": len({r["groupId"] for r in rows if r["split"] == s})}
                          for s in ("training", "validation", "evaluation")})
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-dataset", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text())
    validate_manifest(manifest)
    if args.output.exists():
        raise ValueError("Square dataset destination exists.")
    report = build_captures(args.parent_dataset, args.captures)
    build_dataset(args.captures.resolve(), report["images"], manifest, args.output,
                  provenance={"datasetId": "digital-arrow-squares-v1", "augmentationRenderer": RENDERER,
                              "sourceCaptureReportSha256": digest(args.captures / "captures.json"),
                              "parentDatasetSha256": report["parentDatasetSha256"]})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary(args.captures, args.output), indent=2) + "\n")


if __name__ == "__main__":
    main()
