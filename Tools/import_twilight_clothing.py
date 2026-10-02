"""Import the adventure wardrobe, including native race cuts and separate sleeves.

Usage: python Tools/import_twilight_clothing.py C:/Projects/Twilight-Axis
Existing item IDs and floor/in-hand sprites are retained. New items are grouped
like the main clothing tree. No builds or tests are invoked.
"""

import argparse
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re

from PIL import Image, ImageChops

from import_twilight_species import (DM, RACES, ROOT, blank, composite, dmi,
                                     save_rsi, shifted, tiles, write)

TEXTURES = ROOT / 'Resources/Textures/_Amberfall/Clothing'
PROTOTYPES = ROOT / 'Resources/Prototypes/_Amberfall/Entities/Clothing'
LOCALE = ROOT / 'Resources/Locale/en-US/_Amberfall/clothing'
SOURCE_CLOTHING = 'icons/roguetown/clothing/'
SLOTS = {'shirts': 'INNERCLOTHING', 'pants': 'LEGS', 'armor': 'OUTERCLOTHING',
         'head': 'HELMET', 'feet': 'FEET', 'gloves': 'HAND', 'cloaks': 'NECK', 'belts': 'BELT'}
OFFSETS = {'shirts': 'SHIRT', 'pants': 'PANTS', 'armor': 'ARMOR', 'head': 'HEAD',
           'feet': 'SHOES', 'gloves': 'GLOVES', 'cloaks': 'CLOAK', 'belts': 'BELT'}
INVENTORY_SLOTS = {'shirts': 'jumpsuit', 'pants': 'pants', 'armor': 'outerClothing',
                   'head': 'head', 'feet': 'shoes', 'gloves': 'gloves',
                   'cloaks': 'neck', 'belts': 'belt'}
PARENTS = {'shirts': 'UnsensoredClothingUniformBase', 'pants': 'ClothingPantsBase',
           'armor': 'ClothingOuterBase', 'head': 'ClothingHeadBase',
           'feet': 'ClothingShoesBase', 'gloves': 'ClothingHandsBase', 'cloaks': 'ClothingNeckBase'}

