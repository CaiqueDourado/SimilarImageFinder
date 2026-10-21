# similar-image-finder

Find duplicate and near-duplicate images, product photos in particular: perceptual hashes (aHash, dHash, pHash), border trimming, an exact multi-index search for millions of hashes and a detector of placeholder images. Integer arithmetic throughout, so the .NET version returns the same bits.

```python
from similar_image_finder import perceptual_hash, find_duplicates

perceptual_hash("a.jpg") - perceptual_hash("b.jpg")   # Hamming distance: 0-6 = same picture
```

```bash
similar-image-finder dupes ./photos -r --method phash --max-distance 6 > groups.csv
```

Documentation, benchmark and the .NET version: https://github.com/CaiqueDourado/SimilarImageFinder
