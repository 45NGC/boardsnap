"""Collection planning and strict checkpoint integrity, without remote sites."""

from collections import Counter
from copy import deepcopy
from io import BytesIO
import json

from PIL import Image
import pytest

from tools import collect_clean_corpus as corpus
from tools.capture_batch import plan_hash, record_capture, run_batch
from tools.capture_lichess import expand_placement
from tools.position_dataset import variant_identity


MANIFEST = json.loads(corpus.DEFAULT_MANIFEST.read_text())
RECIPE = json.loads(corpus.DEFAULT_RECIPE.read_text())
pytestmark = pytest.mark.unit


def test_full_collection_keeps_every_position_and_source_group_in_its_partition():
    jobs = corpus.build_jobs(MANIFEST, RECIPE)
    assert len(jobs) == 720
    assert len({j["batchId"] for j in jobs}) == len(jobs)
    counts, compact, standard, identities = Counter(), {}, {}, set()
    for job in jobs:
        config = job["configurations"][0]
        groups = {variant_identity(MANIFEST, pid)["groupId"] for pid in job["positionIds"]}
        assert len(groups) == 1
        assert set(config["orientations"]) == {"white-bottom", "black-bottom"}
        collection = compact if config["id"].endswith("-compact") else standard
        collection.setdefault(config["id"], []).extend(job["positionIds"])
        assert len(job["positionIds"]) == (1 if collection is compact else 4)
        for pid in job["positionIds"]:
            identity = variant_identity(MANIFEST, pid)
            counts[identity["split"]] += 2
            for view in config["orientations"]:
                key = (pid, config["id"], view)
                assert key not in identities
                identities.add(key)
    assert counts == {"training": 2520, "validation": 540, "evaluation": 540}
    assert len(standard) == len(compact) == 18
    assert all(set(pids) == set(RECIPE["positionIds"]) for pids in standard.values())
    assert len({tuple(pids) for pids in compact.values()}) == 1
    assert all(len(pids) == 20 for pids in compact.values())
    assert jobs == corpus.build_jobs(MANIFEST, RECIPE)


def test_partial_base_recipe_is_rejected():
    recipe = deepcopy(RECIPE)
    recipe["positionIds"].pop()
    with pytest.raises(ValueError, match="complete frozen"):
        corpus.build_jobs(MANIFEST, recipe)


@pytest.fixture
def checkpoint(tmp_path):
    # Synthetic bytes are only an integrity fixture, never classification data.
    config = deepcopy(RECIPE["configurations"][0])
    recipe = {"schemaVersion": 1, "batchId": "unit-fixture", "positionIds": ["digital-009"],
              "configurations": [config]}
    target = tmp_path / MANIFEST["datasetId"] / recipe["batchId"]
    annotations = []
    for index, view in enumerate(config["orientations"]):
        stream = BytesIO()
        Image.new("RGB", tuple(config["viewport"].values()), (index, 0, 0)).save(stream, format="PNG")
        identity = variant_identity(MANIFEST, "digital-009")
        rows = expand_placement(identity["piecePlacement"])
        if view == "black-bottom":
            rows = [row[::-1] for row in rows[::-1]]
        bounds = {"x": 64, "y": 80, "width": 512, "height": 512}
        observed = {"boardBounds": bounds, "source": {"cssBoardBounds": bounds,
                    "renderedRows": rows, "renderedOrientation": view}}
        annotations.append(record_capture(target, MANIFEST, "digital-009", config, view,
                                          stream.getvalue(), observed, "unit fixture"))
    batch = {"positionPlanSha256": plan_hash(MANIFEST), "recipe": recipe, "samples": annotations}
    (target / "batch.json").write_text(json.dumps(batch))
    return target, recipe, batch


def test_complete_checkpoint_and_final_report_reconcile_pngs_and_labels(checkpoint):
    target, recipe, _ = checkpoint
    records = corpus.audit_batch(target, MANIFEST, recipe)
    assert len(records) == 2
    report = corpus.audit_corpus(MANIFEST, recipe, [recipe], target.parent.parent)
    assert report["complete"] is True
    assert report["imageCount"] == 2
    assert report["splitCounts"] == {"training": 2}
    assert report["classificationEvaluated"] is False


@pytest.mark.parametrize("fault", ["png", "sidecar", "missing", "extra", "duplicate", "position",
                                       "partition", "orientation", "bounds", "rendered", "plan", "recipe"])
def test_corrupt_or_mislabeled_checkpoint_is_never_accepted(checkpoint, fault):
    target, recipe, batch = checkpoint
    ann = batch["samples"][0]
    png = target / ann["split"] / ann["configuration"]["id"] / ann["image"]
    sidecar = png.with_suffix(".json")
    if fault == "png":
        png.write_bytes(png.read_bytes() + b"changed")
    elif fault == "sidecar":
        sidecar.write_text("{}")
    elif fault == "missing":
        png.unlink()
    elif fault == "extra":
        (target / "unlisted.png").write_bytes(png.read_bytes())
    elif fault == "duplicate":
        batch["samples"].append(deepcopy(ann))
    elif fault == "plan":
        batch["positionPlanSha256"] = "changed"
    elif fault == "recipe":
        batch["recipe"] = dict(recipe, batchId="different")
    else:
        if fault == "position":
            ann["piecePlacement"] = "8/8/8/8/8/8/8/8"
        elif fault == "partition":
            ann["split"] = "evaluation"
        elif fault == "orientation":
            ann["source"]["renderedOrientation"] = "black-bottom"
        elif fault == "bounds":
            ann["source"]["cssBoardBounds"] = dict(ann["boardBounds"], x=60)
        elif fault == "rendered":
            ann["source"]["renderedRows"] = ["........"] * 8
        sidecar.write_text(json.dumps(ann))
    (target / "batch.json").write_text(json.dumps(batch))
    with pytest.raises((ValueError, FileNotFoundError)):
        corpus.audit_batch(target, MANIFEST, recipe)


def test_partial_collection_cannot_produce_complete_report(checkpoint):
    target, recipe, _ = checkpoint
    missing = dict(recipe, batchId="missing-batch")
    with pytest.raises(ValueError, match="missing or unexpected batches"):
        corpus.audit_corpus(MANIFEST, RECIPE, [recipe, missing], target.parent.parent)


def test_session_failure_discards_entire_source_group(tmp_path):
    job = corpus.build_jobs(MANIFEST, RECIPE)[0]
    def failure(staging, *args):
        (staging / "partial.png").write_bytes(b"partial")
        raise ValueError("Rendered position differs")
    with pytest.raises(ValueError, match="Rendered position"):
        run_batch(MANIFEST, job, tmp_path, capture_fn=failure)
    assert list((tmp_path / MANIFEST["datasetId"]).iterdir()) == []


def test_final_audit_failure_prevents_batch_publication(tmp_path):
    job = corpus.build_jobs(MANIFEST, RECIPE)[0]
    def missing_captures(staging, *args):
        return []
    with pytest.raises(ValueError, match="missing or unexpected images"):
        run_batch(MANIFEST, job, tmp_path, capture_fn=missing_captures,
                  audit_fn=corpus.audit_batch)
    assert list((tmp_path / MANIFEST["datasetId"]).iterdir()) == []
