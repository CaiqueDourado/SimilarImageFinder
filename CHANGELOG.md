# Changelog

## 0.1.0 (2026-10-21)

First release, Python and .NET with the same results.

- Hashes: aHash, dHash, pHash (any size), exact SHA-256 signature and the 2019 decimal format.
- Loading with EXIF orientation and transparency composited on white; `trim()` for uniform borders.
- Integer area-average resize and integer DCT: identical bits across languages for the same pixels.
- `HashIndex`: exact multi-index search; duplicate groups; generic-image detector.
- Comparisons: percentage difference and Bhattacharyya distance on 16×16 grids.
- Python command line (`hash`, `dupes`) and a .NET sample.
- Shared test vectors (`testdata/golden.json`) and a benchmark on synthetic product photos.
