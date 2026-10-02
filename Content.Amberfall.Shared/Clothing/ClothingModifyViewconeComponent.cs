namespace Content.Amberfall.Shared.Clothing;

/// <summary>
///     Модифицирует угол обзора, когда надетый предмет активирован.
/// </summary>
[RegisterComponent, NetworkedComponent]
public sealed partial class ClothingModifyViewconeComponent : Component
{
    [DataField]
    public float AngleModifier = 0.75f;
}
