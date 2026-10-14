"""Extend the previous corpus with audited styles, overlays and controlled layouts."""

import argparse
from collections import Counter
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image

from tools.arrow_marks import CASES, arrow_plan
from tools.board_marks import KINDS, mark_conditions, mark_plan, mark_png
from tools.build_marked_dataset import select_sources
from tools.build_square_dataset import (build_dataset, raster_bounds, new_statistics,
                                        add_coverage, finish_statistics, training_weights)
from tools.collect_clean_corpus import audit_corpus
from tools.collect_styles import ROOT, RECIPE, POLICY, style_jobs
from tools.neural_data import child, digest, read_index
from tools.position_dataset import DEFAULT_MANIFEST


def dimensions(config):
    return {"platform": config["platform"], "pieces": config["pieceSet"],
            "background": config["boardTheme"], "combination": config["id"].rsplit("-", 1)[0],
            "layout": "lichess-editor" if config["platform"] == "lichess" else "chesscom-analysis",
            "client": "desktop-web"}


def check_reservation(rows, reserved):
    for row in rows:
        if row["style"]["combination"] in reserved and row["split"] != "evaluation":
            raise ValueError("Reserved combinations cannot appear in development partitions.")


def derive_captures(capture_root, destination, manifest, recipe, policy):
    jobs = style_jobs(manifest, recipe, policy)
    audit = audit_corpus(manifest, recipe, jobs, capture_root)
    config_map = {j["configurations"][0]["id"]: j["configurations"][0] for j in jobs}
    records = []
    for source in audit["images"]:
        row = dict(source, style=dimensions(config_map[source["configurationId"]]),
                   conditions=["clean"], overlayCase="clean", cohort="expansion",
                   baseConfigurationId=source["configurationId"],
                   pairId=f"{source['positionId']}:{source['configurationId']}:{source['orientation']}")
        row["generalization"] = row["style"]["combination"] in policy["heldOutCombinations"]
        records.append(row)
    check_reservation(records, policy["heldOutCombinations"])
    selected = {(r["positionId"], r["configurationId"], r["orientation"]) for r in select_sources(records)}
    if destination.exists():
        raise ValueError("Derived capture destination exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = []
    with tempfile.TemporaryDirectory(prefix=".styles-", dir=destination.parent) as temporary:
        stage = Path(temporary)

        def save(row, png, folder):
            target = stage / folder / row["configurationId"] / f"{row['positionId']}-{row['orientation']}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(png)
            row = dict(row, image=str(target.relative_to(stage)), sha256=digest(target))
            target.with_suffix(".json").write_text(json.dumps(row, indent=2) + "\n")
            output.append(row)

        for number, row in enumerate(records, 1):
            path = capture_root / manifest["datasetId"] / row["image"]
            png = path.read_bytes()
            if digest(path) != row["sha256"]:
                raise ValueError("Audited capture changed.")
            save(row, png, "clean")
            if (row["positionId"], row["configurationId"], row["orientation"]) not in selected:
                continue
            for case in (*KINDS, *CASES):
                key = f"styles-v2:{row['pairId']}:{case}"
                if case in CASES:
                    marks, coverage = arrow_plan(row["piecePlacement"], case, key)
                    if marks is None:
                        raise ValueError(f"Requested arrow scenario unavailable: {key}")
                else:
                    marks, coverage = mark_plan(row["piecePlacement"], case, key), None
                marked, evidence = mark_png(png, row["boardBounds"], row["orientation"], marks, row["piecePlacement"])
                variant = dict(row, configurationId=f"{row['configurationId']}-{case}",
                               marks=marks, augmentation=evidence, conditions=mark_conditions(marks), overlayCase=case,
                               provenanceKind="controlled-style-overlay")
                if coverage is not None:
                    variant["arrowCoverage"] = coverage
                save(variant, marked, "marked")
            # These are controlled layout/size probes, not screenshots of native apps.
            for layout, side, margin in (("board-crop-384", 384, 0), ("synthetic-margins-256", 256, 64)):
                with Image.open(BytesIO(png)) as image:
                    with image.crop(raster_bounds(row["boardBounds"]).as_box()) as crop:
                        with crop.resize((side, side), Image.Resampling.LANCZOS) as resized:
                            with Image.new("RGB", (side+2*margin, side+2*margin), (45, 49, 55)) as canvas:
                                canvas.paste(resized, (margin, margin))
                                buffer = BytesIO()
                                canvas.save(buffer, format="PNG")
                configuration = f"{row['configurationId']}-{layout}"
                variant = dict(row, configurationId=configuration, style=dict(row["style"], layout=layout),
                               pairId=f"{row['positionId']}:{configuration}:{row['orientation']}",
                               imageSize={"width": side+2*margin, "height": side+2*margin},
                               boardBounds={"x": margin, "y": margin, "width": side, "height": side},
                               provenanceKind="controlled-layout-variant",
                               augmentation={"baseImageSha256": row["sha256"], "method": layout})
                save(variant, buffer.getvalue(), "layouts")
            if number % 100 == 0:
                print(f"Derived sources {number}/{len(records)}", flush=True)
        report = {"complete": True, "images": output, "captureImages": len(records),
                  "derivedImages": len(output)-len(records), "stylePolicy": policy,
                  "recipeSha256": digest(RECIPE), "policySha256": digest(POLICY),
                  "generatorSha256": digest(Path(__file__))}
        (stage / "captures.json").write_text(json.dumps(report, indent=2) + "\n")
        stage.rename(destination)
    return report


def merge_datasets(parent, addition, destination, policy):
    """Copy immutable arrays, preserve every group, and attach independent style dimensions."""
    if destination.exists():
        raise ValueError("Merged dataset destination exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stats, count = new_statistics(), 0
    with tempfile.TemporaryDirectory(prefix=".style-squares-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        provenance = {}
        with (stage / "verified.jsonl").open("w") as index:
            for cohort, root in (("previous", parent), ("expansion", addition)):
                metadata, rows = read_index(root)
                provenance[cohort] = {"datasetSha256": digest(root / "dataset.json"),
                                      "indexSha256": metadata["indexes"]["verified"]["sha256"]}
                for original in rows:
                    row = deepcopy(original)
                    if "style" not in row:
                        base = row["baseConfigurationId"]
                        platform, board, pieces, size = base.split("-")
                        row["style"] = dimensions(dict(id=base, platform=platform, boardTheme=board, pieceSet=pieces))
                    row.update(cohort=cohort, generalization=row["style"]["combination"] in policy["heldOutCombinations"])
                    check_reservation([row], policy["heldOutCombinations"])
                    image = child(Path(metadata["sourceRoot"]), row["image"])
                    row["image"] = str(image.relative_to(ROOT))
                    array = child(root, row["array"])
                    if digest(array) != row["arraySha256"]:
                        raise ValueError("Source square archive changed.")
                    target = stage / cohort / row["array"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(array, target)
                    row["array"] = str(target.relative_to(stage))
                    add_coverage(stats[row["split"]], row, row["cells"])
                    stats[row["split"]]["sourceBoards"] += 1
                    count += 1
                    index.write(json.dumps(row, separators=(",", ":")) + "\n")
        finish_statistics(stats)
        result = {"schemaVersion": 1, "complete": True, "datasetId": "digital-style-squares-v2",
                  "sourceRoot": str(ROOT), "sourceBoardCount": count, "classOrder": metadata["classOrder"],
                  "preprocessing": metadata["preprocessing"], "heldOutCombinations": policy["heldOutCombinations"],
                  "sourceDatasets": provenance, "modes": {"verified": stats},
                  "indexes": {"verified": {"path": "verified.jsonl", "sha256": digest(stage / "verified.jsonl")}},
                  "balancing": {"applied": False, "optionalTrainingClassBackgroundWeights": training_weights(stats)}}
        (stage / "dataset.json").write_text(json.dumps(result, indent=2) + "\n")
        read_index(stage)  # Check cross-corpus group identities before publishing.
        stage.rename(destination)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--new-squares", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(DEFAULT_MANIFEST.read_text())
    recipe, policy = json.loads(RECIPE.read_text()), json.loads(POLICY.read_text())
    captures = derive_captures(args.capture_root, args.derived, manifest, recipe, policy)
    build_dataset(args.derived.resolve(), captures["images"], manifest, args.new_squares,
                  provenance={"datasetId": "digital-style-addition-v2", "heldOutCombinations": policy["heldOutCombinations"]})
    merged = merge_datasets(args.parent, args.new_squares, args.output, policy)
    _, rows = read_index(args.output)
    report = {k: v for k, v in captures.items() if k != "images"}
    report.update(boards=merged["sourceBoardCount"], datasetSha256=digest(args.output / "dataset.json"),
                  splitCounts=dict(Counter(r["split"] for r in rows)),
                  coverage={field: dict(Counter(r["style"][field] for r in rows))
                            for field in ("platform", "pieces", "background", "combination", "layout", "client")},
                  heldOutImages=sum(r["generalization"] for r in rows), nativeMobileEvaluated=False)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
