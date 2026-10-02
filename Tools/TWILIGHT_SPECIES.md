# Twilight species port

Source checkout: `C:/Projects/Twilight-Axis`, inspected at commit
`e9a5462490da68a039b8a37ebeea6f1e0243ba81`.

The playable set combines `config/game_options.txt` with species whose
`check_roundstart_eligible()` returns true, including `modular_twilight_axis`.
It contains 26 species:

| Category | Species |
| --- | --- |
| Humankind | Human, HalfElf, HalfOrc, HalfKin |
| Dwarven | Dwarf, Gnome |
| Elven | WoodElf, SunElf, DarkElf |
| Godtouched | Aasimar, Tiefling, Revenant, MetalConstruct, Goblin |
| Beastvolk | WildKin, Verminvolk, Tabaxi, Venardine, Lupian, Axian, Fluvian |
| Zard | Zardman, Drakian, Kobold |
| Standalone | Murkling, AuRa |

The first species in each category is its default. Saved profiles store actual
species IDs. The existing Human and Dwarf IDs are retained. The playable Dwarf
uses `AppearanceMountainDwarf`/`MobMountainDwarf`; existing NPC dwarf prototypes
retain their previous bodies. The existing NPC kobold markings group is also
kept separate from the playable `KoboldMarkings` group.

## Generated resources

- Species/category prototypes: `Resources/Prototypes/_Amberfall/Species/`.
- Bodies and organs: `Resources/Prototypes/_Amberfall/Body/Species/`.
- Marking prototypes/groups: `Resources/Prototypes/_Amberfall/Markings/`.
- Body textures: `Resources/Textures/_Amberfall/Mobs/<body>/`.
- Racial marking textures: `Resources/Textures/_Amberfall/Mobs/Markings/`.
- Names/descriptions: `Resources/Locale/en-US/_Amberfall/species/`.

`port_manifest.json` records each species' source type, source file, selected
male/female bodies, offsets and marking counts. RSI metadata records asset
provenance. `source_sprite_omissions.json` records missing states in the source
DMIs; missing color/layer fragments remain transparent. A source horn option
with no usable state is omitted. Au Ra's existing unsplit resting tail is used
in place of the absent split resting states requested by its DM definition.

Regenerate the port with:

```powershell
python Tools/import_twilight_species.py C:/Projects/Twilight-Axis
```

This converts resources only. It does not build or run the game or test suites.
The Human/Dwarf category fields and the Dwarf's prototype/doll references in
`Resources/Prototypes/Species/` are the small integration changes maintained
outside the generator.

## Visual behavior and scope

Both sexes and four directions are imported. Species with body builds use their
source default builds. Human keeps the previously approved regular `mm.dmi`
male body and `fm.dmi` female body. Alternate selectable body builds are not added.
The female construct has hands integrated into its source arm sprites. Source
legs include feet; local foot states are transparent, as in the existing human port.
Au Ra includes its default scale pattern.

392 racial markings expose source ears, horns, snouts, neck features, antennae,
tails and wings. Color masks remain separate. Static standing frames are used;
wagging/flapping animations are not imported. Defaults enabled in the source
use required local marking slots; source-disabled features start empty and can
be added in the marking editor. Their complete source enable/disable controls
are not reproduced.

`spriteLayerOverrides` puts rear tail states on `tailBehind` and rear wing
states on `wingsBehind`; the latter is above the former. Other rear markings
use `markingsBehind`. Front tail and wing states use their usual body-part
layers, with tail below wings there too.
`layerOffsets` and `femaleLayerOffsets` position markings for the selected body.
The editor rebuilds organ profile data when changing species so newly added
tail/wing organs can receive defaults immediately.

This is the character-selection and appearance port. The new mobs use the local
humanoid body/organ mechanics. Twilight racial abilities, stat bonuses, languages,
special construct/ooze/revenant physiology, full body-tattoo sets and clothing
cuts for the additional silhouettes require separate gameplay/content work.

Verification for this port is static: prototype IDs/references, source eligibility,
RSI states, localization keys, and contact sheets of the assembled sprites.
Runtime rendering has not been checked because builds and tests were prohibited.
