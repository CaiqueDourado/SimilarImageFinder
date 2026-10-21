"""Behaviour that does not depend on golden values."""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageOps

import similar_image_finder as sif
from similar_image_finder import cli
from similar_image_finder._pixels import apply_orientation, area_resize

IMAGES = Path(__file__).resolve().parents[2] / "testdata" / "images"


def test_area_resize_identity_and_mean():
    a = np.arange(48, dtype=np.uint8).reshape(6, 8)
    assert np.array_equal(area_resize(a, 8, 6), a)
    assert area_resize(a, 1, 1)[0, 0] == round(a.mean())


def test_area_resize_partial_pixels():
    # 3 source pixels into 2 cells: cell 0 = (10 + 0.5*20) / 1.5, cell 1 = (0.5*20 + 30) / 1.5
    a = np.array([[10, 20, 30]], dtype=np.uint8)
    assert area_resize(a, 2, 1).tolist() == [[13, 27]]


def test_alpha_is_composited_on_white():
    transparent = np.zeros((4, 4, 4), dtype=np.uint8)
    assert sif.GrayImage.from_array(transparent).pixels.min() == 255


@pytest.mark.parametrize("k", range(1, 9))
def test_orientation_matches_pillow(k):
    path = IMAGES / f"orientation-{k}.jpg"
    with Image.open(path) as img:
        upright = np.asarray(ImageOps.exif_transpose(img).convert("L"))
    ours = sif.load_gray(path)
    assert ours.pixels.shape == upright.shape
    # Pillow's "L" conversion rounds differently; the geometry is what matters here.
    assert np.abs(ours.pixels.astype(int) - upright.astype(int)).max() <= 1


@pytest.mark.parametrize("k", range(1, 9))
def test_orientation_is_applied_to_the_stored_pixels(k):
    # all eight files store the same pixels; only the EXIF tag differs
    stored = sif.load_gray(IMAGES / "orientation-1.jpg").pixels
    assert np.array_equal(sif.load_gray(IMAGES / f"orientation-{k}.jpg").pixels, apply_orientation(stored, k))


def test_inputs_accepted():
    path = IMAGES / "product-1.png"
    expected = sif.difference_hash(path)
    assert sif.difference_hash(str(path)) == expected
    assert sif.difference_hash(path.read_bytes()) == expected
    with Image.open(path) as img:
        assert sif.difference_hash(img) == expected
        assert sif.difference_hash(np.asarray(img.convert("RGB"))) == expected


def test_image_hash_roundtrip_and_distance():
    h = sif.ImageHash.from_hex("f0f0000000000001")
    assert h.to_hex() == "f0f0000000000001"
    assert h - sif.ImageHash.from_hex("f0f0000000000000") == 1
    with pytest.raises(ValueError):
        h - sif.ImageHash.from_hex("00")


def test_exact_signature_and_legacy_decimal():
    sig = sif.exact_signature(IMAGES / "product-1.png")
    assert len(sig) == 64
    assert sif.legacy_decimal("00ff10") == "025516"
    assert sif.exact_signature(IMAGES / "product-1.png") != sif.exact_signature(IMAGES / "product-1-small.png")


def test_near_duplicates_are_close_and_different_products_far():
    a = sif.perceptual_hash(IMAGES / "product-1.png")
    assert a - sif.perceptual_hash(IMAGES / "product-1-small.png") <= 4
    assert a - sif.perceptual_hash(IMAGES / "product-1-300-q60.jpg") <= 4
    assert a - sif.perceptual_hash(IMAGES / "product-2.png") >= 20


def test_hash_index_matches_brute_force():
    rng = np.random.default_rng(1)
    hashes = [sif.ImageHash(int(rng.integers(0, 2**63)) | (int(rng.integers(0, 2)) << 63), 64) for _ in range(300)]
    # add near copies
    for i in range(0, 300, 10):
        flipped = hashes[i].value ^ (1 << int(rng.integers(0, 64))) ^ (1 << int(rng.integers(0, 64)))
        hashes.append(sif.ImageHash(flipped, 64))
    index = sif.HashIndex(max_distance=4)
    for i, h in enumerate(hashes):
        index.add(i, h)
    for qi in range(0, len(hashes), 7):
        q = hashes[qi]
        brute = sorted((i, q - h) for i, h in enumerate(hashes) if q - h <= 4)
        got = sorted(index.query(q))
        assert got == brute


def test_find_duplicates_groups_transitively():
    base = 0x0F0F0F0F0F0F0F0F
    items = [("a", sif.ImageHash(base, 64)), ("b", sif.ImageHash(base ^ 0b11, 64)),
             ("c", sif.ImageHash(base ^ 0b1111, 64)), ("z", sif.ImageHash(~base & (2**64 - 1), 64))]
    assert sif.find_duplicates(items, max_distance=2) == [["a", "b", "c"]]


def test_find_generic():
    items = [(f"product-{i}", "placeholder") for i in range(150)] + [("product-1", "real"), ("product-2", "real")]
    assert sif.find_generic(items, min_owners=100) == {"placeholder": 150}


def test_cli(capsys, tmp_path):
    for name in ["product-1.png", "product-1-small.png", "product-2.png"]:
        (tmp_path / name).write_bytes((IMAGES / name).read_bytes())
    assert cli.main(["dupes", str(tmp_path), "--method", "phash", "--max-distance", "6"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out[0] == "group,path"
    assert len(out) == 3 and all(line.startswith("1,") for line in out[1:])
    assert cli.main(["hash", str(tmp_path / "product-1.png"), "--method", "exact"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()[1].split(",")[1]) == 64


def test_bytesio_roundtrip_png():
    img = Image.new("RGB", (50, 30), (10, 200, 30))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    assert sif.load_gray(buf.getvalue()).pixels.shape == (30, 50)


def test_trim_removes_the_white_margin():
    framed = sif.load_gray(IMAGES / "product-1-border.png")
    plain = sif.load_gray(IMAGES / "product-1.png")
    assert sif.perceptual_hash(framed.trim()) - sif.perceptual_hash(plain.trim()) <= 4
    uniform = sif.GrayImage(np.full((5, 7), 200, dtype=np.uint8))
    assert uniform.trim().pixels.shape == (5, 7)
