# Twilight clothing wardrobe

Import with `python Tools/import_twilight_clothing.py C:/Projects/Twilight-Axis`.
For the expanded wardrobe, run
`python Tools/import_twilight_wardrobe.py C:/Projects/Twilight-Axis` after the
base import. The second command adds items without regenerating the base set.
This supersedes the earlier adventure-clothing and sleeve fix scripts. Run the
species importer first when starting from an empty resource tree: clothing sleeve
masks use the imported body parts. Human retains the approved regular `mm` body.

The wardrobe contains 157 items: the original 38 plus 119 additional pieces.
The additional English names and descriptions come from the matching Twilight
item definitions and their inherited fields. Thirty earlier items with exact
source counterparts use the same strings. The three combined outfits retain
descriptions for both garments, and five earlier items lack an unambiguous
source match. New states without a matching source name and description are
skipped. Prototypes
live under `Resources/Prototypes/_Amberfall/Entities/Clothing`, grouped by slot
and garment type. Localization uses matching file names under
`Resources/Locale/en-US/_Amberfall/clothing`. Shirts, dresses, robes, leather,
mail, plate, gambesons, trousers, skirts, helmets and the other garment types
have their own files; the base pants prototype stays in `Pants/base.yml`.
Textures additionally use the normal Shirts, Jumpsuit, Armor, Robes, Hoods, Hats,
Helmets, Cloaks, Boots, Misc and Gloves subdirectories. English localization,
including descriptions, mirrors the prototype categories.

## Worn state selection

Twilight groups clothing by body build: ordinary masculine and feminine cuts,
plus `_dwarf` and `_f_dwarf` for smaller bodies. Its `offset_features` table
positions each slot on the selected body. Amberfall uses the same four shared
states per garment: `equipped-SLOT`, `equipped-SLOT_f`,
`equipped-SLOT_dwarf`, `equipped-SLOT_f_dwarf`. The same four states live in the
separate sleeve RSI where the item has sleeves. No `slim_m` names are used.

`Resources/Prototypes/_Amberfall/Clothing/body_profiles.yml` maps each of the
26 playable Twilight species to one of these shared cuts for each sex, plus its
per-slot pixel offsets. Adding clothing now means providing up to four cut
states. Adding a species means adding one body profile; neither requires a
separate state in every existing garment.

The renderer uses the wearer's HumanoidProfile species for imported clothing.
HalfOrc females select the masculine cut. Goblins, gnomes, kobolds and
verminvolk use the small feminine cut as in Twilight. Legacy clothing keeps its
existing species-state and sex-state lookup, including `-f`/`-m` and `_f`/`_m`.
Imported clothing skips legacy displacement maps because its body profile
supplies the needed slot offset.

Native small gloves and belts already include their vertical shifts; headgear
uses the shared art shifted to each body's head. Elven clothing follows the
default body build rather than the character's sex alone.

`port_manifest.json` under `_Amberfall/Clothing` records each shared cut's source
state and each species body profile. Twilight provides no dwarf explorer vest or
explorer trousers. Only that outfit substitutes native small tunic and trouser
art; this is recorded explicitly in the manifest.

## Layers and item sprites

Order: legs, pantsBody, shirtBody, armorBody, arms, shirtSleeves, armorSleeves,
gloves/accessories. The existing cloak bookmark is behind the body. Sleeves use
separate RSIs with the same shared cut selection. Pixels overlapping the arms
are removed from the body state, and native left/right sleeve fragments are
added to the sleeve state. This also handles robes with sleeves drawn directly
in their side views. The sleeveless cuirass creates no sleeve overlay.

The three older combined outfits keep their original floor and hand art, while
their shirts and trousers are now separate worn overlays. Each takes its own
slot offset, which matters for the taller Wood Elf body.

All items include floor and left/right hand states. Existing floor/hand art is
retained. New items use native floor sprites; hand states bake the source's
default experimental-inhand scaling and directional placement into static RSI
frames. Dynamic blood, damage, dyeing, sleeve rolling and source-specific
in-hand occlusion mechanics are outside this asset port. Armour values are local
baseline values, not a conversion of Twilight's combat balance.

Floor `icon` states use one direction when Twilight provides only one floor
image. This keeps thrown items visible as their physics body rotates. Floor
icons with distinct directional art retain all four directions.

Wanderer now starts with a separate travel tunic and cloth trousers.

## Dwarf

Dwarf is enabled under Dwarven and points to MobMountainDwarf /
AppearanceMountainDwarf, using reimported male `md.dmi`, female `fd.dmi`, eyes
and native feature offsets. It retains the local dwarf metabolism, accent,
speech, mutations and smaller collision shape. The old SS14 MobDwarf NPC
prototype remains separate.

Validation is limited to static prototype/resource/localization inspection and
offline sprite composites. No game build or tests were run.
