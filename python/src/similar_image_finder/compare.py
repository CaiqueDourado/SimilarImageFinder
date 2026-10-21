"""Direct comparisons of two images on their 16x16 grayscale grids.

The two measures were popularised by Jakob Krarup's ImageComparison (xnafan.net, 2012), which
the 2019 pipeline used; this is an independent reimplementation with documented rounding.
"""

from __future__ import annotations

import math

import numpy as np

from .image import ImageSource, load_gray

GRID = 16


def _grid(source: ImageSource) -> np.ndarray:
    return load_gray(source).resize(GRID, GRID).astype(np.int64)


def percentage_difference(a: ImageSource, b: ImageSource, threshold: int = 3) -> float:
    """Share (0-1) of the 256 grid cells whose gray levels differ by more than ``threshold``."""
    diff = np.abs(_grid(a) - _grid(b))
    return int((diff > threshold).sum()) / (GRID * GRID)


def bhattacharyya_distance(a: ImageSource, b: ImageSource) -> float:
    """Bhattacharyya distance (0 = same, 1 = disjoint) between the two grids seen as
    distributions of brightness over the 256 cells."""
    ga, gb = _grid(a), _grid(b)
    sa, sb = int(ga.sum()), int(gb.sum())
    if sa == 0 or sb == 0:
        return 0.0 if sa == sb else 1.0
    coefficient = 0.0
    for x, y in zip(ga.ravel().tolist(), gb.ravel().tolist()):
        coefficient += math.sqrt(x * y)
    coefficient /= math.sqrt(sa * sb)
    return math.sqrt(max(0.0, 1.0 - coefficient))