# Existing wardrobe. Optional last entry is the trousers in a combined outfit.
EXISTING = [
    ('ClothingUniformTraveler', 'Uniforms/Jumpsuit/traveler_clothes', 'shirts', 'tunic', 'trou'),
    ('ClothingUniformExplorer', 'Uniforms/Jumpsuit/explorer_clothes', 'shirts', 'explorervest', 'explorerpants'),
    ('ClothingUniformRags', 'Uniforms/Jumpsuit/ragged_clothes', 'shirts', 'rags', 'baggypants'),
    ('ClothingOuterLeatherJerkin', 'OuterClothing/Armor/leather_jerkin', 'armor', 'leather'),
    ('ClothingOuterGambeson', 'OuterClothing/Armor/gambeson', 'armor', 'gambeson'),
    ('ClothingOuterHauberk', 'OuterClothing/Armor/hauberk', 'armor', 'hauberk'),
    ('ClothingNeckCape', 'Neck/Cloaks/cape', 'cloaks', 'cape'),
    ('ClothingNeckShortCloak', 'Neck/Cloaks/short_cloak', 'cloaks', 'shortcloak'),
    ('ClothingNeckForestCloak', 'Neck/Cloaks/forest_cloak', 'cloaks', 'forestcloak'),
    ('ClothingHeadBasicHood', 'Head/Hoods/basic_hood', 'head', 'basichood'),
    ('ClothingHeadBanditHood', 'Head/Hoods/bandit_hood', 'head', 'bandithood'),
    ('ClothingHeadStrawHat', 'Head/Hats/straw_hat', 'head', 'strawhat'),
    ('ClothingShoesLeatherBoots', 'Shoes/Boots/leather_boots', 'feet', 'leatherboots'),
    ('ClothingShoesShortBoots', 'Shoes/Boots/short_boots', 'feet', 'shortboots'),
    ('ClothingHandsLeatherGloves', 'Hands/Gloves/leather_gloves', 'gloves', 'leather_gloves'),
    ('ClothingHandsFingerlessGloves', 'Hands/Gloves/fingerless_gloves', 'gloves', 'fingerless_gloves'),
    ('ClothingBeltLeather', 'Belt/leather_belt', 'belts', 'leather'),
]
# ID, resource, DMI, state, localized name, description.
NEW = [
    ('ClothingUniformLinenShirt', 'Uniforms/Shirts/linen_shirt', 'shirts', 'undershirt',
     'linen shirt', 'A plain long-sleeved shirt for work and travel.'),
    ('ClothingUniformShortShirt', 'Uniforms/Shirts/short_shirt', 'shirts', 'shortshirt',
     'short-sleeved shirt', 'A light shirt that leaves the forearms free.'),
    ('ClothingUniformTravelTunic', 'Uniforms/Shirts/travel_tunic', 'shirts', 'tunic',
     'travel tunic', 'A sturdy tunic to wear over a pair of trousers on the road.'),
    ('ClothingPantsCloth', 'Pants/cloth_trousers', 'pants', 'trou',
     'cloth trousers', 'Simple cloth trousers, comfortable enough for a long journey.'),
    ('ClothingPantsLeather', 'Pants/leather_trousers', 'pants', 'leathertrou',
     'leather trousers', 'Supple leather trousers that keep brambles away from your legs.'),
    ('ClothingPantsBaggy', 'Pants/baggy_trousers', 'pants', 'baggypants',
     'baggy trousers', 'Loose trousers with plenty of room to move.'),
    ('ClothingPantsChainLeggings', 'Pants/chain_leggings', 'pants', 'chain_legs',
     'chain leggings', 'Interlinked metal rings protect the legs beneath a coat or tunic.'),
    ('ClothingPantsPlateLeggings', 'Pants/plate_leggings', 'pants', 'plate_legs',
     'plate leggings', 'Articulated metal plates fitted to protect the legs.'),
    ('ClothingOuterPlateHarness', 'OuterClothing/Armor/plate_harness', 'armor', 'plate',
     'plate harness', 'A suit of articulated plate armour with separate shoulder and arm protection.'),
    ('ClothingOuterSteelCuirass', 'OuterClothing/Armor/steel_cuirass', 'armor', 'cuirass',
     'steel cuirass', 'A shaped steel breastplate and backplate. The arms remain uncovered.'),
    ('ClothingOuterTravelRobe', 'OuterClothing/Robes/travel_robe', 'armor', 'white_robe',
     'travel robe', 'A long cloth robe with ample sleeves, suited to a travelling scholar or pilgrim.'),
    ('ClothingNeckHalfCloak', 'Neck/Cloaks/half_cloak', 'cloaks', 'halfcloak',
     'half cloak', 'A short travelling cloak draped over one shoulder.'),
    ('ClothingNeckSnowCloak', 'Neck/Cloaks/snow_cloak', 'cloaks', 'snowcloak',
     'snow cloak', 'A thick cloak for journeys through cold and snowy country.'),
    ('ClothingShoesTravelSandals', 'Shoes/Misc/travel_sandals', 'feet', 'sandals',
     'travel sandals', 'Simple sandals held together by leather straps.'),
    ('ClothingShoesSimpleLeather', 'Shoes/Misc/simple_leather_shoes', 'feet', 'simpleshoe',
     'simple leather shoes', 'Plain leather shoes for everyday wear.'),
    ('ClothingShoesPlateBoots', 'Shoes/Boots/plate_boots', 'feet', 'armorboots',
     'plate boots', 'Boots reinforced with metal plates to protect the feet.'),
    ('ClothingHandsChainGloves', 'Hands/Gloves/chain_gloves', 'gloves', 'cgloves',
     'chain gloves', 'Gloves covered with small interlinked metal rings.'),
    ('ClothingHeadArmingCap', 'Head/Hats/arming_cap', 'head', 'armingcap',
     'arming cap', 'A close-fitting cloth cap worn on its own or beneath a helmet.'),
    ('ClothingHeadLeatherHelm', 'Head/Helmets/leather_helm', 'head', 'leatherhelm',
     'leather helm', 'A light leather helmet for scouts and travellers.'),
    ('ClothingHeadKettleHelm', 'Head/Helmets/kettle_helm', 'head', 'kettle',
     'kettle helm', 'A broad-brimmed metal helmet that shields the head from blows.'),
    ('ClothingHeadNasalHelm', 'Head/Helmets/nasal_helm', 'head', 'nasal',
     'nasal helm', 'An open metal helmet with a narrow guard over the nose.'),
]
SLEEVELESS = {'cuirass'}


