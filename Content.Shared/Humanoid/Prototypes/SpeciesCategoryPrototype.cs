using Robust.Shared.Prototypes;

namespace Content.Shared.Humanoid.Prototypes;

/// <summary>
/// Groups playable species in the character editor.
/// </summary>
[Prototype]
public sealed partial class SpeciesCategoryPrototype : IPrototype
{
    [IdDataField]
    public string ID { get; private set; } = default!;

    /// <summary>
    /// Localized name displayed in the main species selector.
    /// </summary>
    [DataField(required: true)]
    public LocId Name { get; private set; }

    /// <summary>
    /// Species selected when entering this category. It must belong to this category.
    /// If it is unavailable at round start, the editor selects the first available member.
    /// </summary>
    [DataField(required: true)]
    public ProtoId<SpeciesPrototype> DefaultSpecies { get; private set; }
}
