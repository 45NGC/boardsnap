"""External games require reviewed labels and retain existing held-out boundaries."""

from copy import deepcopy
import hashlib
import json

from PIL import Image
import pytest

from tools.capture_batch import import_samples, run_batch
from tools.build_real_squares import build_real_squares
from tools.neural_data import read_index
from tools.position_dataset import DEFAULT_MANIFEST
from tools.real_positions import check_detection_reservation

MANIFEST = json.loads(DEFAULT_MANIFEST.read_text())
PLACEMENT = "4k3/8/1p6/8/3N4/8/8/2K5"
pytestmark = pytest.mark.unit


def specification(tmp_path):
    path = tmp_path / "real.png"
    Image.new("RGB", (640, 640), "tan").save(path)
    return {"schemaVersion": 2, "batchId": "external", "samples": [{
        "id": "real-shot-one", "image": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "externalPosition": {"positionId": "real-position-one", "groupId": "real-game-one",
                             "split": "training", "piecePlacement": PLACEMENT},
        "orientation": "black-bottom", "reviewed": True, "reviewedPlacement": PLACEMENT,
        "boardBounds": {"x": 20, "y": 20, "width": 512, "height": 512},
        "configuration": {"platform": "lichess", "boardTheme": "unknown", "pieceSet": "unknown",
                          "layoutId": "real-desktop", "conditions": ["last-move", "selection"]},
        "source": {"url": None, "capturedAt": None, "clientVersion": None, "client": "desktop-web",
                   "sourceGroupId": "real-test-game-one", "reviewedBy": "fixture author",
                   "reviewedAt": "2026-10-13T12:00:00Z", "reviewMethod": "manual-board-comparison",
                   "provenanceNote": "Invented test fixture with explicitly unknown metadata."}}]}


def test_reviewed_external_image_imports_and_builds_64_canonical_labels(tmp_path):
    spec = specification(tmp_path)
    target = run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    record = json.loads((target / "batch.json").read_text())["samples"][0]
    assert record["piecePlacement"] == PLACEMENT and record["source"]["url"] is None
    assert record["split"] == "training" and record["groupId"] == "real-game-one"
    output = tmp_path / "squares"
    build_real_squares(target.parent, MANIFEST, output)
    _, rows = read_index(output)
    assert len(rows) == 1 and len(rows[0]["cells"]) == 64
    assert rows[0]["conditions"] == ["last-move", "selection"]
    assert rows[0]["cells"][4]["label"] == "k"
    assert rows[0]["cells"][4]["imageRow"] == 7


@pytest.mark.parametrize("fault", ["unreviewed", "prediction", "missing-explanation", "wrong-fen", "plan-overlap", "namespace", "both-identities", "old-schema"])
def test_external_import_rejects_unverified_or_ambiguous_identity(tmp_path, fault):
    spec = specification(tmp_path)
    sample = spec["samples"][0]
    if fault == "unreviewed":
        sample["reviewed"] = False
    elif fault == "prediction":
        sample["source"]["reviewMethod"] = "model-prediction"
    elif fault == "missing-explanation":
        del sample["source"]["provenanceNote"]
    elif fault == "wrong-fen":
        sample["reviewedPlacement"] = "8/8/8/8/8/8/8/8"
    elif fault == "plan-overlap":
        sample["externalPosition"]["piecePlacement"] = MANIFEST["positions"][0]["piecePlacement"]
    elif fault == "namespace":
        sample["externalPosition"]["groupId"] = "sequence-001"
    elif fault == "both-identities":
        sample["positionId"] = "digital-009"
    else:
        spec["schemaVersion"] = 1
    with pytest.raises(ValueError):
        run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    assert not (tmp_path / "out" / MANIFEST["datasetId"] / spec["batchId"]).exists()


