"""Optional neural contract, serialization, and deterministic resume regression tests."""

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
from boardsnap.classification import ClassificationError
from boardsnap.neural import (ARCHITECTURE, CLASSES, PREPROCESSING, NeuralClassifier,
                              SquareNet, load_model, preprocess)
from tools.train_neural import fit, selection_key
from tools.neural_data import load_board, read_index
from tools.evaluate_neural import score, template_profile

pytestmark = pytest.mark.unit


@pytest.fixture
def artifact(tmp_path):
    torch.manual_seed(7)
    model = SquareNet().eval()
    metadata = {"formatVersion": 1, "architecture": ARCHITECTURE, "classOrder": list(CLASSES),
                "preprocessing": PREPROCESSING, "dataVersion": {"datasetId": "test"},
                "trainingConfig": {"seed": 7}}
    path = tmp_path / "model.pt"
    torch.save({"metadata": metadata, "state_dict": model.state_dict()}, path)
    return path, model


def test_preprocess_preserves_rgb_range_and_pixels_without_mutating_source():
    images = np.zeros((2, 64, 64, 3), dtype=np.uint8)
    images[0, 10, 20] = [255, 128, 0]
    before = images.copy()
    tensor = preprocess(images)
    assert tensor.shape == (2, 3, 64, 64) and tensor.dtype == torch.float32
    assert tensor[0, :, 10, 20].tolist() == pytest.approx([1, 128 / 255, 0])
    tensor.fill_(0)
    assert np.array_equal(images, before)


@pytest.mark.parametrize("images", [np.zeros((64, 64, 3), np.uint8), np.zeros((1, 32, 32, 3), np.uint8),
                                   np.zeros((1, 64, 64, 3), np.float32), np.zeros((0, 64, 64, 3), np.uint8)])
def test_invalid_inputs_are_rejected(images):
    with pytest.raises(ValueError):
        preprocess(images)


def test_cpu_saved_model_produces_identical_logits(artifact):
    path, original = artifact
    loaded, metadata = load_model(path)
    pixels = np.random.default_rng(0).integers(0, 256, (4, 64, 64, 3), dtype=np.uint8)
    with torch.inference_mode():
        assert torch.equal(original(preprocess(pixels)), loaded(preprocess(pixels)))
    assert not loaded.training and next(loaded.parameters()).device.type == "cpu"
    assert metadata["classOrder"] == list(CLASSES)
    assert np.array_equal(NeuralClassifier(path).predict_ids(pixels), loaded(preprocess(pixels)).argmax(1).numpy())


@pytest.mark.parametrize("fault", ["classes", "preprocessing", "architecture", "weights", "corrupt"])
def test_invalid_models_fail_clearly(artifact, fault):
    path, _ = artifact
    payload = torch.load(path, weights_only=True)
    if fault == "classes":
        payload["metadata"]["classOrder"].reverse()
    elif fault == "preprocessing":
        payload["metadata"]["preprocessing"] = {"inputSize": [32, 32]}
    elif fault == "architecture":
        payload["metadata"]["architecture"] = "unknown"
    elif fault == "weights":
        next(iter(payload["state_dict"].values())).fill_(float("nan"))
    if fault == "corrupt":
        path.write_bytes(b"invalid model")
    else:
        torch.save(payload, path)
    with pytest.raises(ClassificationError):
        load_model(path)


def test_canonical_output_remains_piece_placement_only(artifact, monkeypatch):
    path, _ = artifact
    classifier = NeuralClassifier(path)
    # Asymmetric image-view labels prove the explicit view reaches canonical output.
    monkeypatch.setattr(classifier, "classify_squares", lambda _: [["R", *([None] * 7)], *[[None] * 8 for _ in range(6)], [*([None] * 7), "k"]])
    from boardsnap import neural
    from boardsnap.detection import BoardBounds
    monkeypatch.setattr(neural, "read_image", lambda _: Image.new("RGB", (512, 512)))
    monkeypatch.setattr(neural, "detect_board", lambda _: BoardBounds(0, 0, 512, 512))
    assert classifier.recognize_image("unused", orientation="white-bottom") == {"piecePlacement": "R7/8/8/8/8/8/8/7k"}
    assert classifier.recognize_image("unused", orientation="black-bottom") == {"piecePlacement": "k7/8/8/8/8/8/8/7R"}
    with pytest.raises(ValueError):
        classifier.recognize_image("unused", orientation="auto")


