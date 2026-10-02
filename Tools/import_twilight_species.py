"""Port playable Twilight species, default bodies and racial markings.

Usage: python Tools/import_twilight_species.py C:/Projects/Twilight-Axis
Only writes generated files under Resources/*/_Amberfall. Human's previously
approved mm.dmi body is deliberately retained. No game build or tests are run.
"""

import argparse
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
import re

from PIL import Image

from dmi_static_to_rsi import read_dmi

ROOT = Path(__file__).resolve().parents[1]
PROTOS = ROOT / 'Resources/Prototypes/_Amberfall'
TEXTURES = ROOT / 'Resources/Textures/_Amberfall/Mobs'
LOCALE = ROOT / 'Resources/Locale/en-US/_Amberfall/species'
URL = 'https://github.com/Twilight-Fortress-SS13/Twilight-Axis'

# Real SS14 species ID, DM type, category, concise appearance description.
RACES = [
    ('Human', 'human/northern', 'Humankind', 'Humans of the northern lands, with varied complexions and sturdy builds.'),
    ('Dwarf', 'dwarf/mountain', 'Dwarven', 'Short, broad mountain folk with stocky limbs and a long tradition of craftsmanship.'),
    ('Gnome', 'dwarf/gnome', 'Dwarven', 'Small relatives of dwarves with compact bodies and an inquisitive nature.'),
    ('WoodElf', 'elf/wood', 'Elven', 'Slender woodland elves with long ears and an affinity for the forest.'),
    ('SunElf', 'elf/sun', 'Elven', 'Graceful elves with pointed ears and the warm complexions of their sunlit homelands.'),
    ('DarkElf', 'elf/dark', 'Elven', 'Elves of the Underdark, distinguished by dark complexions and pointed ears.'),
    ('HalfElf', 'human/halfelf', 'Humankind', 'People of mixed human and elven ancestry, bearing the features of both.'),
    ('HalfOrc', 'halforc', 'Humankind', 'Muscular people of mixed human and orc ancestry, with pointed ears and tusks.'),
    ('HalfKin', 'demihuman', 'Humankind', 'Human-shaped folk whose animal ancestry appears in their ears, tails or other features.'),
    ('Aasimar', 'aasimar', 'Godtouched', 'Mortals marked by celestial ancestry, sometimes bearing wings and other divine features.'),
    ('Tiefling', 'tieberian', 'Godtouched', 'Descendants of infernal bloodlines, with distinctive skin tones, horns and tails.'),
    ('Revenant', 'dullahan', 'Godtouched', 'Returned souls inhabiting pale, death-touched humanoid bodies.'),
    ('MetalConstruct', 'construct/metal', 'Godtouched', 'Humanoid works of artifice assembled from metal and animated by arcane power.'),
    ('Goblin', 'goblinp', 'Godtouched', 'Small, wiry folk with large pointed ears and a wide range of earthy skin tones.'),
    ('Murkling', 'ooze', None, 'Sentient ooze from the Underdark that has taken a mutable humanoid shape.'),
    ('WildKin', 'anthromorph', 'Beastvolk', 'Beastfolk whose fur, scales, ears, snouts and tails reflect diverse animal ancestry.'),
    ('Verminvolk', 'anthromorphsmall', 'Beastvolk', 'Small beastfolk with compact bodies and diverse animal features.'),
    ('Tabaxi', 'tabaxi', 'Beastvolk', 'Feline beastfolk with fur, expressive ears, a short muzzle and a catlike tail.'),
    ('Venardine', 'vulpkanin', 'Beastvolk', 'Foxlike beastfolk with pointed ears, a narrow muzzle and a bushy tail.'),
    ('Lupian', 'lupian', 'Beastvolk', 'Canine beastfolk with prominent muzzles, alert ears and fur-covered bodies.'),
    ('Axian', 'akula', 'Beastvolk', 'Aquatic beastfolk with sharklike features, fins and a powerful tail.'),
    ('Fluvian', 'moth', 'Beastvolk', 'Mothlike folk with insectile eyes, antennae and patterned wings.'),
    ('Zardman', 'lizardfolk', 'Zard', 'Reptilian folk with scaled bodies, elongated snouts and sturdy tails.'),
    ('Drakian', 'dracon', 'Zard', 'Draconic folk with reptilian features, horns, tails and wings.'),
    ('Kobold', 'kobold', 'Zard', 'Small reptilian folk with compact bodies, snouts and horns.'),
    ('AuRa', 'aura', None, 'Horned humanoids with patterned scales and a reptilian tail, hailing from Kazengun.'),
]
CATEGORIES = {
    'Humankind': ('Humankind', 'Human'), 'Dwarven': ('Dwarven folk', 'Dwarf'),
    'Elven': ('Elves', 'WoodElf'), 'Godtouched': ('Godtouched', 'Aasimar'),
    'Beastvolk': ('Beastvolk', 'WildKin'), 'Zard': ('Zard', 'Zardman'),
}
FEATURES = {'ears': 'HeadSide', 'horns': 'HeadTop', 'snout': 'Snout',
            'tail': 'Tail', 'wings': 'Wings', 'neck_feature': 'SnoutCover', 'antennas': 'HeadTop'}
