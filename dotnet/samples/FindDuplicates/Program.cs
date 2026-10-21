// Groups near-duplicate images in a folder and prints CSV: group,path
// Usage: dotnet run --project dotnet/samples/FindDuplicates -- <folder> [maxDistance=6] [--trim]
using SimilarImageFinder;

if (args.Length == 0)
{
    Console.Error.WriteLine("usage: FindDuplicates <folder> [maxDistance=6] [--trim]");
    return 1;
}

var folder = args[0];
var maxDistance = args.Length > 1 && int.TryParse(args[1], out var d) ? d : 6;
var trim = args.Contains("--trim");
string[] extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"];

var items = new List<(string Path, ImageHash Hash)>();
foreach (var path in Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories)
             .Where(p => extensions.Contains(Path.GetExtension(p).ToLowerInvariant()))
             .Order(StringComparer.Ordinal))
{
    try
    {
        var image = ImageLoader.Load(path);
        items.Add((path, ImageHasher.PerceptualHash(trim ? image.Trim() : image)));
    }
    catch (Exception ex) when (ex is InvalidDataException or IOException)
    {
        Console.Error.WriteLine($"skip {path}: {ex.Message}");
    }
}

Console.WriteLine("group,path");
var groups = ImageGroups.FindDuplicates(items, maxDistance);
for (var i = 0; i < groups.Count; i++)
{
    foreach (var path in groups[i])
    {
        Console.WriteLine($"{i + 1},\"{path.Replace("\"", "\"\"", StringComparison.Ordinal)}\"");
    }
}

return 0;
