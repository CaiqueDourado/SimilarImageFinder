"""Draw the README figures (English and Portuguese) into docs/img/.

Run after evaluate.py, from the repository root:  python evaluation/figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import similar_image_finder as sif  # noqa: E402
from similar_image_finder.hashes import dct_table  # noqa: E402
from synth import product_image  # noqa: E402

OUT = ROOT / "docs" / "img"
INK, MUTED = "#1f1f1f", "#666666"
SERIES = {"aHash": "#eb6834", "dHash": "#eda100", "pHash": "#2a78d6", "pHash + trim": "#1baf7a"}
for family in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(family, fallback_to_default=False)
        plt.rcParams["font.family"] = family
        break
    except ValueError:
        continue

TEXT = {
    "en": {
        "fp_title": "Different products wrongly matched",
        "fp_sub": "{pairs} pairs of different synthetic product photos (white backgrounds, same kinds of object)",
        "fp_x": "maximum Hamming distance accepted (bits of 64)",
        "fp_y": "pairs of different products matched",
        "fp_mark": "default in the CLI: 6 bits",
        "steps_title": "pHash: from product photo to 64 bits",
        "steps": ["1. Photo", "2. Gray, 32×32", "3. DCT: keep 8×8\nlowest frequencies", "4. Above the median = 1"],
        "subs": ["any size", "area average,\ninteger arithmetic", "coarse shape of the\nimage, not the details", "64 bits, compared by\nHamming distance"],
        "suffix": "",
    },
    "pt": {
        "fp_title": "Produtos diferentes confundidos",
        "fp_sub": "{pairs} pares de fotos sintéticas de produtos diferentes (fundo branco, mesmos tipos de objeto)",
        "fp_x": "distância de Hamming máxima aceita (bits de 64)",
        "fp_y": "pares de produtos diferentes casados",
        "fp_mark": "padrão da linha de comando: 6 bits",
        "steps_title": "pHash: da foto do produto a 64 bits",
        "steps": ["1. Foto", "2. Cinza, 32×32", "3. DCT: fica com as 8×8\nfrequências mais baixas", "4. Acima da mediana = 1"],
        "subs": ["qualquer tamanho", "média por área,\naritmética inteira", "a forma geral da\nimagem, não os detalhes", "64 bits, comparados pela\ndistância de Hamming"],
        "suffix": ".pt-BR",
    },
}


def false_positive_figure(results: dict, t: dict) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=110)
    fig.subplots_adjust(left=0.1, right=0.83, top=0.8, bottom=0.14)
    fig.text(0.1, 0.93, t["fp_title"], fontsize=17, weight="bold", color=INK)
    fig.text(0.1, 0.86, t["fp_sub"].format(pairs=f"{results['negative_pairs']:,}".replace(",", "." if t["suffix"] else ",")), fontsize=10.5, color=MUTED)
    last = 12
    nudge = {"pHash": 1.2, "pHash + trim": -1.2}
    for name, color in SERIES.items():
        curve = [p for p in results["methods"][name]["curve"] if p["threshold"] <= last]
        xs = [p["threshold"] for p in curve]
        ys = [p["false_positive_rate"] * 100 for p in curve]
        ax.plot(xs, ys, color=color, linewidth=2)
        ax.text(xs[-1] + 0.2, ys[-1] + nudge.get(name, 0), name, color=INK, fontsize=10.5, va="center")
    ax.axvline(6, color="#999999", linewidth=1, linestyle=(0, (3, 3)))
    ax.text(6.15, ax.get_ylim()[1] * 0.97, t["fp_mark"], color=MUTED, fontsize=9.5, va="top")
    ax.set_xlim(0, last)
    ax.set_ylim(0, None)
    ax.set_xticks(range(0, last + 1, 2))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", color="#e8e8e8")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(colors="#333333", labelsize=10)
    ax.set_xlabel(t["fp_x"], color=MUTED, fontsize=10.5)
    ax.set_ylabel(t["fp_y"], color=MUTED, fontsize=10.5)
    fig.savefig(OUT / f"false-matches{t['suffix']}.png", facecolor="white")
    plt.close(fig)


def steps_figure(t: dict) -> None:
    photo = product_image(1, 600)
    g = sif.load_gray(photo)
    grid = g.resize(32, 32).astype(np.int64)
    c = dct_table(8)
    low = c @ grid @ c.T
    h = sif.perceptual_hash(g)
    bits = np.array([int(b) for b in format(h.value, "064b")]).reshape(8, 8)

    fig = plt.figure(figsize=(12, 4.9), dpi=110)
    fig.text(0.025, 0.91, t["steps_title"], fontsize=18, weight="bold", color=INK)
    xs, w = [0.025, 0.27, 0.515, 0.76], 0.19
    for i, (x, title, sub) in enumerate(zip(xs, t["steps"], t["subs"])):
        ax = fig.add_axes([x, 0.33, w * 0.82, 0.5])
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color("#dddddd")
        if i == 0:
            ax.imshow(photo)
        elif i == 1:
            ax.imshow(grid, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        elif i == 2:
            ax.imshow(np.sign(low) * np.log1p(np.abs(low)), cmap="RdBu_r", interpolation="nearest")
        else:
            ax.imshow(bits, cmap="Greys", vmin=0, vmax=1.4, interpolation="nearest")
            for (r, col), v in np.ndenumerate(bits):
                ax.text(col, r, str(v), ha="center", va="center", fontsize=8, color="white" if v else "#444444")
        fig.text(x, 0.29, title, fontsize=12, weight="bold", color=INK, va="top", linespacing=1.2)
        fig.text(x, 0.03, sub, fontsize=10, color=MUTED, va="bottom")
        if i < 3:
            fig.text(x + w * 0.82 + 0.02, 0.58, "→", fontsize=24, color="#2a78d6", va="center")
    fig.text(0.76, 0.85, h.to_hex(), family="DejaVu Sans Mono", fontsize=10.5, color=INK)
    fig.savefig(OUT / f"phash-steps{t['suffix']}.png", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = json.loads((ROOT / "evaluation" / "results.json").read_text(encoding="utf-8"))
    for t in TEXT.values():
        false_positive_figure(results, t)
        steps_figure(t)
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
