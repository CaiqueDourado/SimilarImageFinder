"""How well does each method find near-duplicates, and how often does it confuse different products?

Run from the repository root:  python evaluation/evaluate.py

Data: 300 synthetic product photos (tools/synth.py) at 600x600. Each one gets 11 edits that a
store or reseller typically makes (resize, recompress, crop, add a border...). Positives are
(original, edited copy); negatives are all 44,850 pairs of different originals. Many originals
share the same kind of object (six lamps, six bottles...), so the negatives are hard: same
shape, white background, different colours and details.

Writes evaluation/results.json and evaluation/results.md.
"""

from __future__ import annotations

import io
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import similar_image_finder as sif  # noqa: E402
from synth import product_image  # noqa: E402

N_IMAGES = 300
THRESHOLDS = list(range(0, 21))


def jpeg(img: Image.Image, quality: int) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def watermark(img: Image.Image) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    w, h = out.size
    d.rectangle([w * 0.62, h * 0.88, w * 0.97, h * 0.96], fill=(30, 30, 30))
    d.rectangle([w * 0.64, h * 0.905, w * 0.95, h * 0.935], fill=(240, 240, 240))
    return out


EDITS = {
    "resize 50%": lambda im: im.resize((300, 300), Image.LANCZOS),
    "resize 25%": lambda im: im.resize((150, 150), Image.LANCZOS),
    "JPEG q70": lambda im: jpeg(im, 70),
    "JPEG q30": lambda im: jpeg(im, 30),
    "resize 50% + JPEG q60": lambda im: jpeg(im.resize((300, 300), Image.LANCZOS), 60),
    "non-square resize": lambda im: im.resize((500, 380), Image.LANCZOS),
    "crop 5% each side": lambda im: im.crop((30, 30, 570, 570)),
    "white border 10%": lambda im: ImageOps.expand(im, border=60, fill=(255, 255, 255)),
    "brightness +15%": lambda im: ImageEnhance.Brightness(im).enhance(1.15),
    "watermark": watermark,
    "rotate 3 degrees": lambda im: im.rotate(3, resample=Image.BICUBIC, fillcolor=(255, 255, 255)),
}
EXTRA = {"mirror (not a duplicate)": lambda im: ImageOps.mirror(im)}

METHODS = {
    "aHash": sif.average_hash,
    "dHash": sif.difference_hash,
    "pHash": sif.perceptual_hash,
    "pHash + trim": lambda g: sif.perceptual_hash(g.trim()),
    "dHash + trim": lambda g: sif.difference_hash(g.trim()),
}


def main() -> None:
    t0 = time.time()
    originals = [product_image(1000 + i, 600) for i in range(N_IMAGES)]
    gray = [sif.load_gray(im) for im in originals]
    hashes = {m: [fn(g) for g in gray] for m, fn in METHODS.items()}
    exact = [sif.exact_signature(g) for g in gray]

    # negatives: every pair of different originals
    neg = {m: np.array([a - b for a, b in itertools.combinations(hs, 2)]) for m, hs in hashes.items()}
    neg_exact_equal = sum(a == b for a, b in itertools.combinations(exact, 2))

    pos = {m: {} for m in METHODS}
    pos_exact = {}
    for name, edit in {**EDITS, **EXTRA}.items():
        edited = [sif.load_gray(edit(im)) for im in originals]
        for m, fn in METHODS.items():
            pos[m][name] = np.array([fn(e) - h for e, h in zip(edited, hashes[m])])
        pos_exact[name] = float(np.mean([sif.exact_signature(e) == s for e, s in zip(edited, exact)]))

    results = {
        "images": N_IMAGES,
        "negative_pairs": int(len(neg["pHash"])),
        "edits": list(EDITS),
        "exact": {"recall": pos_exact, "false_positive_rate": neg_exact_equal / len(neg["pHash"])},
        "methods": {},
    }
    for m in METHODS:
        all_pos = np.concatenate([pos[m][e] for e in EDITS])
        results["methods"][m] = {
            "curve": [
                {"threshold": t, "recall": float((all_pos <= t).mean()), "false_positive_rate": float((neg[m] <= t).mean())}
                for t in THRESHOLDS
            ],
            "by_edit": {e: {"median_distance": float(np.median(d)), "recall_at_6": float((d <= 6).mean()),
                            "recall_at_10": float((d <= 10).mean())} for e, d in pos[m].items()},
            "negatives": {"min": int(neg[m].min()), "p01": float(np.percentile(neg[m], 1)),
                          "median": float(np.median(neg[m]))},
        }
    out = Path(__file__).with_name("results.json")
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")

    lines = ["# Evaluation results", "",
             f"{N_IMAGES} synthetic product photos, {len(EDITS)} edits each, {results['negative_pairs']:,} pairs of different products.", "",
             "## Share of edited copies found (64-bit hashes)", "",
             "| Edit | exact | " + " | ".join(f"{m} ≤6" for m in METHODS) + " | pHash + trim ≤10 |", "|---|" + "---:|" * (len(METHODS) + 2)]
    for e in list(EDITS) + list(EXTRA):
        r = [f"{pos_exact[e]:.0%}"] + [f"{results['methods'][m]['by_edit'][e]['recall_at_6']:.0%}" for m in METHODS]
        r.append(f"{results['methods']['pHash + trim']['by_edit'][e]['recall_at_10']:.0%}")
        lines.append(f"| {e} | " + " | ".join(r) + " |")
    lines += ["", "## Different products wrongly matched", "", "| Method | ≤4 | ≤6 | ≤8 | ≤10 | closest pair |", "|---|---:|---:|---:|---:|---:|",
              f"| exact | {results['exact']['false_positive_rate']:.3%} | | | | |"]
    for m in METHODS:
        c = {p["threshold"]: p["false_positive_rate"] for p in results["methods"][m]["curve"]}
        lines.append(f"| {m} | {c[4]:.3%} | {c[6]:.3%} | {c[8]:.3%} | {c[10]:.3%} | {results['methods'][m]['negatives']['min']} bits |")
    # 256-bit pHash (hash_size=16), the recommendation for product photos (see real_photos.md)
    lines += ["", "## 256-bit pHash (`hash_size=16`)", "", "| Edit | pHash 256 ≤20 | pHash 256 + trim ≤20 |", "|---|---:|---:|"]
    big = {"pHash 256": lambda g: sif.perceptual_hash(g, 16), "pHash 256 + trim": lambda g: sif.perceptual_hash(g.trim(), 16)}
    big_hashes = {m: [fn(g) for g in gray] for m, fn in big.items()}
    big_rows = {e: [] for e in list(EDITS) + list(EXTRA)}
    for name, edit in {**EDITS, **EXTRA}.items():
        edited = [sif.load_gray(edit(im)) for im in originals]
        for m, fn in big.items():
            d = np.array([fn(e) - h for e, h in zip(edited, big_hashes[m])])
            big_rows[name].append(f"{(d <= 20).mean():.0%}")
    for e, r in big_rows.items():
        lines.append(f"| {e} | " + " | ".join(r) + " |")
    neg_big = {m: np.array([a - b for a, b in itertools.combinations(hs, 2)]) for m, hs in big_hashes.items()}
    lines.append("| **different products matched** | " + " | ".join(f"{(neg_big[m] <= 20).mean():.3%}" for m in big) + " |")
    lines += ["", f"Run time: {time.time() - t0:.0f} s."]
    Path(__file__).with_name("results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
