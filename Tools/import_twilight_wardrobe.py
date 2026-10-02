"""Import a broad second wardrobe from Twilight-Axis without rewriting earlier items.

Usage: python Tools/import_twilight_wardrobe.py C:/Projects/Twilight-Axis
This converts assets and resource data. It does not build or launch the game.
"""

import argparse
import json
import re
from pathlib import Path

from PIL import ImageChops

from import_twilight_clothing import (
    EXISTING, NEW, PARENTS, PROTOTYPES, ROOT, SLEEVELESS, SLOTS, SOURCE_CLOTHING,
    TEXTURES, LOCALE, arm_masks, complete_floor_icon, inhands, names,
    save_compact_rsi, select_state, sleeves, worn,
)
from import_twilight_species import URL, tiles, write

# The source DM definitions supply names and descriptions. States without both are
# skipped, rather than passing off invented localization as Twilight text.
# (source DMI group, destination category, source states)
WARDROBE = [
    ('shirts', 'Uniforms/Shirts', [
        'apothshirt',
        'archivist',
        'artishirt',
        'blouse',
        'bluedress',
        'butlershirt',
        'courtesandress',
        'greendress',
        'jestershirt',
        'lowcut',
        'maiddressfancy',
        'maidgown',
        'nightgown',
        'noblecoat',
        'nobledress',
        'silkydress',
        'stewardtunic',
        'taverndress',
        'velvetdress',
        'wintercoat',
    ]),
    ('pants', 'Pants/Trousers', [
        'chainhose',
        'chainkilt',
        'dhoti',
        'hose',
        'leathertights',
        'loincloth',
        'monkpants',
        'paddedchausses',
        'roguepants',
        'sailorpants',
        'shalwar',
        'tights',
        'upchainhose',
    ]),
    ('pants', 'Pants/Skirts', [
        'formalskirt',
        'skirt',
        'chain_skirt',
        'baothaskirt',
    ]),
    ('pants', 'Pants/Armor', [
        'splintlegs',
        'bplatelegs',
        'ironsplintlegs',
    ]),
    ('armor', 'OuterClothing/Armor', [
        'brigandine',
        'light_brigandine',
        'haubergeon',
        'haubyrnie',
        'gambesonp',
        'leathercoat',
        'leathertunic',
        'studleather',
        'lamellar',
        'halfplate',
        'cuirbouilli',
        'roguearmor',
        'druidarmor',
        'workervest',
        'sailorvest',
        'monkleather',
        'longcoat',
        'winterjacket',
        'vest',
        'corset',
        'coat_of_plates',
        'ironplate',
        'hidearmor',
    ]),
    ('armor', 'OuterClothing/Robes', [
        'black_robe',
        'openrobe',
        'priestrobe',
        'monkcloth',
        'physcoat',
        'dendorrobe',
        'desertrobe',
        'magerobe',
        'white_robe',
    ]),
    ('head', 'Head/Hats', [
        'bandana',
        'bardhat',
        'chaperon',
        'circlet',
        'fisherhat',
        'headscarf',
        'knitcap',
        'papakha',
        'ricehat',
        'tophat',
        'tricorn',
        'turban',
        'witch',
        'veil',
    ]),
    ('head', 'Head/Hoods', [
        'fur_hood',
        'monkhood',
        'rain_hood',
    ]),
    ('head', 'Head/Helmets', [
        'bascinet',
        'barbute',
        'paddedarmingcap',
        'skullcap',
        'armet',
        'sallet',
        'knight',
        'hounskull',
    ]),
    ('feet', 'Shoes/Boots', [
        'blackboots',
        'furlinedboots',
        'ridingboots',
        'soldierboots',
        'nobleboots',
        'ancientboots',
        'bronzegreaves',
    ]),
    ('feet', 'Shoes/Misc', [
        'buckleshoes',
        'footwraps',
        'gladiator',
        'togasandals',
    ]),
    ('gloves', 'Hands/Gloves', [
        'clothwraps',
        'gauntlets',
        'paddedmitts',
        'roguegloves',
        'agauntlets',
        'bcgloves',
        'bplategloves',
        'feldgloves',
    ]),
    ('cloaks', 'Neck/Cloaks', [
        'bear_cloak',
        'dupatta',
        'poncho',
        'rain_cloak',
        'ranger',
        'ranger_gray',
        'scout_cloak',
        'shadowcloak',
        'thiefcloak',
        'toga',
        'tribal',
        'wardencloak',
        'wicker_cloak',
    ]),
    ('cloaks', 'Neck/Aprons', [
        'apron',
        'aproncook',
        'waistpron',
    ]),
    ('belts', 'Belt/Belts', [
        'blackbelt',
        'cloth',
        'rope',
        'silkbelt',
        'stewardbelt',
        'suspenders',
    ]),
]

