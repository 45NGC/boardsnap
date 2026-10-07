"""Verify metric accounting with controlled outcomes, not recognition accuracy."""

import importlib.util
import json
from pathlib import Path

import pytest

from boardsnap.detection import BoardDetectionError


_spec = importlib.util.spec_from_file_location(
    "evaluate_classification", Path(__file__).resolve().parents[1] / "tools/evaluate_classification.py"
)
assert _spec and _spec.loader
report_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report_tool)
pytestmark = pytest.mark.unit


def test_processing_failures_remain_in_denominators_and_absent_classes_have_zero_support(tmp_path, monkeypatch):
    folder = tmp_path / "data/tuning/lichess-cburnett-brown-v1"
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps({"positions": [
        {"groupId": "case", "split": "tuning", "piecePlacement": "p7/8/8/8/8/8/8/8"}
    ]}))
    asset = tmp_path / "src/boardsnap/assets/piece-templates.json"
    asset.parent.mkdir(parents=True)
    asset.write_text("{}")
    monkeypatch.setattr(report_tool, "ROOT", tmp_path)

    def controlled_outcome(path):
        if path.name == "case-white.png":
            return {"piecePlacement": "P7/8/8/8/8/8/8/8"}
        raise BoardDetectionError("BOARD_NOT_FOUND", "Test failure")

    monkeypatch.setattr(report_tool, "recognize_image", controlled_outcome)
    report = report_tool.evaluate("tuning")
    assert report["exactPositions"] == 0 and report["imageCount"] == 2
    assert report["processingFailures"] == 1
    assert report["correctSquares"] == 63 and report["totalSquares"] == 128
    assert report["squareAccuracy"] == 63 / 128
    assert report["occupiedSquareAccuracy"] == 0
    assert report["macroRecallPresentClasses"] == .25
    assert report["classes"]["p"]["predicted"]["P"] == 1
    assert report["classes"]["p"]["predicted"]["processing-error"] == 1
    assert report["classes"]["p"]["backgrounds"]["light"]["total"] == 2
    assert report["classes"]["Q"]["total"] == 0


def test_split_must_be_explicit_and_valid():
    with pytest.raises(ValueError):
        report_tool.evaluate("all")
