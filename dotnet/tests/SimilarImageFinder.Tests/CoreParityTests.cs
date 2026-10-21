using System.Text.Json;

namespace SimilarImageFinder.Tests;

/// <summary>Raw pixel cases: no decoder involved, so the results must equal Python's exactly.</summary>
public class CoreParityTests
{
    public static IEnumerable<object[]> RawCases() =>
        Golden.Root.GetProperty("raw_cases").EnumerateArray().Select((c, i) => new object[] { i });

    private static JsonElement Case(int i) => Golden.Root.GetProperty("raw_cases")[i];

    [Fact]
    public void DctTableMatches()
    {
        var table = ImageHasher.DctTable(8);
        var expected = Golden.Root.GetProperty("dct8");
        for (var k = 0; k < 8; k++)
        {
            for (var n = 0; n < 32; n++)
            {
                Assert.Equal(expected[k][n].GetInt64(), table[k, n]);
            }
        }
    }

    [Theory]
    [MemberData(nameof(RawCases))]
    public void GrayResizeOrientationAndHashes(int index)
    {
        var c = Case(index);
        int h = c.GetProperty("height").GetInt32(), w = c.GetProperty("width").GetInt32();
        var gray = Pixels.RgbaToGray(Golden.Bytes(c.GetProperty("rgba")), w, h);
        Assert.Equal(Golden.Ints(c.GetProperty("gray")), Golden.ToInts(gray));

        foreach (var r in c.GetProperty("resize").EnumerateArray())
        {
            var resized = Pixels.AreaResize(gray, w, h, r.GetProperty("width").GetInt32(), r.GetProperty("height").GetInt32());
            Assert.Equal(Golden.Ints(r.GetProperty("pixels")), Golden.ToInts(resized));
        }

        foreach (var o in c.GetProperty("orientation").EnumerateObject())
        {
            var (pixels, ow, oh) = Pixels.ApplyOrientation(gray, w, h, int.Parse(o.Name, System.Globalization.CultureInfo.InvariantCulture));
            Assert.Equal(o.Value.GetProperty("width").GetInt32(), ow);
            Assert.Equal(o.Value.GetProperty("height").GetInt32(), oh);
            Assert.Equal(Golden.Ints(o.Value.GetProperty("pixels")), Golden.ToInts(pixels));
        }

        var bounds = Pixels.TrimBounds(gray, w, h, 60);
        Assert.Equal(Golden.Ints(c.GetProperty("trim_bounds")), new[] { bounds.Top, bounds.Bottom, bounds.Left, bounds.Right });

        var image = new GrayImage(gray, w, h);
        Assert.Equal(c.GetProperty("ahash8").GetString(), ImageHasher.AverageHash(image).ToHex());
        Assert.Equal(c.GetProperty("dhash8").GetString(), ImageHasher.DifferenceHash(image).ToHex());
        Assert.Equal(c.GetProperty("phash8").GetString(), ImageHasher.PerceptualHash(image).ToHex());
        Assert.Equal(c.GetProperty("phash16").GetString(), ImageHasher.PerceptualHash(image, 16).ToHex());
        Assert.Equal(c.GetProperty("exact").GetString(), ImageHasher.ExactSignature(image));
    }

    [Fact]
    public void AreaResizeAveragesPartialPixels()
    {
        // 3 source pixels into 2 cells: (10 + 0.5*20) / 1.5 = 13.3 and (0.5*20 + 30) / 1.5 = 26.7
        Assert.Equal(new byte[] { 13, 27 }, Pixels.AreaResize(new byte[] { 10, 20, 30 }, 3, 1, 2, 1));
    }

    [Fact]
    public void TransparentPixelsBecomeWhite()
    {
        var gray = Pixels.RgbaToGray(new byte[16], 2, 2);
        Assert.All(gray, p => Assert.Equal(255, p));
    }

    [Fact]
    public void HashParseAndDistance()
    {
        var h = ImageHash.Parse("f0f0000000000001");
        Assert.Equal("f0f0000000000001", h.ToHex());
        Assert.Equal(1, h - ImageHash.Parse("f0f0000000000000"));
        Assert.Equal(new string('a', 64), ImageHash.Parse(new string('a', 64)).ToHex());
        Assert.Throws<ArgumentException>(() => h.DistanceTo(ImageHash.Parse("00")));
    }

    [Fact]
    public void LegacyDecimal() => Assert.Equal("025516", ImageHasher.LegacyDecimal("00ff10"));

    [Fact]
    public void IndexMatchesBruteForce()
    {
        var rnd = new Random(1);
        var hashes = new List<ImageHash>();
        for (var i = 0; i < 400; i++)
        {
            var bits = new bool[64];
            for (var j = 0; j < 64; j++)
            {
                bits[j] = rnd.Next(2) == 1;
            }

            hashes.Add(ImageHash.FromBits(bits));
            if (i % 10 == 0)
            {
                var near = (bool[])bits.Clone();
                near[rnd.Next(64)] ^= true;
                near[rnd.Next(64)] ^= true;
                hashes.Add(ImageHash.FromBits(near));
            }
        }

        var index = new HashIndex<int>(4);
        for (var i = 0; i < hashes.Count; i++)
        {
            index.Add(i, hashes[i]);
        }

        for (var q = 0; q < hashes.Count; q += 5)
        {
            var brute = Enumerable.Range(0, hashes.Count).Where(i => hashes[i] - hashes[q] <= 4).ToList();
            var got = index.Query(hashes[q]).Select(x => x.Key).OrderBy(i => i).ToList();
            Assert.Equal(brute, got);
        }
    }

    [Fact]
    public void FindDuplicatesGroupsTransitively()
    {
        var a = ImageHash.Parse("0f0f0f0f0f0f0f0f");
        var b = ImageHash.Parse("0f0f0f0f0f0f0f0c");
        var c = ImageHash.Parse("0f0f0f0f0f0f0f00");
        var z = ImageHash.Parse("f0f0f0f0f0f0f0f0");
        var groups = ImageGroups.FindDuplicates(new[] { ("a", a), ("b", b), ("c", c), ("z", z) }, maxDistance: 2);
        Assert.Single(groups);
        Assert.Equal(new[] { "a", "b", "c" }, groups[0]);
    }

    [Fact]
    public void FindGeneric()
    {
        var items = Enumerable.Range(0, 150).Select(i => (i, "placeholder")).Append((1, "real")).Append((2, "real"));
        var generic = ImageGroups.FindGeneric(items, 100);
        Assert.Equal(150, Assert.Single(generic).Value);
    }
}
