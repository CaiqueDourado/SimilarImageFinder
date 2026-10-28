"""Cover image for the README (docs/img/cover.png and cover.pt-BR.png): how pHash turns a photo into 64 bits,
and what the distance between two hashes means. Every value is computed by the library.

    python docs/make_cover.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import similar_image_finder as sif  # noqa: E402
from similar_image_finder.hashes import dct_table  # noqa: E402
from synth import product_image  # noqa: E402

OUT = ROOT / "docs" / "img"
INK, MUTED, LINE, BG = "#111111", "#5c5c5c", "#d9dde3", "#fdfdfc"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
for family in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(family, fallback_to_default=False)
        plt.rcParams["font.family"] = family
        break
    except ValueError:
        continue

T = {
    "": dict(langs="Python · .NET\nsame bits", tag="Find the same product photo across stores,\neven resized or recompressed",
             steps=["photo", "gray 32×32", "DCT, 8×8 low\nfrequencies", "above the\nmedian = 1"],
             pairs="distance between two hashes (bits that differ, of 64)",
             same="same photo, 1000 px → 300 px JPEG", other="a different product",
             same_v="same picture", other_v="different",
             sha="SHA-256 of the two files: completely different",
             foot="aHash · dHash · pHash · border trim · index for millions of hashes · placeholder detector"),
    ".pt-BR": dict(langs="Python · .NET\nmesmos bits", tag="Ache a mesma foto de produto entre lojas,\nmesmo redimensionada ou recomprimida",
                   steps=["foto", "cinza 32×32", "DCT, 8×8\nfrequências baixas", "acima da\nmediana = 1"],
                   pairs="distância entre dois hashes (bits diferentes, de 64)",
                   same="mesma foto, 1000 px → JPEG de 300 px", other="outro produto",
                   same_v="mesma imagem", other_v="diferente",
                   sha="SHA-256 dos dois arquivos: totalmente diferentes",
                   foot="aHash · dHash · pHash · corte de borda · índice para milhões de hashes · detector de \"sem foto\""),
}


def jpeg(img: Image.Image, size: int, quality: int) -> Image.Image:
    buf = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(buf, "JPEG", quality=quality)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def main() -> None:
    photo = product_image(1, 1000)
    small = jpeg(photo, 300, 70)
    other = product_image(7, 1000)
    g = sif.load_gray(photo)
    grid = g.resize(32, 32).astype(np.int64)
    c = dct_table(8)
    low = c @ grid @ c.T
    h = sif.perceptual_hash(g)
    bits = np.array([int(b) for b in format(h.value, "064b")]).reshape(8, 8)
    h_small, h_other = sif.perceptual_hash(sif.load_gray(small)), sif.perceptual_hash(sif.load_gray(other))
    d_same, d_other = h - h_small, h - h_other

    OUT.mkdir(parents=True, exist_ok=True)
    for suf, t in T.items():
        fig = plt.figure(figsize=(12, 6.3), dpi=110)
        fig.patch.set_facecolor(BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 63)
        ax.axis("off")
        ax.add_patch(FancyBboxPatch((4, 52), 7, 7, boxstyle="round,pad=0,rounding_size=1.6", fc=BLUE, ec="none"))
        ax.text(7.5, 55.5, "≈", color="white", fontsize=24, weight="bold", ha="center", va="center")
        ax.text(13.5, 55.5, "SimilarImageFinder", fontsize=24, weight="bold", color=INK, va="center")
        ax.text(4, 46.2, t["tag"], fontsize=12.5, color=INK, va="center", linespacing=1.3)
        ax.text(116, 55.5, t["langs"], fontsize=10, color=MUTED, ha="right", va="center",
                linespacing=1.3)

        # the four steps
        xs = [4, 32, 60, 88]
        for i, (x, lab) in enumerate(zip(xs, t["steps"])):
            sub = fig.add_axes([x / 120, 15.5 / 63, 21 / 120, 0.31])
            sub.set_xticks([])
            sub.set_yticks([])
            for sp in sub.spines.values():
                sp.set_color(LINE)
            if i == 0:
                sub.imshow(photo)
            elif i == 1:
                sub.imshow(grid, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            elif i == 2:
                sub.imshow(np.sign(low) * np.log1p(np.abs(low)), cmap="RdBu_r", interpolation="nearest")
            else:
                sub.imshow(bits, cmap="Greys", vmin=0, vmax=1.4, interpolation="nearest")
                for (r, col), v in np.ndenumerate(bits):
                    sub.text(col, r, str(v), ha="center", va="center", fontsize=7, color="white" if v else "#444444")
            ax.text(x, 13.2, f"{i + 1}. {lab}", fontsize=10, weight="bold", color=INK, va="top", linespacing=1.15)
            if i < 3:
                ax.text(x + 24.4, 25.5, "→", fontsize=22, color=BLUE, ha="center", va="center")
        ax.text(88, 39.2, h.to_hex(), family="DejaVu Sans Mono", fontsize=10.5, color=INK)

        # what the distance means
        ax.plot([4, 116], [6.6, 6.6], color=LINE, lw=1)
        ax.text(4, 4.2, f"{t['same']}:", fontsize=9.6, color=INK, va="center")
        ax.text(43, 4.2, f"{d_same}  → {t['same_v']}", fontsize=9.6, color=AQUA, weight="bold", va="center")
        ax.text(68, 4.2, f"{t['other']}:", fontsize=9.6, color=INK, va="center")
        ax.text(68 + 1.05 * len(t["other"]) + 2.5, 4.2, f"{d_other}  → {t['other_v']}", fontsize=9.6, color=ORANGE,
                weight="bold", va="center")
        ax.text(4, 1.5, t["sha"] + "   ·   " + t["foot"], fontsize=7.8, color=MUTED, va="center")
        fig.savefig(OUT / f"cover{suf}.png", facecolor=BG)
        plt.close(fig)
    print("ok", d_same, d_other)


if __name__ == "__main__":
    main()
