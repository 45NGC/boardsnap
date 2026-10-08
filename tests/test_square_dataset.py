"""Square data labels, pixel ordering, partition isolation and stage separation."""

from copy import deepcopy
import json

import numpy as np
from PIL import Image, ImageDraw
import pytest

from boardsnap.detection import BoardBounds, BoardDetectionError
from tools import build_square_dataset as squares
from tools.position_dataset import LABELS, DEFAULT_MANIFEST, variant_identity

MANIFEST = json.loads(DEFAULT_MANIFEST.read_text())
pytestmark = pytest.mark.unit


def painted_board(view):
    image = Image.new("RGB", (512, 512))
    draw = ImageDraw.Draw(image)
    for index in range(64):
        row, col = divmod(index, 8)
        if view == "black-bottom":
            row, col = 7 - row, 7 - col
        x, y = col * 64, row * 64
        draw.rectangle((x, y, x + 63, y + 63), fill=(index * 3, index, 255 - index))
        # An asymmetric mark catches accidentally rotated piece drawings.
        draw.rectangle((x + 2, y + 2, x + 5, y + 5), fill="white")
    return image


@pytest.mark.parametrize("view", ["white-bottom", "black-bottom"])
def test_all_64_cells_have_correct_identity_and_upright_pixels(view):
    with painted_board(view) as image:
        pixels = squares.extract_squares(image, BoardBounds(0, 0, 512, 512), view)
    assert pixels.shape == (64, 64, 64, 3)
    assert pixels.dtype == np.uint8
    for index in range(64):
        assert tuple(pixels[index, 32, 32]) == (index * 3, index, 255 - index)
        assert tuple(pixels[index, 3, 3]) == (255, 255, 255)
        assert tuple(pixels[index, 60, 60]) == (index * 3, index, 255 - index)


@pytest.mark.parametrize("view", ["white-bottom", "black-bottom"])
def test_labels_classes_backgrounds_and_visual_coordinates(view):
    cells = squares.square_labels("RNBQKPpn/brqk4/8/8/8/8/8/7P", view)
    assert len(cells) == 64
    assert {c["classId"] for c in cells} == set(range(13))
    assert [c["label"] for c in cells[:8]] == list("RNBQKPpn")
    assert cells[0]["square"] == "a8" and cells[0]["background"] == "light"
    assert cells[-1]["square"] == "h1" and cells[-1]["label"] == "P"
    assert cells[8]["background"] == "dark"
    assert {(c["imageRow"], c["imageColumn"]) for c in cells} == {(r, c) for r in range(8) for c in range(8)}
    assert cells[0]["imageRow"] == (0 if view == "white-bottom" else 7)
    assert cells[0]["imageColumn"] == (0 if view == "white-bottom" else 7)
    assert all(LABELS[c["classId"]] == c["label"] for c in cells)


def test_fractional_bounds_round_exclusive_edges_before_production_crop():
    bounds = squares.raster_bounds({"x": 94.5, "y": 147.875, "width": 520, "height": 520})
    assert bounds.as_box() == (94, 148, 614, 668)
    with pytest.raises(ValueError):
        squares.raster_bounds({"x": float("nan"), "y": 0, "width": 512, "height": 512})


@pytest.fixture
def sources(tmp_path):
    records = []
    for view in ("white-bottom", "black-bottom"):
        path = tmp_path / f"{view}.png"
        with painted_board(view) as image:
            image.save(path)
        records.append({**variant_identity(MANIFEST, "digital-009"), "image": path.name,
                        "sha256": squares.sha256(path), "orientation": view, "configurationId": "fixture",
                        "boardBounds": {"x": 0, "y": 0, "width": 512, "height": 512},
                        "imageSize": {"width": 512, "height": 512}})
    return tmp_path, records


def test_published_arrays_preserve_source_labels_and_match_both_views(sources):
    root, records = sources
    target = root / "out"
    def forbidden(_):
        pytest.fail("Classifier-isolation data called the detector")
    report = squares.build_dataset(root, records, MANIFEST, target, detector=forbidden)
    rows = [json.loads(line) for line in (target / "verified.jsonl").read_text().splitlines()]
    assert report["modes"]["verified"]["training"]["squares"] == 128
    assert len(rows) == 2
    for row in rows:
        assert len(row["cells"]) == 64
        assert row["groupId"] == records[0]["groupId"]
        assert row["split"] == "training"
        assert row["sha256"] == next(r["sha256"] for r in records if r["image"] == row["image"])
        assert squares.sha256(target / row["array"]) == row["arraySha256"]
        with np.load(target / row["array"], allow_pickle=False) as array:
            assert np.array_equal(array["class_ids"], [c["classId"] for c in row["cells"]])
    with np.load(target / rows[0]["array"]) as white, np.load(target / rows[1]["array"]) as black:
        assert np.array_equal(white["images"], black["images"])
        assert np.array_equal(white["class_ids"], black["class_ids"])
    with pytest.raises(ValueError, match="already exists"):
        squares.build_dataset(root, records, MANIFEST, target)


