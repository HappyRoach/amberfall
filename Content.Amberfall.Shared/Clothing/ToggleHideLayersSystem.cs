using Content.Shared.Clothing;
using Content.Shared.Clothing.Components;
using Content.Shared.Humanoid;
using Content.Shared.Inventory;
using Content.Shared.Item.ItemToggle.Components;

namespace Content.Amberfall.Shared.Clothing;

public sealed partial class ToggleHideLayersSystem : EntitySystem
{
    [Dependency] private SharedHideableHumanoidLayersSystem _hideableLayers = default!;

    [SubscribeLocalEvent]
    private void OnEquipped(Entity<ToggleHideLayersComponent> ent, ref ClothingGotEquippedEvent args)
    {
        var hide = TryComp<ItemToggleComponent>(ent, out var toggle) &&
                   toggle.Activated == ent.Comp.HideWhenActivated;
        SetLayerVisibility(ent, args.Wearer, args.Clothing.InSlotFlag, hide);
    }

    [SubscribeLocalEvent]
    private void OnUnequipped(Entity<ToggleHideLayersComponent> ent, ref ClothingGotUnequippedEvent args)
    {
        SetLayerVisibility(ent, args.Wearer, args.Clothing.InSlotFlag, false);
    }

    [SubscribeLocalEvent]
    private void OnToggled(Entity<ToggleHideLayersComponent> ent, ref ItemToggledEvent args)
    {
        if (!TryComp<ClothingComponent>(ent, out var clothing))
            return;

        SetLayerVisibility(ent, Transform(ent.Owner).ParentUid, clothing.InSlotFlag,
            args.Activated == ent.Comp.HideWhenActivated);
    }

    private void SetLayerVisibility(Entity<ToggleHideLayersComponent> ent, EntityUid wearer,
        SlotFlags? slot, bool hidden)
    {
        if (slot is not { } equippedSlot || equippedSlot == SlotFlags.NONE ||
            !HasComp<HideableHumanoidLayersComponent>(wearer))
            return;

        foreach (var (layer, allowedSlots) in ent.Comp.Layers)
        {
            if ((allowedSlots & equippedSlot) != SlotFlags.NONE)
                _hideableLayers.SetLayerOcclusion(wearer, layer, hidden, equippedSlot);
        }
    }
}
