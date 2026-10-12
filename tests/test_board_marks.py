"""Controlled marks preserve labels, cell orientation, borders and data identity."""

from io import BytesIO
import json

import numpy as np
from PIL import Image
import pytest

from boardsnap.detection import BoardBounds
from tools.board_marks import KINDS, COLORS, mark_plan, mark_png, render_marks, validate_marks
from tools.build_marked_dataset import build_marked_captures, select_sources
from tools.build_square_dataset import build_dataset, extract_squares, square_labels
from tools.capture_batch import validate_config
from tools.evaluate_marks import paired_results
from tools.neural_data import digest, load_split, read_index, training_indices
from tools.position_dataset import DEFAULT_MANIFEST, variant_identity

MANIFEST = json.loads(DEFAULT_MANIFEST.read_text())
PLACEMENT = "RNBQKPpn/brqk4/8/8/8/8/8/7P"
BOUNDS = {"x": 16, "y": 24, "width": 512, "height": 512}
pytestmark = pytest.mark.unit


@pytest.mark.parametrize("kind", KINDS)
def test_plan_reproducible_and_no_false_check_labels(kind):
    marks = mark_plan(PLACEMENT, kind, "fixed-key")
    assert marks == mark_plan(PLACEMENT, kind, "fixed-key")
    validate_marks(marks, PLACEMENT)
    assert marks[0]["kind"] == kind
    if kind == "check":
        assert set(marks[0]["squares"]) <= {"e8", "d7"}


@pytest.mark.parametrize("kind", KINDS)
def test_same_canonical_mark_pixels_from_both_views_without_rotating_glyphs(kind):
    marks = mark_plan(PLACEMENT, kind, "paired")
    source = Image.new("RGB", (560, 560), (100, 130, 160))
    before = np.asarray(source).copy()
    canonical = []
    for view in ("white-bottom", "black-bottom"):
        with render_marks(source, BOUNDS, view, marks, PLACEMENT) as marked:
            pixels = np.asarray(marked)
            assert np.array_equal(pixels[:24], before[:24])
            assert np.array_equal(pixels[:, :16], before[:, :16])
            assert np.array_equal(pixels[536:], before[536:])
            assert np.array_equal(pixels[:, 528:], before[:, 528:])
            canonical.append(extract_squares(marked, BoardBounds(**BOUNDS), view))
    assert np.array_equal(before, np.asarray(source))
    assert np.array_equal(*canonical)
    changed = {i for i in range(64) if not np.all(canonical[0][i] == before[100, 100])}
    expected = {i for i, c in enumerate(square_labels(PLACEMENT, "white-bottom")) if c["square"] in marks[0]["squares"]}
    assert changed == expected


@pytest.mark.parametrize("bad", [[], [{"kind": "arrows", "squares": ["a1"], "rgba": [1, 2, 3, 4]}],
    [{"kind": "selection", "squares": ["z9"], "rgba": [1, 2, 3, 4]}],
    [{"kind": "selection", "squares": ["a1", "a1"], "rgba": [1, 2, 3, 4]}],
    [{"kind": "last-move", "squares": ["a1"], "rgba": [1, 2, 3, 4]}],
    [{"kind": "selection", "squares": ["a1"], "rgba": [1, 2, 3, 0]}],
    [{"kind": "selection", "squares": ["a1"], "rgba": [True, 2, 3, 40]}],
    [{"kind": "check", "squares": ["a1"], "rgba": [1, 2, 3, 40]}]])
def test_invalid_or_invisible_marks_rejected(bad):
    with pytest.raises(ValueError):
        validate_marks(bad, PLACEMENT)


def test_png_evidence_describes_saved_pixels_and_original_hash():
    source = BytesIO()
    Image.new("RGB", (560, 560), "white").save(source, format="PNG")
    marks = mark_plan(PLACEMENT, "last-move", "test")
    png, evidence = mark_png(source.getvalue(), BOUNDS, "white-bottom", marks, PLACEMENT)
    assert png != source.getvalue()
    assert evidence["marks"] == marks and "not native" in evidence["method"]
    import hashlib
    assert evidence["baseImageSha256"] == hashlib.sha256(source.getvalue()).hexdigest()
    with Image.open(BytesIO(png)) as decoded:
        assert decoded.size == (560, 560)


