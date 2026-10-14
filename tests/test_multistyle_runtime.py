"""Model routing is configuration; recognition requests need only image and view."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from boardsnap import pipeline
from boardsnap.adapters import cli
from boardsnap.classification import ClassificationError

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.unit


@pytest.mark.parametrize("source", ["environment", "explicit"])
def test_model_path_does_not_select_a_piece_profile(monkeypatch, source):
    pytest.importorskip("torch")
    from boardsnap import neural
    calls = []
    class FakeClassifier:
        def __init__(self, path):
            calls.append(path)
        def recognize_image(self, path, *, orientation):
            calls.append((path, orientation))
            return {"piecePlacement": "8/8/8/8/8/8/8/8"}
    monkeypatch.setattr(neural, "NeuralClassifier", FakeClassifier)
    monkeypatch.setattr(pipeline, "get_profile", lambda _: pytest.fail("A model must not select a piece profile"))
    monkeypatch.setenv("BOARDSNAP_MODEL", "chosen.pt" if source == "environment" else "wrong.pt")
    options = {} if source == "environment" else {"model": Path("chosen.pt")}
    assert set(pipeline.recognize_image("photo.png", orientation="black-bottom", **options)) == {"piecePlacement"}
    assert os.fspath(calls[0]) == "chosen.pt"
    assert calls[1] == ("photo.png", "black-bottom")


def test_explicit_profile_ignores_configured_model(monkeypatch):
    monkeypatch.setenv("BOARDSNAP_MODEL", "/nonexistent/model.pt")
    profile = "lichess-cburnett-brown-v1"
    image = ROOT / "data/tuning" / profile / "pos-004-white.png"
    assert pipeline.recognize_image(image, profile=profile) == {"piecePlacement": "8/8/8/8/8/8/8/8"}
    with pytest.raises(ValueError, match="not both"):
        pipeline.recognize_image(image, profile=profile, model="model.pt")


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_configured_model_is_not_a_template_fallback(monkeypatch, value):
    monkeypatch.setenv("BOARDSNAP_MODEL", value)
    with pytest.raises(ClassificationError, match="empty"):
        pipeline.recognize_image("unused.png")


def test_missing_optional_dependency_is_structured(monkeypatch):
    monkeypatch.setitem(sys.modules, "boardsnap.neural", None)
    with pytest.raises(ClassificationError, match=r"boardsnap\[ml\]"):
        pipeline.recognize_image("unused.png", model="model.pt")


def test_cli_rejects_ambiguous_backend_selection(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["unused.png", "--model", "model.pt", "--profile", "lichess-cburnett-brown-v1"])
    assert error.value.code == 2 and capsys.readouterr().out == ""


@pytest.mark.integration
@pytest.mark.parametrize("selection", ["environment", "argument"])
def test_configured_neural_cli_from_another_working_directory(tmp_path, selection):
    torch = pytest.importorskip("torch")
    from boardsnap.neural import SquareNet, CLASSES, ARCHITECTURE, PREPROCESSING
    model = SquareNet()
    for parameter in model.parameters():
        parameter.data.zero_()
    path = tmp_path / "model with spaces.pt"
    torch.save({"state_dict": model.state_dict(), "metadata": {
        "formatVersion": 1, "classOrder": list(CLASSES), "architecture": ARCHITECTURE,
        "preprocessing": PREPROCESSING, "dataVersion": {"fixture": True}, "trainingConfig": {"fixture": True}}}, path)
    image = ROOT / "data/tuning/lichess-cburnett-brown-v1/pos-004-white.png"
    env = dict(os.environ, BOARDSNAP_MODEL=str(path), OMP_NUM_THREADS="1")
    command = [sys.executable, "-m", "boardsnap", str(image), "--orientation", "black-bottom"]
    if selection == "argument":
        env["BOARDSNAP_MODEL"] = str(tmp_path / "missing.pt")
        command.extend(["--model", str(path)])
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 and result.stderr == ""
    assert result.stdout == '{"piecePlacement": "8/8/8/8/8/8/8/8"}\n'
    path.write_bytes(b"corrupt")
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == ""
    assert json.loads(result.stdout)["error"]["code"] == "PROCESSING_FAILED"


@pytest.mark.parametrize("profile", ["lichess-cburnett-brown-v1", "lichess-cburnett-blue-v1", "chesscom-default-green-v1"])
@pytest.mark.parametrize("view", ["white", "black"])
def test_coordinate_layout_selection_does_not_require_a_user_profile(profile, view):
    from boardsnap.detection import BoardBounds
    from boardsnap.image_input import read_image
    from boardsnap.normalization import normalize_board
    from boardsnap.orientation import detect_digital_orientation
    path = ROOT / "data/tuning" / profile / f"pos-006-{view}.png"
    annotation = json.loads(path.with_suffix(".json").read_text())
    bounds = BoardBounds(**{k: round(v) for k, v in annotation["boardBounds"].items()})
    with read_image(path) as image, normalize_board(image, bounds) as board:
        assert detect_digital_orientation(board) == f"{view}-bottom"


def test_explicit_neural_view_never_calls_coordinate_reader(monkeypatch):
    pytest.importorskip("torch")
    from PIL import Image
    from boardsnap import neural
    from boardsnap.detection import BoardBounds
    classifier = object.__new__(neural.NeuralClassifier)
    monkeypatch.setattr(classifier, "classify_squares", lambda _: [[None]*8 for _ in range(8)])
    monkeypatch.setattr(neural, "read_image", lambda _: Image.new("RGB", (512, 512)))
    monkeypatch.setattr(neural, "detect_board", lambda _: BoardBounds(0, 0, 512, 512))
    monkeypatch.setattr(neural, "detect_digital_orientation", lambda _: pytest.fail("Explicit view must win"))
    assert classifier.recognize_image("unused", orientation="black-bottom") == {"piecePlacement": "8/8/8/8/8/8/8/8"}
