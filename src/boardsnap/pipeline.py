"""Compose recognition stages without depending on a CLI, web framework or Flutter."""

from contextlib import ExitStack
from os import PathLike
import os
from typing import Literal

from boardsnap.classification import classify_squares
from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import detect_orientation, to_canonical
from boardsnap.output import build_result
from boardsnap.segmentation import split_squares
from boardsnap.profiles import DEFAULT_PROFILE, get_profile


def recognize_image(path: str | PathLike[str], *, profile: str | None = None,
                    model: str | PathLike[str] | None = None,
                    orientation: Literal["white-bottom", "black-bottom", "auto"] = "auto",
                    input_type: Literal["digital", "photo"] = "digital"
                    ) -> dict[str, str]:
    """Return only piecePlacement, or propagate a stage's structured exception.

    Reads pixels only: no sidecars, expected positions or filename-based hints.
    Adapters serialize success or error.to_dict(); the core writes nothing.
    A model path or BOARDSNAP_MODEL selects the multi-style neural classifier.
    Explicit profiles select legacy templates and ignore the environment model.
    Without either configuration, preserve the legacy brown/cburnett default.
    All owned images are closed. No model is downloaded or guessed from the cwd.

    orientation describes the image view, not the side to move. An explicit
    white-bottom/black-bottom value bypasses coordinate reading and takes
    priority over all image clues. auto preserves coordinate detection and its
    white-bottom fallback. Invalid values raise ValueError before image I/O.
    input_type="photo" opts into perspective detection and rectification. It
    requires a neural model and explicit view; photographic coordinate reading
    has not been validated. Legacy digital behavior remains the default.
    """
    if not isinstance(orientation, str) or orientation not in ("white-bottom", "black-bottom", "auto"):
        raise ValueError("Orientation must be white-bottom, black-bottom or auto.")
    if input_type not in ("digital", "photo"):
        raise ValueError("Input type must be digital or photo.")
    if input_type == "photo" and (orientation == "auto" or profile is not None):
        raise ValueError("Photographs require an explicit orientation and a neural model, without a legacy profile.")
    if profile is not None and model is not None:
        raise ValueError("Choose a model or a legacy profile, not both.")
    selected_model = model if model is not None else (os.environ.get("BOARDSNAP_MODEL") if profile is None else None)
    if input_type == "photo" and selected_model is None:
        from boardsnap.classification import ClassificationError
        raise ClassificationError("Photographs require a model; pass --model or configure BOARDSNAP_MODEL.")
    if selected_model is not None:
        from boardsnap.classification import ClassificationError
        if not os.fspath(selected_model).strip():
            raise ClassificationError("Model path is empty; configure BOARDSNAP_MODEL or pass model explicitly.")
        try:
            from boardsnap.neural import NeuralClassifier
        except ImportError as error:
            raise ClassificationError("Neural recognition requires the boardsnap[ml] extra.") from error
        classifier = NeuralClassifier(selected_model)
        if input_type == "photo":
            return classifier.recognize_photo(path, orientation=orientation)
        return classifier.recognize_image(path, orientation=orientation)
    profile = DEFAULT_PROFILE if profile is None else profile
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
