"""Read, detect, normalize and split real captures without using their labels."""

from contextlib import ExitStack
import json
from pathlib import Path

from PIL import Image
import pytest

from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / "tests/fixtures/detection/references.json").read_text())
CASES = [
    pytest.param(ROOT / folder / REFERENCE["profileId"] / f"{group}-{color}.png",
                 id=f"{split}-{group}-{color}", marks=marker)
    for split, folder, marker in (
        ("tuning", "data/tuning", pytest.mark.integration),
        ("evaluation", "tests/fixtures/evaluation", pytest.mark.evaluation),
    )
    for group in REFERENCE[split]
    for color in ("white", "black")
]


@pytest.mark.parametrize("path", CASES)
def test_real_capture_preserves_context_and_all_square_pixels(path):
    with ExitStack() as stack:
        source = stack.enter_context(read_image(path))
        original = source.tobytes()
        board = stack.enter_context(normalize_board(source, detect_board(source)))
        squares = split_squares(board.image)
        assert len(squares) == 8 and all(len(row) == 8 for row in squares)
        rebuilt = stack.enter_context(Image.new("RGB", (512, 512)))
        for row_index, row in enumerate(squares):
            for col_index, square in enumerate(row):
                stack.enter_context(square)
                assert square.size == (64, 64)
                rebuilt.paste(square, (col_index * 64, row_index * 64))
        # Reviewed bounds supply the expected crop, never detector output.
        cropped = stack.enter_context(source.crop(tuple(REFERENCE["box"])))
        expected = stack.enter_context(cropped.resize((512, 512), Image.Resampling.LANCZOS))
        assert rebuilt.tobytes() == expected.tobytes()
        assert board.source_bounds.as_box() == tuple(REFERENCE["box"])
        assert board.source_image.size == source.size
        assert board.source_image.tobytes() == original == source.tobytes()
