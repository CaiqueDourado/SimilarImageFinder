"""Pixel-level steps shared by every hash: grayscale, EXIF orientation and area-average resize.

Everything here uses integer arithmetic so that the Python and .NET implementations give
bit-for-bit identical results for the same decoded pixels (see spec/ALGORITHMS.md).
"""

from __future__ import annotations

import numpy as np


def rgba_to_gray(rgba: np.ndarray) -> np.ndarray:
    """Convert an (h, w, 3) RGB or (h, w, 4) RGBA uint8 array to (h, w) uint8 luma.

    Transparent pixels are composited on white first, so a logo on a transparent background
    and the same logo on white get the same hash. Luma uses the ITU-R BT.601 weights.
    """
    a = np.asarray(rgba)
    if a.ndim == 2:
        return a.astype(np.uint8, copy=False)
    if a.ndim != 3 or a.shape[2] not in (3, 4):
        raise ValueError("expected an (h, w, 3) or (h, w, 4) array")
    rgb = a[..., :3].astype(np.int64)
    if a.shape[2] == 4:
        alpha = a[..., 3:4].astype(np.int64)
        rgb = (rgb * alpha + 255 * (255 - alpha) + 127) // 255
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return ((299 * r + 587 * g + 114 * b + 500) // 1000).astype(np.uint8)


def apply_orientation(gray: np.ndarray, orientation: int) -> np.ndarray:
    """Apply an EXIF orientation (1-8) so the image is upright, as a viewer would show it."""
    g = np.asarray(gray)
    if orientation == 2:
        g = g[:, ::-1]
    elif orientation == 3:
        g = g[::-1, ::-1]
    elif orientation == 4:
        g = g[::-1, :]
    elif orientation == 5:
        g = g.T
    elif orientation == 6:
        g = np.rot90(g, -1)
    elif orientation == 7:
        g = g[::-1, ::-1].T
    elif orientation == 8:
        g = np.rot90(g, 1)
    return np.ascontiguousarray(g)


def _resize_axis(values: np.ndarray, target: int) -> np.ndarray:
    """Exact box-filter resize along axis 1, returning integer sums (not yet divided).

    Source pixel x covers [x*target, (x+1)*target) and output cell i covers
    [i*source, (i+1)*source) on a common integer grid, so every overlap is an integer.
    """
    source = values.shape[1]
    weighted = values.astype(np.int64)
    prefix = np.zeros((values.shape[0], source + 1), dtype=np.int64)
    np.cumsum(weighted * target, axis=1, out=prefix[:, 1:])
    t = np.arange(target + 1, dtype=np.int64) * source
    q = t // target
    r = t % target
    partial = r[None, :] * weighted[:, np.minimum(q, source - 1)]
    integral = prefix[:, q] + partial
    return integral[:, 1:] - integral[:, :-1]


def area_resize(gray: np.ndarray, width: int, height: int) -> np.ndarray:
    """Shrink (or grow) a grayscale image with an exact area average, rounding half up.

    Each output pixel is the average of the source area it covers, weighting partially
    covered source pixels by the covered fraction. Integer-only: deterministic everywhere.
    """
    g = np.asarray(gray)
    if g.ndim != 2 or g.size == 0:
        raise ValueError("expected a non-empty (h, w) array")
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")
    sh, sw = g.shape
    horizontal = _resize_axis(g, width)                 # (sh, width), each <= 255*sw
    both = _resize_axis(horizontal.T, height).T         # (height, width), each <= 255*sw*sh
    total = sw * sh
    return ((2 * both + total) // (2 * total)).astype(np.uint8)


def trim_bounds(gray: np.ndarray, tolerance: int = 10) -> tuple[int, int, int, int]:
    """Bounding box (top, bottom, left, right; bottom/right exclusive) of the pixels that differ
    from the background by more than ``tolerance``. The background is the top-left pixel.
    Returns the whole image when nothing differs."""
    g = np.asarray(gray).astype(np.int64)
    mask = np.abs(g - g[0, 0]) > tolerance
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0:
        return 0, g.shape[0], 0, g.shape[1]
    return int(rows[0]), int(rows[-1]) + 1, int(cols[0]), int(cols[-1]) + 1
