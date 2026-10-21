using SkiaSharp;

namespace SimilarImageFinder;

/// <summary>Decodes image files into <see cref="GrayImage"/> with SkiaSharp.</summary>
public static class ImageLoader
{
    /// <summary>Loads an image file. The EXIF orientation is applied and transparency is composited on white.</summary>
    public static GrayImage Load(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        using var stream = File.OpenRead(path);
        return Load(stream);
    }

    /// <summary>Loads an encoded image from bytes.</summary>
    public static GrayImage Load(byte[] encoded)
    {
        ArgumentNullException.ThrowIfNull(encoded);
        using var stream = new MemoryStream(encoded, writable: false);
        return Load(stream);
    }

    /// <summary>Loads an encoded image from a stream. For animated images only the first frame is used.</summary>
    public static GrayImage Load(Stream stream)
    {
        ArgumentNullException.ThrowIfNull(stream);
        using var codec = SKCodec.Create(stream)
            ?? throw new InvalidDataException("Unsupported or corrupt image.");
        var info = new SKImageInfo(codec.Info.Width, codec.Info.Height, SKColorType.Rgba8888, SKAlphaType.Unpremul);
        using var bitmap = new SKBitmap(info);
        var result = codec.GetPixels(info, bitmap.GetPixels());
        if (result is not (SKCodecResult.Success or SKCodecResult.IncompleteInput))
        {
            throw new InvalidDataException($"Could not decode the image: {result}.");
        }

        var orientation = (int)codec.EncodedOrigin;
        return GrayImage.FromRgba(bitmap.GetPixelSpan(), info.Width, info.Height, bitmap.RowBytes, orientation);
    }

    /// <summary>Loads a file and computes a hash.</summary>
    public static ImageHash Hash(string path, HashMethod method = HashMethod.Perceptual, int hashSize = 8) =>
        ImageHasher.Compute(Load(path), method, hashSize);
}
