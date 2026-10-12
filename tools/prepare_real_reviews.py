"""Prepare a deliberately non-importable review draft from detection-only images."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DETECTION = ROOT / "data/manifests/digital-detection-v1.json"


def prepare_reviews(destination):
    if destination.exists():
        raise ValueError("Refusing to overwrite review work.")
    references = json.loads(DETECTION.read_text())["samples"]
    samples = []
    aliases = {"last-move-highlights": "last-move", "circles": "circle", "check-highlight": "check",
               "manual-square-highlight": "highlights"}
    for item in references:
        if item["provenance"]["kind"] != "user-supplied-real-use":
            continue
        # Freeze subdivisions of development before consulting labels/results.
        group = item["sourceGroupId"]
        split = "evaluation" if item["split"] == "evaluation" else "validation" if group.endswith("-003") else "training"
        x, y, right, bottom = item["box"]
        samples.append({"id": item["id"], "image": str(ROOT / item["path"]), "sha256": item["sha256"],
            "externalPosition": {"positionId": f"real-{item['id']}", "groupId": f"real-{group}",
                                 "split": split, "piecePlacement": None},
            "orientation": None, "reviewed": False, "reviewedPlacement": None,
            "boardBounds": {"x": x, "y": y, "width": right-x, "height": bottom-y},
            "configuration": {"platform": item["platform"], "boardTheme": "unknown", "pieceSet": "unknown",
                              "layoutId": "real-desktop", "conditions": [aliases.get(c, c) for c in item["conditions"]]},
            "source": {"url": item["provenance"].get("url"), "capturedAt": None, "clientVersion": None,
                       "client": "desktop-web", "sourceGroupId": group,
                       "reviewedBy": None, "reviewedAt": None, "reviewMethod": None,
                       "provenanceNote": "User-supplied screenshot; source URL, date and browser version not supplied. Position and orientation still require independent review."}})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"schemaVersion": 2, "batchId": "real-reviewed-v1", "samples": samples}, indent=2) + "\n")
    return samples


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    samples = prepare_reviews(args.output)
    print(f"Prepared {len(samples)} pending reviews; no classification labels or dataset published.")


if __name__ == "__main__":
    main()
