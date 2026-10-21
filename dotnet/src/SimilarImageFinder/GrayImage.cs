namespace SimilarImageFinder;

/// <summary>An upright grayscale image (one byte per pixel, row-major).</summary>
public sealed class GrayImage
{
    /// <summary>Creates an image from grayscale pixels.</summary>
    public GrayImage(byte[] pixels, int width, int height)
    {
        ArgumentNullException.ThrowIfNull(pixels);
        if (width < 1 || height < 1 || pixels.Length != width * height)
        {
            throw new ArgumentException("pixels.Length must equal width * height, both positive.", nameof(pixels));
        }

        Pixels = pixels;
        Width = width;
        Height = height;
    }

    /// <summary>Gray levels, row-major, <c>Width * Height</c> bytes.</summary>
    public byte[] Pixels { get; }

    /// <summary>Width in pixels.</summary>
    public int Width { get; }

    /// <summary>Height in pixels.</summary>
    public int Height { get; }

    /// <summary>
    /// Builds an image from decoded RGBA pixels (unpremultiplied). Transparency is composited
    /// on white and the EXIF <paramref name="orientation"/> (1-8) is applied.
    /// </summary>
    public static GrayImage FromRgba(ReadOnlySpan<byte> rgba, int width, int height, int rowBytes = 0, int orientation = 1)
    {
        var gray = SimilarImageFinder.Pixels.RgbaToGray(rgba, width, height, rowBytes);
        var (pixels, w, h) = SimilarImageFinder.Pixels.ApplyOrientation(gray, width, height, orientation);
        return new GrayImage(pixels, w, h);
    }

    /// <summary>Builds an image from decoded RGB pixels (row-major, no padding).</summary>
    public static GrayImage FromRgb(ReadOnlySpan<byte> rgb, int width, int height, int orientation = 1)
    {
        var gray = SimilarImageFinder.Pixels.RgbToGray(rgb, width, height);
        var (pixels, w, h) = SimilarImageFinder.Pixels.ApplyOrientation(gray, width, height, orientation);
        return new GrayImage(pixels, w, h);
    }

    /// <summary>
    /// Removes the uniform border (the colour of the top-left pixel, within <paramref name="tolerance"/>).
    /// Product photos are often the same picture with more or less white margin; trimming first
    /// makes the hashes ignore it. Returns an equal image when the image is uniform.
    /// </summary>
    public GrayImage Trim(int tolerance = 10)
    {
        var (top, bottom, left, right) = SimilarImageFinder.Pixels.TrimBounds(Pixels, Width, Height, tolerance);
        int w = right - left, h = bottom - top;
        var output = new byte[w * h];
        for (var y = 0; y < h; y++)
        {
            Array.Copy(Pixels, (top + y) * Width + left, output, y * w, w);
        }

        return new GrayImage(output, w, h);
    }

    /// <summary>Area-average resize. Returns the pixels of the resized image.</summary>
    public byte[] Resize(int width, int height) =>
        SimilarImageFinder.Pixels.AreaResize(Pixels, Width, Height, width, height);
}
