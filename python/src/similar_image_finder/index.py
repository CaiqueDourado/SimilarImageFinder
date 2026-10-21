"""Search among many hashes: near-duplicate index, duplicate groups and generic images."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Dict, Hashable, Iterable, List, Optional, Tuple, TypeVar

import numpy as np

from .hashes import ImageHash

K = TypeVar("K", bound=Hashable)
BAND_BITS = 16
_HAS_BITWISE_COUNT = hasattr(np, "bitwise_count")


def _flip_masks(width: int, radius: int) -> List[int]:
    """Every value with at most ``radius`` bits set among ``width`` bits (XOR masks)."""
    masks = [0]
    for r in range(1, radius + 1):
        for positions in combinations(range(width), r):
            m = 0
            for p in positions:
                m |= 1 << p
            masks.append(m)
    return masks


class HashIndex:
    """Find every stored hash within ``max_distance`` bits of a query.

    Multi-index hashing (Norouzi, Punjani and Fleet, 2012): the bits are cut into bands of about
    16 bits. If two hashes differ in at most ``r`` bits, at least one of the ``m`` bands differs
    in at most ``r // m`` bits, so each band is looked up together with its close variants and
    only those candidates are compared bit by bit. Exact: no false negatives.
    """

    def __init__(self, max_distance: int, bits: int = 64):
        if max_distance < 0 or max_distance >= bits:
            raise ValueError("max_distance must be between 0 and bits - 1")
        self.max_distance = max_distance
        self.bits = bits
        m = max(1, bits // BAND_BITS)
        self._bands = [(i * bits // m, (i + 1) * bits // m) for i in range(m)]
        radius = max_distance // m
        self._flips = [_flip_masks(end - start, radius) for start, end in self._bands]
        self._tables: List[Dict[int, List[int]]] = [defaultdict(list) for _ in self._bands]
        self._hashes: List[int] = []
        self._keys: List[List[Hashable]] = []
        self._slot_of: Dict[int, int] = {}
        self._array: Optional[np.ndarray] = None

    def __len__(self) -> int:
        return sum(len(k) for k in self._keys)

    def _band_values(self, value: int):
        for start, end in self._bands:
            yield (value >> (self.bits - end)) & ((1 << (end - start)) - 1)

    def add(self, key: Hashable, h: ImageHash) -> None:
        if h.bits != self.bits:
            raise ValueError(f"index holds {self.bits}-bit hashes, got {h.bits}")
        slot = self._slot_of.get(h.value)
        if slot is None:
            slot = len(self._hashes)
            self._slot_of[h.value] = slot
            self._hashes.append(h.value)
            self._keys.append([])
            for table, band in zip(self._tables, self._band_values(h.value)):
                table[band].append(slot)
            self._array = None
        self._keys[slot].append(key)

    def _candidates(self, value: int) -> List[int]:
        found = set()
        for table, flips, band in zip(self._tables, self._flips, self._band_values(value)):
            for mask in flips:
                slots = table.get(band ^ mask)
                if slots:
                    found.update(slots)
        return sorted(found)

    def _distances(self, value: int, slots: List[int]) -> List[int]:
        if self.bits == 64 and _HAS_BITWISE_COUNT and len(slots) > 32:
            if self._array is None:
                self._array = np.array(self._hashes, dtype=np.uint64)
            xor = self._array[np.asarray(slots, dtype=np.int64)] ^ np.uint64(value)
            return np.bitwise_count(xor).tolist()
        return [(self._hashes[s] ^ value).bit_count() for s in slots]

    def query(self, h: ImageHash, max_distance: int | None = None) -> List[Tuple[Hashable, int]]:
        """Return ``(key, distance)`` pairs within the distance, closest first."""
        if h.bits != self.bits:
            raise ValueError(f"index holds {self.bits}-bit hashes, got {h.bits}")
        limit = self.max_distance if max_distance is None else min(max_distance, self.max_distance)
        slots = self._candidates(h.value)
        found = []
        for slot, d in zip(slots, self._distances(h.value, slots)):
            if d <= limit:
                found.extend((key, d) for key in self._keys[slot])
        found.sort(key=lambda kd: kd[1])
        return found

    def groups(self) -> List[List[Hashable]]:
        """Connected groups of keys whose hashes are within ``max_distance`` (single linkage),
        in insertion order; only groups with two or more keys."""
        parent = list(range(len(self._hashes)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for slot, value in enumerate(self._hashes):
            slots = [s for s in self._candidates(value) if s > slot]
            for other, d in zip(slots, self._distances(value, slots)):
                if d <= self.max_distance:
                    ra, rb = find(slot), find(other)
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)
        members: Dict[int, List[Hashable]] = {}
        for slot in range(len(self._hashes)):
            members.setdefault(find(slot), []).extend(self._keys[slot])
        return [keys for _, keys in sorted(members.items()) if len(keys) > 1]


def find_duplicates(items: Iterable[Tuple[K, ImageHash]], max_distance: int = 6) -> List[List[K]]:
    """Group keys whose hashes are within ``max_distance`` bits (single linkage).

    ``items`` is any iterable of ``(key, hash)``; all hashes must have the same length.
    """
    index = None
    for key, h in items:
        if index is None:
            index = HashIndex(max_distance, h.bits)
        index.add(key, h)
    return [] if index is None else index.groups()


def find_generic(items: Iterable[Tuple[Hashable, object]], min_owners: int = 100) -> Dict[str, int]:
    """Signatures shared by at least ``min_owners`` distinct owners.

    ``items`` is ``(owner, signature)``, where the owner is typically a product id and the
    signature an exact signature or a hash. An image reused by hundreds of unrelated
    products is almost always a placeholder ("no photo") or a store logo, and should not be
    used as evidence that two products are the same.
    """
    owners: Dict[str, set] = defaultdict(set)
    for owner, signature in items:
        owners[str(signature)].add(owner)
    counts = {sig: len(o) for sig, o in owners.items() if len(o) >= min_owners}
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