@pytest.mark.parametrize("fault", ["same-game", "same-position", "equivalent-position"])
def test_external_variants_cannot_cross_partitions_between_batches(tmp_path, fault):
    first = specification(tmp_path)
    run_batch(MANIFEST, first, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    second = deepcopy(first)
    second["batchId"] = "second"
    sample = second["samples"][0]
    Image.new("RGB", (640, 640), "gray").save(tmp_path / "real.png")
    sample["sha256"] = hashlib.sha256((tmp_path / "real.png").read_bytes()).hexdigest()
    sample["externalPosition"].update(split="evaluation", groupId="real-another-game")
    if fault == "same-game":
        sample["externalPosition"].update(positionId="real-next-position", piecePlacement="4k3/8/1p6/8/8/5N2/8/2K5")
        sample["reviewedPlacement"] = sample["externalPosition"]["piecePlacement"]
    else:
        sample["source"]["sourceGroupId"] = "another-test-game"
        if fault == "equivalent-position":
            sample["externalPosition"]["positionId"] = "real-renamed-position"
    with pytest.raises(ValueError, match="partition|identity|positions"):
        run_batch(MANIFEST, second, tmp_path / "out", mode="import-real", spec_dir=tmp_path)


def test_detection_held_out_games_cannot_be_reassigned_to_training(tmp_path):
    spec = specification(tmp_path)
    sample = spec["samples"][0]
    sample["source"]["sourceGroupId"] = "lichess-game-004"
    with pytest.raises(ValueError, match="held-out"):
        import_samples(tmp_path / "stage", MANIFEST, spec, tmp_path)


def test_known_detection_image_cannot_evade_reservation_by_renaming_source(tmp_path):
    references = json.loads((DEFAULT_MANIFEST.parent / "digital-detection-v1.json").read_text())["samples"]
    reference = next(r for r in references if r["split"] == "evaluation")
    sample = specification(tmp_path)["samples"][0]
    sample["sha256"] = reference["sha256"]
    with pytest.raises(ValueError, match="retain"):
        check_detection_reservation(sample, sample["externalPosition"])


def test_pending_review_draft_has_no_guessed_labels_or_changed_held_out_games(tmp_path):
    from tools.prepare_real_reviews import prepare_reviews
    path = tmp_path / "pending.json"
    samples = prepare_reviews(path)
    assert len(samples) == 20
    assert all(s["reviewed"] is False and s["reviewedPlacement"] is None for s in samples)
    assert all(s["externalPosition"]["piecePlacement"] is None and s["orientation"] is None for s in samples)
    for sample in samples:
        game = sample["source"]["sourceGroupId"]
        expected = "evaluation" if game.endswith(("-004", "-005")) else "validation" if game.endswith("-003") else "training"
        assert sample["externalPosition"]["split"] == expected
    with pytest.raises(ValueError):
        import_samples(tmp_path / "stage", MANIFEST, json.loads(path.read_text()), path.parent)
    with pytest.raises(ValueError, match="overwrite"):
        prepare_reviews(path)


def test_real_training_merge_rejects_cross_corpus_equivalent_positions(tmp_path):
    from tools.real_training import check_combined_partitions
    spec = specification(tmp_path)
    rows = import_samples(tmp_path / "stage", MANIFEST, spec, tmp_path)
    check_combined_partitions([], rows)
    conflicting = dict(rows[0], split="evaluation", groupId="different-group", positionId="different-position")
    with pytest.raises(ValueError, match="crosses partitions"):
        check_combined_partitions([conflicting], rows)
    rows[0]["provenanceKind"] = "model-prediction"
    with pytest.raises(ValueError, match="reviewed"):
        check_combined_partitions([], rows)


@pytest.mark.parametrize("condition", ["arrow", "arrows"])
def test_reviewed_arrows_can_train_without_reassigning_reserved_games(tmp_path, condition):
    from tools.real_training import check_combined_partitions
    spec = specification(tmp_path)
    sample = spec["samples"][0]
    sample["configuration"]["conditions"] = ["last-move", condition]
    target = run_batch(MANIFEST, spec, tmp_path / "out", mode="import-real", spec_dir=tmp_path)
    build_real_squares(target.parent, MANIFEST, tmp_path / "squares")
    _, rows = read_index(tmp_path / "squares")
    check_combined_partitions([], rows)
    assert rows[0]["split"] == "training"
    assert rows[0]["conditions"] == ["last-move", condition]
    sample["source"]["sourceGroupId"] = "lichess-game-005"
    with pytest.raises(ValueError, match="held-out"):
        import_samples(tmp_path / "reserved", MANIFEST, spec, tmp_path)
    rows[0]["conditions"].append("badges")
    with pytest.raises(ValueError, match="Badges"):
        check_combined_partitions([], rows)


def test_real_merge_never_opens_evaluation_arrays(tmp_path, monkeypatch):
    import numpy as np
    from tools import real_training
    rows = import_samples(tmp_path / "stage", MANIFEST, specification(tmp_path), tmp_path)
    rows.append(dict(rows[0], **{"groupId": "real-heldout", "positionId": "real-heldout-one", "split": "evaluation",
                                "piecePlacement": "4k3/8/1p6/8/8/5N2/8/2K5",
                                "source": dict(rows[0]["source"], sourceGroupId="real-heldout-game")}))
    monkeypatch.setattr(real_training, "read_index", lambda root: ({"indexes": {"verified": {"sha256": "test"}}}, rows))
    monkeypatch.setattr(real_training, "digest", lambda path: "test")
    calls = []
    def load(root, entries, split):
        calls.append(split)
        assert split == "training"
        return np.zeros((64, 1), dtype=np.uint8), np.ones(64, dtype=np.int64)
    monkeypatch.setattr(real_training, "load_split", load)
    base = np.zeros((64, 1), dtype=np.uint8), np.zeros(64, dtype=np.int64)
    train, validation, provenance = real_training.add_real_training(tmp_path, [], base, base)
    assert len(train[1]) == 128 and len(validation[1]) == 64
    assert calls == ["training"] and provenance["evaluationArraysLoaded"] is False
