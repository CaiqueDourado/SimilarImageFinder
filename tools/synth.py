"""Synthetic "product photos" for tests and the evaluation.

Every image is drawn from a seed: an object (bottle, box, lamp, ball, shoe, phone) in random
colours on a white or light background, with shading, a label and small details. No real
product photos are used, so the test data has no copyright.
"""

from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFilter

KINDS = ["bottle", "box", "lamp", "ball", "shoe", "phone"]


def _color(rng: random.Random, dark: bool = False):
    if dark:
        return tuple(rng.randint(10, 110) for _ in range(3))
    return tuple(rng.randint(20, 235) for _ in range(3))


def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def product_image(seed: int, size: int = 600) -> Image.Image:
    rng = random.Random(seed)
    bg = (255, 255, 255) if rng.random() < 0.7 else tuple(rng.randint(225, 250) for _ in range(3))
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    s = size / 600
    kind = rng.choice(KINDS)
    c1, c2 = _color(rng), _color(rng)
    cx = 300 + rng.randint(-60, 60)
    cy = 300 + rng.randint(-40, 40)
    k = rng.uniform(0.75, 1.15)

    def box(x0, y0, x1, y1):
        return [cx * s + (x0 * k) * s, cy * s + (y0 * k) * s, cx * s + (x1 * k) * s, cy * s + (y1 * k) * s]

    if kind == "bottle":
        d.rounded_rectangle(box(-70, -120, 70, 200), radius=int(40 * s * k), fill=c1)
        d.rectangle(box(-30, -200, 30, -115), fill=_shade(c1, 0.8))
        d.rectangle(box(-35, -230, 35, -195), fill=c2)
        d.rectangle(box(-70, -10, 70, 90), fill=c2)
    elif kind == "box":
        d.polygon([tuple(box(-150, -60, 0, 0)[:2]), tuple(box(60, -140, 0, 0)[:2]),
                   tuple(box(200, -60, 0, 0)[:2]), tuple(box(0, 20, 0, 0)[:2])], fill=_shade(c1, 1.15))
        d.polygon([tuple(box(-150, -60, 0, 0)[:2]), tuple(box(0, 20, 0, 0)[:2]),
                   tuple(box(0, 220, 0, 0)[:2]), tuple(box(-150, 140, 0, 0)[:2])], fill=c1)
        d.polygon([tuple(box(0, 20, 0, 0)[:2]), tuple(box(200, -60, 0, 0)[:2]),
                   tuple(box(200, 140, 0, 0)[:2]), tuple(box(0, 220, 0, 0)[:2])], fill=_shade(c1, 0.7))
        d.rectangle(box(-120, 40, -40, 80), fill=c2)
    elif kind == "lamp":
        d.line([cx * s, 0, cx * s, (cy - 120 * k) * s], fill=(40, 40, 40), width=max(1, int(8 * s)))
        d.polygon([tuple(box(0, -130, 0, 0)[:2]), tuple(box(-170, 120, 0, 0)[:2]), tuple(box(170, 120, 0, 0)[:2])], fill=c1)
        d.ellipse(box(-170, 95, 170, 150), fill=_shade(c1, 0.6))
        d.ellipse(box(-40, 120, 40, 180), fill=(255, 214, 120))
    elif kind == "ball":
        d.ellipse(box(-160, -160, 160, 160), fill=c1)
        d.ellipse(box(-100, -120, 0, -40), fill=_shade(c1, 1.4))
        d.arc(box(-160, -60, 160, 60), 0, 180, fill=c2, width=max(1, int(14 * s)))
    elif kind == "shoe":
        d.rounded_rectangle(box(-200, 20, 200, 110), radius=int(30 * s * k), fill=_shade(c1, 0.5))
        d.polygon([tuple(box(-200, 30, 0, 0)[:2]), tuple(box(-170, -110, 0, 0)[:2]), tuple(box(-20, -100, 0, 0)[:2]),
                   tuple(box(80, -20, 0, 0)[:2]), tuple(box(200, 30, 0, 0)[:2])], fill=c1)
        for i in range(4):
            d.line(box(-110 + i * 30, -90, -80 + i * 30, -40)[:4], fill=c2, width=max(1, int(6 * s)))
    else:  # phone
        d.rounded_rectangle(box(-110, -210, 110, 210), radius=int(30 * s * k), fill=_color(rng, dark=True))
        d.rounded_rectangle(box(-95, -185, 95, 185), radius=int(12 * s * k), fill=c1)
        d.rectangle(box(-95, -60, 95, 40), fill=c2)
        d.ellipse(box(-10, -205, 10, -195), fill=(20, 20, 20))

    # a small "logo" and some "text" lines, as on real product shots
    lx, ly = rng.randint(30, 140), rng.randint(30, 80)
    d.ellipse([lx * s, ly * s, (lx + 40) * s, (ly + 40) * s], fill=c2)
    for i in range(rng.randint(1, 3)):
        w = rng.randint(80, 200)
        y = 520 + i * 18
        d.rectangle([60 * s, y * s, (60 + w) * s, (y + 8) * s], fill=(90, 90, 90))
    return img.filter(ImageFilter.GaussianBlur(radius=0.6 * s))