PREFIX = {
    'shirts': 'ClothingUniform', 'pants': 'ClothingPants',
    'armor': 'ClothingOuter', 'head': 'ClothingHead',
    'feet': 'ClothingShoes', 'gloves': 'ClothingHands',
    'cloaks': 'ClothingNeck', 'belts': 'ClothingBelt',
}
ID_OVERRIDES = {'vest': 'ClothingOuterRoguetownVest'}

PARENTS['belts'] = 'ClothingBeltStorageBase'
SLEEVELESS.update({'vest', 'corset', 'workervest', 'sailorvest', 'hidearmor'})

ARMOR = {
    'Torso': {
        'light': {'brigandine', 'light_brigandine', 'gambesonp', 'leathercoat',
                  'leathertunic', 'studleather', 'cuirbouilli', 'roguearmor',
                  'druidarmor', 'monkleather', 'longcoat', 'hidearmor'},
        'medium': {'haubergeon', 'haubyrnie', 'lamellar', 'halfplate', 'coat_of_plates'},
        'heavy': {'ironplate'},
    },
    'Head': {
        'light': {'paddedarmingcap', 'skullcap'},
        'medium': {'bascinet', 'barbute', 'sallet'},
        'heavy': {'armet', 'knight', 'hounskull'},
    },
    'Leg': {
        'medium': {'chainhose', 'chainkilt', 'chain_skirt', 'splintlegs', 'ironsplintlegs'},
        'heavy': {'bplatelegs'},
    },
}
COEFFICIENTS = {
    'light': (0.9, 0.8, 0.9),
    'medium': (0.8, 0.7, 0.8),
    'heavy': (0.7, 0.6, 0.7),
}

SHIRT_DRESSES = {
    'bluedress', 'courtesandress', 'greendress', 'maiddressfancy',
    'maidgown', 'nightgown', 'nobledress', 'silkydress',
    'taverndress', 'velvetdress',
}
ARMOR_FILES = {
    'brigandines': {'brigandine', 'light_brigandine', 'coat_of_plates'},
    'gambesons': {'gambesonp'},
    'mail': {'haubergeon', 'haubyrnie', 'lamellar'},
    'leather': {'leathertunic', 'studleather', 'cuirbouilli', 'roguearmor',
                'druidarmor', 'monkleather', 'hidearmor'},
    'plate': {'halfplate', 'ironplate', 'leathercoat'},
    'vests': {'workervest', 'sailorvest', 'vest', 'corset'},
    'coats': {'longcoat', 'winterjacket'},
    'robes': {'black_robe', 'openrobe', 'priestrobe', 'monkcloth',
              'physcoat', 'dendorrobe', 'desertrobe', 'magerobe', 'white_robe'},
}

