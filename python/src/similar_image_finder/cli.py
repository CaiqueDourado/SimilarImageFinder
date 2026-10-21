"""Command line: ``similar-image-finder hash`` and ``similar-image-finder dupes``."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterator, List

from .hashes import METHODS, compute, exact_signature
from .image import load_gray
from .index import find_duplicates

EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}


def _files(paths: List[str], recursive: bool) -> Iterator[Path]:
    for p in map(Path, paths):
        if p.is_dir():
            pattern = "**/*" if recursive else "*"
            yield from sorted(f for f in p.glob(pattern) if f.suffix.lower() in EXTENSIONS and f.is_file())
        elif p.is_file():
            yield p


def _hash_all(files, method: str, size: int, trim: bool = False):
    for f in files:
        try:
            image = load_gray(f)
            if trim:
                image = image.trim()
            value = exact_signature(image) if method == "exact" else compute(image, method, size).to_hex()
            yield f, value
        except Exception as exc:  # noqa: BLE001 - report and keep going
            print(f"skip {f}: {exc}", file=sys.stderr)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="similar-image-finder", description="Hash images and find near-duplicates.")
    sub = parser.add_subparsers(dest="command", required=True)
    choices = sorted(METHODS) + ["exact"]

    p_hash = sub.add_parser("hash", help="print one hash per image (CSV: path,hash)")
    p_hash.add_argument("paths", nargs="+", help="files or folders")
    p_hash.add_argument("--method", choices=choices, default="phash")
    p_hash.add_argument("--size", type=int, default=8, help="hash_size (8 = 64-bit hash)")
    p_hash.add_argument("-r", "--recursive", action="store_true")
    p_hash.add_argument("--trim", action="store_true", help="remove a uniform border before hashing")

    p_dup = sub.add_parser("dupes", help="group near-duplicate images (CSV: group,path)")
    p_dup.add_argument("paths", nargs="+", help="files or folders")
    p_dup.add_argument("--method", choices=sorted(METHODS), default="phash")
    p_dup.add_argument("--size", type=int, default=8)
    p_dup.add_argument("--max-distance", type=int, default=6, help="maximum Hamming distance (default 6 of 64 bits)")
    p_dup.add_argument("-r", "--recursive", action="store_true")
    p_dup.add_argument("--trim", action="store_true", help="remove a uniform border before hashing (product photos with varying margins)")

    args = parser.parse_args(argv)
    out = csv.writer(sys.stdout, lineterminator="\n")
    files = _files(args.paths, args.recursive)

    if args.command == "hash":
        out.writerow(["path", "hash"])
        for f, value in _hash_all(files, args.method, args.size, args.trim):
            out.writerow([str(f), value])
        return 0

    from .hashes import ImageHash

    items = [(str(f), ImageHash.from_hex(v)) for f, v in _hash_all(files, args.method, args.size, args.trim)]
    out.writerow(["group", "path"])
    for i, group in enumerate(find_duplicates(items, args.max_distance), start=1):
        for path in group:
            out.writerow([i, path])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
