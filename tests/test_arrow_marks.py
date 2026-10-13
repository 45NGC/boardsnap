"""Arrow geometry, occupancy labels, combined overlays and partition regressions."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from boardsnap.detection import BoardBounds, BoardDetectionError, detect_board
from tools.arrow_marks import (CASES, affected_indices, arrow_plan, arrows_overlap,
                               draw_arrow, geometry, validate_arrow, validate_coverage)
from tools.board_marks import mark_conditions, render_marks, validate_marks
from tools.build_arrow_dataset import build_captures, summary
from tools.build_square_dataset import build_dataset, extract_squares
from tools.evaluate_marks import summarize
from tools.neural_data import digest, read_index, training_indices
from tools.position_dataset import DEFAULT_MANIFEST, variant_identity

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
BOUNDS = {"x": 16, "y": 24, "width": 512, "height": 512}
MANIFEST = json.loads(DEFAULT_MANIFEST.read_text())
pytestmark = pytest.mark.unit


def arrow(start="b4", end="g4", **extra):
    return {"kind": "arrow", "from": start, "to": end, "path": "straight",
            "width": .14, "rgba": [240, 145, 25, 144], **extra}


@pytest.mark.parametrize("mark,expected", [
    (arrow(), "horizontal"), (arrow("c2", "c7"), "vertical"),
    (arrow("a1", "h8"), "diagonal"),
    (arrow("d4", "f5", path="knight", bend="horizontal-first"), "knight"),
    (arrow("f5", "d4", path="knight", bend="vertical-first"), "knight")])
@pytest.mark.parametrize("view", ["white-bottom", "black-bottom"])
def test_arrow_path_head_and_intermediate_cells_are_kept_after_cropping(mark, expected, view):
    validate_arrow(mark)
    assert geometry(mark) == expected
    with Image.new("RGB", (560, 560), (100, 130, 160)) as source:
        original = np.asarray(source).copy()
        with render_marks(source, BOUNDS, view, [mark], START) as marked:
            pixels = np.asarray(marked)
            assert np.array_equal(original[:24], pixels[:24])
            assert np.array_equal(original[536:], pixels[536:])
            assert np.array_equal(original[:, :16], pixels[:, :16])
            assert np.array_equal(original[:, 528:], pixels[:, 528:])
            cells = extract_squares(marked, BoardBounds(**BOUNDS), view)
            changed = set(np.flatnonzero(np.any(cells != [100, 130, 160], axis=(1, 2, 3))))
            assert changed and changed <= set(affected_indices(mark))
            assert changed <= set(training_indices({"marks": [mark]}))
            assert len(changed) > 2  # endpoints alone cannot identify the training cells.
        assert np.array_equal(np.asarray(source), original)


def test_knight_bends_are_distinct_continuous_l_paths():
    a = arrow("c3", "e4", path="knight", bend="horizontal-first")
    b = dict(a, bend="vertical-first")
    with Image.new("RGBA", (512, 512)) as first, Image.new("RGBA", (512, 512)) as second:
        bounds = {"x": 0, "y": 0, "width": 512, "height": 512}
        draw_arrow(first, a, bounds, "white-bottom")
        draw_arrow(second, b, bounds, "white-bottom")
        assert not np.array_equal(first, second)
        # Each bend is actually inked at its cell centre; it is not a diagonal shortcut.
        assert first.getpixel((288, 352))[3] > 0
        assert second.getpixel((160, 288))[3] > 0
        assert first.getpixel((160, 288))[3] == 0


@pytest.mark.parametrize("change", [
    {"from": "a9"}, {"to": "b4"}, {"to": "c7"}, {"path": "curve"},
    {"path": "knight"}, {"bend": "horizontal-first"}, {"width": 0},
    {"width": float("nan")}, {"width": True}, {"rgba": [1, 2, 3, 0]},
    {"rgba": [1, 2, True, 50]}, {"extra": True}])
def test_invalid_arrow_never_enters_capture(change):
    with pytest.raises(ValueError):
        validate_marks([arrow(**change)], START)


@pytest.mark.parametrize("case", CASES)
def test_scenarios_are_reproducible_and_coverage_labels_match_pixels(case):
    marks, details = arrow_plan(START, case, f"test:{case}")
    assert marks is not None
    assert (marks, details) == arrow_plan(START, case, f"test:{case}")
    validate_marks(marks, START)
    validate_coverage(START, marks, details)
    if case == "arrow-empty":
        assert details["occupiedCoveredIndices"] == []
    elif case == "arrow-piece":
        assert details["occupiedCoveredIndices"]
    elif case == "arrow-crossed":
        assert arrows_overlap(*marks)
        assert mark_conditions(marks) == ["arrow"]
    else:
        assert mark_conditions(marks) == ["last-move", "circle", "arrow"]
    tampered = deepcopy(details)
    tampered["arrowCoveredIndices"] = []
    with pytest.raises(ValueError, match="disagree"):
        validate_coverage(START, marks, tampered)


def test_empty_endpoints_do_not_hide_pieces_under_a_shaft():
    placement = "8/8/8/8/3K4/8/8/8"
    mark = arrow("a4", "h4")
    # d4 is between empty endpoints and must count as covered/occupied.
    assert 35 in affected_indices(mark)
    covered = list(affected_indices(mark))
    details = {"case": "arrow-empty", "geometries": ["horizontal"], "arrowCoveredIndices": covered,
               "occupiedCoveredIndices": [35], "emptyCoveredIndices": [i for i in covered if i != 35]}
    with pytest.raises(ValueError, match="occupancy"):
        validate_coverage(placement, [mark], details)


def test_unavailable_empty_route_is_reported_not_mislabeled():
    full = "/".join(["PPPPPPPP"]*8)
    marks, reason = arrow_plan(full, "arrow-empty", "full-board")
    assert marks is None and "No route" in reason["reason"]


def test_crossing_alpha_layers_composite_and_are_not_erased():
    a, b = arrow("a4", "h4"), arrow("d1", "d8", rgba=[30, 160, 65, 144])
    assert arrows_overlap(a, b)
    with Image.new("RGB", (560, 560), "white") as source:
        with render_marks(source, BOUNDS, "white-bottom", [a], START) as one:
            with render_marks(source, BOUNDS, "white-bottom", [a, b], START) as two:
                assert one.getpixel((16+224, 24+288)) != two.getpixel((16+224, 24+288))
    assert mark_conditions([a, b]) == ["arrow"]


def test_direction_color_width_and_alpha_vary_without_changing_labels():
    plans = [arrow_plan(START, "arrow-piece", f"coverage-{i}")[0][0] for i in range(100)]
    assert {geometry(m) for m in plans} == {"horizontal", "vertical", "diagonal", "knight"}
    assert len({tuple(m["rgba"][:3]) for m in plans}) == 4
    assert len({m["rgba"][3] for m in plans}) == 3
    assert len({m["width"] for m in plans}) == 3


def test_exclusive_case_scores_do_not_mix_combined_with_simple_controls():
    base = {"pairId": "p", "positionId": "p", "image": "base.png", "conditions": ["clean"],
            "expected": [0]*64, "predictions": [0]*64, "overlayCase": "clean"}
    marked = dict(base, image="arrow.png", conditions=["last-move", "circle", "arrow"], overlayCase="arrow-combined",
                  arrowGeometries=["horizontal"], predictions=[1]*64)
    result = summarize([base, marked])
    assert result["cases"]["clean"]["exactBoards"] == 1
    assert result["cases"]["arrow-combined"]["exactBoards"] == 0
    assert result["pairedCases"]["arrow-combined"]["cleanOnlyCorrect"] == 1
    assert result["geometries"]["horizontal"]["images"] == 1


def test_build_preserves_controls_partitions_hashes_and_64_labels(tmp_path):
    records = []
    for n, pid in enumerate(("digital-009", "digital-013", "digital-001")):
        path = tmp_path / f"{pid}.png"
        with Image.new("RGB", (560, 560), (80+n, 120, 160)) as image:
            image.save(path)
        record = dict(variant_identity(MANIFEST, pid), image=path.name, sha256=digest(path),
                      boardBounds=BOUNDS, imageSize={"width": 560, "height": 560}, conditions=["clean"],
                      configurationId="fixture-standard", baseConfigurationId="fixture-standard",
                      pairId=pid, orientation="white-bottom")
        records.append(record)
    build_dataset(tmp_path, records, MANIFEST, tmp_path / "parent")
    captured = build_captures(tmp_path / "parent", tmp_path / "captures")
    assert captured["controlBoards"] == 3 and captured["arrowBoards"] == 12
    assert not captured["skippedUnavailableRoutes"]
    build_dataset(tmp_path / "captures", captured["images"], MANIFEST, tmp_path / "arrows",
                  provenance={"sourceCaptureReportSha256": digest(tmp_path / "captures/captures.json")})
    _, rows = read_index(tmp_path / "arrows")
    for row in rows:
        identity = variant_identity(MANIFEST, row["positionId"])
        assert all(row[k] == v for k, v in identity.items())
        assert len(row["cells"]) == 64
    report = summary(tmp_path / "captures", tmp_path / "arrows")
    assert all(s["positions"] == s["groups"] == 1 for s in report["splits"].values())
    for row in records:
        control = next(r for r in captured["images"] if r["positionId"] == row["positionId"] and r["conditions"] == ["clean"])
        assert control["sha256"] == row["sha256"]
    # Case tampering must be rejected even if the index hash is regenerated.
    row = next(r for r in rows if r["overlayCase"] == "arrow-piece")
    row["overlayCase"] = "arrow-empty"
    index = tmp_path / "arrows/verified.jsonl"
    index.write_text("".join(json.dumps(r)+"\n" for r in rows))
    metadata_path = tmp_path / "arrows/dataset.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["indexes"]["verified"]["sha256"] = digest(index)
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="scenario differs"):
        read_index(tmp_path / "arrows")


@pytest.mark.parametrize("view", ["white", "black"])
@pytest.mark.parametrize("case", CASES)
@pytest.mark.integration
def test_detector_keeps_actual_capture_bounds_with_new_overlays(view, case):
    root = Path(__file__).resolve().parents[1] / "data/tuning/lichess-cburnett-brown-v1"
    annotation = json.loads((root / f"pos-001-{view}.json").read_text())
    marks, _ = arrow_plan(annotation["piecePlacement"], case, f"detection:{case}")
    assert marks is not None
    with Image.open(root / annotation["image"]) as source, source.convert("RGB") as rgb:
        expected = detect_board(rgb)
        with render_marks(rgb, annotation["boardBounds"], annotation["orientation"], marks, annotation["piecePlacement"]) as marked:
            assert detect_board(marked) == expected


def test_control_validation_takes_priority_over_aggregate_arrow_improvement():
    pytest.importorskip("torch")
    from tools.train_neural import selection_key
    protected = {"controlExactBoards": 10, "exactBoards": 15, "macroRecall": .95, "loss": .1}
    regressed = {"controlExactBoards": 9, "exactBoards": 19, "macroRecall": .99, "loss": .01}
    assert selection_key(protected) > selection_key(regressed)


def test_arrows_on_a_plain_square_do_not_create_a_detectable_chessboard():
    marks, _ = arrow_plan(START, "arrow-crossed", "no-board")
    with Image.new("RGB", (560, 560), (240, 217, 181)) as source:
        with render_marks(source, BOUNDS, "white-bottom", marks, START) as marked:
            with pytest.raises(BoardDetectionError):
                detect_board(marked)


def test_capture_recipe_accepts_combined_and_repeated_arrows():
    from tools.capture_batch import validate_recipe
    recipe = json.loads((Path(__file__).resolve().parents[1] / "tools/capture-arrows.example.json").read_text())
    validate_recipe(recipe, MANIFEST)
    recipe["configurations"][0]["conditions"].append("arrow")
    with pytest.raises(ValueError, match="Conditions"):
        validate_recipe(recipe, MANIFEST)


def test_resume_preserves_control_selection_and_rejects_a_changed_control_mask(tmp_path):
    torch = pytest.importorskip("torch")
    from tools.train_neural import fit
    config = {"seed": 14, "epochs": 2, "batchSize": 64, "learningRate": .002, "weightDecay": .0001, "threads": 1}
    labels = np.arange(128, dtype=np.int64) % 13
    images = np.zeros((128, 64, 64, 3), np.uint8)
    images[:] = (labels*19).astype(np.uint8)[:, None, None, None]
    data = images, labels
    controls = np.array([True, False])
    full = fit(data, data, config, tmp_path / "full", {"fixture": "arrows"}, control_boards=controls)
    fit(data, data, config, tmp_path / "resume", {"fixture": "arrows"}, control_boards=controls, stop_after=1)
    with pytest.raises(ValueError, match="changed"):
        fit(data, data, config, tmp_path / "resume", {"fixture": "arrows"}, control_boards=~controls, resume=True)
    resumed = fit(data, data, config, tmp_path / "resume", {"fixture": "arrows"}, control_boards=controls, resume=True)
    assert full["selected"] == resumed["selected"]
    assert full["selected"]["metrics"]["controlBoards"] == 1
    a = torch.load(tmp_path / "full/best.pt", weights_only=True)["state_dict"]
    b = torch.load(tmp_path / "resume/best.pt", weights_only=True)["state_dict"]
    assert all(torch.equal(value, b[key]) for key, value in a.items())
