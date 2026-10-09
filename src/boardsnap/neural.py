"""Optional small PyTorch classifier; importing the default pipeline needs no torch."""

from contextlib import ExitStack
import pickle

import numpy as np
import torch
from torch import nn
from PIL import Image

from boardsnap.classification import ClassificationError
from boardsnap.detection import detect_board
from boardsnap.image_input import read_image
from boardsnap.normalization import normalize_board
from boardsnap.orientation import to_canonical
from boardsnap.output import build_result
from boardsnap.segmentation import split_squares

CLASSES = ("empty", *"PNBRQKpnbrqk")
ARCHITECTURE = "small-square-cnn-v1"
PREPROCESSING = {"inputSize": [64, 64], "colorMode": "RGB", "inputDtype": "uint8",
                 "tensorLayout": "NCHW", "tensorDtype": "float32", "scale": "divide by 255",
                 "additionalNormalization": None, "augmentation": None}


class SquareNet(nn.Module):
    """About forty thousand parameters; no downloaded/pretrained weights."""

    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.AvgPool2d(2),
            nn.Conv2d(3, 8, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(8, 16, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, 13),
        )

    def forward(self, pixels):
        return self.layers(pixels)


def preprocess(images):
    """Identical conversion for training and CPU inference; reject implicit resizing."""
    if not isinstance(images, np.ndarray) or images.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB square arrays.")
    if images.ndim != 4 or images.shape[1:] != (64, 64, 3) or not len(images):
        raise ValueError("Expected a nonempty (N, 64, 64, 3) batch.")
    return torch.from_numpy(np.array(images, copy=True)).permute(0, 3, 1, 2).contiguous().float().div_(255)


def load_model(path):
    """Load only tensors/primitive metadata on CPU and enforce the versioned contract."""
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
        metadata = payload["metadata"]
        if (metadata["formatVersion"] != 1 or metadata["architecture"] != ARCHITECTURE
                or metadata["classOrder"] != list(CLASSES) or metadata["preprocessing"] != PREPROCESSING
                or not metadata.get("dataVersion") or not metadata.get("trainingConfig")):
            raise ValueError("Incompatible neural artifact metadata.")
        model = SquareNet()
        model.load_state_dict(payload["state_dict"], strict=True)
        if any(not torch.isfinite(tensor).all() for tensor in model.state_dict().values()):
            raise ValueError("Nonfinite model weights.")
        return model.eval(), metadata
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, EOFError, pickle.UnpicklingError) as error:
        raise ClassificationError("Could not load a compatible neural model.") from error


class NeuralClassifier:
    """Explicit opt-in CPU inference, with one predicted class per square."""

    def __init__(self, path):
        self.model, self.metadata = load_model(path)

    @torch.inference_mode()
    def predict_ids(self, images):
        return self.model(preprocess(images)).argmax(1).numpy()

    def classify_squares(self, squares):
        if len(squares) != 8 or any(len(row) != 8 for row in squares):
            raise ValueError("Expected an 8 by 8 matrix of square images.")
        if any(not isinstance(cell, Image.Image) or cell.mode != "RGB" or cell.size != (64, 64)
               for row in squares for cell in row):
            raise ValueError("Expected 64 by 64 RGB Pillow squares.")
        predictions = self.predict_ids(np.stack([np.asarray(cell) for row in squares for cell in row]))
        labels = [None if value == 0 else CLASSES[value] for value in predictions]
        return [labels[start:start + 8] for start in range(0, 64, 8)]

    def recognize_image(self, path, *, orientation):
        """Pixel-only pipeline with explicit view; preserves piecePlacement-only output."""
        if orientation not in ("white-bottom", "black-bottom"):
            raise ValueError("Choose white-bottom or black-bottom explicitly.")
        with ExitStack() as stack:
            image = stack.enter_context(read_image(path))
            board = stack.enter_context(normalize_board(image, detect_board(image)))
            squares = split_squares(board.image)
            for row in squares:
                for square in row:
                    stack.enter_context(square)
            labels = self.classify_squares(squares)
            return build_result(to_canonical(labels, orientation))
