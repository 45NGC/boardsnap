"""Reviewed positions outside the generated plan, with conservative split guards."""

import json
from pathlib import Path
import re

from tools.capture_lichess import expand_placement
from tools.position_dataset import SPLITS, legacy_families, placement_family

ROOT = Path(__file__).resolve().parents[1]


def external_identity(position, manifest):
    if not isinstance(position, dict) or set(position) != {"positionId", "groupId", "split", "piecePlacement"}:
        raise ValueError("External position needs positionId, groupId, split and piecePlacement.")
    for field in ("positionId", "groupId"):
        if not isinstance(position[field], str) or not re.fullmatch(r"real-[a-z0-9][a-z0-9_-]{0,58}", position[field]):
            raise ValueError("External position and group IDs must use the real- namespace.")
    if position["split"] not in SPLITS:
        raise ValueError("External game requires a frozen partition.")
    expand_placement(position["piecePlacement"])
    family = placement_family(position["piecePlacement"])
    if family in {placement_family(p["piecePlacement"]) for p in manifest["positions"]} | legacy_families():
        raise ValueError("External position overlaps an existing corpus; use/review its original identity.")
    return dict(position, datasetId=manifest["datasetId"])


def check_detection_reservation(sample, identity):
    """Detection-held-out games must never become classifier training/validation data."""
    references = json.loads((ROOT / "data/manifests/digital-detection-v1.json").read_text())["samples"]
    platform = sample["configuration"]["platform"]
    group = sample["source"]["sourceGroupId"]
    for reference in references:
        same_image = sample["sha256"] == reference["sha256"]
        if same_image and (platform != reference["platform"] or group != reference["sourceGroupId"]):
            raise ValueError("Real image must retain its reviewed detection source group and platform.")
        same_group = platform == reference["platform"] and group == reference["sourceGroupId"]
        if (same_image or same_group) and reference["split"] == "evaluation" and identity["split"] != "evaluation":
            raise ValueError("A detection-held-out game must remain in evaluation.")
        if same_image:
            b = sample["boardBounds"]
            if [b["x"], b["y"], b["x"]+b["width"], b["y"]+b["height"]] != reference["box"]:
                raise ValueError("Imported image disagrees with its reviewed detection bounds.")
