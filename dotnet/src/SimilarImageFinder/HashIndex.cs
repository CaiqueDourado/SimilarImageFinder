namespace SimilarImageFinder;

/// <summary>
/// Finds every stored hash within <c>MaxDistance</c> bits of a query. Multi-index hashing
/// (Norouzi, Punjani and Fleet, 2012): the bits are cut into bands of about 16 bits. If two
/// hashes differ in at most r bits, at least one of the m bands differs in at most r / m bits,
/// so each band is looked up together with its close variants and only those candidates are
/// compared bit by bit. Exact: no false negatives.
/// </summary>
/// <typeparam name="TKey">Identifier stored with each hash (a file path, a product id...).</typeparam>
public sealed class HashIndex<TKey>
{
    private const int BandBits = 16;
    private readonly (int Start, int Count)[] _bands;
    private readonly ulong[][] _flips;
    private readonly Dictionary<ulong, List<int>>[] _tables;
    private readonly List<ImageHash> _hashes = new();
    private readonly List<List<TKey>> _keys = new();
    private readonly Dictionary<ImageHash, int> _slotOf = new();
    private readonly List<ulong[]> _bandValues = new();
    private readonly List<int> _candidates = new();
    private int[] _seen = Array.Empty<int>();
    private int _query;

    /// <summary>Creates an index for hashes of <paramref name="bits"/> bits.</summary>
    public HashIndex(int maxDistance, int bits = 64)
    {
        if (maxDistance < 0 || maxDistance >= bits)
        {
            throw new ArgumentOutOfRangeException(nameof(maxDistance), "maxDistance must be between 0 and bits - 1.");
        }

        MaxDistance = maxDistance;
        Bits = bits;
        var m = Math.Max(1, bits / BandBits);
        var radius = maxDistance / m;
        _bands = new (int, int)[m];
        _flips = new ulong[m][];
        _tables = new Dictionary<ulong, List<int>>[m];
        for (var i = 0; i < m; i++)
        {
            var start = i * bits / m;
            var end = (i + 1) * bits / m;
            if (end - start > 64)
            {
                throw new ArgumentOutOfRangeException(nameof(bits), "Hash too long for the band layout.");
            }

            _bands[i] = (start, end - start);
            _flips[i] = FlipMasks(end - start, radius);
            _tables[i] = new Dictionary<ulong, List<int>>();
        }
    }

    /// <summary>Largest distance returned by <see cref="Query"/>.</summary>
    public int MaxDistance { get; }

    /// <summary>Length of the stored hashes.</summary>
    public int Bits { get; }

    /// <summary>Number of keys added.</summary>
    public int Count => _keys.Sum(k => k.Count);

    /// <summary>Adds a key with its hash.</summary>
    public void Add(TKey key, ImageHash hash)
    {
        ArgumentNullException.ThrowIfNull(hash);
        if (hash.Bits != Bits)
        {
            throw new ArgumentException($"The index holds {Bits}-bit hashes, got {hash.Bits}.", nameof(hash));
        }

        if (!_slotOf.TryGetValue(hash, out var slot))
        {
            slot = _hashes.Count;
            _slotOf[hash] = slot;
            _hashes.Add(hash);
            _keys.Add(new List<TKey>());
            var values = BandValues(hash);
            _bandValues.Add(values);
            for (var b = 0; b < _bands.Length; b++)
            {
                var band = values[b];
                if (!_tables[b].TryGetValue(band, out var list))
                {
                    list = new List<int>();
                    _tables[b][band] = list;
                }

                list.Add(slot);
            }
        }

        _keys[slot].Add(key);
    }

    /// <summary>Returns the keys within the distance, closest first.</summary>
    public IReadOnlyList<(TKey Key, int Distance)> Query(ImageHash hash, int? maxDistance = null)
    {
        ArgumentNullException.ThrowIfNull(hash);
        if (hash.Bits != Bits)
        {
            throw new ArgumentException($"The index holds {Bits}-bit hashes, got {hash.Bits}.", nameof(hash));
        }

        var limit = Math.Min(maxDistance ?? MaxDistance, MaxDistance);
        var found = new List<(TKey Key, int Distance)>();
        foreach (var slot in Candidates(BandValues(hash)))
        {
            var d = _hashes[slot].DistanceTo(hash);
            if (d <= limit)
            {
                found.AddRange(_keys[slot].Select(k => (k, d)));
            }
        }

        return found.OrderBy(kd => kd.Distance).ToList();
    }

