"""Adapter exception/stream policy; recognition accuracy is tested separately."""

import json
import sys

import pytest

from boardsnap.adapters import cli
from boardsnap.classification import ClassificationError
from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("failure", [None, RuntimeError("unexpected failure")])
def test_diagnostics_never_mix_with_result_json(monkeypatch, capsys, failure):
    def noisy_recognizer(path):
        assert path == "image with spaces.png"
        print("diagnostic sent to stdout by a stage")
        print("diagnostic sent to stderr", file=sys.stderr)
        if failure:
            raise failure
        return {"piecePlacement": "8/8/8/8/8/8/8/8"}

    monkeypatch.setattr(cli, "recognize_image", noisy_recognizer)
    original_stdout = sys.stdout
    assert cli.main(["image with spaces.png"]) == (1 if failure else 0)
    assert sys.stdout is original_stdout
    captured = capsys.readouterr()
    expected = ({"error": {"code": "PROCESSING_FAILED", "message": "Could not recognize the image."}}
                if failure else {"piecePlacement": "8/8/8/8/8/8/8/8"})
    assert captured.out == json.dumps(expected) + "\n"
    assert "diagnostic sent to stdout" in captured.err
    assert "diagnostic sent to stderr" in captured.err
    if failure:
        assert "RuntimeError: unexpected failure" in captured.err


@pytest.mark.parametrize("error", [
    ImageInputError("INPUT_READ_ERROR", "Could not read the image file."),
    ImageInputError("INVALID_IMAGE", "Invalid image."),
    ImageInputError("UNSUPPORTED_IMAGE", "Unsupported image."),
    BoardDetectionError("BOARD_NOT_FOUND", "No board."),
    BoardDetectionError("UNSUPPORTED_IMAGE", "Multiple boards."),
    ClassificationError("Could not load the piece recognition templates."),
])
def test_preserves_structured_stage_errors(monkeypatch, capsys, error):
    def fail(path):
        raise error

    monkeypatch.setattr(cli, "recognize_image", fail)
    assert cli.main(["input.png"]) == 1
    captured = capsys.readouterr()
    assert captured.out == json.dumps(error.to_dict()) + "\n"
    assert captured.err == ""


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(4)])
def test_does_not_convert_process_control_into_image_errors(monkeypatch, capsys, error):
    def interrupt(path):
        raise error

    monkeypatch.setattr(cli, "recognize_image", interrupt)
    original_stdout = sys.stdout
    with pytest.raises(type(error)):
        cli.main(["input.png"])
    assert sys.stdout is original_stdout
    assert capsys.readouterr().out == ""
