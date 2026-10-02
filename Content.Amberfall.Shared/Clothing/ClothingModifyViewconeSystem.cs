using Content.Shared.Inventory;
using Content.Shared.Item.ItemToggle.Components;
using Content.Trauma.Shared.Viewcone;

namespace Content.Amberfall.Shared.Clothing;

public sealed partial class ClothingModifyViewconeSystem : EntitySystem
{
    [SubscribeLocalEvent]
    private void OnModifyViewconeAngle(Entity<ClothingModifyViewconeComponent> ent,
        ref InventoryRelayedEvent<ModifyViewconeAngleEvent> args)
    {
        if (TryComp<ItemToggleComponent>(ent, out var toggle) && toggle.Activated)
            args.Args.ModifyAngle(ent.Comp.AngleModifier);
    }
}