RESOURCE_MOVES = {
    'ClothingHandsChainGloves': ('Hands', 'gloves.yml'),
    'ClothingHeadArmingCap': ('Head', 'hats.yml'),
    'ClothingHeadLeatherHelm': ('Head', 'helmets.yml'),
    'ClothingHeadKettleHelm': ('Head', 'helmets.yml'),
    'ClothingHeadNasalHelm': ('Head', 'helmets.yml'),
    'ClothingNeckHalfCloak': ('Neck', 'cloaks.yml'),
    'ClothingNeckSnowCloak': ('Neck', 'cloaks.yml'),
    'ClothingOuterPlateHarness': ('OuterClothing', 'plate.yml'),
    'ClothingOuterSteelCuirass': ('OuterClothing', 'plate.yml'),
    'ClothingOuterTravelRobe': ('OuterClothing', 'robes.yml'),
    'ClothingPantsCloth': ('Pants', 'trousers.yml'),
    'ClothingPantsLeather': ('Pants', 'trousers.yml'),
    'ClothingPantsBaggy': ('Pants', 'trousers.yml'),
    'ClothingPantsChainLeggings': ('Pants', 'armor.yml'),
    'ClothingPantsPlateLeggings': ('Pants', 'armor.yml'),
    'ClothingShoesTravelSandals': ('Shoes', 'misc.yml'),
    'ClothingShoesSimpleLeather': ('Shoes', 'misc.yml'),
    'ClothingShoesPlateBoots': ('Shoes', 'boots.yml'),
    'ClothingUniformLinenShirt': ('Uniforms', 'shirts.yml'),
    'ClothingUniformShortShirt': ('Uniforms', 'shirts.yml'),
    'ClothingUniformTravelTunic': ('Uniforms', 'shirts.yml'),
    'ClothingOuterLeatherJerkin': ('OuterClothing', 'leather.yml'),
    'ClothingOuterGambeson': ('OuterClothing', 'gambesons.yml'),
    'ClothingOuterHauberk': ('OuterClothing', 'mail.yml'),
    'ClothingPantsChainhose': ('Pants', 'armor.yml'),
    'ClothingPantsChainkilt': ('Pants', 'armor.yml'),
    'ClothingPantsUpchainhose': ('Pants', 'armor.yml'),
}


def resource_file(group, state, asset):
    if group == 'shirts':
        if state in SHIRT_DRESSES:
            return 'dresses.yml'
        if state in {'noblecoat', 'wintercoat'}:
            return 'coats.yml'
        if state == 'archivist':
            return 'robes.yml'
        return 'shirts.yml'
    if group == 'armor':
        for filename, states in ARMOR_FILES.items():
            if state in states:
                return filename + '.yml'
        raise ValueError(f'Unclassified armor state: {state}')
    if group == 'pants' and state in {'chainhose', 'chainkilt', 'upchainhose'}:
        return 'armor.yml'
    family = asset.split('/')[1].lower()
    return family + '.yml'


def write_grouped_resources(root, groups, identifiers, extension):
    for path in root.rglob('*' + extension):
        original = path.read_text(encoding='utf-8')
        if extension == '.yml':
            blocks = re.split(r'(?=^- type: )', original, flags=re.M)
            identifier_pattern = r'(?m)^  id: (\S+)'
        else:
            blocks = re.split(r'(?=^ent-)', original, flags=re.M)
            identifier_pattern = r'^ent-(\S+)\s*='
        kept = []
        for block in blocks:
            found = re.search(identifier_pattern, block)
            if not found or found.group(1) not in identifiers:
                kept.append(block)
        if len(kept) == len(blocks):
            continue
        content = ''.join(kept).strip()
        if content:
            write(path, content)
        else:
            path.unlink()
    for (slot, filename), blocks in groups.items():
        path = root / slot / filename.replace('.yml', extension)
        previous = path.read_text(encoding='utf-8').rstrip() if path.exists() else ''
        content = (previous + '\n\n' if previous else '') + '\n'.join(blocks)
        write(path, content)


def organize_existing_resources():
    for root, extension in ((PROTOTYPES, '.yml'), (LOCALE, '.ftl')):
        groups = {}
        found = set()
        for path in root.rglob('*' + extension):
            content = path.read_text(encoding='utf-8')
            if extension == '.yml':
                blocks = re.split(r'(?=^- type: )', content, flags=re.M)
                pattern = r'(?m)^  id: (\S+)'
            else:
                blocks = re.split(r'(?=^ent-)', content, flags=re.M)
                pattern = r'^ent-(\S+)\s*='
            for block in blocks:
                match = re.search(pattern, block)
                if not match or match.group(1) not in RESOURCE_MOVES:
                    continue
                identifier = match.group(1)
                slot, filename = RESOURCE_MOVES[identifier]
                if extension == '.ftl':
                    slot = slot.lower()
                    filename = filename.replace('.yml', '.ftl')
                groups.setdefault((slot, filename), []).append(block.strip() + '\n')
                found.add(identifier)
        write_grouped_resources(root, groups, found, extension)


