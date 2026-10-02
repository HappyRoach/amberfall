// <Trauma>
using Content.Medical.Common.Body;
// </Trauma>
using System.Linq;
using System.Numerics;
using Content.Client.DisplacementMap;
using Content.Shared.Body;
using Content.Shared.CCVar;
using Content.Shared.DisplacementMap;
using Content.Shared.Humanoid.Markings;
using Content.Shared.Humanoid;
using Robust.Client.GameObjects;
using Robust.Client.Graphics;
using Robust.Shared.Configuration;
using Robust.Shared.Utility;

namespace Content.Client.Body;

public sealed partial class VisualBodySystem : SharedVisualBodySystem
{
    [Dependency] private IConfigurationManager _cfg = default!;
    [Dependency] private DisplacementMapSystem _displacement = default!;
    [Dependency] private MarkingManager _marking = default!;
    [Dependency] private SpriteSystem _sprite = default!;

    public override void Initialize()
    {
        base.Initialize();

        SubscribeLocalEvent<VisualOrganComponent, OrganGotInsertedEvent>(OnOrganGotInserted);
        SubscribeLocalEvent<VisualOrganComponent, OrganGotRemovedEvent>(OnOrganGotRemoved);
        SubscribeLocalEvent<VisualOrganComponent, AfterAutoHandleStateEvent>(OnOrganState);

        SubscribeLocalEvent<VisualOrganMarkingsComponent, OrganGotInsertedEvent>(OnMarkingsGotInserted);
        SubscribeLocalEvent<VisualOrganMarkingsComponent, OrganGotRemovedEvent>(OnMarkingsGotRemoved);
        SubscribeLocalEvent<VisualOrganMarkingsComponent, AfterAutoHandleStateEvent>(OnMarkingsState);

        SubscribeLocalEvent<VisualOrganMarkingsComponent, BodyRelayedEvent<HumanoidLayerVisibilityChangedEvent>>(OnMarkingsChangedVisibility);

        Subs.CVar(_cfg, CCVars.AccessibilityClientCensorNudity, OnCensorshipChanged, true);
        Subs.CVar(_cfg, CCVars.AccessibilityServerCensorNudity, OnCensorshipChanged, true);
    }

    private void OnCensorshipChanged(bool value)
    {
        var query = AllEntityQuery<OrganComponent, VisualOrganMarkingsComponent>();
        while (query.MoveNext(out var ent, out var organComp, out var markingsComp))
        {
            if (organComp.Body is not { } body)
                continue;

            RemoveMarkings((ent, markingsComp), body);
            ApplyMarkings((ent, markingsComp), body);
        }
    }

    private void OnOrganGotInserted(Entity<VisualOrganComponent> ent, ref OrganGotInsertedEvent args)
    {
        ApplyVisual(ent, args.Target);
    }

    private void OnOrganGotRemoved(Entity<VisualOrganComponent> ent, ref OrganGotRemovedEvent args)
    {
        RemoveVisual(ent, args.Target);
    }

    private void OnOrganState(Entity<VisualOrganComponent> ent, ref AfterAutoHandleStateEvent args)
    {
        if (Comp<OrganComponent>(ent).Body is not { } body)
            return;

        ApplyVisual(ent, body);
    }

    private void ApplyVisual(Entity<VisualOrganComponent> ent, EntityUid target)
    {
        if (!_sprite.LayerMapTryGet(target, ent.Comp.Layer, out var index, false)) // Trauma - don't log for missing layers
            return;

        _sprite.LayerSetData(target, index, ent.Comp.Data);

        // The organ profile can update independently of its markings state.
        if (TryComp<VisualOrganMarkingsComponent>(ent, out var markings))
            ApplyMarkingOffsets((ent.Owner, markings), target);

        if (ent.Comp.OverlayLayer is { } overlayLayer && ent.Comp.OverlayState is { } overlayState &&
            _sprite.LayerMapTryGet(target, overlayLayer, out var overlayIndex, false))
        {
            if (ent.Comp.OverlaySexStateOverrides?.TryGetValue(ent.Comp.Profile.Sex, out var sexState) == true)
                overlayState = sexState;

            _sprite.LayerSetData(target, overlayIndex, new PrototypeLayerData
            {
                RsiPath = ent.Comp.Data.RsiPath,
                State = overlayState,
                Color = ent.Comp.Data.Color,
            });
        }

        var displacement = ent.Comp.Displacement;
        if (displacement != null && ProtoMan.Resolve(displacement, out var displacementProto))
        {
            _displacement.TryAddDisplacement(displacementProto.Displacement,
                (target, Comp<SpriteComponent>(target)),
                index,
                ent.Comp.Layer,
                out _);
        }
    }

