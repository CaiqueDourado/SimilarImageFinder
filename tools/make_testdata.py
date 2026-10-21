"""Create testdata/ (images and golden.json) shared by the Python and .NET test suites.

Run from the repository root:  python tools/make_testdata.py

The golden values come from the Python implementation. The .NET tests must reproduce them
exactly for the lossless (PNG) images and for the raw pixel cases; that is the parity check.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import similar_image_finder as sif  # noqa: E402
from similar_image_finder._pixels import apply_orientation, area_resize, rgba_to_gray, trim_bounds  # noqa: E402
from similar_image_finder.hashes import dct_table  # noqa: E402
from synth import product_image  # noqa: E402

OUT = ROOT / "testdata"
IMG = OUT / "images"


def hashes_of(source) -> dict:
    g = sif.load_gray(source)
    return {
        "width": g.width,
        "height": g.height,
        "grid16": g.resize(16, 16).ravel().tolist(),
        "ahash8": sif.average_hash(g).to_hex(),
        "dhash8": sif.difference_hash(g).to_hex(),
        "phash8": sif.perceptual_hash(g).to_hex(),
        "ahash16": sif.average_hash(g, 16).to_hex(),
        "dhash16": sif.difference_hash(g, 16).to_hex(),
        "phash16": sif.perceptual_hash(g, 16).to_hex(),
        "exact": sif.exact_signature(g),
        "trim_bounds": list(trim_bounds(g.pixels)),
        "phash8_trim": sif.perceptual_hash(g.trim()).to_hex(),
    }


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    for old in IMG.glob("*"):
        old.unlink()

    # Lossless images: exact parity between Python (Pillow) and .NET (SkiaSharp) is expected.
    p1 = product_image(1, 600)
    p1.save(IMG / "product-1.png")
    p1.resize((200, 200), Image.LANCZOS).save(IMG / "product-1-small.png")
    p1.crop((0, 50, 600, 550)).resize((480, 400), Image.LANCZOS).save(IMG / "product-1-wide.png")
    product_image(2, 600).save(IMG / "product-2.png")
    from PIL import ImageOps
    ImageOps.expand(p1.resize((400, 400), Image.LANCZOS), border=(40, 90, 60, 20), fill=(255, 255, 255)).save(IMG / "product-1-border.png")
    product_image(7, 600).resize((257, 391), Image.LANCZOS).save(IMG / "product-7-odd-size.png")
    product_image(8, 300).convert("L").save(IMG / "product-8-gray.png")
    product_image(9, 300).convert("P", palette=Image.ADAPTIVE, colors=64).save(IMG / "product-9-palette.png")

    # Transparent logo: transparency must be composited on white.
    logo = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(logo)
    d.ellipse([20, 20, 220, 220], fill=(200, 30, 60, 255))
    d.rectangle([90, 60, 150, 180], fill=(255, 255, 255, 128))
    logo.save(IMG / "logo-transparent.png")
    flat = Image.new("RGB", logo.size, (255, 255, 255))
    flat.paste(logo, mask=logo.split()[3])
    flat.save(IMG / "logo-on-white.png")

    # Lossy copies: only the distance is compared across languages.
    p1.save(IMG / "product-1-q85.jpg", quality=85)
    p1.resize((300, 300), Image.LANCZOS).save(IMG / "product-1-300-q60.jpg", quality=60)

    # EXIF orientation: same JPEG pixels, different orientation tag.
    base = product_image(4, 320).crop((0, 0, 320, 240))
    for k in range(1, 9):
        exif = Image.Exif()
        exif[0x0112] = k
        base.save(IMG / f"orientation-{k}.jpg", quality=92, exif=exif.tobytes())

    golden: dict = {"generator": "tools/make_testdata.py", "dct8": dct_table(8).tolist(), "files": {}, "pairs": []}
    for f in sorted(IMG.glob("*.png")):
        golden["files"][f.name] = hashes_of(f)
    pairs = [
        ("product-1.png", "product-1-small.png"),
        ("product-1.png", "product-1-wide.png"),
        ("product-1.png", "product-2.png"),
        ("logo-transparent.png", "logo-on-white.png"),
        ("product-1.png", "product-1-q85.jpg"),
        ("product-1.png", "product-1-300-q60.jpg"),
    ]
    for a, b in pairs:
        pa, pb = IMG / a, IMG / b
        golden["pairs"].append({
            "a": a,
            "b": b,
            "percentage_difference": sif.percentage_difference(pa, pb),
            "bhattacharyya_distance": sif.bhattacharyya_distance(pa, pb),
            "dhash8_distance": sif.difference_hash(pa) - sif.difference_hash(pb),
            "phash8_distance": sif.perceptual_hash(pa) - sif.perceptual_hash(pb),
            "lossless": a.endswith(".png") and b.endswith(".png"),
        })

    # Raw pixel cases: no image decoder involved, so both languages must match exactly.
    rng = random.Random(2026)
    cases = []
    shapes = [(1, 1), (3, 2), (17, 16), (9, 8), (31, 33), (64, 48), (5, 120), (300, 7)]
    for h, w in shapes:
        rgba = np.array([[[rng.randrange(256) for _ in range(4)] for _ in range(w)] for _ in range(h)], dtype=np.uint8)
        gray = rgba_to_gray(rgba)
        case = {
            "height": h,
            "width": w,
            "rgba": rgba.ravel().tolist(),
            "gray": gray.ravel().tolist(),
            "resize": [],
            "orientation": {},
        }
        for tw, th in [(16, 16), (9, 8), (32, 32), (3, 5), (40, 25)]:
            case["resize"].append({"width": tw, "height": th, "pixels": area_resize(gray, tw, th).ravel().tolist()})
        for k in range(1, 9):
            o = apply_orientation(gray, k)
            case["orientation"][str(k)] = {"height": int(o.shape[0]), "width": int(o.shape[1]), "pixels": o.ravel().tolist()}
        g = sif.GrayImage(gray)
        case["trim_bounds"] = list(trim_bounds(gray, 60))
        case.update({
            "ahash8": sif.average_hash(g).to_hex(),
            "dhash8": sif.difference_hash(g).to_hex(),
            "phash8": sif.perceptual_hash(g).to_hex(),
            "phash16": sif.perceptual_hash(g, 16).to_hex(),
            "exact": sif.exact_signature(g),
        })
        cases.append(case)
    golden["raw_cases"] = cases

    (OUT / "golden.json").write_text(json.dumps(golden, indent=1), encoding="utf-8")
    print(f"{len(golden['files'])} images, {len(pairs)} pairs, {len(cases)} raw cases -> {OUT / 'golden.json'}")


if __name__ == "__main__":
    main()