def twilight_strings(source):
    """Resolve static BYOND text and icon files through the type hierarchy."""
    definitions = {}
    folder = source / 'code/modules/clothing/rogueclothes'
    for path in sorted(folder.rglob('*.dm')):
        source_text = path.read_text(encoding='utf-8-sig', errors='replace')
        blocks = list(re.finditer(r'(?m)^(/obj/item/(?:clothing|storage/belt)/[\w/]+)\s*$', source_text))
        for index, match in enumerate(blocks):
            end = blocks[index + 1].start() if index + 1 < len(blocks) else len(source_text)
            body = source_text[match.end():end]
            # Only top-level static assignments belong to the declared type.
            body = body.split('\n/', 1)[0]
            fields = dict(re.findall(
                r'(?m)^\t(name|desc|icon_state|icon|mob_overlay_icon|parent_type)\s*=\s*'
                r'("(?:\\\r?\n[ \t]*|\\.|[^"\n])*"|\x27[^\x27\n]*\x27|/obj/item/[\w/]+)', body
            ))
            if fields:
                key = match.group(1)
                record = definitions.setdefault(key, {'sourceFile': path.relative_to(source).as_posix()})
                record.update(fields)

    def inherited(key, field):
        for _ in range(20):
            data = definitions.get(key, {})
            if field in data:
                return re.sub(r'\\\r?\n[ \t]*', ' ', data[field].strip('"\x27')).replace('\\"', '"')
            parent = data.get('parent_type', key.rsplit('/', 1)[0])
            if parent == key:
                break
            key = parent
        return ''

    by_state = {}
    for source_type, fields in definitions.items():
        state = fields.get('icon_state', '').strip('"')
        if not state:
            continue
        icon = inherited(source_type, 'icon')
        if not icon.startswith('icons/roguetown/clothing/'):
            continue
        group = icon.rsplit('/', 1)[-1].removesuffix('.dmi')
        if group not in PREFIX:
            continue
        overlay = inherited(source_type, 'mob_overlay_icon')
        if overlay and overlay != f'icons/roguetown/clothing/onmob/{group}.dmi':
            continue
        name, desc = inherited(source_type, 'name'), inherited(source_type, 'desc')
        if name and desc:
            # Preserve Twilight wording; only flatten source line-break markup for FTL.
            desc = re.sub(r'\s+', ' ', re.sub(r'</?br\s*/?>', ' ', desc, flags=re.I)).strip()
            by_state.setdefault((group, state), (name, desc, source_type, fields['sourceFile']))
    return by_state


def save_sprite(destination, states, sources):
    save_compact_rsi(destination, states, sources)
    metadata_path = destination / 'meta.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata['copyright'] = f'Twilight Fortress SS13 contributors ({URL})'
    write(metadata_path, json.dumps(metadata, indent=2))


def sync_base_locales(strings):
    combined = {'ClothingUniformTraveler', 'ClothingUniformExplorer', 'ClothingUniformRags'}
    replacements = {}
    for identifier, _, group, state, *_ in EXISTING + NEW:
        if identifier in combined or (group, state) not in strings:
            continue
        name, desc, *_ = strings[group, state]
        replacements[identifier] = (name, desc)
    found = set()
    for path in LOCALE.rglob('*.ftl'):
        if path.name.startswith('twilight_'):
            continue
        content = path.read_text(encoding='utf-8')
        for identifier, (name, desc) in replacements.items():
            pattern = rf'(?m)^ent-{re.escape(identifier)} = [^\n]*\n    \.desc = [^\n]*'
            content, count = re.subn(pattern, lambda _: f'ent-{identifier} = {name}\n    .desc = {desc}', content)
            if count:
                found.add(identifier)
        write(path, content)
    missing = set(replacements) - found
    if missing:
        raise ValueError(f'Missing base localization: {sorted(missing)}')


