"""Report per-class/background and exact-position results on one explicit split."""

import argparse
import hashlib
import json
from pathlib import Path

from boardsnap.classification import ClassificationError
from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError
from boardsnap.pipeline import recognize_image


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "lichess-cburnett-brown-v1"
LABELS = ("empty", *"PNBRQKpnbrqk")


def _expand(placement: str) -> list[str]:
    return [piece for rank in placement.split("/") for token in rank
            for piece in (["empty"] * int(token) if token.isdigit() else [token])]


def evaluate(split: str) -> dict:
    """Score the real pipeline; annotations supply expectations, never predictions."""
    if split not in ("tuning", "evaluation"):
        raise ValueError("Split must be tuning or evaluation.")
    folder = ROOT / ("data/tuning" if split == "tuning" else "tests/fixtures/evaluation") / PROFILE
    manifest = json.loads((folder / "manifest.json").read_text())
    classes = {
        label: {"correct": 0, "total": 0,
                "backgrounds": {color: {"correct": 0, "total": 0} for color in ("light", "dark")},
                "predicted": {predicted: 0 for predicted in (*LABELS, "processing-error")}}
        for label in LABELS
    }
    results = []
    for position in manifest["positions"]:
        if position["split"] != split:
            raise ValueError("Mixed dataset splits are not allowed.")
        for view in ("white", "black"):
            path = folder / f"{position['groupId']}-{view}.png"
            expected = position["piecePlacement"]
            row = {"image": path.relative_to(ROOT).as_posix(), "expected": expected}
            try:
                actual = recognize_image(path)["piecePlacement"]
                row.update(actual=actual, exact=actual == expected)
                predictions = _expand(actual)
            except (ImageInputError, BoardDetectionError, ClassificationError) as error:
                row.update(error=error.to_dict()["error"], exact=False)
                predictions = ["processing-error"] * 64
            for index, (label, prediction) in enumerate(zip(_expand(expected), predictions, strict=True)):
                correct = int(label == prediction)
                color = ("light", "dark")[(index // 8 + index % 8) % 2]
                counts = classes[label]
                counts["total"] += 1
                counts["correct"] += correct
                counts["backgrounds"][color]["total"] += 1
                counts["backgrounds"][color]["correct"] += correct
                counts["predicted"][prediction] += 1
            results.append(row)
    total = sum(value["total"] for value in classes.values())
    correct = sum(value["correct"] for value in classes.values())
    occupied_total = total - classes["empty"]["total"]
    occupied_correct = correct - classes["empty"]["correct"]
    present = [value for value in classes.values() if value["total"]]
    return {
        "profileId": PROFILE, "split": split,
        "templateManifestSha256": hashlib.sha256((ROOT / "src/boardsnap/assets/piece-templates.json").read_bytes()).hexdigest(),
        "imageCount": len(results), "positionCount": len(manifest["positions"]),
        "exactPositions": sum(row["exact"] for row in results),
        "processingFailures": sum("error" in row for row in results),
        "correctSquares": correct, "totalSquares": total,
        "squareAccuracy": correct / total if total else None,
        "occupiedSquareAccuracy": occupied_correct / occupied_total if occupied_total else None,
        "macroRecallPresentClasses": sum(v["correct"] / v["total"] for v in present) / len(present) if present else None,
        "classes": classes, "images": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", required=True, choices=("tuning", "evaluation"))
    parser.add_argument("--output", type=Path, help="Save the development report instead of printing it.")
    args = parser.parse_args()
    content = json.dumps(evaluate(args.split), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"Saved evaluation report to {args.output}")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
