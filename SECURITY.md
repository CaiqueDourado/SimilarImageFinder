# Security

Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on this repository. Do not open a public issue.

Supported versions: the latest release.

Notes for users:

- Decoding is done by Pillow (Python) and SkiaSharp (.NET). Keep them up to date: image decoders are a common attack surface.
- Pillow refuses images above its decompression-bomb limit (`Image.MAX_IMAGE_PIXELS`). Check sizes yourself before decoding untrusted files in .NET.
- `HashIndex` is not thread-safe for concurrent queries; use one index per thread or a lock.
