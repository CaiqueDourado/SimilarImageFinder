"""Image hashes: exact signature, average, difference and perceptual (DCT) hash."""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache

import numpy as np

from .image import ImageSource, load_gray

DCT_SCALE = 1 << 14


class ImageHash:
    """A fixed-length bit string. ``a - b`` (or :meth:`distance`) is the Hamming distance."""

    __slots__ = ("value", "bits")

    def __init__(self, value: int, bits: int):
        if bits <= 0 or bits % 4:
            raise ValueError("bits must be a positive multiple of 4")
        if value < 0 or value >> bits:
            raise ValueError("value does not fit in the given number of bits")
        self.value = value
        self.bits = bits

    @classmethod
    def from_bits(cls, bits: np.ndarray) -> "ImageHash":
        """Build from a boolean array, first element = most significant bit."""
        flat = np.asarray(bits, dtype=bool).ravel()
        value = 0
        for b in flat:
            value = (value << 1) | int(b)
        return cls(value, flat.size)

    @classmethod
    def from_hex(cls, text: str) -> "ImageHash":
        text = text.strip().lower()
        return cls(int(text, 16), len(text) * 4)

    def to_hex(self) -> str:
        return format(self.value, f"0{self.bits // 4}x")

    def distance(self, other: "ImageHash") -> int:
        if self.bits != other.bits:
            raise ValueError(f"cannot compare a {self.bits}-bit hash with a {other.bits}-bit hash")
        return (self.value ^ other.value).bit_count()

    def __sub__(self, other: "ImageHash") -> int:
        return self.distance(other)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ImageHash) and self.bits == other.bits and self.value == other.value

    def __hash__(self) -> int:
        return hash((self.value, self.bits))

    def __str__(self) -> str:
        return self.to_hex()

    def __repr__(self) -> str:
        return f"ImageHash('{self.to_hex()}')"


def _check_size(hash_size: int) -> None:
    if hash_size < 2 or hash_size > 32:
        raise ValueError("hash_size must be between 2 and 32")


def average_hash(source: ImageSource, hash_size: int = 8) -> ImageHash:
    """aHash: shrink to hash_size x hash_size; a bit is 1 when the pixel is above the mean."""
    _check_size(hash_size)
    grid = load_gray(source).resize(hash_size, hash_size).astype(np.int64)
    n = hash_size * hash_size
    return ImageHash.from_bits(grid * n > grid.sum())


def difference_hash(source: ImageSource, hash_size: int = 8) -> ImageHash:
    """dHash: shrink to (hash_size+1) x hash_size; a bit is 1 when a pixel is brighter than its left neighbour."""
    _check_size(hash_size)
    grid = load_gray(source).resize(hash_size + 1, hash_size).astype(np.int64)
    return ImageHash.from_bits(grid[:, 1:] > grid[:, :-1])


@lru_cache(maxsize=8)
def dct_table(hash_size: int) -> np.ndarray:
    """Integer DCT-II basis: round(cos(pi * (2n + 1) * k / (2N)) * 2**14), k < hash_size, n < N = 4 * hash_size."""
    n_total = 4 * hash_size
    table = np.empty((hash_size, n_total), dtype=np.int64)
    for k in range(hash_size):
        for n in range(n_total):
            table[k, n] = int(math.floor(math.cos(math.pi * (2 * n + 1) * k / (2 * n_total)) * DCT_SCALE + 0.5))
    return table


def perceptual_hash(source: ImageSource, hash_size: int = 8) -> ImageHash:
    """pHash: shrink to 4*hash_size squared, keep the lowest hash_size x hash_size DCT
    frequencies, and set a bit when the coefficient is above their median."""
    _check_size(hash_size)
    n_total = 4 * hash_size
    grid = load_gray(source).resize(n_total, n_total).astype(np.int64)
    c = dct_table(hash_size)
    low = c @ grid @ c.T                      # (hash_size, hash_size) int64
    values = np.sort(low.ravel())
    half = values.size // 2
    twice_median = values[half - 1] + values[half]
    return ImageHash.from_bits(2 * low > twice_median)


def exact_signature(source: ImageSource) -> str:
    """SHA-256 (hex) of the 16x16 grayscale grid. Equal only for the same picture at the
    same pixels: any resize or recompression changes it. Kept for compatibility with the
    original 2019 technique; use a perceptual hash to find near-duplicates."""
    grid = load_gray(source).resize(16, 16)
    return hashlib.sha256(grid.tobytes()).hexdigest()


def legacy_decimal(hex_digest: str) -> str:
    """Write a hex digest the way the 2019 pipeline stored it: each byte in decimal, concatenated.

    The format is ambiguous (bytes 1, 23 and 12, 3 both give "123"); it exists only to compare
    with old data. Values in the 2019 catalog hashed the encoded 16x16 file, not the pixels,
    so they cannot be reproduced exactly from the original images.
    """
    return "".join(str(b) for b in bytes.fromhex(hex_digest))


METHODS = {
    "ahash": average_hash,
    "dhash": difference_hash,
    "phash": perceptual_hash,
}


def compute(source: ImageSource, method: str = "phash", hash_size: int = 8) -> ImageHash:
    """Compute a hash by name: ``ahash``, ``dhash`` or ``phash``."""
    try:
        fn = METHODS[method]
    except KeyError:
        raise ValueError(f"unknown method {method!r}; use one of {sorted(METHODS)}") from None
    return fn(source, hash_size)
