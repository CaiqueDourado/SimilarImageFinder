"""How each method does on real product photos from the 2019 catalog.

The photos are not in this repository (they belong to the stores). The numbers, the labels and a
figure with a few small thumbnails are. To rerun on the same photos, or on your own:

    python evaluation/real_photos.py FOLDER [--labels evaluation/real_photos_labels.json] [--figures]

FOLDER holds the image files. The labels file lists the pictures that appear in more than one
file (same photo, possibly resized, recompressed, saved in another format, with other margins);
every other pair of files is a pair of different pictures. Writes evaluation/real_photos.json and
evaluation/real_photos.md; with --figures also docs/img/real-photos*.png and docs/img/real-examples*.png.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

import similar_image_finder as sif  # noqa: E402

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
# (key, label, method, hash_size, trim)
METHODS = [
    ("ahash", "aHash 64", "ahash", 8, False),
    ("dhash", "dHash 64", "dhash", 8, False),
    ("phash", "pHash 64", "phash", 8, False),
    ("phash_trim", "pHash 64 + trim", "phash", 8, True),
    ("dhash16", "dHash 256", "dhash", 16, False),
    ("phash16", "pHash 256", "phash", 16, False),
    ("phash16_trim", "pHash 256 + trim", "phash", 16, True),
]


def hash_folder(folder: Path) -> dict:
    out = {}
    for path in sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTENSIONS):
        gray = sif.load_gray(path)
        trimmed = gray.trim()
        row = {"exact": sif.exact_signature(gray), "size": [gray.width, gray.height]}
        for key, _, method, size, trim in METHODS:
            row[key] = int(str(sif.compute(trimmed if trim else gray, method, size)), 16)
        out[path.name] = row
    return out


def evaluate(hashes: dict, pictures: list) -> dict:
    files = sorted(hashes)
    picture_of = {f: i for i, group in enumerate(pictures) for f in group if f in hashes}
    pairs = list(itertools.combinations(files, 2))
    same = [picture_of.get(a, -1) == picture_of.get(b, -2) for a, b in pairs]
    positives = sum(same)
    result = {
        "files": len(files),
        "pictures_with_copies": len(pictures),
        "same_picture_pairs": positives,
        "different_picture_pairs": len(pairs) - positives,
        "exact": {
            "found": sum(1 for (a, b), s in zip(pairs, same) if s and hashes[a]["exact"] == hashes[b]["exact"]),
            "false": sum(1 for (a, b), s in zip(pairs, same) if not s and hashes[a]["exact"] == hashes[b]["exact"]),
        },
        "methods": {},
    }
    for key, label, _, size, _ in METHODS:
        bits = size * size
        dist = [bin(hashes[a][key] ^ hashes[b][key]).count("1") for a, b in pairs]
        curve = []
        for t in range(bits // 4 + 1):
            found = sum(1 for d, s in zip(dist, same) if s and d <= t)
            false = sum(1 for d, s in zip(dist, same) if not s and d <= t)
            curve.append([t, found, false])
        same_d = [d for d, s in zip(dist, same) if s]
        diff_d = [d for d, s in zip(dist, same) if not s]
        result["methods"][key] = {
            "label": label, "bits": bits, "curve": curve,
            "max_same_picture": max(same_d), "min_different_picture": min(diff_d),
        }
    return result


def write_markdown(res: dict, path: Path) -> None:
    p = res["same_picture_pairs"]
    lines = [
        "# Real product photos",
        "",
        f"{res['files']} product photos from the 2019 catalog (99 product groups, mostly shoes and sandals, plus wallets and belts "
        f"on white backgrounds), as the crawler saved them: several sizes (150 to 724 px), JPEG and PNG. "
        f"{res['pictures_with_copies']} pictures appear in more than one file: {p} pairs of files that are the same picture, "
        f"and {res['different_picture_pairs']:,} pairs that are not.",
        "",
        f"Exact SHA-256 of the 16×16 grid: {res['exact']['found']} of {p} same-picture pairs found "
        f"({res['exact']['found'] / p:.1%}), {res['exact']['false']} false matches.",
        "",
        "| Method | Bits | Threshold | Same-picture pairs found | Different pictures matched | Largest distance, same picture | Smallest distance, different pictures |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, m in res["methods"].items():
        for t in ((6, 8) if m["bits"] == 64 else (20, 25)):
            _, found, false = m["curve"][t]
            lines.append(f"| {m['label']} | {m['bits']} | {t} | {found / p:.1%} | {false:,} | {m['max_same_picture']} | {m['min_different_picture']} |")
    lines += [
        "",
        "How the labels were made: candidate groups were formed with pHash 256 at 20 bits or less and every group was "
        "checked by eye; every pair between 21 and 45 bits was also checked by eye (none was the same picture: they were "
        "colour variants of one model or different models in the same pose); pairs farther apart were sampled. So the "
        "recall of pHash 256 is close to 100% partly by construction. The false matches of the other methods are pairs "
        "at least 30 bits apart in pHash 256; every one of those I looked at was two different pictures.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--labels", type=Path, default=ROOT / "evaluation" / "real_photos_labels.json")
    ap.add_argument("--figures", action="store_true")
    args = ap.parse_args()
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    hashes = hash_folder(args.folder)
    res = evaluate(hashes, labels["pictures"])
    (ROOT / "evaluation" / "real_photos.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    write_markdown(res, ROOT / "evaluation" / "real_photos.md")
    print((ROOT / "evaluation" / "real_photos.md").read_text(encoding="utf-8"))
    if args.figures:
        from real_photos_figures import draw  # noqa: E402
        draw(res, hashes, args.folder)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