BODY_PARTS = {'Torso': 'torso', 'Head': 'head', 'ArmLeft': 'l_arm', 'ArmRight': 'r_arm',
              'HandLeft': 'l_hand', 'HandRight': 'r_hand', 'LegLeft': 'l_leg',
              'LegRight': 'r_leg', 'FootLeft': 'l_foot', 'FootRight': 'r_foot'}
MISSING_SOURCE_STATES = []


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + '\n', encoding='utf-8')


def pascal(value):
    return ''.join(p[:1].upper() + p[1:] for p in re.split(r'[^A-Za-z0-9]+', value) if p)


def unquote(value):
    return value.strip().strip('\"\'')


class DM:
    """Read the declarative type fields needed by this importer, not DM procedures."""
    def __init__(self, source):
        self.source = source
        self.blocks = {}
        self.files = {}
        directories = ['code/modules/mob/living/carbon/human/species_types',
                       'code/modules/client/customizer/customizers/organ',
                       'code/modules/mob/dead/new_player/sprite_accessory']
        paths = [source / 'code/modules/mob/living/carbon/human/species.dm']
        for directory in directories:
            paths.extend(sorted((source / directory).rglob('*.dm')))
        for directory in ('modular', 'modular_deserttown', 'modular_twilight_axis'):
            paths.extend(sorted((source / directory).rglob('*.dm')))
        for path in paths:
            text = path.read_text(encoding='utf-8-sig')
            # Commented-out customizers must not enter the port.
            text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
            text = re.sub(r'(?m)^\s*//.*$', '', text)
            blocks = re.split(r'(?m)^(?=/)', text)
            for block in blocks:
                header, _, body = block.partition('\n')
                header = header.split('//')[0].strip()
                if re.fullmatch(r'/datum/[\w/]+', header.strip()):
                    key = header.strip()
                    self.blocks[key] = self.blocks.get(key, '') + '\n' + body
                    self.files[key] = path.relative_to(source).as_posix()
        self.defines = {}
        for path in (source / 'code/__DEFINES').rglob('*.dm'):
            text = path.read_text(encoding='utf-8-sig')
            text = text.replace('\\\n', '')
            for match in re.finditer(r'(?m)^#define[ \t]+(\w+)[ \t]+([^\n]+)', text):
                self.defines[match[1]] = match[2]

    @lru_cache(None)
    def fields(self, key):
        if not key or key == '/datum':
            return {}
        body = self.blocks.get(key, '')
        matches = list(re.finditer(r'(?m)^\t(?:var/(?:list/)?)?([a-z]\w*)\s*=\s*', body))
        local = {}
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            value = body[match.end():end].strip()
            # Strip trailing procedure text, preprocessor directives and comments.
            value = re.split(r'\n(?=[/#])', value)[0]
            if not value.startswith(('list(', 'sortList(')):
                value = value.split('\n')[0].split(' //')[0].strip()
            local[match[1]] = value
        parent = local.get('parent_type', key.rsplit('/', 1)[0])
        return dict(self.fields(parent), **local)

    def offsets(self, fields, sex):
        table = fields.get('offset_features', '')
        build = fields.get('default_body_build_' + sex)
        if build:
            table = 'OFFSET_FEATURES_' + build.removeprefix('BODY_BUILD_') + '_REFERENCE'
        table = self.defines.get(table, table)
        values = dict((key, (int(x), int(y))) for key, x, y in
                      re.findall(r'(OFFSET_\w+)\s*=\s*list\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', table))
        suffix = '_F' if sex == 'f' else ''
        return {key.removeprefix('OFFSET_').removesuffix(suffix) if suffix else key.removeprefix('OFFSET_'): val
                for key, val in values.items() if key.endswith('_F') == (sex == 'f')}


