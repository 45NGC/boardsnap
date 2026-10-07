"""Compose recognition stages without depending on a CLI, web framework or Flutter."""

from contextlib import ExitStack
from os import PathLike
from typing import Literal

from boardsnap.classification import classify_squares
from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import detect_orientation, to_canonical
from boardsnap.output import build_result
from boardsnap.segmentation import split_squares
from boardsnap.profiles import DEFAULT_PROFILE, get_profile


def recognize_image(path: str | PathLike[str], *, profile: str = DEFAULT_PROFILE,
                    orientation: Literal["white-bottom", "black-bottom", "auto"] = "auto"
                    ) -> dict[str, str]:
    """Return only piecePlacement, or propagate a stage's structured exception.

    Reads pixels only: no sidecars, expected positions or filename-based hints.
    Adapters serialize success or error.to_dict(); the core writes nothing.
    The explicit profile defaults to brown/cburnett. All owned images are closed.

    orientation describes the image view, not the side to move. An explicit
    white-bottom/black-bottom value bypasses coordinate reading and takes
    priority over all image clues. auto preserves coordinate detection and its
    white-bottom fallback. Invalid values raise ValueError before image I/O.
    """
    if not isinstance(orientation, str) or orientation not in ("white-bottom", "black-bottom", "auto"):
        raise ValueError("Orientation must be white-bottom, black-bottom or auto.")
    get_profile(profile)
    with ExitStack() as stack:
        source = stack.enter_context(read_image(path))
        board = stack.enter_context(normalize_board(source, detect_board(source, profile=profile)))
        squares = split_squares(board.image)
        for row in squares:
            for square in row:
                stack.enter_context(square)
        resolved_orientation = (detect_orientation(board, profile=profile)
                                if orientation == "auto" else orientation)
        visual = classify_squares(squares, profile=profile)
        return build_result(to_canonical(visual, resolved_orientation))
