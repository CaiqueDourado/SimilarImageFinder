# Third-party notices

This repository does not include third-party source code.

- **Pillow** (Python, MIT-CMU license), **NumPy** (BSD-3-Clause) and **SkiaSharp** (.NET, MIT) are dependencies, installed by the package managers.
- The percentage-difference and Bhattacharyya comparisons on 16×16 grids follow the ideas of *ImageComparison* by Jakob Krarup (xnafan.net, 2012), which the author's 2019 pipeline used. The code here is an independent implementation with its own rounding rules.
- pHash follows the DCT method described by Christoph Zauner (2010) and Neal Krawetz (2011). The search index follows Norouzi, Punjani and Fleet, *Fast Search in Hamming Space with Multi-Index Hashing* (CVPR 2012).
