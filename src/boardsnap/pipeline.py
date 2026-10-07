"""Compose recognition stages without depending on a CLI, web framework or Flutter."""

from contextlib import ExitStack
from os import PathLike

from boardsnap.classification import classify_squares
from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import detect_orientation, to_canonical
from boardsnap.output import build_result
from boardsnap.segmentation import split_squares


def recognize_image(path: str | PathLike[str]) -> dict[str, str]:
    """Return only piecePlacement, or propagate a stage's structured exception.

    Reads pixels only: no sidecars, expected positions or filename-based hints.
    Adapters serialize success or error.to_dict(); the core writes nothing.
    Supports only the initial brown/cburnett profile. All owned images are closed.
    """
    with ExitStack() as stack:
        source = stack.enter_context(read_image(path))
        board = stack.enter_context(normalize_board(source, detect_board(source)))
        squares = split_squares(board.image)
        for row in squares:
            for square in row:
                stack.enter_context(square)
        orientation = detect_orientation(board)
        visual = classify_squares(squares)
        return build_result(to_canonical(visual, orientation))
