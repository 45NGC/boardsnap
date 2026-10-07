"""Real piece pixels: development coverage and held-out complete positions."""

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest

from boardsnap.classification import classify_square, classify_squares
from boardsnap.detection import BoardBounds, BoardDetectionError
from boardsnap.image_input import ImageInputError, read_image
from boardsnap.normalization import normalize_board
from boardsnap.pipeline import recognize_image
from boardsnap.segmentation import split_squares


ROOT = Path(__file__).resolve().parents[1]
PROFILE = "lichess-cburnett-brown-v1"
REFERENCE = json.loads((ROOT / "tests/fixtures/detection/references.json").read_text())
ASSET = json.loads((ROOT / "src/boardsnap/assets/piece-templates.json").read_text())
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


def expected_visual(annotation):
    board = [[p for token in rank for p in ([None] * int(token) if token.isdigit() else [token])]
             for rank in annotation["piecePlacement"].split("/")]
    return board if annotation["orientation"] == "white-bottom" else [row[::-1] for row in board[::-1]]


@pytest.mark.parametrize("path", CASES)
def test_all_64_predictions_against_known_square_labels(path):
    annotation = json.loads(path.with_suffix(".json").read_text())
    with ExitStack() as stack:
        image = stack.enter_context(read_image(path))
        # Isolate classification from detection/orientation using reviewed bounds.
        board = stack.enter_context(normalize_board(image, BoardBounds(190, 158, 584, 584)))
        squares = split_squares(board.image)
        for row in squares:
            for square in row:
                stack.enter_context(square)
        before = board.image.tobytes()
        assert classify_squares(squares) == expected_visual(annotation)
        assert board.image.tobytes() == before


@pytest.mark.parametrize("path", CASES)
@pytest.mark.parametrize("variant", ["original", "cropped", "translated", "double-size"])
def test_complete_position_from_pixels_only(path, variant, tmp_path):
    expected = json.loads(path.with_suffix(".json").read_text())["piecePlacement"]
    with ExitStack() as stack:
        image = stack.enter_context(read_image(path))
        if variant == "cropped":
            image = stack.enter_context(image.crop((190, 158, 774, 742)))
        elif variant == "translated":
            canvas = stack.enter_context(Image.new("RGB", (1491, 1097), "white"))
            canvas.paste(image, (91, 53))
            image = canvas
        elif variant == "double-size":
            image = stack.enter_context(image.resize((2560, 2000), Image.Resampling.NEAREST))
        anonymous = tmp_path / "input.png"
        image.save(anonymous)
    # No annotation or orientation-bearing filename accompanies the input.
    assert recognize_image(anonymous) == {"piecePlacement": expected}


@pytest.mark.integration
@pytest.mark.parametrize("label", [None, *"PNBRQKpnbrqk"], ids=lambda p: p or "empty")
@pytest.mark.parametrize("background", ["light", "dark"])
def test_each_class_on_both_backgrounds_outside_the_selected_template_crop(label, background):
    selected = {(entry["source"]["image"], entry["source"]["row"], entry["source"]["column"])
                for entry in ASSET["templates"]}
    for path in sorted((ROOT / "data/tuning" / PROFILE).glob("pos-*.json")):
        annotation = json.loads(path.read_text())
        for row_index, row in enumerate(expected_visual(annotation)):
            for col_index, piece in enumerate(row):
                image_path = path.with_suffix(".png")
                key = (image_path.relative_to(ROOT).as_posix(), row_index, col_index)
                if (piece != label or ("light", "dark")[(row_index + col_index) % 2] != background
                        or key in selected):
                    continue
                with read_image(image_path) as image:
                    with normalize_board(image, BoardBounds(190, 158, 584, 584)) as board:
                        with board.image.crop((col_index * 64, row_index * 64,
                                               (col_index + 1) * 64, (row_index + 1) * 64)) as square:
                            assert classify_square(square) == label
                return
    pytest.fail(f"No non-template tuning example for {label!r} on {background}.")


@pytest.mark.integration
def test_template_provenance_labels_coverage_and_pixels():
    atlas_path = ROOT / "src/boardsnap/assets/piece-templates.png"
    assert hashlib.sha256(atlas_path.read_bytes()).hexdigest() == ASSET["atlasSha256"]
    assert {(entry["label"], entry["background"]) for entry in ASSET["templates"]} == {
        (label, color) for label in [None, *"PNBRQKpnbrqk"] for color in ("light", "dark")
    }
    with Image.open(atlas_path) as atlas:
        for entry in ASSET["templates"]:
            source = entry["source"]
            path = ROOT / source["image"]
            assert path.parent == ROOT / "data/tuning" / PROFILE
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
            annotation_path = path.with_suffix(".json")
            assert hashlib.sha256(annotation_path.read_bytes()).hexdigest() == source["annotationSha256"]
            annotation = json.loads(annotation_path.read_text())
            assert annotation["split"] == "tuning" and annotation["groupId"] in REFERENCE["tuning"]
            row, col = source["row"], source["column"]
            assert expected_visual(annotation)[row][col] == entry["label"]
            assert entry["tuningCount"] >= 2
            with read_image(path) as image, normalize_board(image, BoardBounds(190, 158, 584, 584)) as board:
                with board.image.crop((col*64, row*64, (col+1)*64, (row+1)*64)) as expected:
                    with atlas.crop(tuple(entry["atlasBox"])) as actual:
                        assert actual.tobytes() == expected.tobytes()


@pytest.mark.integration
@pytest.mark.parametrize("failure,code", [("missing", "INPUT_READ_ERROR"), ("empty", "INVALID_IMAGE"),
                                         ("corrupt", "INVALID_IMAGE"), ("no-board", "BOARD_NOT_FOUND")])
def test_pipeline_propagates_errors_instead_of_fabricating_positions(tmp_path, failure, code):
    path = tmp_path / "input.png"
    if failure in {"empty", "corrupt"}:
        path.write_bytes(b"" if failure == "empty" else b"not an image")
    elif failure == "no-board":
        with Image.new("RGB", (600, 600), "white") as image:
            image.save(path)
    with pytest.raises((ImageInputError, BoardDetectionError)) as caught:
        recognize_image(path)
    assert caught.value.to_dict()["error"]["code"] == code
    assert "piecePlacement" not in caught.value.to_dict()