    private void RemoveVisual(Entity<VisualOrganComponent> ent, EntityUid target)
    {
        // <Trauma> - removed parts have their body's skin colour. not enabled for eyes yet until it supports an iris layer
        if (ent.Comp.Data.Color is {} color && !HasComp<InternalOrganComponent>(ent))
            _sprite.SetColor(ent.Owner, color);
        // </Trauma>
        if (!_sprite.LayerMapTryGet(target, ent.Comp.Layer, out var index, false)) // Trauma - don't log for missing layers
            return;

        _sprite.LayerSetRsiState(target, index, RSI.StateId.Invalid);

        if (ent.Comp.OverlayLayer is { } overlayLayer &&
            _sprite.LayerMapTryGet(target, overlayLayer, out var overlayIndex, false))
            _sprite.LayerSetRsiState(target, overlayIndex, RSI.StateId.Invalid);

        _displacement.EnsureDisplacementIsNotOnSprite((target, Comp<SpriteComponent>(target)), ent.Comp.Layer);
    }

    private void OnMarkingsGotInserted(Entity<VisualOrganMarkingsComponent> ent, ref OrganGotInsertedEvent args)
    {
        ApplyMarkings(ent, args.Target.Owner); // Trauma - .Owner
    }

    private void OnMarkingsGotRemoved(Entity<VisualOrganMarkingsComponent> ent, ref OrganGotRemovedEvent args)
    {
        RemoveMarkings(ent, args.Target.Owner); // Trauma - .Owner
    }

    private void OnMarkingsState(Entity<VisualOrganMarkingsComponent> ent, ref AfterAutoHandleStateEvent args)
    {
        if (Comp<OrganComponent>(ent).Body is not { } body)
            return;

        RemoveMarkings(ent, body);
        ApplyMarkings(ent, body);
    }

    protected override void SetOrganColor(Entity<VisualOrganComponent> ent, Color color)
    {
        base.SetOrganColor(ent, color);

        if (Comp<OrganComponent>(ent).Body is not { } body)
            return;

        ApplyVisual(ent, body);
    }

    public override void SetOrganMarkings(Entity<VisualOrganMarkingsComponent> ent, Dictionary<HumanoidVisualLayers, List<Marking>> markings) // Trauma - made public
    {
        base.SetOrganMarkings(ent, markings);

        if (Comp<OrganComponent>(ent).Body is not { } body)
            return;

        RemoveMarkings(ent, body);
        ApplyMarkings(ent, body);
    }

    protected override void SetOrganAppearance(Entity<VisualOrganComponent> ent, PrototypeLayerData data)
    {
        base.SetOrganAppearance(ent, data);

        if (Comp<OrganComponent>(ent).Body is not { } body)
            return;

        ApplyVisual(ent, body);
    }

    private IEnumerable<Marking> AllMarkings(Entity<VisualOrganMarkingsComponent> ent)
    {
        foreach (var markings in ent.Comp.Markings.Values)
        {
            foreach (var marking in markings)
            {
                yield return marking;
            }
        }

        var censorNudity = _cfg.GetCVar(CCVars.AccessibilityClientCensorNudity) || _cfg.GetCVar(CCVars.AccessibilityServerCensorNudity);
        if (!censorNudity)
            yield break;

        var group = ProtoMan.Index(ent.Comp.MarkingData.Group);
        foreach (var layer in ent.Comp.MarkingData.Layers)
        {
            if (!group.Limits.TryGetValue(layer, out var layerLimits))
                continue;

            if (layerLimits.NudityDefault.Count < 1)
                continue;

            var markings = ent.Comp.Markings.GetValueOrDefault(layer) ?? [];
            if (markings.Any(marking => _marking.TryGetMarking(marking, out var proto) && proto.BodyPart == layer))
                continue;

            foreach (var marking in layerLimits.NudityDefault)
            {
                yield return new(marking, 1);
            }
        }
    }

    private void ApplyMarkings(Entity<VisualOrganMarkingsComponent> ent, Entity<SpriteComponent?> target)
    {
        if (!Resolve(target, ref target.Comp, false)) // Trauma - no shit test fails
            return;

        var applied = new List<Marking>();
        foreach (var marking in AllMarkings(ent))
        {
            if (!_marking.TryGetMarking(marking, out var proto))
                continue;

            ent.Comp.MarkingsDisplacement.TryGetValue(proto.BodyPart, out var displacement);

            var insertionPoints = new Dictionary<object, string>();

            for (var i = 0; i < proto.Sprites.Count; i++)
            {
                var sprite = proto.Sprites[i];

                DebugTools.Assert(sprite is SpriteSpecifier.Rsi);
                if (sprite is not SpriteSpecifier.Rsi rsi)
                    continue;

                object bookmark = proto.SpriteLayerOverrides.TryGetValue(rsi.RsiState, out var mappedLayer)
                    ? mappedLayer
                    : proto.BodyPart;
                object insertAfter = insertionPoints.TryGetValue(bookmark, out var previousLayer)
                    ? previousLayer
                    : bookmark;
                int index;
                var hasLayer = insertAfter is string layerName
                    ? _sprite.LayerMapTryGet(target, layerName, out index, true)
                    : _sprite.LayerMapTryGet(target, (Enum) insertAfter, out index, true);
                if (!hasLayer)
                    continue;

                var layerId = $"{proto.ID}-{rsi.RsiState}";

                if (!_sprite.LayerMapTryGet(target, layerId, out _, false))
                {
                    var spriteLayer = _sprite.AddLayer(target, sprite, index + 1);
                    _sprite.LayerMapSet(target, layerId, spriteLayer);
                    _sprite.LayerSetSprite(target, layerId, rsi);
                }

                insertionPoints[bookmark] = layerId;

                if (marking.MarkingColors is not null && i < marking.MarkingColors.Count)
                    _sprite.LayerSetColor(target, layerId, marking.MarkingColors[i]);
                else
                    _sprite.LayerSetColor(target, layerId, Color.White);

                if (displacement != null && proto.CanBeDisplaced)
                    _displacement.TryAddDisplacement(displacement, (target, target.Comp), _sprite.LayerMapGet(target, layerId), layerId, out _);
            }

            applied.Add(marking);
        }
        ent.Comp.AppliedMarkings = applied;
        ApplyMarkingOffsets(ent, target);
    }

