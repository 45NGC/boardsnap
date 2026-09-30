"""Integrity checks for the first dataset; no recognition accuracy is measured."""

import hashlib
import json
import math
from pathlib import Path
import struct
from urllib.parse import parse_qs, urlparse

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "lichess-cburnett-brown-v1"
DIRECTORIES = {
    "tuning": ROOT / "data/tuning" / PROFILE,
    "evaluation": ROOT / "tests/fixtures/evaluation" / PROFILE,
}
MANIFEST = json.loads((ROOT / "data/manifests" / f"{PROFILE}.json").read_text())
POSITIONS = MANIFEST["positions"]
pytestmark = pytest.mark.evaluation


@pytest.mark.parametrize("position", POSITIONS, ids=lambda p: p["groupId"])
@pytest.mark.parametrize("color", ["white", "black"])
def test_sample_matches_manifest_and_png(position, color):
    folder = DIRECTORIES[position["split"]]
    stem = f"{position['groupId']}-{color}"
    annotation = json.loads((folder / f"{stem}.json").read_text())
    png = (folder / f"{stem}.png").read_bytes()

    assert annotation["image"] == f"{stem}.png"
    assert annotation["profileId"] == PROFILE
    assert annotation["groupId"] == position["groupId"]
    assert annotation["split"] == position["split"]
    assert annotation["orientation"] == f"{color}-bottom"
    assert annotation["piecePlacement"] == position["piecePlacement"]
    assert annotation["sha256"] == hashlib.sha256(png).hexdigest()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png[12:16] == b"IHDR"
    assert png[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82"
    width, height = struct.unpack(">II", png[16:24])
    assert annotation["imageSize"] == {"width": width, "height": height}
    assert (width, height) == (1280, 1000)

    bounds = annotation["boardBounds"]
    assert set(bounds) == {"x", "y", "width", "height"}
    assert all(math.isfinite(value) for value in bounds.values())
    assert bounds["x"] >= 0 and bounds["y"] >= 0
    assert bounds["width"] == bounds["height"] > 0
    assert bounds["x"] + bounds["width"] <= width
    assert bounds["y"] + bounds["height"] <= height

    ranks = annotation["piecePlacement"].split("/")
    assert len(ranks) == 8
    for rank in ranks:
        assert rank and all(symbol in "12345678PNBRQKpnbrqk" for symbol in rank)
        assert sum(int(symbol) if symbol.isdigit() else 1 for symbol in rank) == 8
    query = parse_qs(urlparse(annotation["source"]["url"]).query)
    assert query["fen"] == [position["piecePlacement"]]
    assert query["color"] == [color]


def test_dataset_inventory_and_partition_separation():
    assert MANIFEST["profileId"] == PROFILE
    assert len(POSITIONS) == 10
    assert len({p["groupId"] for p in POSITIONS}) == 10
    assert len({p["piecePlacement"] for p in POSITIONS}) == 10
    all_hashes = []
    for split, folder in DIRECTORIES.items():
        positions = [p for p in POSITIONS if p["split"] == split]
        assert len(positions) == (8 if split == "tuning" else 2)
        partition_manifest = json.loads((folder / "manifest.json").read_text())
        assert partition_manifest == dict(MANIFEST, positions=positions)
        stems = {f"{p['groupId']}-{color}" for p in positions for color in ("white", "black")}
        assert {p.stem for p in folder.glob("*.png")} == stems
        assert {p.stem for p in folder.glob("*.json")} == stems | {"manifest"}
        all_hashes.extend(hashlib.sha256((folder / f"{stem}.png").read_bytes()).hexdigest() for stem in stems)
    assert len(set(all_hashes)) == 20
