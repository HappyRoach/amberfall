using Content.Shared.Humanoid;
using Content.Shared.Inventory;

namespace Content.Amberfall.Shared.Clothing;

/// <summary>
///     Скрывает humanoid слои при переключении экипированной одежды.
///     Требует компонент ItemToggle.
/// </summary>
[RegisterComponent, NetworkedComponent]
public sealed partial class ToggleHideLayersComponent : Component
{
    /// <summary>
    /// Humanoid layers and the equipment slots where each layer should be hidden.
    /// </summary>
    [DataField]
    public Dictionary<HumanoidVisualLayers, SlotFlags> Layers = new();

    [DataField]
    public bool HideWhenActivated = true;
}
