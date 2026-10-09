"""Compare an explicitly selected neural artifact with supported templates on CPU."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image

from boardsnap.classification import ClassificationError, classify_squares
from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError
from boardsnap.pipeline import recognize_image
from tools.capture_lichess import expand_placement
from tools.neural_data import CLASSES, child, digest, load_board, read_index

TEMPLATE_PROFILES = {"lichess-brown-cburnett": "lichess-cburnett-brown-v1",
                     "lichess-blue-cburnett": "lichess-cburnett-blue-v1",
                     "chesscom-green-neo": "chesscom-default-green-v1"}


def template_profile(row):
    return TEMPLATE_PROFILES.get(row["configurationId"].rsplit("-", 1)[0])


def template_ids(images, profile):
    squares = [[Image.fromarray(images[row * 8 + col]) for col in range(8)] for row in range(8)]
    try:
        labels = classify_squares(squares, profile=profile)
        return np.array([CLASSES.index("empty" if cell is None else cell) for row in labels for cell in row])
    finally:
        for row in squares:
            for square in row:
                square.close()


def placement_ids(placement):
    return np.array([CLASSES.index("empty" if c == "." else c) for row in expand_placement(placement) for c in row])


def score(records):
    confusion = np.zeros((13, 14), dtype=np.int64)
    by_position = defaultdict(list)
    for row in records:
        actual = np.asarray(row["predictions"])
        expected = np.asarray(row["expected"])
        np.add.at(confusion, (expected, np.where(actual < 0, 13, actual)), 1)
        by_position[row["positionId"]].append(bool(np.array_equal(actual, expected)))
    total = int(confusion.sum())
    correct = int(np.trace(confusion[:, :13]))
    classes = {}
    for i, label in enumerate(CLASSES):
        support, predicted, tp = int(confusion[i].sum()), int(confusion[:, i].sum()), int(confusion[i, i])
        classes[label] = {"total": support, "correct": tp, "predicted": predicted,
                          "recall": tp / support if support else None,
                          "precision": tp / predicted if predicted else None,
                          "f1": 2 * tp / (support + predicted) if support + predicted else None}
    return {"images": len(records), "positions": len(by_position),
            "exactBoards": sum(r["predictions"] == r["expected"] for r in records),
            "exactPositionsAllVariants": sum(all(values) for values in by_position.values()),
            "correctSquares": correct, "totalSquares": total,
            "squareAccuracy": correct / total if total else None,
            "macroRecall": float(np.mean([c["recall"] for c in classes.values() if c["recall"] is not None])) if total else None,
            "classes": classes, "confusionRowsExpectedColumnsPredicted": confusion.tolist(),
            "lastConfusionColumn": "processing-error"}


def timing(values):
    if not values:
        return {"samples": 0, "medianMilliseconds": None, "p95Milliseconds": None}
    return {"samples": len(values), "medianMilliseconds": float(np.median(values)) * 1000,
            "p95Milliseconds": float(np.percentile(values, 95)) * 1000}


def worker(dataset, model_path, backend, split, threads):
    cv2.setNumThreads(1)
    if backend == "neural":
        import torch
        from boardsnap.neural import NeuralClassifier
        torch.set_num_threads(threads)
        torch.use_deterministic_algorithms(True)
        classifier = NeuralClassifier(model_path)
    else:
        classifier = None
    metadata, rows = read_index(dataset, "verified")
    selected = [row for row in rows if row["split"] == split and (backend == "neural" or template_profile(row))]
    del rows
    if not selected:
        raise ValueError("No images in the requested comparison subset.")
    # Warm up once per supported appearance, outside the latency sample.
    first, _ = load_board(dataset, selected[0])
    if classifier:
        for _ in range(3):
            classifier.predict_ids(first)
    else:
        for profile in TEMPLATE_PROFILES.values():
            template_ids(first, profile)
    records = {"verified": [], "pipeline": []}
    latencies = {mode: [] for mode in records}
    source_root = Path(metadata["sourceRoot"])
    for number, row in enumerate(selected, 1):
        pixels, expected = load_board(dataset, row)
        profile = template_profile(row)
        base = {key: row[key] for key in ("image", "positionId", "groupId", "configurationId", "orientation")}
        base.update(expected=expected.tolist(), coverage="shared" if profile else "new")
        started = time.perf_counter()
        predictions = classifier.predict_ids(pixels) if classifier else template_ids(pixels, profile)
        latencies["verified"].append(time.perf_counter() - started)
        records["verified"].append(dict(base, predictions=predictions.tolist(), seconds=latencies["verified"][-1]))
        path = child(source_root, row["image"])
        if digest(path) != row["sha256"]:
            raise ValueError("Source screenshot changed before pipeline evaluation.")
        started = time.perf_counter()
        try:
            result = (classifier.recognize_image(path, orientation=row["orientation"]) if classifier else
                      recognize_image(path, profile=profile, orientation=row["orientation"]))
            outcome = {"predictions": placement_ids(result["piecePlacement"]).tolist()}
        except (ImageInputError, BoardDetectionError, ClassificationError) as error:
            outcome = {"predictions": [-1] * 64, "error": error.to_dict()["error"]}
        latencies["pipeline"].append(time.perf_counter() - started)
        records["pipeline"].append(dict(base, **outcome, seconds=latencies["pipeline"][-1]))
        if number % 100 == 0:
            print(f"{backend}: {number}/{len(selected)} images", flush=True)
    summaries = {}
    for mode, results in records.items():
        summaries[mode] = {"all": score(results), "shared": score([r for r in results if r["coverage"] == "shared"]),
                           "new": score([r for r in results if r["coverage"] == "new"]),
                           "configurations": {c: score([r for r in results if r["configurationId"] == c])
                                              for c in sorted({r["configurationId"] for r in results})},
                           "latency": timing(latencies[mode]),
                           "sharedLatency": timing([r["seconds"] for r in results if r["coverage"] == "shared"]),
                           "newLatency": timing([r["seconds"] for r in results if r["coverage"] == "new"]),
                           "processingFailures": sum("error" in row for row in results)}
    return {"backend": backend, "split": split, "summaries": summaries, "records": records,
            "peakEvaluationProcessRssMiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "memoryScope": "fresh Linux worker, imports + dataset index + model + evaluation; not model-only",
            "latencyScope": {"verified": "64 square classification incl. preprocessing; excludes NPZ I/O",
                             "pipeline": "PNG decode + detection + normalization + classification + output; explicit view"},
            "environment": {"platform": platform.platform(), "processor": platform.processor(),
                            "opencvThreads": 1, "torchThreads": threads if classifier else None}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "evaluation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--worker", choices=("neural", "templates"))
    args = parser.parse_args(argv)
    if args.worker:
        report = worker(args.dataset, args.model, args.worker, args.split, args.threads)
    else:
        training = json.loads((args.model.parent / "training.json").read_text())
        if not training["complete"] or training["weightsSha256"] != digest(args.model):
            raise ValueError("Require the completed, validation-selected artifact before evaluation.")
        reports = {}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        for backend in ("neural", "templates"):
            path = args.model.parent / f"{args.split}-{backend}.json"
            subprocess.run([sys.executable, "-m", "tools.evaluate_neural", "--dataset", str(args.dataset),
                            "--model", str(args.model), "--split", args.split, "--output", str(path),
                            "--threads", str(args.threads), "--worker", backend], check=True)
            reports[backend] = json.loads(path.read_text())
        # Exact intersection by image identity prevents accidental unpaired comparisons.
        for mode in ("verified", "pipeline"):
            paired = [r["image"] for r in reports["neural"]["records"][mode] if r["coverage"] == "shared"]
            assert paired == [r["image"] for r in reports["templates"]["records"][mode]]
        report = {"schemaVersion": 1, "modelSha256": digest(args.model),
                  "squareDatasetSha256": digest(args.dataset / "dataset.json"),
                  "evaluationCodeSha256": digest(Path(__file__)), "training": training,
                  "split": args.split, "templatesRemainDefault": True,
                  "templateProfiles": TEMPLATE_PROFILES, "results": reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
