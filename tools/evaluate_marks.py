"""Paired clean/marked regression measurements, with detection scored separately."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import platform

import cv2
import numpy as np
from PIL import Image

from boardsnap.detection import BoardDetectionError, detect_board
from tools.build_square_dataset import extract_squares, raster_bounds
from tools.evaluate_detection import rectangle_metrics
from tools.evaluate_neural import score
from tools.neural_data import child, digest, load_board, read_index


def paired_results(records, *, by_case=False):
    """Compare exact boards, not just similar predictions (both can be wrong)."""
    clean = {r["pairId"]: r for r in records if r["conditions"] == ["clean"]}
    output = {}
    labels = lambda r: [r.get("overlayCase", "+".join(r["conditions"]))] if by_case else r["conditions"]
    for condition in sorted({c for r in records for c in labels(r)} - {"clean"}):
        rows = [r for r in records if condition in labels(r)]
        counts = {"pairs": len(rows), "bothCorrect": 0, "cleanOnlyCorrect": 0,
                  "markedOnlyCorrect": 0, "neitherCorrect": 0, "identicalPredictions": 0}
        for row in rows:
            if row["pairId"] not in clean:
                raise ValueError("Marked variant has no paired clean control.")
            base = clean[row["pairId"]]
            if base["expected"] != row["expected"]:
                raise ValueError("Paired clean/marked labels disagree.")
            a, b = base["expected"] == base["predictions"], row["expected"] == row["predictions"]
            key = "bothCorrect" if a and b else "cleanOnlyCorrect" if a else "markedOnlyCorrect" if b else "neitherCorrect"
            counts[key] += 1
            counts["identicalPredictions"] += base["predictions"] == row["predictions"]
        output[condition] = counts
    return output


def summarize(records):
    conditions = sorted({c for r in records for c in r["conditions"]})
    result = {"all": score(records), "conditions": {c: score([r for r in records if c in r["conditions"]]) for c in conditions},
            "paired": paired_results(records), "pairedCases": paired_results(records, by_case=True),
            "cases": {c: score([r for r in records if r.get("overlayCase", "+".join(r["conditions"])) == c])
                      for c in sorted({r.get("overlayCase", "+".join(r["conditions"])) for r in records})},
            "geometries": {g: score([r for r in records if g in r.get("arrowGeometries", [])])
                           for g in sorted({g for r in records for g in r.get("arrowGeometries", [])})},
            "errors": [{"image": r["image"], "condition": r["conditions"],
                        "wrongSquares": [i for i, (a, b) in enumerate(zip(r["expected"], r["predictions"])) if a != b]}
                       for r in records if r["expected"] != r["predictions"]]}
    if any("dimensions" in r for r in records):
        result["strata"] = {}
        for field in sorted({k for r in records for k in r.get("dimensions", {})}):
            groups = defaultdict(list)
            for row in records:
                groups[row["dimensions"][field]].append(row)
            result["strata"][field] = {}
            for value, group in sorted(groups.items()):
                metrics = score(group)
                del metrics["confusionRowsExpectedColumnsPredicted"]
                result["strata"][field][value] = metrics
    return result


def dimensions(row):
    style = row["style"]
    result = dict(style, cohort=row["cohort"], orientation=row["orientation"],
                  boardSide=str(round(row["boardBounds"]["width"])),
                  generalization="held-out-combination" if row["generalization"] else "seen-combination")
    for field in ("pieces", "background"):
        result[field] = f"{style['platform']}/{style[field]}"
    return result


def evaluate(dataset, baseline_path, candidate_path, split, threads=4, *,
             baseline_name="cleanBaseline", candidate_name="markedCandidate", verified_only=False):
    import torch
    from boardsnap.neural import NeuralClassifier
    torch.set_num_threads(threads)
    cv2.setNumThreads(1)
    metadata, rows = read_index(dataset)
    if baseline_name == candidate_name:
        raise ValueError("Comparison model names must differ.")
    models = {baseline_name: NeuralClassifier(baseline_path), candidate_name: NeuralClassifier(candidate_path)}
    measured_modes = ("verified",) if verified_only else ("verified", "detected")
    records = {name: {mode: [] for mode in measured_modes} for name in models}
    detections = defaultdict(list)
    detection_strata = defaultdict(list)
    selected = [r for r in rows if r["split"] == split]
    if not selected:
        raise ValueError("No boards in requested split.")
    for number, row in enumerate(selected, 1):
        pixels, expected = load_board(dataset, row)
        path = child(Path(metadata["sourceRoot"]), row["image"])
        if digest(path) != row["sha256"]:
            raise ValueError("Source screenshot changed.")
        base = {k: row[k] for k in ("image", "positionId", "groupId", "pairId", "conditions")}
        base["expected"] = expected.tolist()
        base["overlayCase"] = row.get("overlayCase", "+".join(row["conditions"]))
        base["arrowGeometries"] = row.get("arrowCoverage", {}).get("geometries", [])
        if "style" in row:
            base["dimensions"] = dimensions(row)
        for name, model in models.items():
            records[name]["verified"].append(dict(base, predictions=model.predict_ids(pixels).tolist()))
        if verified_only:
            if number % 100 == 0:
                print(f"Compared {number}/{len(selected)} {split} boards (verified bounds only)", flush=True)
            continue
        with Image.open(path) as source, source.convert("RGB") as image:
            try:
                bounds = detect_board(image)  # Pixel-only: no annotated bounds or mark labels.
            except BoardDetectionError as error:
                metrics = {"error": error.to_dict()["error"], "withinTwoPixels": False}
                detected = None
            else:
                metrics = rectangle_metrics(bounds.as_box(), raster_bounds(row["boardBounds"]).as_box())
                metrics["withinTwoPixels"] = metrics["maxEdgeErrorPixels"] <= 2
                detected = extract_squares(image, bounds, row["orientation"])
            detections[base["overlayCase"]].append(dict(image=row["image"], **metrics))
            for field, value in base.get("dimensions", {}).items():
                detection_strata[f"{field}:{value}"].append(dict(image=row["image"], **metrics))
            for name, model in models.items():
                predictions = [-1]*64 if detected is None else model.predict_ids(detected).tolist()
                records[name]["detected"].append(dict(base, predictions=predictions))
        if number % 100 == 0:
            print(f"Compared {number}/{len(selected)} {split} boards", flush=True)
    results = {name: {mode: summarize(data) for mode, data in modes.items()} for name, modes in records.items()}
    clean_ok = all(results[candidate_name][mode]["conditions"]["clean"]["exactBoards"] >=
                   results[baseline_name][mode]["conditions"]["clean"]["exactBoards"] for mode in measured_modes)
    # Also check square accuracy: equal whole-board totals must not hide more square errors.
    clean_ok &= all(results[candidate_name][mode]["conditions"]["clean"]["correctSquares"] >=
                    results[baseline_name][mode]["conditions"]["clean"]["correctSquares"] for mode in measured_modes)
    controls = ["clean", "last-move", "selection", "check", "circle", "move-dot"]
    regressions = {mode: {case: {
        "exactBoardsDelta": results[candidate_name][mode]["cases"][case]["exactBoards"] - results[baseline_name][mode]["cases"][case]["exactBoards"],
        "correctSquaresDelta": results[candidate_name][mode]["cases"][case]["correctSquares"] - results[baseline_name][mode]["cases"][case]["correctSquares"]}
        for case in controls if case in results[candidate_name][mode]["cases"]} for mode in measured_modes}
    return {"schemaVersion": 1, "split": split, "datasetSha256": digest(dataset / "dataset.json"),
            "models": {baseline_name: digest(baseline_path), candidate_name: digest(candidate_path)},
            "evaluationCodeSha256": digest(Path(__file__)),
            "runtimeSha256": {str(p.relative_to(Path(__file__).resolve().parents[1])): digest(p)
                              for p in sorted((Path(__file__).resolve().parents[1]/'src/boardsnap').rglob('*.py'))},
            "environment": {"python": platform.python_version(), "torch": str(torch.__version__), "threads": threads},
            "scope": "controlled overlays and clean controls; identical input pixels for both models; explicit view; no removal",
            "measuredModes": list(measured_modes),
            "detectionMeasured": not verified_only,
            "pipelineMeasured": not verified_only,
            "controlRegressions": regressions,
            "cleanPerformanceMaintained": bool(clean_ok), "templatesRemainDefault": True,
            "realUseClassificationIncluded": False,
            "detectionStrata": {c: {"images": len(values), "withinTwoPixels": sum(v["withinTwoPixels"] for v in values),
                "failures": [v for v in values if not v["withinTwoPixels"]]} for c, values in detection_strata.items()},
            "detection": {c: {"images": len(values), "withinTwoPixels": sum(v["withinTwoPixels"] for v in values),
                "failures": [v for v in values if not v["withinTwoPixels"]]} for c, values in detections.items()},
            "results": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "evaluation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--baseline-name", default="cleanBaseline")
    parser.add_argument("--candidate-name", default="markedCandidate")
    parser.add_argument("--regression", action="store_true",
                        help="Label already consulted images as regression evidence, not a new independent test")
    parser.add_argument("--verified-only", action="store_true",
                        help="Measure classification with reviewed bounds only; do not run or score detection")
    args = parser.parse_args(argv)
    training = json.loads((args.candidate.parent / "training.json").read_text())
    if not training["complete"] or training["weightsSha256"] != digest(args.candidate):
        raise ValueError("Compare only the completed, validation-selected candidate.")
    report = evaluate(args.dataset, args.baseline, args.candidate, args.split, args.threads,
                      baseline_name=args.baseline_name, candidate_name=args.candidate_name,
                      verified_only=args.verified_only)
    report["training"] = training
    report['dataRole'] = 'consulted-regression' if args.regression else args.split
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