    private void ApplyMarkingOffsets(Entity<VisualOrganMarkingsComponent> ent, Entity<SpriteComponent?> target)
    {
        if ((ent.Comp.FemaleLayerOffsets.Count == 0 && ent.Comp.LayerOffsets.Count == 0) ||
            !Resolve(target, ref target.Comp, false))
            return;

        var female = CompOrNull<VisualOrganComponent>(ent)?.Profile.Sex == Sex.Female;
        foreach (var marking in ent.Comp.AppliedMarkings)
        {
            if (!_marking.TryGetMarking(marking, out var proto))
                continue;

            var hasOffset = ent.Comp.LayerOffsets.TryGetValue(proto.BodyPart, out var offset);
            if (female && ent.Comp.FemaleLayerOffsets.TryGetValue(proto.BodyPart, out var femaleOffset))
            {
                offset = femaleOffset;
                hasOffset = true;
            }

            // Also reset an offset after changing a formerly female organ to male.
            if (!hasOffset && !ent.Comp.FemaleLayerOffsets.ContainsKey(proto.BodyPart))
                continue;

            foreach (var sprite in proto.Sprites)
            {
                if (sprite is not SpriteSpecifier.Rsi rsi)
                    continue;

                var layerId = $"{proto.ID}-{rsi.RsiState}";
                if (_sprite.LayerMapTryGet(target, layerId, out var index, false))
                    _sprite.LayerSetOffset(target, index, offset);
            }
        }
    }

    private void RemoveMarkings(Entity<VisualOrganMarkingsComponent> ent, Entity<SpriteComponent?> target)
    {
        if (!Resolve(target, ref target.Comp, false)) // Trauma - no shit test fails
            return;

        foreach (var marking in ent.Comp.AppliedMarkings)
        {
            if (!_marking.TryGetMarking(marking, out var proto))
                continue;

            foreach (var sprite in proto.Sprites)
            {
                DebugTools.Assert(sprite is SpriteSpecifier.Rsi);
                if (sprite is not SpriteSpecifier.Rsi rsi)
                    continue;

                var layerId = $"{proto.ID}-{rsi.RsiState}";

                // If this marking is one that can be displaced, we need to remove the displacement as well; otherwise
                // altering a marking at runtime can lead to the renderer falling over.
                // The Vulps must be shaved.
                // (https://github.com/space-wizards/space-station-14/issues/40135).
                if (proto.CanBeDisplaced)
                    _displacement.EnsureDisplacementIsNotOnSprite((target, target.Comp), layerId);

                if (!_sprite.LayerMapTryGet(target, layerId, out var index, false))
                    continue;

                _sprite.LayerMapRemove(target, layerId);
                _sprite.RemoveLayer(target, index);
            }
        }
    }

    private void OnMarkingsChangedVisibility(Entity<VisualOrganMarkingsComponent> ent, ref BodyRelayedEvent<HumanoidLayerVisibilityChangedEvent> args)
    {
        if (!ent.Comp.HideableLayers.Contains(args.Args.Layer))
            return;

        foreach (var markings in ent.Comp.Markings.Values)
        {
            foreach (var marking in markings)
            {
                if (!_marking.TryGetMarking(marking, out var proto))
                    continue;

                if (proto.BodyPart != args.Args.Layer && !(ent.Comp.DependentHidingLayers.TryGetValue(args.Args.Layer, out var dependent) && dependent.Contains(proto.BodyPart)))
                    continue;

                foreach (var sprite in proto.Sprites)
                {
                    DebugTools.Assert(sprite is SpriteSpecifier.Rsi);
                    if (sprite is not SpriteSpecifier.Rsi rsi)
                        continue;

                    var layerId = $"{proto.ID}-{rsi.RsiState}";

                    if (!_sprite.LayerMapTryGet(args.Body.Owner, layerId, out var index, true))
                        continue;

                    _sprite.LayerSetVisible(args.Body.Owner, index, args.Args.Visible);
                }
            }
        }
    }
}
