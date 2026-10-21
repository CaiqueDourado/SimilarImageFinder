namespace SimilarImageFinder.Tests;

/// <summary>Decoding with SkiaSharp. PNG results must equal Python's (Pillow) exactly.</summary>
public class ImageTests
{
    public static IEnumerable<object[]> Files() =>
        Golden.Root.GetProperty("files").EnumerateObject().Select(f => new object[] { f.Name });

    public static IEnumerable<object[]> Pairs() =>
        Golden.Root.GetProperty("pairs").EnumerateArray().Select((p, i) => new object[] { i });

    [Theory]
    [MemberData(nameof(Files))]
    public void PngHashesEqualPython(string name)
    {
        var e = Golden.Root.GetProperty("files").GetProperty(name);
        var image = ImageLoader.Load(Golden.ImagePath(name));
        Assert.Equal(e.GetProperty("width").GetInt32(), image.Width);
        Assert.Equal(e.GetProperty("height").GetInt32(), image.Height);
        Assert.Equal(Golden.Ints(e.GetProperty("grid16")), Golden.ToInts(image.Resize(16, 16)));
        Assert.Equal(e.GetProperty("ahash8").GetString(), ImageHasher.AverageHash(image).ToHex());
        Assert.Equal(e.GetProperty("dhash8").GetString(), ImageHasher.DifferenceHash(image).ToHex());
        Assert.Equal(e.GetProperty("phash8").GetString(), ImageHasher.PerceptualHash(image).ToHex());
        Assert.Equal(e.GetProperty("ahash16").GetString(), ImageHasher.AverageHash(image, 16).ToHex());
        Assert.Equal(e.GetProperty("dhash16").GetString(), ImageHasher.DifferenceHash(image, 16).ToHex());
        Assert.Equal(e.GetProperty("phash16").GetString(), ImageHasher.PerceptualHash(image, 16).ToHex());
        Assert.Equal(e.GetProperty("exact").GetString(), ImageHasher.ExactSignature(image));
        var bounds = Pixels.TrimBounds(image.Pixels, image.Width, image.Height);
        Assert.Equal(Golden.Ints(e.GetProperty("trim_bounds")), new[] { bounds.Top, bounds.Bottom, bounds.Left, bounds.Right });
        Assert.Equal(e.GetProperty("phash8_trim").GetString(), ImageHasher.PerceptualHash(image.Trim()).ToHex());
    }

    [Theory]
    [MemberData(nameof(Pairs))]
    public void PairsMatchPython(int index)
    {
        var p = Golden.Root.GetProperty("pairs")[index];
        var a = ImageLoader.Load(Golden.ImagePath(p.GetProperty("a").GetString()!));
        var b = ImageLoader.Load(Golden.ImagePath(p.GetProperty("b").GetString()!));
        var dhash = ImageHasher.DifferenceHash(a) - ImageHasher.DifferenceHash(b);
        var phash = ImageHasher.PerceptualHash(a) - ImageHasher.PerceptualHash(b);
        if (p.GetProperty("lossless").GetBoolean())
        {
            Assert.Equal(p.GetProperty("percentage_difference").GetDouble(), Similarity.PercentageDifference(a, b));
            Assert.Equal(p.GetProperty("bhattacharyya_distance").GetDouble(), Similarity.BhattacharyyaDistance(a, b), 12);
            Assert.Equal(p.GetProperty("dhash8_distance").GetInt32(), dhash);
            Assert.Equal(p.GetProperty("phash8_distance").GetInt32(), phash);
        }
        else
        {
            // JPEG decoders may differ by a gray level here and there: allow a small margin.
            Assert.InRange(dhash, 0, p.GetProperty("dhash8_distance").GetInt32() + 3);
            Assert.InRange(phash, 0, p.GetProperty("phash8_distance").GetInt32() + 3);
        }
    }

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    [InlineData(4)]
    [InlineData(5)]
    [InlineData(6)]
    [InlineData(7)]
    [InlineData(8)]
    public void ExifOrientationIsApplied(int orientation)
    {
        // all eight files store the same pixels; only the EXIF tag differs
        var stored = ImageLoader.Load(Golden.ImagePath("orientation-1.jpg"));
        var expected = Pixels.ApplyOrientation(stored.Pixels, stored.Width, stored.Height, orientation);
        var image = ImageLoader.Load(Golden.ImagePath($"orientation-{orientation}.jpg"));
        Assert.Equal(expected.Width, image.Width);
        Assert.Equal(expected.Height, image.Height);
        Assert.Equal(expected.Pixels, image.Pixels);
    }

    [Fact]
    public void NearDuplicatesAreCloseAndDifferentProductsFar()
    {
        var a = ImageLoader.Hash(Golden.ImagePath("product-1.png"));
        Assert.True(a - ImageLoader.Hash(Golden.ImagePath("product-1-small.png")) <= 4);
        Assert.True(a - ImageLoader.Hash(Golden.ImagePath("product-1-300-q60.jpg")) <= 4);
        Assert.True(a - ImageLoader.Hash(Golden.ImagePath("product-2.png")) >= 20);
    }

    [Fact]
    public void TrimRemovesTheWhiteMargin()
    {
        var framed = ImageLoader.Load(Golden.ImagePath("product-1-border.png")).Trim();
        var plain = ImageLoader.Load(Golden.ImagePath("product-1.png")).Trim();
        Assert.True(ImageHasher.PerceptualHash(framed) - ImageHasher.PerceptualHash(plain) <= 4);
    }
}
