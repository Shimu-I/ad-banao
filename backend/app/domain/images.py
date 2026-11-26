"""Validation and storage of uploaded product photos and logos.

The original bytes are never modified: the file is checked, fingerprinted with
SHA-256 and saved exactly as uploaded. The ad renderer later places this photo
as-is, and the integrity check compares against this fingerprint.
"""

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

# "MPO" is what many phone cameras write for ordinary JPEG photos.
ALLOWED_FORMATS = {"JPEG": ".jpg", "MPO": ".jpg", "PNG": ".png", "WEBP": ".webp"}

MAX_BYTES = 5 * 1024 * 1024
# Decoding is rejected above this many pixels to protect small free-tier servers.
MAX_PIXELS = 16_000_000
MIN_SIDE_PRODUCT = 600
MIN_SIDE_LOGO = 64
EXTREME_ASPECT = 3.0

_EXIF_ORIENTATION = 0x0112


class ImageRejected(ValueError):
    """The upload cannot be accepted. ``code`` is stable for clients and tests."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImageWarning:
    code: str
    message: str


@dataclass(frozen=True)
class ImageInfo:
    width: int
    height: int
    format: str
    extension: str
    mode: str
    size_bytes: int
    sha256: str
    warnings: tuple[ImageWarning, ...]


def inspect_image(
    data: bytes, *, min_side: int = MIN_SIDE_PRODUCT, max_bytes: int = MAX_BYTES
) -> ImageInfo:
    """Validate an upload. Raises ImageRejected, or returns info with any warnings."""
    if not data:
        raise ImageRejected("empty", "The uploaded file is empty.")
    if len(data) > max_bytes:
        raise ImageRejected(
            "too_large", f"The image is larger than {max_bytes // (1024 * 1024)} MB."
        )
    sha256 = hashlib.sha256(data).hexdigest()

    try:
        image = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError:
        raise ImageRejected("too_many_pixels", "The image has too many pixels.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ImageRejected("not_an_image", "The file is not a readable image.") from None

    with image:
        fmt = image.format or ""
        if fmt not in ALLOWED_FORMATS:
            raise ImageRejected(
                "unsupported_format", f"{fmt or 'This'} images are not supported. Use JPEG, PNG or WebP."
            )
        width, height = image.size
        if width * height > MAX_PIXELS:
            raise ImageRejected(
                "too_many_pixels",
                f"The image is {width}x{height}; the limit is {MAX_PIXELS // 1_000_000} megapixels.",
            )
        try:
            image.load()  # decode fully so truncated or corrupt files are caught now
        except (OSError, SyntaxError, ValueError):
            raise ImageRejected("corrupt", "The image file is damaged or incomplete.") from None

        warnings: list[ImageWarning] = []
        if min(width, height) < min_side:
            warnings.append(
                ImageWarning(
                    "low_resolution",
                    f"The image is {width}x{height}; at least {min_side}px on the short side is recommended.",
                )
            )
        if max(width, height) / min(width, height) > EXTREME_ASPECT:
            warnings.append(
                ImageWarning(
                    "extreme_aspect",
                    "The image is very wide or very tall and may be cropped by ad templates.",
                )
            )
        mode = image.mode
        if mode in ("RGBA", "LA") or (mode == "P" and "transparency" in image.info):
            warnings.append(
                ImageWarning(
                    "transparency",
                    "The image has a transparent background; the template background will show through.",
                )
            )
        if mode == "CMYK":
            warnings.append(
                ImageWarning("cmyk", "CMYK image: colors may shift when shown on screen.")
            )
        if getattr(image, "n_frames", 1) > 1:
            warnings.append(
                ImageWarning("animated", "The image is animated; only the first frame is used.")
            )
        try:
            orientation = image.getexif().get(_EXIF_ORIENTATION, 1)
        except Exception:  # damaged metadata must not reject an otherwise good photo
            orientation = 1
        if orientation not in (1, None):
            warnings.append(
                ImageWarning(
                    "exif_rotated",
                    "The photo carries a rotation flag; check it appears the right way up.",
                )
            )

        return ImageInfo(
            width=width,
            height=height,
            format=fmt,
            extension=ALLOWED_FORMATS[fmt],
            mode=mode,
            size_bytes=len(data),
            sha256=sha256,
            warnings=tuple(warnings),
        )


CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def save_image(data: bytes, info: ImageInfo, storage, subdir: str) -> str:
    """Store the untouched bytes under the key ``subdir/<sha256><ext>`` and return that key.

    The name comes from the content hash, never from the user's file name, so there is no
    path-traversal risk and identical uploads share one file. The key is what the database stores.
    ``storage`` is any object from ``app.storage`` (local disk or a bucket).
    """
    key = f"{subdir}/{info.sha256}{info.extension}"
    if not storage.exists(key):
        storage.put(key, data, CONTENT_TYPES[info.extension])
    return key
