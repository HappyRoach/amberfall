using System.Numerics;
using Robust.Shared.Prototypes;

namespace Content.Shared.Clothing.Prototypes;

/// <summary>
/// Twilight-style shared clothing cuts and per-slot pixel placement for a species.
/// One profile serves every garment instead of copying states into every RSI.
/// </summary>
[Prototype]
public sealed partial class ClothingBodyProfilePrototype : IPrototype
{
    [IdDataField]
    public string ID { get; private set; } = default!;

    [DataField]
    public string MaleStateSuffix { get; private set; } = "";

    [DataField]
    public string FemaleStateSuffix { get; private set; } = "_f";

    /// <summary>Pixel offsets, keyed by inventory slot.</summary>
    [DataField]
    public Dictionary<string, Vector2> MaleOffsets { get; private set; } = new();

    [DataField]
    public Dictionary<string, Vector2> FemaleOffsets { get; private set; } = new();
}
