"""Checked square-dataset input shared by training and independent evaluation."""

import hashlib
import json
from pathlib import Path

import numpy as np

from tools.board_marks import validate_marks
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
            if "marks" in row:
                validate_marks(row["marks"], row["piecePlacement"])
                if row.get("conditions") != [m["kind"] for m in row["marks"]]:
                    raise ValueError("Mark conditions disagree with annotations.")
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


def training_indices(row):
    """Keep clean boards intact; avoid repeating 58+ untouched cells per variant.

    Only for training. Full cells and original frequencies are retained for
    validation/evaluation. Include immediate neighbours of rectangular overlays
    because whole-board LANCZOS resizing can bleed across a cell boundary.
    """
    if "marks" not in row:
        return list(range(64))
    result = set()
    for mark in row["marks"]:
        for square in mark["squares"]:
            row_id, col = 8-int(square[1]), ord(square[0])-97
            result.add(row_id*8+col)
            if mark["kind"] in ("last-move", "selection"):
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if 0 <= row_id+dr < 8 and 0 <= col+dc < 8:
                            result.add((row_id+dr)*8+col+dc)
    return sorted(result)


def load_split(root, rows, split, *, marked_cells_only=False):
    if marked_cells_only and split != "training":
        raise ValueError("Subsampling is allowed only in training.")
    selected = [row for row in rows if row["split"] == split]
    if not selected or any(row["status"] != "ok" for row in selected):
        raise ValueError("Expected a nonempty verified split.")
    indices = [training_indices(row) if marked_cells_only else list(range(64)) for row in selected]
    total = sum(map(len, indices))
    images = np.empty((total, 64, 64, 3), dtype=np.uint8)
    labels = np.empty(total, dtype=np.int64)
    offset = 0
    for row, keep in zip(selected, indices):
        pixels, targets = load_board(root, row)
        images[offset:offset+len(keep)], labels[offset:offset+len(keep)] = pixels[keep], targets[keep]
        offset += len(keep)
    return images, labels
