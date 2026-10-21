# Contributing

Issues and pull requests are welcome in English or Portuguese.

```bash
python -m pip install ./python[test] && python -m pytest python/tests
cd dotnet && dotnet test
```

## Rules that keep both languages identical

- Change the algorithm in [spec/ALGORITHMS.md](spec/ALGORITHMS.md) first, then in **both** implementations.
- Use integer arithmetic after decoding. No floating point in resize, hashes or trim.
- Regenerate the test vectors with `python tools/make_testdata.py` and commit `testdata/`. Both test suites must pass with the new `golden.json`.
- Test images must be generated (`tools/synth.py`) or your own; never copyrighted product photos.

## Useful contributions

- Images where pHash fails (a duplicate it misses or two products it confuses), with permission to publish them.
- Benchmarks on real photo collections.
- Other decoders for .NET (ImageSharp, System.Drawing) as separate small packages.