@pytest.mark.parametrize("fault", ["split", "group", "placement", "duplicate", "path"])
def test_bad_source_identity_fails_before_creating_dataset(sources, fault):
    root, records = sources
    if fault == "split":
        records[0]["split"] = "evaluation"
    elif fault == "group":
        records[0]["groupId"] = "sequence-001"
    elif fault == "placement":
        records[0]["piecePlacement"] = "8/8/8/8/8/8/8/8"
    elif fault == "duplicate":
        records.append(deepcopy(records[0]))
    else:
        records[0]["image"] = "../escape.png"
    target = root / "out"
    with pytest.raises(ValueError):
        squares.build_dataset(root, records, MANIFEST, target)
    assert not target.exists()


def test_image_changed_after_audit_discards_entire_build(sources):
    root, records = sources
    (root / records[-1]["image"]).write_bytes(b"changed")
    target = root / "out"
    with pytest.raises(ValueError, match="changed"):
        squares.build_dataset(root, records, MANIFEST, target)
    assert not target.exists()
    assert not list(root.glob(".squares-*"))


def test_detected_failures_are_recorded_without_ground_truth_fallback(sources):
    root, records = sources
    calls = []
    def failing(image):
        calls.append(image.size)
        raise BoardDetectionError("BOARD_NOT_FOUND", "No board")
    target = root / "out"
    report = squares.build_dataset(root, records, MANIFEST, target, ("verified", "detected"), failing)
    assert calls == [(512, 512)] * 2
    stats = report["modes"]["detected"]["training"]
    assert stats["sourceBoards"] == stats["failedBoards"] == 2
    assert stats["writtenBoards"] == stats["squares"] == 0
    rows = [json.loads(line) for line in (target / "detected.jsonl").read_text().splitlines()]
    assert all(r["status"] == "detection-failed" and "array" not in r for r in rows)
    assert report["modes"]["verified"]["training"]["squares"] == 128


def test_wrong_detected_bounds_are_kept_and_measured_not_repaired(sources):
    root, records = sources
    target = root / "out"
    report = squares.build_dataset(root, records[:1], MANIFEST, target, ("detected",),
                                   lambda image: BoardBounds(10, 10, 480, 480))
    row = json.loads((target / "detected.jsonl").read_text())
    assert row["cropBounds"] == {"x": 10, "y": 10, "width": 480, "height": 480}
    assert row["detectionMetrics"]["maxEdgeErrorPixels"] == 22
    assert report["modes"]["detected"]["training"]["withinOnePixelBoards"] == 0
    assert "optionalTrainingClassBackgroundWeights" not in report["balancing"]


def test_weights_depend_only_on_training_and_do_not_resample_other_splits():
    stats = squares.new_statistics()
    for label in LABELS:
        stats["training"]["classes"][label] = {"light": 2, "dark": 4}
    stats["training"]["squares"] = 78
    before = deepcopy(stats)
    weights = squares.training_weights(stats)
    stats["evaluation"]["classes"]["empty"]["light"] = 1000000
    assert squares.training_weights(stats) == weights
    assert weights["K"] == {"light": 1.5, "dark": 0.75}
    assert stats["training"] == before["training"]


def test_known_starting_position_labels_in_both_views():
    placement = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
    expected = [*"rnbqkbnrpppppppp", *(["empty"] * 32), *"PPPPPPPPRNBQKBNR"]
    for view in ("white-bottom", "black-bottom"):
        assert [c["label"] for c in squares.square_labels(placement, view)] == expected


def test_coverage_counts_every_class_on_both_backgrounds_and_tracks_missing():
    stats = squares.new_statistics()
    record = {"configurationId": "fixture", "positionId": "first", "groupId": "group"}
    # Moving the same two rows down one rank reverses their square parity.
    for position, placement in enumerate(("PNBRQKpn/brqk4/8/8/8/8/8/8", "8/PNBRQKpn/brqk4/8/8/8/8/8")):
        record["positionId"] = str(position)
        squares.add_coverage(stats["training"], record, squares.square_labels(placement, "white-bottom"))
    result = squares.finish_statistics(stats)
    train = result["training"]
    assert train["squares"] == 128
    assert train["uniquePositions"] == 2 and train["sourceGroups"] == 1
    assert train["missingClassBackgrounds"] == []
    assert sum(n for counts in train["classes"].values() for n in counts.values()) == 128
    assert all(n > 0 for counts in train["configurations"]["fixture"].values() for n in counts.values())
    assert len(result["validation"]["missingClassBackgrounds"]) == 26


def test_validation_and_evaluation_keep_all_original_squares(sources):
    root, records = sources
    base = records[0]
    all_records = []
    for index, pid in enumerate(("digital-009", "digital-013", "digital-001")):
        item = {**base, **variant_identity(MANIFEST, pid), "image": f"{pid}.png"}
        with painted_board("white-bottom") as image:
            image.putpixel((511, 511), (index, 0, 0))
            image.save(root / item["image"])
        item["sha256"] = squares.sha256(root / item["image"])
        all_records.append(item)
    report = squares.build_dataset(root, all_records, MANIFEST, root / "all-splits")
    assert report["balancing"]["applied"] is False
    for split in ("training", "validation", "evaluation"):
        stats = report["modes"]["verified"][split]
        assert stats["writtenBoards"] == stats["sourceBoards"] == 1
        assert stats["squares"] == 64
    rows = [json.loads(line) for line in (root / "all-splits/verified.jsonl").read_text().splitlines()]
    assert len(rows) == 3 and all(len(row["cells"]) == 64 for row in rows)
    assert len({row["groupId"] for row in rows}) == 3
