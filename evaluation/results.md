# Evaluation results

300 synthetic product photos, 11 edits each, 44,850 pairs of different products.

## Share of edited copies found (64-bit hashes)

| Edit | exact | aHash ≤6 | dHash ≤6 | pHash ≤6 | pHash + trim ≤6 | dHash + trim ≤6 | pHash + trim ≤10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| resize 50% | 3% | 100% | 100% | 100% | 100% | 100% | 100% |
| resize 25% | 0% | 100% | 99% | 100% | 99% | 100% | 100% |
| JPEG q70 | 1% | 100% | 100% | 100% | 100% | 100% | 100% |
| JPEG q30 | 0% | 100% | 100% | 100% | 99% | 100% | 100% |
| resize 50% + JPEG q60 | 0% | 100% | 100% | 100% | 86% | 96% | 99% |
| non-square resize | 11% | 100% | 100% | 100% | 100% | 100% | 100% |
| crop 5% each side | 0% | 93% | 55% | 11% | 96% | 99% | 100% |
| white border 10% | 0% | 60% | 9% | 5% | 78% | 78% | 78% |
| brightness +15% | 0% | 100% | 100% | 99% | 98% | 100% | 99% |
| watermark | 0% | 95% | 100% | 35% | 0% | 9% | 2% |
| rotate 3 degrees | 0% | 100% | 60% | 79% | 22% | 41% | 54% |
| mirror (not a duplicate) | 0% | 23% | 0% | 0% | 0% | 0% | 0% |

## Different products wrongly matched

| Method | ≤4 | ≤6 | ≤8 | ≤10 | closest pair |
|---|---:|---:|---:|---:|---:|
| exact | 0.000% | | | | |
| aHash | 2.785% | 7.650% | 18.125% | 34.165% | 0 bits |
| dHash | 0.589% | 1.920% | 4.633% | 9.365% | 0 bits |
| pHash | 0.091% | 0.223% | 0.551% | 1.037% | 2 bits |
| pHash + trim | 0.054% | 0.187% | 0.470% | 0.892% | 2 bits |
| dHash + trim | 0.923% | 2.606% | 5.543% | 10.399% | 0 bits |

## 256-bit pHash (`hash_size=16`)

| Edit | pHash 256 ≤20 | pHash 256 + trim ≤20 |
|---|---:|---:|
| resize 50% | 100% | 100% |
| resize 25% | 100% | 94% |
| JPEG q70 | 100% | 92% |
| JPEG q30 | 100% | 71% |
| resize 50% + JPEG q60 | 100% | 14% |
| non-square resize | 100% | 100% |
| crop 5% each side | 0% | 83% |
| white border 10% | 0% | 78% |
| brightness +15% | 99% | 97% |
| watermark | 0% | 0% |
| rotate 3 degrees | 4% | 0% |
| mirror (not a duplicate) | 0% | 0% |
| **different products matched** | 0.000% | 0.000% |

Run time: 141 s.
