"""Optional reviewed real-use additions, without changing the frozen synthetic splits."""

import numpy as np

from tools.neural_data import load_split, read_index, digest
from tools.position_dataset import placement_family


def check_combined_partitions(base_rows, real_rows):
    groups, positions, families, games = {}, {}, {}, {}
    for row in real_rows:
        source = row.get("source", {})
        if (row.get("provenanceKind") != "reviewed-real-use"
                or row.get("verification") != "human-reviewed; no DOM evidence"
                or not source.get("reviewedBy") or not source.get("reviewedAt")):
            raise ValueError("Additional data must come from reviewed real-use imports.")
        if row["split"] != "evaluation" and any(c in ("arrows", "badges") for c in row.get("conditions", [])):
            raise ValueError("Arrows and badges are outside this simple-mark training stage.")
        origin = (row["configuration"]["platform"], source["sourceGroupId"])
        if games.setdefault(origin, row["split"]) != row["split"]:
            raise ValueError("Related real-game captures cross partitions.")
    for row in [*base_rows, *real_rows]:
        for seen, key in ((groups, row["groupId"]), (positions, row["positionId"]),
                          (families, placement_family(row["piecePlacement"]))):
            if seen.setdefault(key, row["split"]) != row["split"]:
                raise ValueError("Combined data crosses partitions.")


def add_real_training(root, base_rows, train, validation):
    """Open only real training/validation arrays; retain the original whole-board validation distribution."""
    metadata, rows = read_index(root)
    check_combined_partitions(base_rows, rows)
    output = []
    for split, original in (("training", train), ("validation", validation)):
        if any(r["split"] == split for r in rows):
            extra = load_split(root, rows, split)
            output.append(tuple(np.concatenate((a, b)) for a, b in zip(original, extra)))
        else:
            output.append(original)
    provenance = {"datasetSha256": digest(root / "dataset.json"), "indexSha256": metadata["indexes"]["verified"]["sha256"],
                  "trainingBoards": sum(r["split"] == "training" for r in rows),
                  "validationBoards": sum(r["split"] == "validation" for r in rows),
                  "evaluationArraysLoaded": False}
    return *output, provenance
