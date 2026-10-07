"""Explicit image view overrides coordinate pixels without changing the output contract."""

from contextlib import ExitStack
import json
from pathlib import Path

import pytest

import boardsnap.pipeline as pipeline
from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import _coordinate_boxes, detect_orientation
from boardsnap.profiles import PROFILES

ROOT = Path(__file__).resolve().parents[1]
DIGITAL = tuple(name for name, config in PROFILES.items() if config.kind == "digital")


def make_input(tmp_path, profile, view, clues):
    """Modify only coordinate patches on a real asymmetric tuning position."""
    folder = ROOT / "data/tuning" / profile
    source = folder / f"pos-006-{view}.png"
    expected = json.loads(source.with_suffix(".json").read_text())["piecePlacement"]
    with ExitStack() as stack:
        image = stack.enter_context(read_image(source))
        bounds = detect_board(image, profile=profile)
        if clues != "original":
            opposite = "black" if view == "white" else "white"
            empty = stack.enter_context(read_image(folder / f"pos-004-{opposite}.png"))
            other_bounds = detect_board(empty, profile=profile)
            boxes = [box for axis in _coordinate_boxes(bounds, profile) for box in axis]
            other_boxes = [box for axis in _coordinate_boxes(other_bounds, profile) for box in axis]
            for box, other_box in zip(boxes, other_boxes, strict=True):
                if clues == "opposite":
                    with empty.crop(other_box) as patch:
                        assert patch.size == (box[2] - box[0], box[3] - box[1])
                        image.paste(patch, box)
                else:
                    col = int(((box[0] + box[2]) / 2 - bounds.x) * 8 / bounds.width)
                    row = int(((box[1] + box[3]) / 2 - bounds.y) * 8 / bounds.height)
                    image.paste(PROFILES[profile].colors[(row + col) % 2], box)
        with normalize_board(image, bounds) as board:
            observed = detect_orientation(board, profile=profile)
        # Prove that the pixel clues would contradict the override or be absent.
        detected_view = ("white-bottom" if clues == "absent" else
                         f"{'black' if view == 'white' else 'white'}-bottom" if clues == "opposite"
                         else f"{view}-bottom")
        assert observed == detected_view
        path = tmp_path / "anonymous.png"
        image.save(path)
    return path, expected


@pytest.mark.integration
@pytest.mark.parametrize("profile", DIGITAL)
@pytest.mark.parametrize("view", ["white", "black"])
@pytest.mark.parametrize("clues", ["original", "absent", "opposite"])
def test_explicit_view_recognizes_same_asymmetric_position(tmp_path, monkeypatch, profile, view, clues):
    path, expected = make_input(tmp_path, profile, view, clues)

    def forbidden_reader(*args, **kwargs):
        pytest.fail("Explicit orientation must bypass automatic coordinate reading")

    monkeypatch.setattr(pipeline, "detect_orientation", forbidden_reader)
    assert pipeline.recognize_image(path, profile=profile, orientation=f"{view}-bottom") == {
        "piecePlacement": expected}


@pytest.mark.integration
@pytest.mark.parametrize("profile", DIGITAL)
@pytest.mark.parametrize("view", ["white", "black"])
def test_auto_is_backward_compatible_with_coordinates(profile, view):
    path = ROOT / "data/tuning" / profile / f"pos-006-{view}.png"
    expected = json.loads(path.with_suffix(".json").read_text())["piecePlacement"]
    assert pipeline.recognize_image(path, profile=profile, orientation="auto") == (
        pipeline.recognize_image(path, profile=profile)) == {"piecePlacement": expected}


@pytest.mark.integration
@pytest.mark.parametrize("profile", DIGITAL)
def test_auto_keeps_white_bottom_fallback_without_clues(tmp_path, profile):
    path, expected = make_input(tmp_path, profile, "black", "absent")
    assumed_white = pipeline.recognize_image(path, profile=profile, orientation="white-bottom")
    assert pipeline.recognize_image(path, profile=profile, orientation="auto") == (
        pipeline.recognize_image(path, profile=profile)) == assumed_white
    assert assumed_white != {"piecePlacement": expected}
    assert pipeline.recognize_image(path, profile=profile, orientation="black-bottom") == {
        "piecePlacement": expected}


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", "white", "black", "AUTO", "White-bottom", None, False, 0, [], {}])
def test_invalid_orientation_fails_before_opening_image(monkeypatch, value):
    def forbidden_read(*args, **kwargs):
        pytest.fail("Invalid options must be rejected before image I/O")

    monkeypatch.setattr(pipeline, "read_image", forbidden_read)
    with pytest.raises(ValueError, match="Orientation must be white-bottom, black-bottom or auto"):
        pipeline.recognize_image("does-not-exist.png", orientation=value)
