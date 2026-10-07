"""Actual installed command and module: JSON bytes, process status and stderr."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image
import pytest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "lichess-cburnett-brown-v1"
REFERENCE = json.loads((ROOT / "tests/fixtures/detection/references.json").read_text())
CASES = [
    pytest.param(ROOT / folder / PROFILE / f"{group}-{view}.png",
                 id=f"{split}-{group}-{view}", marks=marker)
    for split, folder, marker in (
        ("tuning", "data/tuning", pytest.mark.integration),
        ("evaluation", "tests/fixtures/evaluation", pytest.mark.evaluation),
    )
    for group in REFERENCE[split]
    for view in ("white", "black")
]


@pytest.fixture(params=["console", "module"])
def command(request):
    if request.param == "module":
        return [sys.executable, "-m", "boardsnap"]
    executable = Path(sys.executable).parent / ("boardsnap.exe" if os.name == "nt" else "boardsnap")
    assert executable.is_file(), "Reinstall the package with python -m pip install -e '.[dev]' to register boardsnap."
    return [str(executable)]


def run(command, args, cwd):
    return subprocess.run([*command, *args], cwd=cwd, capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("path", CASES)
def test_known_positions_as_exact_json_without_sidecars(command, path, tmp_path):
    expected = json.loads(path.with_suffix(".json").read_text())["piecePlacement"]
    # Foreign cwd, spaces/unicode and a filename unrelated to the expected position.
    image = tmp_path / "test board ñ.png"
    shutil.copyfile(path, image)
    result = run(command, [image.name], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == json.dumps({"piecePlacement": expected}) + "\n"
    assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.parametrize("failure,code", [
    ("missing", "INPUT_READ_ERROR"), ("directory", "INPUT_READ_ERROR"),
    ("empty", "INVALID_IMAGE"), ("corrupt", "INVALID_IMAGE"),
    ("unsupported", "UNSUPPORTED_IMAGE"), ("no-board", "BOARD_NOT_FOUND"),
    ("multiple-boards", "UNSUPPORTED_IMAGE"),
])
def test_real_input_errors_have_one_json_error_and_exit_one(command, tmp_path, failure, code):
    path = tmp_path / "input.png"
    if failure == "directory":
        path.mkdir()
    elif failure in {"empty", "corrupt"}:
        path.write_bytes(b"" if failure == "empty" else b"not an image")
    elif failure in {"unsupported", "no-board"}:
        with Image.new("RGB", (300, 300), "white") as image:
            image.save(path, format="GIF" if failure == "unsupported" else "PNG")
    elif failure == "multiple-boards":
        with Image.new("RGB", (620, 300), "white") as image:
            for offset in (10, 330):
                for row in range(8):
                    for col in range(8):
                        color = ((240, 217, 181), (181, 136, 99))[(row + col) % 2]
                        image.paste(color, (offset + col*32, 10 + row*32,
                                           offset + (col+1)*32, 10 + (row+1)*32))
            image.save(path)
    result = run(command, [str(path)], tmp_path)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert set(data) == {"error"} and set(data["error"]) == {"code", "message"}
    assert data["error"]["code"] == code and data["error"]["message"]
    assert result.stdout == json.dumps(data) + "\n"
    assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.parametrize("args", [[], ["--unknown"], ["one.png", "two.png"]])
def test_invalid_invocation_has_no_json_and_exits_two(command, tmp_path, args):
    result = run(command, args, tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "usage: boardsnap" in result.stderr


@pytest.mark.integration
def test_help_is_not_a_recognition_result(command, tmp_path):
    result = run(command, ["--help"], tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert result.stdout.startswith("usage: boardsnap")


@pytest.mark.integration
def test_double_dash_allows_filename_starting_with_dash(command, tmp_path):
    path = tmp_path / "-board.png"
    shutil.copyfile(ROOT / "data/tuning" / PROFILE / "pos-004-white.png", path)
    result = run(command, ["--", path.name], tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert result.stdout == '{"piecePlacement": "8/8/8/8/8/8/8/8"}\n'


@pytest.mark.integration
@pytest.mark.parametrize("orientation,placement", [
    ("auto", "6k1/5pp1/7p/3q4/8/2Q2P2/5KPP/8"),
    ("black-bottom", "6k1/5pp1/7p/3q4/8/2Q2P2/5KPP/8"),
    ("white-bottom", "8/PPK5/2P2Q2/8/4q3/p7/1pp5/1k6"),
])
def test_orientation_option_controls_mapping_without_extra_json(command, tmp_path, orientation, placement):
    # White-bottom intentionally contradicts the visible black-bottom labels:
    # an explicit user choice must still win. Exercise profile+orientation together.
    profile = "chesscom-default-green-v1"
    image = tmp_path / "anonymous.png"
    shutil.copyfile(ROOT / "data/tuning" / profile / "pos-006-black.png", image)
    result = run(command, [str(image), "--profile", profile, "--orientation", orientation], tmp_path)
    assert result.returncode == 0
    assert result.stdout == json.dumps({"piecePlacement": placement}) + "\n"
    assert result.stderr == ""


@pytest.mark.integration
@pytest.mark.parametrize("option", [["--orientation", "white"], ["--orientation"]])
def test_invalid_orientation_is_usage_error_before_image_io(command, tmp_path, option):
    result = run(command, ["does-not-exist.png", *option], tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "--orientation" in result.stderr