@lru_cache(None)
def names(path):
    return {s[0] for s in dmi(str(path))[-1]}


def read_rsi(path):
    if not path.exists():
        return {}
    meta = json.loads((path / 'meta.json').read_text())
    result = {}
    for entry in meta['states']:
        image = Image.open(path / (entry['name'] + '.png')).convert('RGBA')
        directions = entry.get('directions', 1)
        if directions == 1:
            result[entry['name']] = [image.copy() for _ in range(4)]
        elif directions == 4:
            result[entry['name']] = [image.crop((i % 2 * 32, i // 2 * 32,
                                              i % 2 * 32 + 32, i // 2 * 32 + 32)) for i in range(4)]
        else:
            raise ValueError(f'Unsupported directions in {path}: {entry["name"]}')
    return result


def complete_floor_icon(states):
    """A one-direction BYOND floor icon must remain visible after item rotation."""
    if 'icon' not in states:
        return
    frames = states['icon']
    visible = [frame for frame in frames if frame.getchannel('A').getbbox() is not None]
    if len(visible) == 1:
        states['icon'] = [visible[0].copy() for _ in range(4)]


@lru_cache(None)
def arm_masks(body, sex, hands=False):
    folder = ROOT / 'Resources/Textures/_Amberfall/Mobs' / body / 'parts.rsi'
    suffix = '_f' if sex == 'f' else ''
    masks = [Image.new('L', (32, 32)) for _ in range(4)]
    for part in ['l_arm', 'r_arm'] + (['l_hand', 'r_hand'] if hands else []):
        sheet = Image.open(folder / (part + suffix + '.png')).convert('RGBA')
        for i in range(4):
            alpha = sheet.crop((i % 2 * 32, i // 2 * 32, i % 2 * 32 + 32, i // 2 * 32 + 32)).getchannel('A')
            masks[i] = ImageChops.lighter(masks[i], alpha)
    return masks


def clothing_cut(dm, fields, sex):
    build = fields.get('default_body_build_' + sex)
    if build:
        bulky = dm.fields('/datum/body_build/' + build.removeprefix('BODY_BUILD_').lower()).get('bulky_cut') == 'TRUE'
    else:
        bulky = fields.get('use_m') == 'TRUE' or (sex == 'm' and fields.get('use_f') != 'TRUE')
    return '' if bulky else '_f'


def select_state(path, state, cut, small, substitutions):
    suffix = cut + ('_dwarf' if small else '')
    candidate = state + suffix
    if candidate in names(path):
        return candidate
    # Explorer art has no small-body cut upstream. Use matching native tunic /
    # trousers for those bodies instead of stretching or clipping a tall outfit.
    if small and state in ('explorervest', 'explorerpants'):
        substitute = {'explorervest': 'tunic', 'explorerpants': 'trou'}[state] + suffix
        if substitute in names(path):
            substitutions.add((path.name, candidate, substitute))
            return substitute
    # Hats are shared by all bodies and aligned with the native HEAD offsets.
    if path.stem == 'head' and state in names(path):
        return state
    raise ValueError(f'Missing required clothing cut: {path}: {candidate}')


def worn(source, group, state, cut, small, offset, substitutions):
    path = source / SOURCE_CLOTHING / 'onmob' / (group + '.dmi')
    selected = select_state(path, state, cut, small, substitutions)
    frames = tiles(path, selected)
    # These fragments form the side views; without them the garment disappears.
    for side in ('r_', 'l_'):
        if side + selected in names(path):
            frames = composite(frames, tiles(path, side + selected))
    helper = source / SOURCE_CLOTHING / 'onmob/helpers' / ('sleeves_' + group + '.dmi')
    if group in ('pants', 'cloaks') and helper.exists():
        for side in ('r_', 'l_'):
            if side + selected in names(helper):
                frames = composite(frames, tiles(helper, side + selected))
    return shifted(frames, offset), selected


def sleeves(source, group, selected, body_frames, body, sex, offset):
    result = blank()
    masks = arm_masks(body, sex)
    for i in range(4):
        result[i] = body_frames[i].copy()
        result[i].putalpha(ImageChops.multiply(result[i].getchannel('A'), masks[i]))
    # Helpers supply the portions missing from the east/west body sprite.
    # Some robes already contain side sleeves in the body image. Their overlap
    # with the arms was extracted above; no nonexistent limb states are needed.
    for relative in ('onmob/helpers/sleeves_' + group + '.dmi', 'onmob/' + group + '.dmi'):
        path = source / SOURCE_CLOTHING / relative
        if path.exists():
            for side in ('r_', 'l_'):
                if side + selected in names(path):
                    result = composite(result, shifted(tiles(path, side + selected), offset))
    return result


def inhands(floor):
    """Bake Twilight's default experimental_inhand (0.4 scale) into RSI states."""
    result = {}
    for hand, mirror in [('right', False), ('left', True)]:
        frames = []
        for i, (x, y) in enumerate([(-7, -4), (7, -4), (2, -4), (-4, -4)]):
            tile = floor[i].resize((13, 13), Image.Resampling.NEAREST)
            if mirror:
                tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                x = -x
            frame = Image.new('RGBA', (32, 32))
            frame.paste(tile, (9 + x, 9 - y))
            frames.append(frame)
        result['inhand-' + hand] = frames
    return result


def prototype(entry):
    ident, asset, group, state, name, description = entry
    sprite = '_Amberfall/Clothing/' + asset + '.rsi'
    text = f'- type: entity\n  parent: {PARENTS[group]}\n  id: {ident}\n  components:\n'
    text += f'  - type: Sprite\n    sprite: {sprite}\n    state: icon\n'
    text += f'  - type: Item\n    sprite: {sprite}\n'
    text += f'  - type: Clothing\n    sprite: {sprite}\n    bodyProfile: true\n'
    if group in ('shirts', 'armor'):
        layer = 'shirt' if group == 'shirts' else 'armor'
        text += f'    wornLayer: {layer}Body\n'
        if state not in SLEEVELESS:
            text += f'    sleeveSprite: _Amberfall/Clothing/{asset}_sleeves.rsi\n'
            text += f'    sleeveState: equipped-SLEEVES\n    sleeveLayer: {layer}Sleeves\n'
    if group == 'pants':
        text += '    wornLayer: pantsBody\n'
    if group == 'cloaks':
        text += '    wornLayer: cloakBehind\n'
    armor = {'plate': ('Torso', .7, .55, .65), 'cuirass': ('Torso', .8, .65, .7),
             'chain_legs': ('Leg', .9, .75, .85), 'plate_legs': ('Leg', .8, .65, .75),
             'leatherhelm': ('Head', .95, .9, .95), 'kettle': ('Head', .85, .75, .85),
             'nasal': ('Head', .85, .8, .85)}
    if state in armor:
        part, blunt, slash, piercing = armor[state]
        text += f'  - type: Armor\n    coverage: [ {part} ]\n    modifiers:\n      coefficients:\n'
        text += f'        Blunt: {blunt}\n        Slash: {slash}\n        Piercing: {piercing}\n'
    return text, f'ent-{ident} = {name}\n    .desc = {description}\n'


def save_compact_rsi(destination, states, sources):
    # The earlier per-race import produced fifty-two equipped PNGs per item.
    # Only remove those generated equipped names from this known Amberfall RSI.
    if not destination.resolve().is_relative_to(TEXTURES.resolve()):
        raise ValueError(f'Unexpected clothing output: {destination}')
    stale = {path.stem for path in destination.glob('equipped-*.png')} - states.keys()
    save_rsi(destination, states, sources)
    metadata_path = destination / 'meta.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    for entry in metadata['states']:
        name = entry['name']
        if name not in ('icon', 'icon-down') or name not in states:
            continue
        frames = states[name]
        if all(frame.tobytes() == frames[0].tobytes() for frame in frames[1:]):
            frames[0].save(destination / (name + '.png'))
            entry['directions'] = 1
    write(metadata_path, json.dumps(metadata, indent=2))
    for name in stale:
        (destination / (name + '.png')).unlink()


def body_profile(dm, species, fields):
    small = fields.get('custom_clothes') == 'TRUE'
    text = f'- type: clothingBodyProfile\n  id: {species}\n'
    record = {'species': species}
    for sex, label in [('m', 'male'), ('f', 'female')]:
        suffix = clothing_cut(dm, fields, sex) + ('_dwarf' if small else '')
        text += f'  {label}StateSuffix: "{suffix}"\n'
        record[label + 'StateSuffix'] = suffix
        offsets = dm.offsets(fields, sex)
        values = {}
        for group, slot in INVENTORY_SLOTS.items():
            offset = offsets.get(OFFSETS[group], (0, 0))
            # Twilight's native small glove and belt sprites already sit low.
            if small and group in ('gloves', 'belts'):
                offset = (0, 0)
            if offset != (0, 0):
                values[slot] = offset
        if values:
            text += f'  {label}Offsets:\n'
            for slot, (x, y) in values.items():
                text += f'    {slot}: {x}, {y}\n'
        record[label + 'Offsets'] = values
    return text, record


def enable_existing_profiles():
    for ident, asset, group, state, *pants in EXISTING:
        pattern = re.compile(rf'(?m)(^  id: {re.escape(ident)}\n(?:(?!^- type: entity).)*?^  - type: Clothing\n)', re.S)
        found = False
        for path in PROTOTYPES.rglob('*.yml'):
            text = path.read_text(encoding='utf-8')
            if not pattern.search(text):
                continue
            found = True
            block = pattern.search(text).group(1)
            if 'bodyProfile: true' not in text[text.index(block):text.index(block) + len(block) + 240]:
                text = text.replace(block, block + '    bodyProfile: true\n', 1)
            if pants and f'lowerSprite: _Amberfall/Clothing/{asset}_pants.rsi' not in text:
                lower = (f'    lowerSprite: _Amberfall/Clothing/{asset}_pants.rsi\n'
                         '    lowerState: equipped-PANTS\n')
                text = text.replace(block, block + lower, 1)
            write(path, text)
            break
        if not found:
            raise ValueError(f'Existing clothing prototype not found: {ident}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    dm = DM(args.source)
    races = []
    profile_yaml = []
    profiles = []
    for species, source_type, *_ in RACES:
        fields = dm.fields('/datum/species/' + source_type)
        races.append((species, fields))
        profile_text, profile_record = body_profile(dm, species, fields)
        profile_yaml.append(profile_text)
        profiles.append(profile_record)
    write(ROOT / 'Resources/Prototypes/_Amberfall/Clothing/body_profiles.yml', '\n'.join(profile_yaml))
    substitutions = set()
    manifest = []
    for entry in EXISTING + [e[:4] for e in NEW]:
        ident, asset, group, state, *pants = entry
        destination = TEXTURES / (asset + '.rsi')
        states = {name: frames for name, frames in read_rsi(destination).items()
                  if not name.startswith('equipped-')}
        sources = [SOURCE_CLOTHING + group + '.dmi', SOURCE_CLOTHING + 'onmob/' + group + '.dmi']
        if pants:
            sources.append(SOURCE_CLOTHING + 'onmob/pants.dmi')
        if 'icon' not in states:
            states['icon'] = tiles(args.source / sources[0], state)
            states.update(inhands(states['icon']))
        complete_floor_icon(states)
        if state == 'basichood':
            states['icon-down'] = tiles(args.source / sources[0], 'basichood_t')
        has_sleeves = group in ('shirts', 'armor') and state not in SLEEVELESS
        sleeve_states = {}
        lower_states = {}
        variants = []
        for suffix, body, sex, cut, small in (
            ('', 'Human', 'm', '', False),
            ('_f', 'Human', 'f', '_f', False),
            ('_dwarf', 'MountainDwarf', 'm', '', True),
            ('_f_dwarf', 'MountainDwarf', 'f', '_f', True),
        ):
            frames, selected = worn(args.source, group, state, cut, small, (0, 0), substitutions)
            if has_sleeves:
                sleeve = sleeves(args.source, group, selected, frames, body, sex, (0, 0))
                sleeve_states['equipped-SLEEVES' + suffix] = sleeve
                for i in range(4):
                    alpha = ImageChops.subtract(frames[i].getchannel('A'), sleeve[i].getchannel('A'))
                    frames[i].putalpha(alpha)
            if pants:
                trousers, _ = worn(args.source, 'pants', pants[0], cut, small, (0, 0), substitutions)
                lower_states['equipped-PANTS' + suffix] = trousers
            if group == 'belts':
                for frame, mask in zip(frames, arm_masks(body, sex, True)):
                    frame.putalpha(ImageChops.subtract(frame.getchannel('A'), mask))
            states['equipped-' + SLOTS[group] + suffix] = frames
            if state == 'basichood':
                lowered, _ = worn(args.source, group, 'basichood_t', cut, small, (0, 0), substitutions)
                states['down-equipped-HELMET' + suffix] = lowered
            variants.append({'suffix': suffix, 'sourceState': selected})
        save_compact_rsi(destination, states, sources)
        if has_sleeves:
            save_compact_rsi(TEXTURES / (asset + '_sleeves.rsi'), sleeve_states,
                             [SOURCE_CLOTHING + 'onmob/helpers/sleeves_' + group + '.dmi', sources[1]])
        if pants:
            save_compact_rsi(TEXTURES / (asset + '_pants.rsi'), lower_states,
                             [SOURCE_CLOTHING + 'onmob/pants.dmi'])
        manifest.append({'id': ident, 'sprite': asset, 'variants': variants})

    from import_twilight_wardrobe import (RESOURCE_MOVES, organize_existing_resources,
                                           twilight_strings, write_grouped_resources)
    source_strings = twilight_strings(args.source)
    yaml_groups, locale_groups = defaultdict(list), defaultdict(list)
    for entry in NEW:
        directory, filename = RESOURCE_MOVES[entry[0]]
        source_text = source_strings.get((entry[2], entry[3]))
        localized = (*entry[:4], *source_text[:2]) if source_text else entry
        yaml, locale = prototype(localized)
        yaml_groups[directory, filename].append(yaml)
        locale_groups[directory.lower(), filename.replace('.yml', '.ftl')].append(locale)
    new_ids = {entry[0] for entry in NEW}
    write_grouped_resources(PROTOTYPES, yaml_groups, new_ids, '.yml')
    write_grouped_resources(LOCALE, locale_groups, new_ids, '.ftl')
    organize_existing_resources()
    enable_existing_profiles()
    write(PROTOTYPES / 'Pants/base.yml', '''- type: entity
  abstract: true
  parent: Clothing
  id: ClothingPantsBase
  components:
  - type: Sprite
    state: icon
  - type: Clothing
    slots: [ LEGS ]
    wornLayer: pantsBody
  - type: Item
    size: Normal
  - type: Tag
    tags: [ ClothMade, WhitelistChameleon ]''')
    manifest_path = ROOT / 'Resources/Prototypes/_Amberfall/Clothing/port_manifest.json'
    previous = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    by_id = {entry['id']: entry for entry in previous.get('items', [])}
    by_id.update({entry['id']: entry for entry in manifest})
    old_substitutions = {tuple(entry) for entry in previous.get('nativeSmallCutSubstitutions', [])}
    report = {'items': list(by_id.values()), 'bodyProfiles': profiles,
              'nativeSmallCutSubstitutions': sorted(old_substitutions | substitutions)}
    write(manifest_path, json.dumps(report, indent=2))
    print(f'Imported {len(manifest)} base items ({len(NEW)} new), {len(report["items"])} total, four shared cuts, {len(races)} body profiles.')
    print('Native small-cut substitutions:', sorted(substitutions))


if __name__ == '__main__':
    main()
