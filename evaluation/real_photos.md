# Real product photos

442 product photos from the 2019 catalog (99 product groups, mostly shoes and sandals, plus wallets and belts on white backgrounds), as the crawler saved them: several sizes (150 to 724 px), JPEG and PNG. 104 pictures appear in more than one file: 348 pairs of files that are the same picture, and 97,113 pairs that are not.

Exact SHA-256 of the 16×16 grid: 20 of 348 same-picture pairs found (5.7%), 0 false matches.

| Method | Bits | Threshold | Same-picture pairs found | Different pictures matched | Largest distance, same picture | Smallest distance, different pictures |
|---|---:|---:|---:|---:|---:|---:|
| aHash 64 | 64 | 6 | 100.0% | 11,719 | 2 | 0 |
| aHash 64 | 64 | 8 | 100.0% | 18,942 | 2 | 0 |
| dHash 64 | 64 | 6 | 100.0% | 1,569 | 3 | 0 |
| dHash 64 | 64 | 8 | 100.0% | 4,430 | 3 | 0 |
| pHash 64 | 64 | 6 | 100.0% | 714 | 4 | 0 |
| pHash 64 | 64 | 8 | 100.0% | 1,177 | 4 | 0 |
| pHash 64 + trim | 64 | 6 | 98.3% | 51 | 22 | 0 |
| pHash 64 + trim | 64 | 8 | 99.1% | 158 | 22 | 0 |
| dHash 256 | 256 | 20 | 100.0% | 168 | 19 | 3 |
| dHash 256 | 256 | 25 | 100.0% | 556 | 19 | 3 |
| pHash 256 | 256 | 20 | 100.0% | 0 | 14 | 30 |
| pHash 256 | 256 | 25 | 100.0% | 0 | 14 | 30 |
| pHash 256 + trim | 256 | 20 | 79.3% | 1 | 140 | 8 |
| pHash 256 + trim | 256 | 25 | 83.3% | 1 | 140 | 8 |

How the labels were made: candidate groups were formed with pHash 256 at 20 bits or less and every group was checked by eye; every pair between 21 and 45 bits was also checked by eye (none was the same picture: they were colour variants of one model or different models in the same pose); pairs farther apart were sampled. So the recall of pHash 256 is close to 100% partly by construction. The false matches of the other methods are pairs at least 30 bits apart in pHash 256; every one of those I looked at was two different pictures.