def test_condition_configuration_cannot_lie_about_marks():
    config = {"id": "test", "platform": "lichess", "boardTheme": "brown", "pieceSet": "cburnett",
              "orientations": ["white-bottom"], "viewport": {"width": 900, "height": 900},
              "deviceScaleFactor": 1, "conditions": ["selection"],
              "marks": [{"kind": "selection", "squares": ["a1"], "rgba": COLORS["selection"]}]}
    validate_config(config)
    config["conditions"] = ["clean"]
    with pytest.raises(ValueError, match="Conditions"):
        validate_config(config)


def test_training_subsampling_is_canonical_and_never_changes_validation(tmp_path):
    row = {"marks": [{"kind": "selection", "squares": ["a8"], "rgba": COLORS["selection"]}]}
    assert training_indices(row) == [0, 1, 8, 9]
    row["marks"][0]["kind"] = "circle"
    assert training_indices(row) == [0]
    assert training_indices({}) == list(range(64))
    with pytest.raises(ValueError, match="only in training"):
        load_split(tmp_path, [], "validation", marked_cells_only=True)


def test_pair_metrics_distinguish_consistency_from_correctness():
    base = {"pairId": "first", "expected": [0]*64, "predictions": [1]*64, "conditions": ["clean"]}
    marked = dict(base, conditions=["selection"])
    result = paired_results([base, marked])["selection"]
    assert result["identicalPredictions"] == result["neitherCorrect"] == 1
    assert result["bothCorrect"] == 0
    with pytest.raises(ValueError, match="no paired"):
        paired_results([marked])
    with pytest.raises(ValueError, match="labels disagree"):
        paired_results([base, dict(marked, expected=[2]*64)])


def test_actual_corpus_round_trip_and_original_partition_inheritance(tmp_path):
    records = []
    for n, pid in enumerate(("digital-009", "digital-013", "digital-001")):
        identity = variant_identity(MANIFEST, pid)
        source = tmp_path / f"{pid}.png"
        with Image.new("RGB", (560, 560), (80+n, 120, 160)) as image:
            image.save(source)
        records.append(dict(identity, image=source.name, sha256=digest(source), boardBounds=BOUNDS,
                            orientation="white-bottom", configurationId="test-standard",
                            imageSize={"width": 560, "height": 560}))
    build_dataset(tmp_path, records, MANIFEST, tmp_path / "clean")
    report = build_marked_captures(tmp_path / "clean", tmp_path / "captures")
    assert report["cleanBoards"] == 3 and report["markedBoards"] == 15
    assert report["realUseClassificationIncluded"] is False
    build_dataset(tmp_path / "captures", report["images"], MANIFEST, tmp_path / "marked")
    _, rows = read_index(tmp_path / "marked")
    for row in rows:
        identity = variant_identity(MANIFEST, row["positionId"])
        assert all(row[k] == v for k, v in identity.items())
        assert len(row["cells"]) == 64
    for split in ("validation", "evaluation"):
        images, labels = load_split(tmp_path / "marked", rows, split)
        assert len(labels) == len(images) == 6*64
        assert all(np.array_equal(labels[:64], labels[i*64:(i+1)*64]) for i in range(6))
    images, labels = load_split(tmp_path / "marked", rows, "training", marked_cells_only=True)
    assert 64 < len(labels) < 6*64
    assert len(images) == len(labels)
    _, clean_rows = read_index(tmp_path / "clean")
    assert select_sources(clean_rows) == select_sources(list(reversed(clean_rows)))
    # Fail closed on changed pixels and leave no partially published corpus.
    (tmp_path / records[0]["image"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="source changed"):
        build_marked_captures(tmp_path / "clean", tmp_path / "failed")
    assert not (tmp_path / "failed").exists()
