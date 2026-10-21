namespace SimilarImageFinder;

/// <summary>
/// Direct comparisons of two images on their 16x16 grayscale grids. The measures were
/// popularised by Jakob Krarup's ImageComparison (xnafan.net, 2012); independent implementation.
/// </summary>
public static class Similarity
{
    private const int Grid = 16;

    /// <summary>Share (0-1) of the 256 grid cells whose gray levels differ by more than <paramref name="threshold"/>.</summary>
    public static double PercentageDifference(GrayImage a, GrayImage b, int threshold = 3)
    {
        var ga = a.Resize(Grid, Grid);
        var gb = b.Resize(Grid, Grid);
        var count = 0;
        for (var i = 0; i < ga.Length; i++)
        {
            if (Math.Abs(ga[i] - gb[i]) > threshold)
            {
                count++;
            }
        }

        return count / (double)(Grid * Grid);
    }

    /// <summary>
    /// Bhattacharyya distance (0 = same, 1 = disjoint) between the two grids seen as distributions
    /// of brightness over the 256 cells.
    /// </summary>
    public static double BhattacharyyaDistance(GrayImage a, GrayImage b)
    {
        var ga = a.Resize(Grid, Grid);
        var gb = b.Resize(Grid, Grid);
        long sa = 0, sb = 0;
        for (var i = 0; i < ga.Length; i++)
        {
            sa += ga[i];
            sb += gb[i];
        }

        if (sa == 0 || sb == 0)
        {
            return sa == sb ? 0.0 : 1.0;
        }

        var coefficient = 0.0;
        for (var i = 0; i < ga.Length; i++)
        {
            coefficient += Math.Sqrt((double)ga[i] * gb[i]);
        }

        coefficient /= Math.Sqrt((double)sa * sb);
        return Math.Sqrt(Math.Max(0.0, 1.0 - coefficient));
    }
}
