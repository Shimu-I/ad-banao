import hashlib
import io
import os

import pytest
from PIL import Image

from app.domain.images import (
    MAX_PIXELS,
    ImageRejected,
    inspect_image,
    save_image,
)


def encode(image, fmt="PNG", **kwargs):
    buffer = io.BytesIO()
    image.save(buffer, fmt, **kwargs)
    return buffer.getvalue()


def noisy(size=(800, 800), mode="RGB"):
    channels = len(mode)
    return Image.frombytes(mode, size, os.urandom(size[0] * size[1] * channels))


def codes(info):
    return {w.code for w in info.warnings}


def test_good_jpeg_is_accepted_without_warnings():
    data = encode(Image.new("RGB", (800, 800), (200, 30, 30)), "JPEG")
    info = inspect_image(data)
    assert (info.width, info.height) == (800, 800)
    assert info.format == "JPEG"
    assert info.extension == ".jpg"
    assert info.sha256 == hashlib.sha256(data).hexdigest()
    assert info.size_bytes == len(data)
    assert info.warnings == ()


def test_good_png_and_webp_are_accepted():
    png = inspect_image(encode(Image.new("RGB", (700, 700)), "PNG"))
    assert png.extension == ".png"
    webp = inspect_image(encode(Image.new("RGB", (700, 700)), "WEBP"))
    assert webp.extension == ".webp"


def test_low_resolution_warns_but_is_accepted():
    info = inspect_image(encode(Image.new("RGB", (300, 300))))
    assert "low_resolution" in codes(info)


def test_min_side_is_configurable_for_logos():
    data = encode(Image.new("RGB", (100, 100)))
    assert "low_resolution" in codes(inspect_image(data))
    assert "low_resolution" not in codes(inspect_image(data, min_side=64))


def test_transparent_png_warns():
    info = inspect_image(encode(Image.new("RGBA", (800, 800), (0, 0, 0, 0))))
    assert "transparency" in codes(info)


def test_palette_png_with_transparency_warns():
    image = Image.new("P", (800, 800))
    info = inspect_image(encode(image, "PNG", transparency=0))
    assert "transparency" in codes(info)


def test_cmyk_jpeg_warns():
    info = inspect_image(encode(Image.new("CMYK", (800, 800)), "JPEG"))
    assert "cmyk" in codes(info)


def test_extreme_aspect_ratio_warns():
    info = inspect_image(encode(Image.new("RGB", (2400, 600))))
    assert "extreme_aspect" in codes(info)


def test_exif_rotation_flag_warns():
    exif = Image.Exif()
    exif[0x0112] = 6
    data = encode(Image.new("RGB", (800, 800)), "JPEG", exif=exif)
    assert "exif_rotated" in codes(inspect_image(data))


def test_animated_png_warns():
    frames = [Image.new("RGB", (700, 700), color) for color in ((255, 0, 0), (0, 255, 0))]
    data = encode(frames[0], "PNG", save_all=True, append_images=frames[1:])
    assert "animated" in codes(inspect_image(data))


def test_empty_upload_is_rejected():
    with pytest.raises(ImageRejected) as caught:
        inspect_image(b"")
    assert caught.value.code == "empty"


def test_non_image_is_rejected():
    with pytest.raises(ImageRejected) as caught:
        inspect_image(b"%PDF-1.4 this is not a picture")
    assert caught.value.code == "not_an_image"


def test_oversized_upload_is_rejected_before_decoding():
    data = encode(Image.new("RGB", (800, 800)))
    with pytest.raises(ImageRejected) as caught:
        inspect_image(data, max_bytes=100)
    assert caught.value.code == "too_large"


def test_unsupported_format_is_rejected():
    with pytest.raises(ImageRejected) as caught:
        inspect_image(encode(Image.new("RGB", (800, 800)), "GIF"))
    assert caught.value.code == "unsupported_format"


def test_too_many_pixels_is_rejected_without_decoding():
    # A 1-bit PNG compresses to a few KB, so this is cheap to build but over the limit.
    image = Image.new("1", (5000, 3300))
    assert image.size[0] * image.size[1] > MAX_PIXELS
    with pytest.raises(ImageRejected) as caught:
        inspect_image(encode(image))
    assert caught.value.code == "too_many_pixels"


def test_truncated_file_is_rejected_as_corrupt():
    data = encode(noisy(), "JPEG")
    with pytest.raises(ImageRejected) as caught:
        inspect_image(data[: len(data) // 2])
    assert caught.value.code == "corrupt"


# ----------------------------------------------------------------- saving


def test_save_image_writes_the_original_bytes_under_the_hash_name(tmp_path):
    data = encode(Image.new("RGB", (800, 800), (10, 20, 30)), "JPEG")
    info = inspect_image(data)
    relative = save_image(data, info, tmp_path, "products")
    assert relative == f"products/{info.sha256}.jpg"
    assert (tmp_path / relative).read_bytes() == data  # untouched


def test_save_image_is_idempotent_and_leaves_no_temp_files(tmp_path):
    data = encode(Image.new("RGB", (800, 800)), "PNG")
    info = inspect_image(data)
    first = save_image(data, info, tmp_path, "brands")
    second = save_image(data, info, tmp_path, "brands")
    assert first == second
    assert sorted(p.name for p in (tmp_path / "brands").iterdir()) == [f"{info.sha256}.png"]


def test_different_images_get_different_files(tmp_path):
    a = encode(Image.new("RGB", (800, 800), (1, 1, 1)))
    b = encode(Image.new("RGB", (800, 800), (2, 2, 2)))
    path_a = save_image(a, inspect_image(a), tmp_path, "products")
    path_b = save_image(b, inspect_image(b), tmp_path, "products")
    assert path_a != path_b
