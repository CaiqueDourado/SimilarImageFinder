using System.Numerics;
using System.Text;

namespace SimilarImageFinder;

/// <summary>
/// A fixed-length bit string. <see cref="DistanceTo"/> (or the <c>-</c> operator) returns the
/// Hamming distance. The first bit is the most significant bit of <see cref="ToHex"/>.
/// </summary>
public sealed class ImageHash : IEquatable<ImageHash>
{
    private readonly ulong[] _words; // big-endian: _words[0] holds the first 64 bits

    private ImageHash(ulong[] words, int bits)
    {
        _words = words;
        Bits = bits;
    }

    /// <summary>Number of bits.</summary>
    public int Bits { get; }

    /// <summary>Builds a hash from booleans; the first element is the most significant bit.</summary>
    public static ImageHash FromBits(ReadOnlySpan<bool> bits)
    {
        if (bits.Length == 0 || bits.Length % 4 != 0)
        {
            throw new ArgumentException("The number of bits must be a positive multiple of 4.", nameof(bits));
        }

        var words = new ulong[(bits.Length + 63) / 64];
        var pad = words.Length * 64 - bits.Length; // leading zero bits in the first word
        for (var i = 0; i < bits.Length; i++)
        {
            if (bits[i])
            {
                var position = pad + i;
                words[position / 64] |= 1UL << (63 - position % 64);
            }
        }

        return new ImageHash(words, bits.Length);
    }

    /// <summary>Parses a hexadecimal hash (length * 4 bits).</summary>
    public static ImageHash Parse(string hex)
    {
        ArgumentNullException.ThrowIfNull(hex);
        hex = hex.Trim();
        var bits = new bool[hex.Length * 4];
        for (var i = 0; i < hex.Length; i++)
        {
            var nibble = Convert.ToInt32(hex[i].ToString(), 16);
            for (var b = 0; b < 4; b++)
            {
                bits[i * 4 + b] = (nibble & (8 >> b)) != 0;
            }
        }

        return FromBits(bits);
    }

    /// <summary>Lower-case hexadecimal, zero-padded to <c>Bits / 4</c> characters.</summary>
    public string ToHex()
    {
        var sb = new StringBuilder(_words.Length * 16);
        foreach (var w in _words)
        {
            sb.Append(w.ToString("x16"));
        }

        return sb.ToString(sb.Length - Bits / 4, Bits / 4);
    }

    /// <summary>Number of differing bits.</summary>
    public int DistanceTo(ImageHash other)
    {
        ArgumentNullException.ThrowIfNull(other);
        if (other.Bits != Bits)
        {
            throw new ArgumentException($"Cannot compare a {Bits}-bit hash with a {other.Bits}-bit hash.", nameof(other));
        }

        var d = 0;
        for (var i = 0; i < _words.Length; i++)
        {
            d += BitOperations.PopCount(_words[i] ^ other._words[i]);
        }

        return d;
    }

    /// <summary>Hamming distance.</summary>
    public static int operator -(ImageHash a, ImageHash b) => a.DistanceTo(b);

    /// <summary>Reads <paramref name="count"/> bits starting at <paramref name="start"/> (1 &lt;= count &lt;= 64).</summary>
    internal ulong Band(int start, int count)
    {
        var position = _words.Length * 64 - Bits + start;
        int word = position / 64, offset = position % 64;
        var value = (_words[word] << offset) >> (64 - count);
        if (offset + count > 64)
        {
            value |= _words[word + 1] >> (128 - offset - count);
        }

        return value;
    }

    /// <inheritdoc />
    public bool Equals(ImageHash? other) =>
        other is not null && other.Bits == Bits && _words.AsSpan().SequenceEqual(other._words);

    /// <inheritdoc />
    public override bool Equals(object? obj) => Equals(obj as ImageHash);

    /// <inheritdoc />
    public override int GetHashCode()
    {
        var h = new HashCode();
        h.Add(Bits);
        foreach (var w in _words)
        {
            h.Add(w);
        }

        return h.ToHashCode();
    }

    /// <inheritdoc />
    public override string ToString() => ToHex();
}
