"""Decode local image files into detached, fully loaded RGB images."""

from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import Literal
import warnings

from PIL import Image, ImageOps


InputErrorCode = Literal["INPUT_READ_ERROR", "INVALID_IMAGE", "UNSUPPORTED_IMAGE"]
_FORMATS = frozenset({"PNG", "JPEG"})
_MODES = frozenset({"1", "L", "LA", "P", "RGB", "RGBA", "CMYK"})


class ImageInputError(Exception):
    """Expected input failure, ready to translate at an adapter boundary."""

    def __init__(self, code: InputErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, dict[str, str]]:
        """Return the error contract without encoding JSON or writing output."""
        return {"error": {"code": self.code, "message": self.message}}


def read_image(path: str | PathLike[str]) -> Image.Image:
    """Read a static PNG or JPEG and return an 8-bit-per-channel RGB image.

    Identify format from content, apply EXIF orientation, composite transparency
    on white and discard source metadata. Do not resize, crop or infer chess
    orientation. The returned image owns its pixels and keeps no file open.

    Raises:
        ImageInputError: File access failed, decoding failed, or the identified
            format, mode, animation or Pillow pixel limit is unsupported.
        TypeError: The caller did not provide a string or text path object.
    """
    file_path = Path(path)
    # Keep filesystem failures separate from decoder OSErrors. Read once so
    # verification and decoding operate on exactly the same bytes.
    try:
        content = file_path.read_bytes()
    except (OSError, ValueError) as error:
        raise ImageInputError("INPUT_READ_ERROR", "Could not read the image file.") from error
    if not content:
        raise ImageInputError("INVALID_IMAGE", "The image file is empty.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as probe:
                if probe.format not in _FORMATS:
                    raise ImageInputError(
                        "UNSUPPORTED_IMAGE", "Only static PNG and JPEG images are supported."
                    )
                # For PNG this also checks chunk checksums; open() alone only
                # identifies the header and does not validate the pixel stream.
                probe.verify()

            with Image.open(BytesIO(content)) as source:
                if getattr(source, "n_frames", 1) != 1:
                    raise ImageInputError("UNSUPPORTED_IMAGE", "Animated images are not supported.")
                if source.mode not in _MODES:
                    raise ImageInputError(
                        "UNSUPPORTED_IMAGE", f"Image mode {source.mode!r} is not supported."
                    )
                source.load()
                with ImageOps.exif_transpose(source) as oriented:
                    if "A" in oriented.getbands() or "transparency" in oriented.info:
                        with oriented.convert("RGBA") as rgba:
                            result = Image.new("RGB", rgba.size, "white")
                            result.paste(rgba, mask=rgba.getchannel("A"))
                    else:
                        result = oriented.convert("RGB")
                    result.info.clear()
                    return result
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise ImageInputError(
            "UNSUPPORTED_IMAGE", "The image exceeds the decoder's pixel limit."
        ) from error
    except (OSError, ValueError, SyntaxError, EOFError) as error:
        raise ImageInputError(
            "INVALID_IMAGE", "The file is not a valid, fully decodable image."
        ) from error
