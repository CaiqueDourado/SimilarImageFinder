using System.Security.Cryptography;
using System.Text;

namespace SimilarImageFinder;

/// <summary>Hash algorithms available by name.</summary>
public enum HashMethod
{
    /// <summary>aHash: bits above the mean.</summary>
    Average,

    /// <summary>dHash: horizontal gradient.</summary>
    Difference,

    /// <summary>pHash: low DCT frequencies above their median.</summary>
    Perceptual,
}

/// <summary>Image hashes: exact signature, average, difference and perceptual (DCT) hash.</summary>
public static class ImageHasher
{
    private const long DctScale = 1 << 14;

    /// <summary>aHash: shrink to hashSize x hashSize; a bit is 1 when the pixel is above the mean.</summary>
    public static ImageHash AverageHash(GrayImage image, int hashSize = 8)
    {
        CheckSize(hashSize);
        var grid = image.Resize(hashSize, hashSize);
        long sum = 0;
        foreach (var p in grid)
        {
            sum += p;
        }

        long n = hashSize * hashSize;
        var bits = new bool[grid.Length];
        for (var i = 0; i < grid.Length; i++)
        {
            bits[i] = grid[i] * n > sum;
        }

        return ImageHash.FromBits(bits);
    }

    /// <summary>dHash: shrink to (hashSize+1) x hashSize; a bit is 1 when a pixel is brighter than its left neighbour.</summary>
    public static ImageHash DifferenceHash(GrayImage image, int hashSize = 8)
    {
        CheckSize(hashSize);
        var w = hashSize + 1;
        var grid = image.Resize(w, hashSize);
        var bits = new bool[hashSize * hashSize];
        for (var r = 0; r < hashSize; r++)
        {
            for (var c = 0; c < hashSize; c++)
            {
                bits[r * hashSize + c] = grid[r * w + c + 1] > grid[r * w + c];
            }
        }

        return ImageHash.FromBits(bits);
    }

    /// <summary>
    /// pHash: shrink to (4*hashSize) squared, keep the lowest hashSize x hashSize DCT frequencies,
    /// and set a bit when the coefficient is above their median.
    /// </summary>
    public static ImageHash PerceptualHash(GrayImage image, int hashSize = 8)
    {
        CheckSize(hashSize);
        var n = 4 * hashSize;
        var grid = image.Resize(n, n);
        var c = DctTable(hashSize);

        // tmp = C * G  (hashSize x n), then low = tmp * C^T (hashSize x hashSize)
        var tmp = new long[hashSize * n];
        for (var k = 0; k < hashSize; k++)
        {
            for (var col = 0; col < n; col++)
            {
                long s = 0;
                for (var row = 0; row < n; row++)
                {
                    s += c[k, row] * grid[row * n + col];
                }

                tmp[k * n + col] = s;
            }
        }

        var low = new long[hashSize * hashSize];
        for (var k = 0; k < hashSize; k++)
        {
            for (var l = 0; l < hashSize; l++)
            {
                long s = 0;
                for (var col = 0; col < n; col++)
                {
                    s += tmp[k * n + col] * c[l, col];
                }

                low[k * hashSize + l] = s;
            }
        }

        var sorted = (long[])low.Clone();
        Array.Sort(sorted);
        var half = sorted.Length / 2;
        var twiceMedian = sorted[half - 1] + sorted[half];
        var bits = new bool[low.Length];
        for (var i = 0; i < low.Length; i++)
        {
            bits[i] = 2 * low[i] > twiceMedian;
        }

        return ImageHash.FromBits(bits);
    }

    /// <summary>Computes a hash by method.</summary>
    public static ImageHash Compute(GrayImage image, HashMethod method = HashMethod.Perceptual, int hashSize = 8) =>
        method switch
        {
            HashMethod.Average => AverageHash(image, hashSize),
            HashMethod.Difference => DifferenceHash(image, hashSize),
            HashMethod.Perceptual => PerceptualHash(image, hashSize),
            _ => throw new ArgumentOutOfRangeException(nameof(method)),
        };

    /// <summary>
    /// SHA-256 (hex) of the 16x16 grayscale grid. Equal only for the same picture at the same
    /// pixels; any resize or recompression changes it. Use a perceptual hash for near-duplicates.
    /// </summary>
    public static string ExactSignature(GrayImage image)
    {
        var grid = image.Resize(16, 16);
        return Convert.ToHexString(SHA256.HashData(grid)).ToLowerInvariant();
    }

    /// <summary>
    /// Writes a hex digest the way the 2019 pipeline stored it: each byte in decimal, concatenated.
    /// Ambiguous by design of the old format; only for comparing with old data.
    /// </summary>
    public static string LegacyDecimal(string hexDigest)
    {
        var sb = new StringBuilder();
        foreach (var b in Convert.FromHexString(hexDigest))
        {
            sb.Append(b.ToString(System.Globalization.CultureInfo.InvariantCulture));
        }

        return sb.ToString();
    }

    /// <summary>
    /// Integer DCT-II basis: round(cos(pi * (2n + 1) * k / (2N)) * 2^14) for k &lt; hashSize, n &lt; N = 4 * hashSize.
    /// </summary>
    public static long[,] DctTable(int hashSize)
    {
        CheckSize(hashSize);
        var n = 4 * hashSize;
        var table = new long[hashSize, n];
        for (var k = 0; k < hashSize; k++)
        {
            for (var i = 0; i < n; i++)
            {
                table[k, i] = (long)Math.Floor(Math.Cos(Math.PI * (2 * i + 1) * k / (2.0 * n)) * DctScale + 0.5);
            }
        }

        return table;
    }

    private static void CheckSize(int hashSize)
    {
        if (hashSize is < 2 or > 32)
        {
            throw new ArgumentOutOfRangeException(nameof(hashSize), "hashSize must be between 2 and 32.");
        }
    }
}
