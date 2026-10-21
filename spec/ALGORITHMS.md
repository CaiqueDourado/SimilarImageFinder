# Algorithms

Both implementations follow this document step by step. Every step after decoding uses integer
arithmetic, so the same decoded pixels give the same hashes in Python and .NET, bit for bit.
`testdata/golden.json` holds the expected values and both test suites check them.

## 1. Decode

- Python: Pillow. .NET: SkiaSharp (`SimilarImageFinder.SkiaSharp`), or any decoder that gives
  RGBA bytes to `GrayImage.FromRgba`.
- Pixels are 8-bit RGBA, not premultiplied. For animated images, the first frame.
- Lossless formats (PNG, GIF, BMP) decode to the same pixels in both. JPEG decoders may differ by
  one gray level in a few pixels, so JPEG hashes can differ by a bit or two across languages.

## 2. Transparency and gray

For each pixel, with `a` the alpha:

```
c' = (c * a + 255 * (255 - a) + 127) // 255        for c in R, G, B   (composite on white)
Y  = (299 * R' + 587 * G' + 114 * B' + 500) // 1000                     (ITU-R BT.601 luma)
```

## 3. Orientation

The EXIF orientation tag (1–8) is applied after the gray conversion, so the image is upright
as a viewer would show it. With `h`, `w` the stored size, output pixel `(r, c)` comes from:

| Tag | Source pixel | Output size |
|---|---|---|
| 1 | `(r, c)` | `h × w` |
| 2 | `(r, w-1-c)` | `h × w` |
| 3 | `(h-1-r, w-1-c)` | `h × w` |
| 4 | `(h-1-r, c)` | `h × w` |
| 5 | `(c, r)` | `w × h` |
| 6 | `(h-1-c, r)` | `w × h` |
| 7 | `(h-1-c, w-1-r)` | `w × h` |
| 8 | `(c, w-1-r)` | `w × h` |

## 4. Trim (optional)

`trim(tolerance = 10)`: the background is the top-left pixel. Keep the bounding box of the pixels
whose gray level differs from it by more than `tolerance`. If no pixel differs, keep the whole image.

## 5. Area-average resize

Shrinking a `W × H` image to `w × h`: each output pixel is the average of the source area it
covers, partially covered source pixels weighted by the covered fraction. Separable, exact:

1. Put source pixel `x` on `[x·w, (x+1)·w)` and output cell `i` on `[i·W, (i+1)·W)`. All
   overlaps are integers. With `P(t) = w · Σ_{x < t div w} v[x] + (t mod w) · v[t div w]`,
   the horizontal sum is `S[i] = P((i+1)·W) − P(i·W)`.
2. Repeat on the columns of `S` with `h` and `H`.
3. The output is `(2·T + W·H) // (2·W·H)`, where `T` is the double sum (round half up).

Every value fits in a signed 64-bit integer for images up to about 10⁷ × 10⁷ pixels.

## 6. Hashes

The hash bits are read row by row; the first bit is the most significant bit of the
hexadecimal form. `n = hash_size` (default 8, so 64-bit hashes).

| Hash | Grid | Bit is 1 when |
|---|---|---|
| aHash | `n × n` | `pixel · n² > Σ pixels` (above the mean) |
| dHash | `(n+1)` wide, `n` high | the pixel to the right is brighter |
| pHash | `4n × 4n` | the DCT coefficient is above the median of the `n × n` lowest ones |

pHash uses an integer DCT-II basis `C[k][j] = floor(cos(π·(2j+1)·k / (2N)) · 2¹⁴ + 0.5)` with
`N = 4n`, `k < n`, `j < N`. The low frequencies are `L = C · G · Cᵀ` (64-bit integers). The
median of the `n²` values `m₁ ≤ … ≤ m_{n²}` is compared as `2·L > m_{n²/2} + m_{n²/2+1}`.
The DC coefficient is included, as in the common pHash definition.

**Exact signature:** SHA-256 of the 256 bytes of the `16 × 16` grid, in hexadecimal. It only
matches the same pixels; see the README for why.

## 7. Comparisons

- **Hamming distance:** number of differing bits.
- **Percentage difference:** share of the 256 cells of the `16 × 16` grids whose values differ
  by more than `threshold` (default 3).
- **Bhattacharyya distance:** with `a`, `b` the grids and `Sa`, `Sb` their sums,
  `BC = Σ √(aᵢ·bᵢ) / √(Sa·Sb)` and the distance is `√max(0, 1 − BC)` (0 when both sums are 0,
  1 when only one is). Floating point: equal across languages to about 1e-12.

## 8. Index (multi-index hashing)

For `b`-bit hashes and a search radius `r`:

1. Cut the bits into `m = max(1, b div 16)` bands; band `i` covers bits `[i·b div m, (i+1)·b div m)`.
2. If two hashes differ in at most `r` bits, at least one band differs in at most `r div m` bits.
3. Each band value is stored in a table. A query looks up, in every band, all values within
   `r div m` bits of its own (enumerated as XOR masks), then checks the candidates bit by bit.

The search is exact. Duplicate groups are the connected components (single linkage) of the
graph "within `r` bits", numbered in insertion order.

## 9. Generic images

A signature (exact or hash) attached to at least `min_owners` distinct owners (default 100) is
reported as generic: a placeholder or a logo, not evidence that the products are the same.
