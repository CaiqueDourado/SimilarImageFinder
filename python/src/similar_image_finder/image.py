"""Loading images into a grayscale pixel grid."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Union

import numpy as np
from PIL import Image

from ._pixels import apply_orientation, area_resize, rgba_to_gray, trim_bounds

_EXIF_ORIENTATION = 0x0112


@dataclass(frozen=True)
class GrayImage:
    """An upright grayscale image: ``pixels`` is an (height, width) uint8 array."""

    pixels: np.ndarray

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])

    @classmethod
    def from_array(cls, array: np.ndarray, orientation: int = 1) -> "GrayImage":
        """Build from an (h, w) gray, (h, w, 3) RGB or (h, w, 4) RGBA uint8 array."""
        return cls(apply_orientation(rgba_to_gray(array), orientation))

    def trim(self, tolerance: int = 10) -> "GrayImage":
        """Remove the uniform border (the colour of the top-left pixel, within ``tolerance``).

        Product photos are often the same picture with more or less white margin; trimming
        first makes the hashes ignore the margin. Returns the image unchanged when it is uniform.
        """
        top, bottom, left, right = trim_bounds(self.pixels, tolerance)
        return GrayImage(np.ascontiguousarray(self.pixels[top:bottom, left:right]))

    def resize(self, width: int, height: int) -> np.ndarray:
        """Area-average resize; returns an (height, width) uint8 array."""
        return area_resize(self.pixels, width, height)


ImageSource = Union[str, os.PathLike, bytes, bytearray, Image.Image, GrayImage, np.ndarray]


def _from_pil(img: Image.Image) -> GrayImage:
    orientation = 1
    try:
        orientation = int(img.getexif().get(_EXIF_ORIENTATION, 1) or 1)
    except Exception:  # noqa: BLE001 - broken EXIF must not stop hashing
        orientation = 1
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        arr = np.asarray(img.convert("RGBA"))
    else:
        arr = np.asarray(img.convert("RGB"))
    return GrayImage.from_array(arr, orientation if 1 <= orientation <= 8 else 1)


def load_gray(source: ImageSource) -> GrayImage:
    """Decode an image (path, bytes, PIL image or array) into an upright :class:`GrayImage`.

    Transparency is composited on white and the EXIF orientation is applied.
    For animated images only the first frame is used.
    """
    if isinstance(source, GrayImage):
        return source
    if isinstance(source, np.ndarray):
        return GrayImage.from_array(source)
    if isinstance(source, Image.Image):
        return _from_pil(source)
    if isinstance(source, (bytes, bytearray)):
        with Image.open(io.BytesIO(source)) as img:
            img.load()
            return _from_pil(img)
    with Image.open(source) as img:
        img.load()
        return _from_pil(img)
