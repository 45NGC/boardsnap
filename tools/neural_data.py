"""Checked square-dataset input shared by training and independent evaluation."""

import hashlib
import json
from pathlib import Path

import numpy as np

from tools.build_square_dataset import square_labels
from tools.position_dataset import LABELS as CLASSES


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def child(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Dataset path escapes its root.")
    return path


def read_index(root, mode="verified"):
    metadata = json.loads((root / "dataset.json").read_text())
    if (not metadata.get("complete") or metadata["classOrder"] != list(CLASSES)
            or metadata["preprocessing"]["squareSize"] != 64
            or metadata["preprocessing"]["colorMode"] != "RGB"):
        raise ValueError("Incompatible square dataset.")
    index = child(root, metadata["indexes"][mode]["path"])
    if digest(index) != metadata["indexes"][mode]["sha256"]:
        raise ValueError("Square index changed.")
    rows = [json.loads(line) for line in index.read_text().splitlines()]
    groups, positions, variants = {}, {}, set()
    for row in rows:
        split = row["split"]
        if split not in ("training", "validation", "evaluation"):
            raise ValueError("Invalid split.")
        for seen, key in ((groups, "groupId"), (positions, "positionId")):
            if seen.setdefault(row[key], split) != split:
                raise ValueError("Source group or position crosses partitions.")
        identity = (row["positionId"], row["configurationId"], row["orientation"])
        if identity in variants:
            raise ValueError("Duplicate square-dataset variant.")
        variants.add(identity)
        if row["status"] == "ok":
            if row["cells"] != square_labels(row["piecePlacement"], row["orientation"]):
                raise ValueError("Square labels do not match canonical placement.")
        elif mode != "detected" or row["status"] != "detection-failed":
            raise ValueError("Unexpected failed square record.")
    return metadata, rows


def load_board(root, row):
    path = child(root, row["array"])
    if digest(path) != row["arraySha256"]:
        raise ValueError("Square archive changed.")
    with np.load(path, allow_pickle=False) as archive:
        images, labels = archive["images"], archive["class_ids"]
    if (images.shape != (64, 64, 64, 3) or images.dtype != np.uint8
            or labels.shape != (64,) or labels.dtype != np.uint8
            or not np.array_equal(labels, [cell["classId"] for cell in row["cells"]])):
        raise ValueError("Invalid square pixels or labels.")
    return images, labels.astype(np.int64)


def load_split(root, rows, split):
    selected = [row for row in rows if row["split"] == split]
    if not selected or any(row["status"] != "ok" for row in selected):
        raise ValueError("Expected a nonempty verified split.")
    images = np.empty((64 * len(selected), 64, 64, 3), dtype=np.uint8)
    labels = np.empty(64 * len(selected), dtype=np.int64)
    for number, row in enumerate(selected):
        images[number * 64:(number + 1) * 64], labels[number * 64:(number + 1) * 64] = load_board(root, row)
    return images, labels
