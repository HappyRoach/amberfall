"""Import base male worn states and restore Twilight Axis clothing limb overlays.

Usage: python Tools/fix_twilight_adventure_clothing.py C:/Projects/Twilight-Axis
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops

from dmi_static_to_rsi import read_dmi


ROOT = Path(__file__).resolve().parents[1] / "Resources/Textures/_Amberfall"
CLOTHING = ROOT / "Clothing"
PARTS = ROOT / "Mobs/Human/parts.rsi"


def directional_state(dmi, name):
    image, width, height, columns, states = dmi
    matches = [(offset, directions, frames) for state, offset, directions, frames in states if state == name]
    if len(matches) != 1 or matches[0][1:] != (4, 1) or (width, height) != (32, 32):
        raise ValueError(f"Unexpected DMI state {name!r}")
    offset = matches[0][0]
    result = Image.new("RGBA", (64, 64))
    for direction in range(4):
        index = offset + direction
        tile = image.crop((index % columns * 32, index // columns * 32,
                           (index % columns + 1) * 32, (index // columns + 1) * 32))
        result.paste(tile, (direction % 2 * 32, direction // 2 * 32))
    return result


def arm_mask(sex):
    mask = Image.new("L", (64, 64))
    for part in ("l_arm", "r_arm", "l_hand", "r_hand"):
        alpha = Image.open(PARTS / f"{part}{sex}.png").convert("RGBA").getchannel("A")
        mask = ImageChops.lighter(mask, alpha)
    return mask


def hide_arms(image, sex):
    image = image.copy()
    image.putalpha(Image.frombytes("L", image.size, bytes(
        0 if arm else alpha for alpha, arm in zip(image.getchannel("A").tobytes(), arm_mask(sex).tobytes())
    )))
    return image


def import_male_clothing(source):
    """Regular male mm.dmi uses the source's unsuffixed clothing states."""
    cache = {}

    def state(group, name):
        if group not in cache:
            cache[group] = read_dmi(source / f"{group}.dmi")
        return directional_state(cache[group], name)

    for asset, shirt, pants in (
        ("Uniforms/Jumpsuit/traveler_clothes", "tunic", "trou"),
        ("Uniforms/Jumpsuit/explorer_clothes", "explorervest", "explorerpants"),
        ("Uniforms/Jumpsuit/ragged_clothes", "rags", "baggypants"),
    ):
        outfit = Image.alpha_composite(state("pants", pants), state("shirts", shirt))
        outfit.save(CLOTHING / f"{asset}.rsi" / "equipped-INNERCLOTHING.png")

    for asset, group, name, slot in (
        ("OuterClothing/Armor/leather_jerkin", "armor", "leather", "OUTERCLOTHING"),
        ("OuterClothing/Armor/gambeson", "armor", "gambeson", "OUTERCLOTHING"),
        ("OuterClothing/Armor/hauberk", "armor", "hauberk", "OUTERCLOTHING"),
        ("Neck/Cloaks/cape", "cloaks", "cape", "NECK"),
        ("Neck/Cloaks/short_cloak", "cloaks", "shortcloak", "NECK"),
        ("Head/Hoods/basic_hood", "head", "basichood", "HELMET"),
        ("Head/Hoods/bandit_hood", "head", "bandithood", "HELMET"),
        ("Head/Hats/straw_hat", "head", "strawhat", "HELMET"),
        ("Shoes/Boots/leather_boots", "feet", "leatherboots", "FEET"),
        ("Shoes/Boots/short_boots", "feet", "shortboots", "FEET"),
        ("Hands/Gloves/leather_gloves", "gloves", "leather_gloves", "HAND"),
    ):
        state(group, name).save(CLOTHING / f"{asset}.rsi" / f"equipped-{slot}.png")


def main():
    source = Path(sys.argv[1]) / "icons/roguetown/clothing/onmob"
    import_male_clothing(source)
    cloaks = read_dmi(source / "cloaks.dmi")
    gloves = read_dmi(source / "gloves.dmi")
    belts = read_dmi(source / "belts.dmi")
    for sex in ("", "_f"):
        # BYOND draws the left and right cloak pieces as separate limb overlays.
        cloak = directional_state(cloaks, f"forestcloak{sex}")
        for side in ("r", "l"):
            cloak = Image.alpha_composite(cloak, directional_state(cloaks, f"{side}_forestcloak{sex}"))
        cloak.save(CLOTHING / "Neck/Cloaks/forest_cloak.rsi" / f"equipped-NECK{sex}.png")

        glove = directional_state(gloves, f"fingerless_gloves{sex}")
        for side in ("r", "l"):
            glove = Image.alpha_composite(glove, directional_state(gloves, f"{side}_fingerless_gloves{sex}"))
        glove.save(CLOTHING / "Hands/Gloves/fingerless_gloves.rsi" / f"equipped-HAND{sex}.png")

        belt_path = CLOTHING / "Belt/leather_belt.rsi" / f"equipped-BELT{sex}.png"
        belt = directional_state(belts, f"leather{sex}")
        # The belt slot is in front of the arms, so leave their pixels transparent.
        hide_arms(belt, sex).save(belt_path)


if __name__ == "__main__":
    main()