def sync_sprite_credits():
    for path in TEXTURES.rglob('meta.json'):
        metadata = json.loads(path.read_text(encoding='utf-8'))
        if metadata.get('copyright', '').startswith(f'Converted from {URL}'):
            metadata['copyright'] = f'Twilight Fortress SS13 contributors ({URL})'
            write(path, json.dumps(metadata, indent=2))


def items(source):
    strings = twilight_strings(source)
    for group, category, entries in WARDROBE:
        for state in entries:
            if (group, state) not in strings:
                continue
            name, description, source_type, source_file = strings[group, state]
            identifier = ID_OVERRIDES.get(state) or PREFIX[group] + ''.join(
                part.capitalize() for part in re.split(r'[^a-zA-Z0-9]+', state) if part
            )
            asset = category + '/' + state
            yield identifier, asset, group, state, name, description, source_type, source_file


def item_prototype(entry, has_sleeves):
    identifier, asset, group, state, name, description = entry[:6]
    sprite = '_Amberfall/Clothing/' + asset + '.rsi'
    text = (f'- type: entity\n  parent: {PARENTS[group]}\n  id: {identifier}\n'
            f'  components:\n  - type: Sprite\n    sprite: {sprite}\n    state: icon\n'
            f'  - type: Item\n    sprite: {sprite}\n'
            f'  - type: Clothing\n    sprite: {sprite}\n    bodyProfile: true\n')
    if group in ('shirts', 'armor'):
        layer = 'shirt' if group == 'shirts' else 'armor'
        text += f'    wornLayer: {layer}Body\n'
        if has_sleeves:
            text += (f'    sleeveSprite: _Amberfall/Clothing/{asset}_sleeves.rsi\n'
                     f'    sleeveState: equipped-SLEEVES\n    sleeveLayer: {layer}Sleeves\n')
    elif group == 'pants':
        text += '    wornLayer: pantsBody\n'
    elif group == 'cloaks':
        text += '    wornLayer: cloakBehind\n'
    for part, tiers in ARMOR.items():
        for tier, states in tiers.items():
            if state not in states:
                continue
            blunt, slash, piercing = COEFFICIENTS[tier]
            text += (f'  - type: Armor\n    coverage: [ {part} ]\n'
                     '    modifiers:\n      coefficients:\n'
                     f'        Blunt: {blunt}\n        Slash: {slash}\n'
                     f'        Piercing: {piercing}\n')
    locale = f'ent-{identifier} = {name}\n    .desc = {description}\n'
    return text, locale


