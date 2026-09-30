"""Input decoding, normalization and structured error contract."""

from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest


pytestmark = pytest.mark.unit


def read_image(path):
    from boardsnap.image_input import read_image as read

    return read(path)


def assert_error(path, code):
    from boardsnap.image_input import ImageInputError

    with pytest.raises(ImageInputError) as caught:
        read_image(path)
    error = caught.value
    assert error.code == code
    assert error.message and str(error) == error.message
    assert error.to_dict() == {"error": {"code": code, "message": error.message}}
    return error


@pytest.mark.parametrize("file_format", ["PNG", "JPEG"])
@pytest.mark.parametrize("as_string", [False, True])
def test_reads_supported_content_without_relying_on_extension(tmp_path, file_format, as_string):
    path = tmp_path / "image.unrelated"
    Image.new("RGB", (3, 2), (40, 80, 120)).save(path, format=file_format)
    original = path.read_bytes()
    result = read_image(str(path) if as_string else path)
    assert result.mode == "RGB" and result.size == (3, 2)
    assert all(abs(a - b) <= 2 for a, b in zip(result.getpixel((0, 0)), (40, 80, 120)))
    assert path.read_bytes() == original
    path.unlink()
    assert len(result.tobytes()) == 18  # Fully loaded and detached from the file.


def test_preserves_rgb_channels_and_pixel_order(tmp_path):
    path = tmp_path / "colors.png"
    image = Image.new("RGB", (2, 2))
    pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (9, 20, 31)]
    image.putdata(pixels)
    image.save(path)
    result = read_image(path)
    assert [result.getpixel((x, y)) for y in range(2) for x in range(2)] == pixels


@pytest.mark.parametrize("mode,value,expected", [
    ("1", 1, (255, 255, 255)),
    ("L", 75, (75, 75, 75)),
    ("LA", (0, 128), (127, 127, 127)),
    ("RGBA", (255, 0, 0, 0), (255, 255, 255)),
    ("RGBA", (255, 0, 0, 128), (255, 127, 127)),
])
def test_normalizes_modes_and_composites_transparency_on_white(tmp_path, mode, value, expected):
    path = tmp_path / "mode.png"
    Image.new(mode, (2, 1), value).save(path)
    result = read_image(path)
    assert result.mode == "RGB" and result.getpixel((0, 0)) == expected


def test_palette_transparency(tmp_path):
    path = tmp_path / "palette.png"
    image = Image.new("P", (2, 1))
    image.putpalette([255, 0, 0, 0, 0, 255] + [0] * 762)
    image.putdata([0, 1])
    image.save(path, transparency=0)
    result = read_image(path)
    assert result.getpixel((0, 0)) == (255, 255, 255)
    assert result.getpixel((1, 0)) == (0, 0, 255)


def test_rgb_color_key_transparency(tmp_path):
    path = tmp_path / "transparent.png"
    Image.new("RGB", (2, 1), (10, 20, 30)).save(path, transparency=(10, 20, 30))
    assert read_image(path).getpixel((0, 0)) == (255, 255, 255)


def test_cmyk_jpeg_becomes_rgb(tmp_path):
    path = tmp_path / "cmyk.jpg"
    Image.new("CMYK", (2, 2), (0, 255, 255, 0)).save(path)
    result = read_image(path)
    assert result.mode == "RGB" and result.getpixel((0, 0)) == (255, 0, 0)


@pytest.mark.parametrize("orientation,expected_size,expected_pixels", [
    (6, (1, 2), [(255, 0, 0), (0, 0, 255)]),
    (2, (2, 1), [(0, 0, 255), (255, 0, 0)]),
])
def test_applies_exif_once_without_inferring_chess_orientation(tmp_path, orientation, expected_size, expected_pixels):
    path = tmp_path / "exif.png"
    image = Image.new("RGB", (2, 1))
    image.putdata([(255, 0, 0), (0, 0, 255)])
    exif = Image.Exif()
    exif[274] = orientation
    image.save(path, exif=exif)
    result = read_image(path)
    assert result.size == expected_size
    assert [result.getpixel((x, y)) for y in range(result.height) for x in range(result.width)] == expected_pixels
    assert result.getexif().get(274) is None


def test_missing_file_is_read_error(tmp_path):
    error = assert_error(tmp_path / "missing.png", "INPUT_READ_ERROR")
    assert isinstance(error.__cause__, FileNotFoundError)


def test_directory_is_read_error(tmp_path):
    assert_error(tmp_path, "INPUT_READ_ERROR")


def test_permission_failure_is_read_error(tmp_path, monkeypatch):
    def denied(_self):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "read_bytes", denied)
    error = assert_error(tmp_path / "blocked.png", "INPUT_READ_ERROR")
    assert isinstance(error.__cause__, PermissionError)


@pytest.mark.parametrize("content", [b"", b"not an image", b"\x89PNG\r\n\x1a\n"])
def test_empty_or_unidentifiable_content_is_invalid(tmp_path, content):
    path = tmp_path / "invalid.png"
    path.write_bytes(content)
    assert_error(path, "INVALID_IMAGE")


@pytest.mark.parametrize("file_format", ["PNG", "JPEG"])
def test_truncated_image_is_decode_error_even_if_header_is_readable(tmp_path, file_format):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buffer, format=file_format)
    path = tmp_path / "truncated"
    path.write_bytes(buffer.getvalue()[:-20])
    with Image.open(path) as header:
        assert header.format == file_format
    assert_error(path, "INVALID_IMAGE")


def test_png_checksum_corruption_is_invalid(tmp_path):
    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    content = bytearray(buffer.getvalue())
    start = content.index(b"IDAT")
    content[start + 4] ^= 1
    path = tmp_path / "bad-checksum.png"
    path.write_bytes(content)
    assert_error(path, "INVALID_IMAGE")


@pytest.mark.parametrize("file_format", ["GIF", "BMP", "TIFF"])
def test_known_unsupported_formats_are_distinct_from_invalid_content(tmp_path, file_format):
    path = tmp_path / "pretends-to-be.png"
    Image.new("RGB", (2, 2)).save(path, format=file_format)
    assert_error(path, "UNSUPPORTED_IMAGE")


def test_animated_png_is_unsupported(tmp_path):
    path = tmp_path / "animated.png"
    first = Image.new("RGB", (2, 2), "red")
    second = Image.new("RGB", (2, 2), "blue")
    first.save(path, save_all=True, append_images=[second], duration=100, loop=0)
    assert_error(path, "UNSUPPORTED_IMAGE")


def test_high_bit_depth_grayscale_is_explicitly_unsupported(tmp_path):
    path = tmp_path / "depth.png"
    Image.new("I;16", (2, 2), 1000).save(path)
    assert_error(path, "UNSUPPORTED_IMAGE")


@pytest.mark.parametrize("limit", [3, 1])
def test_pixel_limit_is_structured_without_disabling_pillow_guard(tmp_path, monkeypatch, limit):
    path = tmp_path / "large.png"
    Image.new("RGB", (2, 2)).save(path)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", limit)
    assert_error(path, "UNSUPPORTED_IMAGE")
    assert Image.MAX_IMAGE_PIXELS == limit
