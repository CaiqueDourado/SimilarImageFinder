"""Figures for evaluation/real_photos.py (needs the photos; called with --figures)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
INK, MUTED, BAR, HIGHLIGHT, GOOD, BAD = "#1f1f1f", "#666666", "#9aa4b1", "#2a78d6", "#1a7f4e", "#b3261e"
for family in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(family, fallback_to_default=False)
        plt.rcParams["font.family"] = family
        break
    except ValueError:
        continue

# (method key, threshold) shown in the bar chart
BARS = [("ahash", 6), ("dhash", 6), ("phash", 6), ("phash_trim", 6), ("dhash16", 20), ("phash16", 20)]

# Example pairs: three that are the same picture in different files, one that is not.
SAME = [
    ("bota-montaria-paro-feminino_1_.jpg", "bota-montaria-paro-feminino_1_.png"),
    ("chinelo-masculino-freeway-maldivas-19.jpg", "chinelo-masculino-freeway-maldivas-19_1_.png"),
    ("sapatilha-feminino-tchocco-strass-40-bege-claro.png", "sapatilha-feminino-tchocco-strass_1_.png"),
]
DIFFERENT = ("kit-4-em-1-sapato-rafarillo-masculino.jpg", "sapato-masculino-pegada-couro-com-cadarco.jpg")

TEXT = {
    "en": {
        "suffix": "",
        "title": "Different pictures wrongly matched, on real product photos",
        "sub": "{pairs} pairs of different pictures · every method finds 98–100% of the {same} same-picture pairs at this threshold",
        "label": "{name}, up to {t} bits",
        "found": "{f:.0%} found",
        "ex_title": "Same picture, different files",
        "ex_sub": "Real catalog photos, shown small for illustration (removed on request)",
        "exact": "exact signature",
        "equal": "equal", "different": "different",
        "same": "same picture", "not_same": "different products",
        "bits": "{d} of {n} bits differ",
    },
    "pt": {
        "suffix": ".pt-BR",
        "title": "Imagens diferentes casadas por engano, em fotos reais de produtos",
        "sub": "{pairs} pares de imagens diferentes · todos os métodos acham 98–100% dos {same} pares da mesma imagem neste limite",
        "label": "{name}, até {t} bits",
        "found": "{f:.0%} achados",
        "ex_title": "A mesma imagem em arquivos diferentes",
        "ex_sub": "Fotos reais do catálogo, em tamanho pequeno para ilustrar (removo a pedido)",
        "exact": "assinatura exata",
        "equal": "igual", "different": "diferente",
        "same": "mesma imagem", "not_same": "produtos diferentes",
        "bits": "{d} de {n} bits diferentes",
    },
}


def _fmt(n: int, lang: str) -> str:
    return f"{n:,}".replace(",", "." if lang == "pt" else ",")


def _bars(res: dict, lang: str, t: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=110)
    fig.subplots_adjust(left=0.27, right=0.86, top=0.78, bottom=0.08)
    fig.text(0.02, 0.92, t["title"], fontsize=16, weight="bold", color=INK)
    fig.text(0.02, 0.86, t["sub"].format(pairs=_fmt(res["different_picture_pairs"], lang), same=res["same_picture_pairs"]),
             fontsize=10, color=MUTED)
    labels, values, colors, found = [], [], [], []
    for key, thr in BARS:
        m = res["methods"][key]
        _, f, false = m["curve"][thr]
        labels.append(t["label"].format(name=m["label"], t=thr))
        values.append(false)
        colors.append(HIGHLIGHT if key == "phash16" else BAR)
        found.append(f / res["same_picture_pairs"])
    ys = list(range(len(labels)))[::-1]
    ax.barh(ys, [max(v, 0.0) for v in values], height=0.62, color=colors)
    top = max(values)
    for y, v, f in zip(ys, values, found):
        ax.text(v + top * 0.01, y, f"{_fmt(v, lang)}   ·   {t['found'].format(f=f)}", va="center", fontsize=10, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=10.5, color=INK)
    ax.set_xlim(0, top * 1.05)
    ax.set_xticks([])
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False)
    fig.savefig(OUT / f"real-photos{t['suffix']}.png", facecolor="white")
    plt.close(fig)


def _thumb(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im.thumbnail((200, 200))
    return im


def _examples(hashes: dict, folder: Path, lang: str, t: dict) -> None:
    rows = [(a, b, True) for a, b in SAME] + [(DIFFERENT[0], DIFFERENT[1], False)]
    fig = plt.figure(figsize=(10, 2.1 * len(rows) + 0.9), dpi=110)
    fig.text(0.02, 1 - 0.32 / fig.get_figheight(), t["ex_title"], fontsize=16, weight="bold", color=INK)
    fig.text(0.02, 1 - 0.58 / fig.get_figheight(), t["ex_sub"], fontsize=10, color=MUTED)
    usable = 1 - 0.9 / fig.get_figheight()
    h = usable / len(rows)
    for i, (a, b, same) in enumerate(rows):
        y0 = usable - (i + 1) * h
        for j, name in enumerate((a, b)):
            ax = fig.add_axes([0.02 + j * 0.2, y0 + 0.02, 0.18, h - 0.06])
            ax.imshow(_thumb(folder / name))
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color("#dddddd")
            w, hh = hashes[name]["size"]
            ax.set_xlabel(f"{w}×{hh} · {name.rsplit('.', 1)[1].upper()} · {(folder / name).stat().st_size // 1024} KB",
                          fontsize=9, color=MUTED)
        ha, hb = hashes[a], hashes[b]
        d64 = bin(ha["phash"] ^ hb["phash"]).count("1")
        d256 = bin(ha["phash16"] ^ hb["phash16"]).count("1")
        x = 0.45
        yt = y0 + h * 0.72
        exact = t["equal"] if ha["exact"] == hb["exact"] else t["different"]
        fig.text(x, yt, f"{t['exact']}: {exact}", fontsize=10.5, color=INK)
        fig.text(x, yt - h * 0.18, f"pHash 64: {t['bits'].format(d=d64, n=64)}", fontsize=10.5,
                 color=BAD if (not same and d64 <= 6) else INK)
        fig.text(x, yt - h * 0.36, f"pHash 256: {t['bits'].format(d=d256, n=256)}", fontsize=10.5, color=INK, weight="bold")
        verdict = t["same"] if same else t["not_same"]
        fig.text(x, yt - h * 0.58, verdict, fontsize=12, weight="bold", color=GOOD if same else BAD)
    fig.savefig(OUT / f"real-examples{t['suffix']}.png", facecolor="white")
    plt.close(fig)


def draw(res: dict, hashes: dict, folder: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang, t in TEXT.items():
        _bars(res, lang, t)
        _examples(hashes, folder, lang, t)
    print("figures written to", OUT)
