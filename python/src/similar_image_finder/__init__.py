"""Find duplicate and near-duplicate images with perceptual hashes.

>>> from similar_image_finder import difference_hash
>>> difference_hash("photo.jpg") - difference_hash("photo-small.jpg")   # doctest: +SKIP
1
"""

from .compare import bhattacharyya_distance, percentage_difference
from .hashes import (
    ImageHash,
    average_hash,
    compute,
    difference_hash,
    exact_signature,
    legacy_decimal,
    perceptual_hash,
)
from .image import GrayImage, load_gray
from .index import HashIndex, find_duplicates, find_generic

__version__ = "0.1.0"

__all__ = [
    "GrayImage",
    "HashIndex",
    "ImageHash",
    "average_hash",
    "bhattacharyya_distance",
    "compute",
    "difference_hash",
    "exact_signature",
    "find_duplicates",
    "find_generic",
    "legacy_decimal",
    "load_gray",
    "percentage_difference",
    "perceptual_hash",
]
