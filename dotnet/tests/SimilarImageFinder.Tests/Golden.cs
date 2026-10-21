using System.Text.Json;

namespace SimilarImageFinder.Tests;

/// <summary>Reads testdata/golden.json, written by tools/make_testdata.py (the Python implementation).</summary>
internal static class Golden
{
    public static readonly string TestData = Path.Combine(AppContext.BaseDirectory, "testdata");

    public static readonly JsonElement Root =
        JsonDocument.Parse(File.ReadAllText(Path.Combine(TestData, "golden.json"))).RootElement;

    public static string ImagePath(string name) => Path.Combine(TestData, "images", name);

    public static int[] Ints(JsonElement array) => array.EnumerateArray().Select(e => e.GetInt32()).ToArray();

    public static byte[] Bytes(JsonElement array) => array.EnumerateArray().Select(e => (byte)e.GetInt32()).ToArray();

    public static int[] ToInts(byte[] bytes) => bytes.Select(b => (int)b).ToArray();
}