@lru_cache(None)
def dmi(path):
    return read_dmi(Path(path))


def tiles(source, state):
    image, width, height, columns, states = dmi(str(source))
    matches = [entry for entry in states if entry[0] == state]
    if not matches:
        raise ValueError(f'{source}: missing {state!r} state')
    # A few source DMIs contain duplicate names; the last definition wins.
    _, offset, directions, frames = matches[-1]
    if directions not in (1, 4, 8):
        raise ValueError(f'Unsupported directions: {source}: {state}')
    result = []
    # Static standing anatomy: use the first frame, preserving S/N/E/W ordering.
    for direction in range(4):
        index = offset + (direction if directions > 1 else 0)
        result.append(image.crop((index % columns * width, index // columns * height,
                                  index % columns * width + width, index // columns * height + height)))
    return result


def blank(size=32):
    return [Image.new('RGBA', (size, size)) for _ in range(4)]


def shifted(frames, offset):
    x, y = offset
    result = []
    for frame in frames:
        out = Image.new('RGBA', frame.size)
        out.paste(frame, (x, -y))
        result.append(out)
    return result


def composite(a, b):
    return [Image.alpha_composite(x, y) for x, y in zip(a, b)]


def save_rsi(destination, states, sources, size=32):
    destination.mkdir(parents=True, exist_ok=True)
    metadata = {'version': 1, 'license': 'CC-BY-SA-3.0',
                'copyright': f'Converted from {URL}: ' + ', '.join(sorted(set(sources))),
                'size': {'x': size, 'y': size}, 'states': []}
    for name, frames in states.items():
        sheet = Image.new('RGBA', (size * 2, size * 2))
        for i, frame in enumerate(frames):
            sheet.paste(frame, (i % 2 * size, i // 2 * size))
        sheet.save(destination / (name + '.png'))
        metadata['states'].append({'name': name, 'directions': 4})
    write(destination / 'meta.json', json.dumps(metadata, indent=2))


def import_body(source, key, male, female, offsets, moth=False):
    states = {}
    for sex, relative in [('m', male), ('f', female)]:
        path = source / relative
        names = {s[0] for s in dmi(str(path))[4]}
        for part, target in BODY_PARTS.items():
            state = {'Torso': 'chest', 'Head': 'head'}.get(part, target)
            # fcom.dmi draws the hands as part of its arms, with no separate hand states.
            integrated_hand = relative.endswith('/fcom.dmi') and 'Hand' in part
            frames = blank() if 'Foot' in part or integrated_hand else tiles(path, state)
            if key == 'AuRa' and part in ('Torso', 'ArmLeft', 'ArmRight', 'LegLeft', 'LegRight'):
                # Au Ra's default scale pattern is part of its racial appearance.
                scales = 'modular_twilight_axis/icons/mob/body_markings/aura_markings.dmi'
                frames = composite(frames, tiles(source / scales, f'z_{state}_{sex}'))
            if 'Leg' in part and state + '_above' in names:
                frames = composite(frames, tiles(path, state + '_above'))
            out_name = target + ('_' + sex if part in ('Torso', 'Head') else ('_f' if sex == 'f' else ''))
            states[out_name] = frames
        states['r_leg_above' + ('_f' if sex == 'f' else '')] = (
            tiles(path, 'r_leg_above') if 'r_leg_above' in names else blank())
    states['tail'] = blank()
    states['wings'] = blank()
    # Base state is also used for severed parts and generic sprite consumers.
    states['head'] = states['head_m']
    states['torso'] = states['torso_m']
    assembled = blank()
    for name in ('torso_m', 'head_m', 'r_leg', 'l_leg', 'r_leg_above', 'r_arm', 'l_arm', 'r_hand', 'l_hand'):
        assembled = composite(assembled, states[name])
    states['full'] = assembled
    sources = [male, female]
    if key == 'AuRa':
        sources.append('modular_twilight_axis/icons/mob/body_markings/aura_markings.dmi')
    save_rsi(TEXTURES / key / 'parts.rsi', states, sources)
    eye_path = 'icons/mob/sprite_accessory/eyes/eyes.dmi'
    base = 'moth' if moth else 'human'
    eye = composite(tiles(source / eye_path, base + '_1'), tiles(source / eye_path, base + '_2'))
    save_rsi(TEXTURES / key / 'eyes.rsi',
             {'eyes': shifted(eye, offsets['m'].get('FACE', (0, 0))),
              'eyes_f': shifted(eye, offsets['f'].get('FACE', (0, 0))), 'no_eyes': blank()}, [eye_path])
    return states


def marking_id(key):
    return pascal(key.removeprefix('/datum/sprite_accessory/'))


def group_id(body):
    # The existing NPC kobold has a separate markings group named Kobold.
    return 'KoboldMarkings' if body == 'Kobold' else body


def accessory(dm, key, kind):
    fields = dm.fields(key)
    path = unquote(fields['icon'])
    base = unquote(fields['icon_state'])
    available = {state[0] for state in dmi(str(dm.source / path))[4]}
    layers = re.findall(r'BODY_(\w+)_LAYER', fields.get('relevant_layers', '')) or ['']
    layers = ['BEHIND' if layer == 'BEHIND' else 'FFRONT' if layer == 'FRONT_FRONT' else layer for layer in layers]
    # Au Ra's resting tail is an unsplit state although its DM type requests
    # FRONT/BEHIND states. Use the existing resting art, not a missing state.
    if base in available and not any(s.startswith(base + '_FRONT') or s.startswith(base + '_BEHIND') for s in available):
        layers = ['']
    colors = int(fields.get('color_keys', '1'))
    _, width, height, _, _ = dmi(str(dm.source / path))
    x = int(fields.get('pixel_x', '0'))
    y = int(fields.get('pixel_y', '0'))
    # Symmetric canvas around the humanoid's center, large enough to preserve
    # oversized ears/wings and their BYOND bottom-left origin without clipping.
    extent = max(32, width + abs(2 * x + width - 32), height + abs(2 * y + height - 32))
    size = (extent + 31) // 32 * 32
    states = {}
    overrides = {}
    for layer in layers:
        name = base + ('_' + layer if layer else '')
        names = [name + ('_' + str(i + 1) if colors > 1 else '') for i in range(colors)]
        if fields.get('extra_state') == 'TRUE':
            names.append(name + '_extra')
        for state in names:
            if state not in available:
                # BYOND renders absent color/layer states as transparent. Preserve
                # that behavior, and record source omissions for future art fixes.
                MISSING_SOURCE_STATES.append({'accessory': key, 'file': path, 'state': state})
                continue
            frames = tiles(dm.source / path, state)
            centered = []
            for frame in frames:
                canvas = Image.new('RGBA', (size, size))
                canvas.paste(frame, ((size - 32) // 2 + x, (size + 32) // 2 - frame.height - y))
                centered.append(canvas)
            states[state] = centered
            if layer in ('BEHIND', 'UNDER'):
                overrides[state] = {'tail': 'tailBehind', 'wings': 'wingsBehind'}.get(kind, 'markingsBehind')
    ident = marking_id(key)
    if not states:
        return None
    save_rsi(TEXTURES / 'Markings' / (ident + '.rsi'), states, [path], size=size)
    return ident, unquote(fields.get('name', base)), states, overrides


def feature_options(dm, fields):
    result = defaultdict(list)
    defaults = {}
    for customizer in re.findall(r'/datum/customizer/organ/[\w/]+', fields.get('customizers', '')):
        kind = customizer.split('/')[4]
        if kind not in FEATURES:
            continue
        settings = dm.fields(customizer)
        choices = re.findall(r'/datum/customizer_choice/[\w/]+', settings.get('customizer_choices', ''))
        for choice in choices:
            options = re.findall(r'/datum/sprite_accessory/[\w/]+', dm.fields(choice).get('sprite_accessories', ''))
            result[kind].extend(option for option in options if option not in result[kind])
            if options and settings.get('default_disabled', 'FALSE') != 'TRUE':
                defaults.setdefault(kind, options[0])
    return dict(result), defaults


def vector(value):
    return f'{value[0] / 32:g}, {value[1] / 32:g}'


def organ_offsets(offsets, layers):
    feature_offset = {'Hair': 'HEAD', 'FacialHair': 'FACE', 'HeadSide': 'FACE', 'HeadTop': 'FACE',
                      'Snout': 'FACE', 'SnoutCover': 'NECK', 'Tail': 'UNDIES', 'Wings': 'BACK'}
    text = ''
    for sex, field in [('m', 'layerOffsets'), ('f', 'femaleLayerOffsets')]:
        text += f'    {field}:\n'
        for layer in layers:
            text += f'      {layer}: {vector(offsets[sex].get(feature_offset[layer], (0, 0)))}\n'
    return text


def generate_body(key, species, offsets, features):
    sprite = f'_Amberfall/Mobs/{key}/parts.rsi'
    dwarf_components = '''  - type: Mutatable
    dormant: [ MutationDwarfism, MutationRockEater ]
  - type: ScaleVisuals
    scale: 1, 1
  - type: Fixtures
    fixtures:
      fix1:
        shape: !type:PhysShapeCircle
          radius: 0.35
        density: 120
        restitution: 0.0
        mask: [ MobMask ]
        layer: [ MobLayer ]
  - type: Vocal
    emoteSounds: UnisexDwarf
  - type: ReplacementAccent
    accent: dwarf
  - type: Speech
    speechSounds: Bass
''' if species == 'Dwarf' else ''
    text = f'''
- type: entity
  parent: BaseSpeciesAppearance
  id: Appearance{key}
  name: {key} appearance
  categories: [ HideSpawnMenu ]
  components:
  - type: InitialBody
    organs:
'''
    parts = list(BODY_PARTS)
    if 'tail' in features:
        parts.append('Tail')
    if 'wings' in features:
        parts.append('Wings')
    for part in parts + ['Eyes']:
        text += f'      {part}: Organ{key}{part}\n'
    for part in ['Brain', 'Tongue', 'Appendix', 'Ears', 'Lungs', 'Heart', 'Stomach', 'Liver', 'Kidneys']:
        organ_race = 'Dwarf' if species == 'Dwarf' and part in ('Heart', 'Stomach', 'Liver') else 'Human'
        text += f'      {part}: Organ{organ_race}{part}\n'
    text += f'''  - type: HumanoidProfile
    species: {species}

- type: entity
  parent: [ Appearance{key}, BaseSpeciesMobOrganic ]
  id: Mob{key}
  name: {key}
  components:
{dwarf_components}
  - type: Butcherable
    spawned:
    - id: FoodMeatHuman
      amount: 5
    - id: MaterialBones1
      amount: 3

- type: entity
  parent: OrganHumanExternal
  id: Organ{key}External
  abstract: true
  components:
  - type: Sprite
    sprite: {sprite}
  - type: VisualOrgan
    data:
      sprite: {sprite}
  - type: VisualOrganMarkings
    markingData:
      group: {group_id(key)}
'''
    for part in parts:
        parents = [f'OrganBase{part}', f'Organ{key}External']
        if part in ('Head', 'Torso'):
            parents.insert(0, f'OrganBase{part}Sexed')
        text += f'\n- type: entity\n  parent: [ {", ".join(parents)} ]\n  id: Organ{key}{part}\n'
        components = ''
        if part == 'Torso' and ('tail' in features or 'wings' in features):
            slots = ['Head', 'ArmLeft', 'ArmRight', 'LegLeft', 'LegRight', 'Appendix', 'Lungs', 'Heart', 'Stomach', 'Liver', 'Kidneys']
            slots += [s for s in ('Tail', 'Wings') if s.lower() in features]
            components += '  - type: BodyPart\n    slots: [ ' + ', '.join(slots) + ' ]\n'
        if part in BODY_PARTS and part not in ('Head', 'Torso'):
            components += f'  - type: VisualOrgan\n    sexStateOverrides:\n      Male: {BODY_PARTS[part]}\n      Female: {BODY_PARTS[part]}_f\n'
            if part == 'LegRight':
                components += '    overlayLayer: rLegAbove\n    overlayState: r_leg_above\n    overlaySexStateOverrides:\n      Female: r_leg_above_f\n'
        if part == 'Head':
            layers = ['Hair', 'FacialHair', 'HeadSide', 'HeadTop', 'Snout', 'SnoutCover']
            components += '  - type: VisualOrganMarkings\n' + organ_offsets(offsets, layers)
            components += '    hideableLayers:\n' + ''.join(f'    - enum.HumanoidVisualLayers.{layer}\n' for layer in layers)
        if part in ('Tail', 'Wings'):
            components += '  - type: VisualOrganMarkings\n' + organ_offsets(offsets, [part])
            components += f'    hideableLayers: [ enum.HumanoidVisualLayers.{part} ]\n'
        if components:
            text += '  components:\n' + components
    text += f'''
- type: entity
  parent: OrganHumanEyes
  id: Organ{key}Eyes
  components:
  - type: VisualOrgan
    data:
      sprite: _Amberfall/Mobs/{key}/eyes.rsi
    sexStateOverrides:
      Male: eyes
      Female: eyes_f
'''
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    dm = DM(args.source)
    catalog = []
    accessories = defaultdict(set)
    defaults_by_race = {}
    feature_sets = {}
    locale = []
    for species, source_type, category, description in RACES:
        type_path = '/datum/species/' + source_type
        fields = dm.fields(type_path)
        key = 'MountainDwarf' if species == 'Dwarf' else species
        options, defaults = feature_options(dm, fields)
        for kind, entries in options.items():
            for entry in entries:
                accessories[(kind, entry)].add(group_id(key))
        feature_sets[species] = options
        defaults_by_race[species] = defaults
        offsets = {sex: dm.offsets(fields, sex) for sex in ('m', 'f')}
        name = unquote(fields.get('sub_name', fields['name']))
        if species == 'Human':
            name = 'Northern Human'
        male, female = [unquote(fields['limbs_icon_' + sex]) for sex in ('m', 'f')]
        body_sources = {'m': male, 'f': female}
        for sex in ('m', 'f'):
            build = fields.get('default_body_build_' + sex)
            if build:
                build_type = '/datum/body_build/' + build.removeprefix('BODY_BUILD_').lower()
                body_sources[sex] = unquote(dm.fields(build_type)['limbs_icon_' + sex])
        male, female = body_sources['m'], body_sources['f']
        # Human is already imported using the regular, not tall or elven, body.
        if species == 'Human':
            male = 'icons/roguetown/mob/bodies/m/mm.dmi'
        else:
            import_body(args.source, key, male, female, offsets, species == 'Fluvian')
            write(PROTOS / 'Body/Species' / (species.lower() + '.yml'), generate_body(key, species, offsets, options))
        color = unquote(fields.get('default_color', 'FFFFFF'))
        color = color if re.fullmatch(r'[0-9a-fA-F]{6}', color) else 'FFFFFF'
        # Representative initial complexions; the color picker remains available.
        color = {'DarkElf': '74617F', 'Tiefling': 'BF594D', 'Goblin': '7B8D54', 'HalfOrc': '83915C',
                 'MetalConstruct': 'BABBB9', 'Revenant': 'B5BDC4', 'Tabaxi': 'C99E6C',
                 'Venardine': 'C68C63', 'Lupian': '85817E', 'Axian': '869FA9',
                 'Zardman': '789360', 'Drakian': '9B5656', 'Kobold': '9A7452'}.get(species, color)
        if species not in ('Human', 'Dwarf'):
            yml = f'- type: species\n  id: {species}\n  name: species-name-{species.lower()}\n'
            if category:
                yml += f'  category: {category}\n'
            yml += f'  roundStart: true\n  prototype: Mob{key}\n  dollPrototype: Appearance{key}\n'
            if species == 'HalfOrc':
                yml += '  clothingSex: Male\n'
            human_toned = species in ('Gnome', 'WoodElf', 'SunElf', 'HalfElf', 'HalfKin', 'Aasimar', 'AuRa')
            yml += f'  skinColoration: {"HumanToned" if human_toned else "Hues"}\n  defaultSkinTone: "#{color}"\n'
            write(PROTOS / 'Species' / (species.lower() + '.yml'), yml)
        locale.append(f'species-name-{species.lower()} = {name}' if species not in ('Human', 'Dwarf', 'Kobold') else '')
        locale.extend([f'ent-Mob{key} = {name}', f'    .desc = {description}',
                       f'ent-Appearance{key} = {name} appearance', f'    .desc = {description}'])
        catalog.append({'species': species, 'body': key, 'name': name, 'category': category,
                        'sourceType': type_path, 'sourceFile': dm.files[type_path],
                        'male': male, 'female': female, 'offsets': offsets,
                        'markingOptions': {k: len(v) for k, v in options.items()}})

    markings = []
    marking_locale = []
    imported_accessories = set()
    for (kind, path), groups in sorted(accessories.items()):
        imported = accessory(dm, path, kind)
        if imported is None:
            continue
        imported_accessories.add(path)
        ident, name, states, overrides = imported
        text = f'- type: marking\n  id: {ident}\n  bodyPart: {FEATURES[kind]}\n  groupWhitelist: [ {", ".join(sorted(groups))} ]\n'
        text += '  canBeDisplaced: false\n'
        fields = dm.fields(path)
        explicit_colors = re.findall(r'"(#[0-9A-Fa-f]{6})"|\b(null)\b', fields.get('default_colors', ''))
        fixed_colors = {}
        for state in states:
            index = re.search(r'_(\d+)$', state)
            index = int(index[1]) - 1 if index else 0
            if state.endswith('_extra') or fields.get('color_disabled') == 'TRUE':
                fixed_colors[state] = '#FFFFFF'
            elif index < len(explicit_colors) and explicit_colors[index][0]:
                fixed_colors[state] = explicit_colors[index][0]
        if fixed_colors:
            text += '  coloring:\n    default:\n      type: !type:SkinColoring {}\n    layers:\n'
            for state, color in fixed_colors.items():
                text += f'      {state}:\n        type: !type:SimpleColoring\n          color: "{color}"\n'
        if overrides:
            text += '  spriteLayerOverrides:\n' + ''.join(f'    {state}: {layer}\n' for state, layer in overrides.items())
        text += '  sprites:\n'
        for state in states:
            text += f'  - sprite: _Amberfall/Mobs/Markings/{ident}.rsi\n    state: {state}\n'
        markings.append(text)
        marking_locale.append(f'marking-{ident} = {name} ({kind.replace("_", " ")})')
        for state in states:
            marking_locale.append(f'marking-{ident}-{state} = {name}')
    write(PROTOS / 'Markings/racial_features.yml', '\n'.join(markings))
    write(LOCALE / 'racial_features.ftl', '\n'.join(marking_locale))

    for species, _, _, _ in RACES:
        if species == 'Human':
            continue
        key = 'MountainDwarf' if species == 'Dwarf' else species
        options = {kind: [p for p in paths if p in imported_accessories]
                   for kind, paths in feature_sets[species].items()}
        options = {kind: paths for kind, paths in options.items() if paths}
        defaults = {kind: path if path in imported_accessories else options[kind][0]
                    for kind, path in defaults_by_race[species].items() if kind in options}
        text = f'- type: markingsGroup\n  parent: Human\n  id: {group_id(key)}\n  limits:\n'
        by_layer = defaultdict(list)
        for kind in options:
            by_layer[FEATURES[kind]].append(kind)
        # Do not offer vanilla head anatomy that was authored for unrelated bodies.
        for layer in ('HeadSide', 'HeadTop', 'Snout', 'SnoutCover', 'Tail', 'Wings'):
            kinds = by_layer[layer]
            default_ids = [marking_id(defaults[k]) for k in kinds if k in defaults]
            text += f'    enum.HumanoidVisualLayers.{layer}:\n      limit: {max(len(kinds), 1) if kinds else 0}\n'
            text += f'      required: {str(bool(default_ids)).lower()}\n      onlyGroupWhitelisted: true\n'
            if default_ids:
                text += f'      default: [ {", ".join(default_ids)} ]\n'
        write(PROTOS / 'Markings/Species' / (species.lower() + '.yml'), text)

    categories = []
    for ident, (name, default) in CATEGORIES.items():
        categories.append(f'- type: speciesCategory\n  id: {ident}\n  name: species-category-{ident.lower()}\n  defaultSpecies: {default}\n')
        locale.append(f'species-category-{ident.lower()} = {name}')
    write(PROTOS / 'Species/categories.yml', '\n'.join(categories))
    # Existing Human and Dwarf entity localization belongs to the base locale.
    text = '\n'.join(locale)
    text = re.sub(r'(?m)^ent-(?:MobHuman|AppearanceHuman) = .*\n    \.desc = .*\n?', '', text)
    write(LOCALE / 'species.ftl', text.lstrip())
    write(PROTOS / 'Species/port_manifest.json', json.dumps(catalog, indent=2))
    write(PROTOS / 'Species/source_sprite_omissions.json', json.dumps(MISSING_SOURCE_STATES, indent=2))
    print(f'Imported {len(catalog)} playable species, {len(imported_accessories)} markings, {len(CATEGORIES)} categories.')


if __name__ == '__main__':
    main()
