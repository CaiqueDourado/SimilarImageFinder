namespace SimilarImageFinder;

/// <summary>
/// Pixel-level steps shared by every hash: grayscale, EXIF orientation and area-average resize.
/// Integer arithmetic only, so results match the Python implementation bit for bit.
/// </summary>
public static class Pixels
{
    /// <summary>
    /// Converts 8-bit RGBA pixels (unpremultiplied, row-major) to BT.601 luma.
    /// Transparent pixels are composited on white first.
    /// </summary>
    /// <param name="rgba">Pixel bytes in R, G, B, A order.</param>
    /// <param name="width">Width in pixels.</param>
    /// <param name="height">Height in pixels.</param>
    /// <param name="rowBytes">Bytes per row; 0 means <c>width * 4</c>.</param>
    public static byte[] RgbaToGray(ReadOnlySpan<byte> rgba, int width, int height, int rowBytes = 0)
    {
        CheckSize(width, height);
        if (rowBytes == 0)
        {
            rowBytes = width * 4;
        }

        if (rowBytes < width * 4 || rgba.Length < (long)rowBytes * (height - 1) + width * 4)
        {
            throw new ArgumentException("The buffer is smaller than width * height * 4.", nameof(rgba));
        }

        var gray = new byte[width * height];
        for (var y = 0; y < height; y++)
        {
            var row = rgba.Slice(y * rowBytes, width * 4);
            for (var x = 0; x < width; x++)
            {
                long r = row[x * 4], g = row[x * 4 + 1], b = row[x * 4 + 2], a = row[x * 4 + 3];
                r = (r * a + 255 * (255 - a) + 127) / 255;
                g = (g * a + 255 * (255 - a) + 127) / 255;
                b = (b * a + 255 * (255 - a) + 127) / 255;
                gray[y * width + x] = (byte)((299 * r + 587 * g + 114 * b + 500) / 1000);
            }
        }

        return gray;
    }

    /// <summary>Converts 8-bit RGB pixels (row-major, no padding) to BT.601 luma.</summary>
    public static byte[] RgbToGray(ReadOnlySpan<byte> rgb, int width, int height)
    {
        CheckSize(width, height);
        if (rgb.Length < width * height * 3)
        {
            throw new ArgumentException("The buffer is smaller than width * height * 3.", nameof(rgb));
        }

        var gray = new byte[width * height];
        for (var i = 0; i < gray.Length; i++)
        {
            long r = rgb[i * 3], g = rgb[i * 3 + 1], b = rgb[i * 3 + 2];
            gray[i] = (byte)((299 * r + 587 * g + 114 * b + 500) / 1000);
        }

        return gray;
    }

    /// <summary>
    /// Applies an EXIF orientation (1-8) so the image is upright. Returns the new pixels and size.
    /// </summary>
    public static (byte[] Pixels, int Width, int Height) ApplyOrientation(byte[] gray, int width, int height, int orientation)
    {
        CheckSize(width, height);
        if (orientation is < 2 or > 8)
        {
            return ((byte[])gray.Clone(), width, height);
        }

        var swap = orientation >= 5;
        int ow = swap ? height : width, oh = swap ? width : height;
        var output = new byte[gray.Length];
        for (var r = 0; r < oh; r++)
        {
            for (var c = 0; c < ow; c++)
            {
                // (sr, sc) = source row and column that land on output (r, c)
                var (sr, sc) = orientation switch
                {
                    2 => (r, width - 1 - c),
                    3 => (height - 1 - r, width - 1 - c),
                    4 => (height - 1 - r, c),
                    5 => (c, r),
                    6 => (height - 1 - c, r),
                    7 => (height - 1 - c, width - 1 - r),
                    _ => (c, width - 1 - r), // 8
                };
                output[r * ow + c] = gray[sr * width + sc];
            }
        }

        return (output, ow, oh);
    }

    /// <summary>
    /// Exact area-average resize of a grayscale image, rounding half up.
    /// Each output pixel is the average of the source area it covers.
    /// </summary>
    public static byte[] AreaResize(byte[] gray, int width, int height, int targetWidth, int targetHeight)
    {
        CheckSize(width, height);
        if (targetWidth < 1 || targetHeight < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(targetWidth), "Target size must be positive.");
        }

        if (gray.Length < width * height)
        {
            throw new ArgumentException("The buffer is smaller than width * height.", nameof(gray));
        }

        // Horizontal pass: rows x targetWidth, each value <= 255 * width.
        var horizontal = new long[height * targetWidth];
        var line = new long[width];
        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                line[x] = gray[y * width + x];
            }

            ResizeLine(line, width, targetWidth, horizontal.AsSpan(y * targetWidth, targetWidth));
        }

        // Vertical pass over each output column.
        var column = new long[height];
        var resized = new long[targetHeight];
        var output = new byte[targetWidth * targetHeight];
        long total = (long)width * height;
        for (var x = 0; x < targetWidth; x++)
        {
            for (var y = 0; y < height; y++)
            {
                column[y] = horizontal[y * targetWidth + x];
            }

            ResizeLine(column, height, targetHeight, resized);
            for (var y = 0; y < targetHeight; y++)
            {
                output[y * targetWidth + x] = (byte)((2 * resized[y] + total) / (2 * total));
            }
        }

        return output;
    }

    /// <summary>
    /// Box filter on one line. Source pixel i covers [i*target, (i+1)*target) and output cell j
    /// covers [j*source, (j+1)*source) on a shared integer grid, so all overlaps are integers.
    /// Writes the weighted sums (not divided).
    /// </summary>
    private static void ResizeLine(long[] values, int source, int target, Span<long> output)
    {
        long Integral(long t, Span<long> prefixSpan)
        {
            var q = (int)(t / target);
            var r = t % target;
            var partial = q < source ? r * values[q] : 0;
            return prefixSpan[q] + partial;
        }

        Span<long> prefix = source + 1 <= 4096 ? stackalloc long[source + 1] : new long[source + 1];
        prefix[0] = 0;
        for (var i = 0; i < source; i++)
        {
            prefix[i + 1] = prefix[i] + values[i] * target;
        }

        var previous = Integral(0, prefix);
        for (var j = 0; j < target; j++)
        {
            var next = Integral((long)(j + 1) * source, prefix);
            output[j] = next - previous;
            previous = next;
        }
    }

    /// <summary>
    /// Bounding box of the pixels that differ from the background (the top-left pixel) by more
    /// than <paramref name="tolerance"/>. Bottom and Right are exclusive. Returns the whole
    /// image when nothing differs.
    /// </summary>
    public static (int Top, int Bottom, int Left, int Right) TrimBounds(byte[] gray, int width, int height, int tolerance = 10)
    {
        CheckSize(width, height);
        int background = gray[0];
        int top = height, bottom = -1, left = width, right = -1;
        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                if (Math.Abs(gray[y * width + x] - background) > tolerance)
                {
                    top = Math.Min(top, y);
                    bottom = Math.Max(bottom, y);
                    left = Math.Min(left, x);
                    right = Math.Max(right, x);
                }
            }
        }

        return bottom < 0 ? (0, height, 0, width) : (top, bottom + 1, left, right + 1);
    }

    private static void CheckSize(int width, int height)
    {
        if (width < 1 || height < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(width), "Width and height must be positive.");
        }
    }
}
