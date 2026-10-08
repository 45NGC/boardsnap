"""Capture configuration, partition integrity, publication and real-use imports."""

from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from tools import capture_batch as capture
from tools.position_dataset import DEFAULT_MANIFEST, variant_identity

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(DEFAULT_MANIFEST.read_text())
RECIPE = json.loads((ROOT / "tools/capture-clean.example.json").read_text())
pytestmark = pytest.mark.unit


def png_bytes():
    stream = BytesIO()
    Image.new("RGB", (640, 640), "white").save(stream, format="PNG")
    return stream.getvalue()


def real_spec(tmp_path, pid="digital-009"):
    png = png_bytes()
    (tmp_path / "original.png").write_bytes(png)
    return {"schemaVersion": 1, "batchId": "real-test", "samples": [{
        "id": "reviewed-image", "positionId": pid, "image": "original.png",
        "sha256": hashlib.sha256(png).hexdigest(), "orientation": "white-bottom",
        "reviewed": True, "reviewedPlacement": variant_identity(MANIFEST, pid)["piecePlacement"],
        "boardBounds": {"x": 32, "y": 32, "width": 512, "height": 512},
        "configuration": {"platform": "lichess", "boardTheme": "green", "pieceSet": "merida",
                          "layoutId": "LC03", "conditions": ["clean"]},
        "source": {"url": "https://lichess.org/test-source", "capturedAt": "2026-10-08T00:00:00Z",
                   "client": "desktop-web", "clientVersion": "test", "sourceGroupId": "test-game",
                   "reviewedBy": "test fixture author", "reviewedAt": "2026-10-08T00:00:00Z"},
    }]}


def test_clean_recipe_is_separate_from_runtime_profiles_and_inherits_splits():
    capture.validate_recipe(RECIPE, MANIFEST)
    assert len(RECIPE["configurations"]) == 4
    assert all(variant_identity(MANIFEST, pid)["split"] == "training" for pid in RECIPE["positionIds"])


@pytest.mark.parametrize("field,value", [
    ("id", "../escape"), ("platform", "unknown"), ("boardTheme", 'green"'),
    ("pieceSet", ""), ("orientations", ["auto"]), ("orientations", ["white-bottom", "white-bottom"]),
    ("viewport", {"width": 0, "height": 900}), ("viewport", {"width": True, "height": 900}),
    ("deviceScaleFactor", True), ("deviceScaleFactor", 4), ("conditions", ["arrows"]),
])
def test_bad_configuration_rejected(field, value):
    recipe = deepcopy(RECIPE)
    recipe["configurations"][0][field] = value
    with pytest.raises(ValueError):
        capture.validate_recipe(recipe, MANIFEST)


@pytest.mark.parametrize("field,value", [("positionIds", ["unknown"]), ("positionIds", []),
                                       ("positionIds", ["digital-009", "digital-009"]),
                                       ("batchId", "../escape"), ("schemaVersion", 5)])
def test_bad_recipe_rejected(field, value):
    recipe = deepcopy(RECIPE)
    recipe[field] = value
    with pytest.raises(ValueError):
        capture.validate_recipe(recipe, MANIFEST)


@pytest.mark.parametrize("bounds", [
    {"x": -1, "y": 0, "width": 512, "height": 512},
    {"x": 200, "y": 0, "width": 512, "height": 512},
    {"x": 0, "y": 0, "width": 512, "height": 256},
    {"x": float("nan"), "y": 0, "width": 512, "height": 512},
    {"x": 0, "y": 0, "width": 64, "height": 64},
])
def test_image_geometry_is_checked_in_saved_pixels(bounds):
    with pytest.raises(ValueError):
        capture.check_png(png_bytes(), bounds)


def test_validate_only_does_not_launch_browser_or_create_output(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "capture_samples", lambda *a: pytest.fail("Browser started"))
    assert capture.main(["capture", str(ROOT / "tools/capture-clean.example.json"),
                         "--output-root", str(tmp_path / "out"), "--validate-only"]) == 0
    assert not (tmp_path / "out").exists()


def test_failed_batch_publishes_nothing_and_removes_lock(tmp_path, monkeypatch):
    def fail(staging, *args):
        (staging / "partial.png").write_bytes(png_bytes())
        raise ValueError("changed pieces")
    monkeypatch.setattr(capture, "capture_samples", fail)
    with pytest.raises(ValueError, match="changed pieces"):
        capture.run_batch(MANIFEST, RECIPE, tmp_path)
    assert list((tmp_path / MANIFEST["datasetId"]).iterdir()) == []


def test_real_import_preserves_bytes_hash_and_inherited_identity(tmp_path):
    spec = real_spec(tmp_path)
    target = capture.run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    record = json.loads((target / "batch.json").read_text())["samples"][0]
    assert (target / "training/real-use/reviewed-image.png").read_bytes() == (tmp_path / "original.png").read_bytes()
    assert record["provenanceKind"] == "reviewed-real-use"
    assert record["verification"] == "human-reviewed; no DOM evidence"
    assert record["imageSize"] == {"width": 640, "height": 640}
    for key, value in variant_identity(MANIFEST, "digital-009").items():
        assert record[key] == value
    with pytest.raises(ValueError, match="exists"):
        capture.run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)


@pytest.mark.parametrize("field,value", [("reviewed", False), ("reviewedPlacement", "8/8/8/8/8/8/8/8"),
                                       ("sha256", "wrong"), ("orientation", "auto")])
def test_unreviewed_or_changed_import_fails(tmp_path, field, value):
    spec = real_spec(tmp_path)
    spec["samples"][0][field] = value
    with pytest.raises(ValueError):
        capture.run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    assert not (tmp_path / "out" / MANIFEST["datasetId"] / spec["batchId"]).exists()


def test_real_game_cannot_cross_splits_between_batches(tmp_path):
    spec = real_spec(tmp_path)
    capture.run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    evaluation_pid = next(p["positionId"] for p in MANIFEST["positions"]
                          if variant_identity(MANIFEST, p["positionId"])["split"] == "evaluation")
    new = real_spec(tmp_path, evaluation_pid)
    new["batchId"] = "another-batch"
    # Different bytes ensure the source-group guard, rather than hash guard, catches it.
    Image.new("RGB", (640, 640), "gray").save(tmp_path / "original.png")
    new["samples"][0]["sha256"] = hashlib.sha256((tmp_path / "original.png").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="source already exists"):
        capture.run_batch(MANIFEST, new, tmp_path / "out", mode="import-real", spec_dir=tmp_path)


def test_real_validation_only_creates_no_dataset(tmp_path):
    spec = real_spec(tmp_path)
    path = tmp_path / "review.json"
    path.write_text(json.dumps(spec))
    assert capture.main(["import-real", str(path), "--output-root", str(tmp_path / "out"), "--validate-only"]) == 0
    assert not (tmp_path / "out").exists()


def test_existing_dataset_cannot_silently_change_its_frozen_plan(tmp_path):
    spec = real_spec(tmp_path)
    capture.run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    changed = deepcopy(MANIFEST)
    changed["description"] = "A different plan revision"
    spec["batchId"] = "another-batch"
    with pytest.raises(ValueError, match="Position plan changed"):
        capture.run_batch(changed, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)


def test_import_schema_version_cannot_be_boolean(tmp_path):
    spec = real_spec(tmp_path)
    spec["schemaVersion"] = True
    with pytest.raises(ValueError, match="specification"):
        capture.import_samples(tmp_path / "stage", MANIFEST, spec, tmp_path)