def inspect_catalog(source, entries):
    existing = {item[0] for item in EXISTING + [e[:4] for e in NEW]}
    new_ids = [entry[0] for entry in entries]
    if len(new_ids) != len(set(new_ids)) or existing.intersection(new_ids):
        raise ValueError('Duplicate wardrobe ID')
    manifest_path = ROOT / 'Resources/Prototypes/_Amberfall/Clothing/port_manifest.json'
    imported = {entry['id'] for entry in json.loads(manifest_path.read_text(encoding='utf-8'))['items']}
    for path in (ROOT / 'Resources/Prototypes').rglob('*.yml'):
        old = set(re.findall(r'(?m)^\s+id: (\S+)', path.read_text(encoding='utf-8')))
        clash = old.intersection(new_ids)
        if path.is_relative_to(PROTOTYPES):
            clash -= imported
        if clash:
            raise ValueError(f'Prototype ID collision in {path}: {sorted(clash)}')
    for entry in entries:
        _, _, group, state, *_ = entry
        floor = source / SOURCE_CLOTHING / (group + '.dmi')
        onmob = source / SOURCE_CLOTHING / 'onmob' / (group + '.dmi')
        if state not in names(floor):
            raise ValueError(f'Missing floor state: {floor}: {state}')
        for cut, small in (('', False), ('_f', False), ('', True), ('_f', True)):
            select_state(onmob, state, cut, small, set())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    source = parser.parse_args().source
    strings = twilight_strings(source)
    entries = list(items(source))
    inspect_catalog(source, entries)
    sync_base_locales(strings)

    manifest_path = ROOT / 'Resources/Prototypes/_Amberfall/Clothing/port_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    by_id = {entry['id']: entry for entry in manifest['items']}
    yaml_groups, locale_groups = {}, {}
    substitutions = set()
    for entry in entries:
        identifier, asset, group, state, *_ = entry
        output = TEXTURES / (asset + '.rsi')
        icon = tiles(source / SOURCE_CLOTHING / (group + '.dmi'), state)
        states = {'icon': icon}
        complete_floor_icon(states)
        states.update(inhands(states['icon']))
        make_sleeves = group in ('shirts', 'armor') and state not in SLEEVELESS
        sleeve_states = {}
        variants = []
        for suffix, body, sex, cut, small in (
            ('', 'Human', 'm', '', False),
            ('_f', 'Human', 'f', '_f', False),
            ('_dwarf', 'MountainDwarf', 'm', '', True),
            ('_f_dwarf', 'MountainDwarf', 'f', '_f', True),
        ):
            frames, selected = worn(source, group, state, cut, small, (0, 0), substitutions)
            if make_sleeves:
                sleeve = sleeves(source, group, selected, frames, body, sex, (0, 0))
                sleeve_states['equipped-SLEEVES' + suffix] = sleeve
                for index in range(4):
                    alpha = ImageChops.subtract(frames[index].getchannel('A'),
                                                sleeve[index].getchannel('A'))
                    frames[index].putalpha(alpha)
            if group == 'belts':
                for frame, mask in zip(frames, arm_masks(body, sex, True)):
                    frame.putalpha(ImageChops.subtract(frame.getchannel('A'), mask))
            states['equipped-' + SLOTS[group] + suffix] = frames
            variants.append({'suffix': suffix, 'sourceState': selected})
        if make_sleeves and not any(
            frame.getchannel('A').getbbox() for frames in sleeve_states.values() for frame in frames
        ):
            make_sleeves = False
        sources = [SOURCE_CLOTHING + group + '.dmi',
                   SOURCE_CLOTHING + 'onmob/' + group + '.dmi']
        save_sprite(output, states, sources)
        if make_sleeves:
            helper = SOURCE_CLOTHING + 'onmob/helpers/sleeves_' + group + '.dmi'
            sleeve_sources = [sources[1]]
            if (source / helper).exists():
                sleeve_sources.append(helper)
            save_sprite(TEXTURES / (asset + '_sleeves.rsi'), sleeve_states, sleeve_sources)
        yaml, locale = item_prototype(entry, make_sleeves)
        slot = asset.split('/')[0]
        filename = resource_file(group, state, asset)
        key = (slot, filename)
        yaml_groups.setdefault(key, []).append(yaml)
        locale_groups.setdefault((slot.lower(), filename.replace('.yml', '.ftl')), []).append(locale)
        by_id[identifier] = {'id': identifier, 'sprite': asset,
                             'sourceType': entry[6], 'sourceFile': entry[7],
                             'variants': variants}

    identifiers = {entry[0] for entry in entries}
    write_grouped_resources(PROTOTYPES, yaml_groups, identifiers, '.yml')
    write_grouped_resources(LOCALE, locale_groups, identifiers, '.ftl')
    organize_existing_resources()
    sync_sprite_credits()
    manifest['items'] = list(by_id.values())
    manifest['nativeSmallCutSubstitutions'] = sorted(
        {tuple(entry) for entry in manifest.get('nativeSmallCutSubstitutions', [])} | substitutions
    )
    write(manifest_path, json.dumps(manifest, indent=2))
    print(f'Imported {len(entries)} additional items; total {len(manifest["items"])}.')


if __name__ == '__main__':
    main()