def test_resume_matches_uninterrupted_weights_and_validation(tmp_path):
    config = {"seed": 123, "epochs": 2, "batchSize": 64, "learningRate": .002, "weightDecay": 0., "threads": 1}
    labels = np.arange(128, dtype=np.int64) % 13
    pixels = np.zeros((128, 64, 64, 3), dtype=np.uint8)
    pixels[:] = (labels * 19).astype(np.uint8)[:, None, None, None]
    data = (pixels, labels)
    full = fit(data, data, config, tmp_path / "full", {"version": "synthetic-test"})
    fit(data, data, config, tmp_path / "resumed", {"version": "synthetic-test"}, stop_after=1)
    resumed = fit(data, data, config, tmp_path / "resumed", {"version": "synthetic-test"}, resume=True)
    a = torch.load(tmp_path / "full/last.pt", weights_only=True)
    b = torch.load(tmp_path / "resumed/last.pt", weights_only=True)
    assert all(torch.equal(v, b["state_dict"][k]) for k, v in a["state_dict"].items())
    assert full["selected"] == resumed["selected"]
    assert [r["validation"] for r in full["history"]] == [r["validation"] for r in resumed["history"]]
    with pytest.raises(ValueError, match="changed"):
        fit(data, data, config, tmp_path / "resumed", {"version": "changed"}, resume=True)


def test_validation_selection_prioritizes_complete_boards():
    assert selection_key({"exactBoards": 2, "macroRecall": .9, "loss": .2}) > selection_key({"exactBoards": 1, "macroRecall": .99, "loss": .01})


def test_metrics_include_failed_boards_and_separate_precision_from_recall():
    records = [{"positionId": "p1", "expected": [1] * 64, "predictions": [1] * 64},
               {"positionId": "p1", "expected": [2] * 64, "predictions": [1] * 64},
               {"positionId": "p2", "expected": [1] * 64, "predictions": [-1] * 64}]
    metrics = score(records)
    assert metrics["exactBoards"] == 1 and metrics["exactPositionsAllVariants"] == 0
    assert metrics["classes"]["P"]["recall"] == .5
    assert metrics["classes"]["P"]["precision"] == .5
    assert metrics["totalSquares"] == 192
    assert metrics["squareAccuracy"] == pytest.approx(1 / 3)
    assert score([])["squareAccuracy"] is None


def test_template_comparison_excludes_unsupported_styles():
    assert template_profile({"configurationId": "lichess-brown-cburnett-compact"}) == "lichess-cburnett-brown-v1"
    assert template_profile({"configurationId": "lichess-brown-alpha-standard"}) is None


@pytest.fixture
def square_dataset(tmp_path):
    import hashlib
    from tools.build_square_dataset import square_labels
    rows = []
    for split in ("training", "evaluation"):
        labels = square_labels("8/8/8/8/8/8/8/8", "white-bottom")
        row = {"positionId": split, "groupId": split, "configurationId": "test-standard",
               "orientation": "white-bottom", "split": split, "status": "ok", "piecePlacement": "8/8/8/8/8/8/8/8",
               "cells": labels, "array": f"{split}.npz", "arraySha256": "not-loaded"}
        if split == "training":
            np.savez_compressed(tmp_path / row["array"], images=np.zeros((64, 64, 64, 3), np.uint8), class_ids=np.zeros(64, np.uint8))
            row["arraySha256"] = hashlib.sha256((tmp_path / row["array"]).read_bytes()).hexdigest()
        rows.append(row)
    def publish():
        index = tmp_path / "verified.jsonl"
        index.write_text("".join(json.dumps(row) + "\n" for row in rows))
        (tmp_path / "dataset.json").write_text(json.dumps({"complete": True, "classOrder": list(CLASSES),
            "preprocessing": {"squareSize": 64, "colorMode": "RGB"},
            "indexes": {"verified": {"path": index.name, "sha256": hashlib.sha256(index.read_bytes()).hexdigest()}}}))
    publish()
    return tmp_path, rows, publish


def test_training_loader_never_opens_evaluation_arrays(square_dataset):
    from tools.neural_data import load_split
    root, _, _ = square_dataset
    _, rows = read_index(root)
    images, labels = load_split(root, rows, "training")
    assert images.shape == (64, 64, 64, 3) and labels.shape == (64,)
    assert not (root / "evaluation.npz").exists()


def test_cross_partition_group_rejected_even_when_index_hash_matches(square_dataset):
    root, rows, publish = square_dataset
    rows[1]["groupId"] = rows[0]["groupId"]
    publish()
    with pytest.raises(ValueError, match="crosses partitions"):
        read_index(root)


def test_altered_training_pixels_rejected(square_dataset):
    root, rows, _ = square_dataset
    (root / rows[0]["array"]).write_bytes(b"altered")
    with pytest.raises(ValueError, match="changed"):
        load_board(root, rows[0])


def test_default_pipeline_import_does_not_require_torch():
    import subprocess
    import sys
    code = '''
import importlib.abc, sys
class BlockTorch(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "torch" or fullname.startswith("torch."):
            raise ImportError("optional dependency unavailable")
sys.meta_path.insert(0, BlockTorch())
from boardsnap.pipeline import recognize_image
assert "torch" not in sys.modules
'''
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
