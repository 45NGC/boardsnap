"""Pixel-based coordinate reading; annotated piece matrices are not recognition."""

from contextlib import ExitStack
import hashlib
from importlib.resources import files
import json
from pathlib import Path

from PIL import Image
import pytest

from boardsnap.detection import BoardBounds, detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import detect_orientation, to_canonical
from boardsnap.output import build_result


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / "tests/fixtures/detection/references.json").read_text())
CASES = [
    pytest.param(ROOT / folder / REFERENCE["profileId"] / f"{group}-{view}.png",
                 id=f"{split}-{group}-{view}", marks=marker)
    for split, folder, marker in (
        ("tuning", "data/tuning", pytest.mark.integration),
        ("evaluation", "tests/fixtures/evaluation", pytest.mark.evaluation),
    )
    for group in REFERENCE[split]
    for view in ("white", "black")
]


def annotated_matrix(placement):
    """Independent test labels for the future classifier's output."""
    return [[piece for token in rank for piece in ([None] * int(token) if token.isdigit() else [token])]
            for rank in placement.split("/")]


@pytest.mark.parametrize("path", CASES)
@pytest.mark.parametrize("variant", ["original", "cropped", "translated", "double-size",
                                     "no-labels", "files-only", "ranks-only", "one-label"])
def test_coordinate_pixels_and_annotated_position_mapping(path, variant):
    annotation = json.loads(path.with_suffix(".json").read_text())
    expected_orientation = annotation["orientation"]
    canonical = annotated_matrix(annotation["piecePlacement"])
    # Simulate only the matrix hand-off, never claim to have classified pieces.
    visual = ([row[:] for row in canonical] if expected_orientation == "white-bottom"
              else [row[::-1] for row in canonical[::-1]])
    with ExitStack() as stack:
        image = stack.enter_context(read_image(path))
        if variant in {"no-labels", "files-only", "ranks-only", "one-label"}:
            # Independent, deliberately wider rectangles than the reader's ROIs.
            for index in range(8):
                if variant in {"no-labels", "ranks-only", "one-label"}:
                    if variant != "one-label" or index != 0:
                        color = (181, 136, 99) if index % 2 == 0 else (240, 217, 181)
                        image.paste(color, (190 + index * 73, 722, 210 + index * 73, 742))
                if variant in {"no-labels", "files-only", "one-label"}:
                    color = (181, 136, 99) if index % 2 == 0 else (240, 217, 181)
                    image.paste(color, (754, 158 + index * 73, 774, 178 + index * 73))
        if variant == "cropped":
            image = stack.enter_context(image.crop((190, 158, 774, 742)))
        elif variant == "translated":
            canvas = stack.enter_context(Image.new("RGB", (1550, 1140), "white"))
            canvas.paste(image, (123, 71))
            image = canvas
        elif variant == "double-size":
            image = stack.enter_context(image.resize((2560, 2000), Image.Resampling.NEAREST))
        before = image.tobytes()
        # Small normalized output proves the reader uses the preserved source.
        board = stack.enter_context(normalize_board(image, detect_board(image), square_size=16))
        orientation = detect_orientation(board)
        if variant in {"no-labels", "one-label"}:
            assert orientation == "white-bottom"
            assert to_canonical(visual, orientation) == visual
        else:
            assert orientation == expected_orientation
            assert to_canonical(visual, orientation) == canonical
            assert build_result(to_canonical(visual, orientation)) == {"piecePlacement": annotation["piecePlacement"]}
        assert image.tobytes() == before == board.source_image.tobytes()


@pytest.mark.integration
def test_conflicting_real_axes_fall_back_even_with_asymmetric_pieces():
    folder = ROOT / "data/tuning" / REFERENCE["profileId"]
    with read_image(folder / "pos-002-black.png") as black, read_image(folder / "pos-002-white.png") as white:
        # Replace just the rank coordinates with the opposite view's labels.
        for row in range(8):
            box = (754, 158 + row * 73, 774, 178 + row * 73)
            with white.crop(box) as patch:
                black.paste(patch, box)
        with normalize_board(black, BoardBounds(190, 158, 584, 584)) as board:
            assert detect_orientation(board) == "white-bottom"


@pytest.mark.integration
def test_packaged_templates_have_only_declared_tuning_sources():
    data = json.loads(files("boardsnap").joinpath("assets/coordinate-glyphs.json").read_text())
    assert set(data["glyphs"]) == set("abcdefgh12345678")
    assert all(len(examples) == 2 for examples in data["glyphs"].values())
    assert {entry["path"] for entry in data["sources"]} == {
        f"data/tuning/lichess-cburnett-brown-v1/pos-004-{view}.png" for view in ("white", "black")
    }
    for entry in data["sources"]:
        assert hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
