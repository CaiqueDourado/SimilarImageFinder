"""Golden values shared with the .NET tests (testdata/golden.json)."""

import json
from pathlib import Path

import numpy as np
import pytest

import similar_image_finder as sif
from similar_image_finder._pixels import apply_orientation, area_resize, rgba_to_gray, trim_bounds
from similar_image_finder.hashes import dct_table

TESTDATA = Path(__file__).resolve().parents[2] / "testdata"
GOLDEN = json.loads((TESTDATA / "golden.json").read_text(encoding="utf-8"))
IMAGES = TESTDATA / "images"


def test_dct_table():
    assert dct_table(8).tolist() == GOLDEN["dct8"]


@pytest.mark.parametrize("name", sorted(GOLDEN["files"]))
def test_image_hashes(name):
    expected = GOLDEN["files"][name]
    g = sif.load_gray(IMAGES / name)
    assert (g.width, g.height) == (expected["width"], expected["height"])
    assert g.resize(16, 16).ravel().tolist() == expected["grid16"]
    assert sif.average_hash(g).to_hex() == expected["ahash8"]
    assert sif.difference_hash(g).to_hex() == expected["dhash8"]
    assert sif.perceptual_hash(g).to_hex() == expected["phash8"]
    assert sif.average_hash(g, 16).to_hex() == expected["ahash16"]
    assert sif.difference_hash(g, 16).to_hex() == expected["dhash16"]
    assert sif.perceptual_hash(g, 16).to_hex() == expected["phash16"]
    assert sif.exact_signature(g) == expected["exact"]
    assert list(trim_bounds(g.pixels)) == expected["trim_bounds"]
    assert sif.perceptual_hash(g.trim()).to_hex() == expected["phash8_trim"]


@pytest.mark.parametrize("pair", GOLDEN["pairs"], ids=lambda p: f"{p['a']}~{p['b']}")
def test_pairs(pair):
    a, b = IMAGES / pair["a"], IMAGES / pair["b"]
    assert sif.percentage_difference(a, b) == pytest.approx(pair["percentage_difference"])
    assert sif.bhattacharyya_distance(a, b) == pytest.approx(pair["bhattacharyya_distance"], abs=1e-12)
    assert sif.difference_hash(a) - sif.difference_hash(b) == pair["dhash8_distance"]
    assert sif.perceptual_hash(a) - sif.perceptual_hash(b) == pair["phash8_distance"]


@pytest.mark.parametrize("case", GOLDEN["raw_cases"], ids=lambda c: f"{c['height']}x{c['width']}")
def test_raw_cases(case):
    h, w = case["height"], case["width"]
    rgba = np.array(case["rgba"], dtype=np.uint8).reshape(h, w, 4)
    gray = rgba_to_gray(rgba)
    assert gray.ravel().tolist() == case["gray"]
    for r in case["resize"]:
        assert area_resize(gray, r["width"], r["height"]).ravel().tolist() == r["pixels"]
    for k, o in case["orientation"].items():
        out = apply_orientation(gray, int(k))
        assert out.shape == (o["height"], o["width"])
        assert out.ravel().tolist() == o["pixels"]
    assert list(trim_bounds(gray, 60)) == case["trim_bounds"]
    g = sif.GrayImage(gray)
    assert sif.average_hash(g).to_hex() == case["ahash8"]
    assert sif.difference_hash(g).to_hex() == case["dhash8"]
    assert sif.perceptual_hash(g).to_hex() == case["phash8"]
    assert sif.perceptual_hash(g, 16).to_hex() == case["phash16"]
    assert sif.exact_signature(g) == case["exact"]