    /// <summary>
    /// Connected groups of keys whose hashes are within <see cref="MaxDistance"/> (single linkage),
    /// in insertion order; only groups with two or more keys.
    /// </summary>
    public IReadOnlyList<IReadOnlyList<TKey>> Groups()
    {
        var parent = Enumerable.Range(0, _hashes.Count).ToArray();

        int Find(int i)
        {
            while (parent[i] != i)
            {
                parent[i] = parent[parent[i]];
                i = parent[i];
            }

            return i;
        }

        for (var slot = 0; slot < _hashes.Count; slot++)
        {
            foreach (var other in Candidates(_bandValues[slot]))
            {
                if (other > slot && _hashes[other].DistanceTo(_hashes[slot]) <= MaxDistance)
                {
                    int ra = Find(slot), rb = Find(other);
                    if (ra != rb)
                    {
                        parent[Math.Max(ra, rb)] = Math.Min(ra, rb);
                    }
                }
            }
        }

        var members = new SortedDictionary<int, List<TKey>>();
        for (var slot = 0; slot < _hashes.Count; slot++)
        {
            var root = Find(slot);
            if (!members.TryGetValue(root, out var list))
            {
                list = new List<TKey>();
                members[root] = list;
            }

            list.AddRange(_keys[slot]);
        }

        return members.Values.Where(l => l.Count > 1).Select(l => (IReadOnlyList<TKey>)l).ToList();
    }

    private ulong[] BandValues(ImageHash hash)
    {
        var values = new ulong[_bands.Length];
        for (var b = 0; b < _bands.Length; b++)
        {
            values[b] = hash.Band(_bands[b].Start, _bands[b].Count);
        }

        return values;
    }

    /// <summary>Slots sharing a close band value. The returned list is reused by the next call.</summary>
    private List<int> Candidates(ulong[] bandValues)
    {
        if (_seen.Length < _hashes.Count)
        {
            Array.Resize(ref _seen, Math.Max(_hashes.Count, _seen.Length * 2));
        }

        _query++;
        _candidates.Clear();
        for (var b = 0; b < _bands.Length; b++)
        {
            var band = bandValues[b];
            foreach (var mask in _flips[b])
            {
                if (_tables[b].TryGetValue(band ^ mask, out var slots))
                {
                    foreach (var slot in slots)
                    {
                        if (_seen[slot] != _query)
                        {
                            _seen[slot] = _query;
                            _candidates.Add(slot);
                        }
                    }
                }
            }
        }

        return _candidates;
    }

    private static ulong[] FlipMasks(int width, int radius)
    {
        var masks = new List<ulong> { 0UL };
        void Add(int from, int left, ulong mask)
        {
            if (left == 0)
            {
                return;
            }

            for (var p = from; p < width; p++)
            {
                var next = mask | (1UL << p);
                masks.Add(next);
                Add(p + 1, left - 1, next);
            }
        }

        Add(0, radius, 0UL);
        return masks.ToArray();
    }
}

/// <summary>Helpers over many hashes.</summary>
public static class ImageGroups
{
    /// <summary>Groups keys whose hashes are within <paramref name="maxDistance"/> bits (single linkage).</summary>
    public static IReadOnlyList<IReadOnlyList<TKey>> FindDuplicates<TKey>(IEnumerable<(TKey Key, ImageHash Hash)> items, int maxDistance = 6)
    {
        ArgumentNullException.ThrowIfNull(items);
        HashIndex<TKey>? index = null;
        foreach (var (key, hash) in items)
        {
            index ??= new HashIndex<TKey>(maxDistance, hash.Bits);
            index.Add(key, hash);
        }

        return index?.Groups() ?? Array.Empty<IReadOnlyList<TKey>>();
    }

    /// <summary>
    /// Signatures shared by at least <paramref name="minOwners"/> distinct owners (for example
    /// product ids). An image reused by hundreds of unrelated products is almost always a
    /// placeholder or a store logo and should not count as evidence that two products are the same.
    /// </summary>
    public static IReadOnlyDictionary<string, int> FindGeneric<TOwner>(IEnumerable<(TOwner Owner, string Signature)> items, int minOwners = 100)
        where TOwner : notnull
    {
        ArgumentNullException.ThrowIfNull(items);
        var owners = new Dictionary<string, HashSet<TOwner>>(StringComparer.Ordinal);
        foreach (var (owner, signature) in items)
        {
            if (!owners.TryGetValue(signature, out var set))
            {
                set = new HashSet<TOwner>();
                owners[signature] = set;
            }

            set.Add(owner);
        }

        var result = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var kv in owners.Where(kv => kv.Value.Count >= minOwners)
                     .OrderByDescending(kv => kv.Value.Count).ThenBy(kv => kv.Key, StringComparer.Ordinal))
        {
            result[kv.Key] = kv.Value.Count;
        }

        return result;
    }
}
