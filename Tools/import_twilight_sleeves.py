"""Import separate Twilight Axis sleeve layers for Amberfall adventure clothes.

Usage: python Tools/import_twilight_sleeves.py C:/Projects/Twilight-Axis
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

from dmi_static_to_rsi import read_dmi


ROOT = Path(__file__).resolve().parents[1] / "Resources/Textures/_Amberfall"
CLOTHING = ROOT / "Clothing"
PARTS = ROOT / "Mobs/Human/parts.rsi"
CONFIG = (
    ("Uniforms/Jumpsuit/traveler_clothes", "tunic", "shirts"),
    ("Uniforms/Jumpsuit/explorer_clothes", "explorervest", "shirts"),
    ("Uniforms/Jumpsuit/ragged_clothes", "rags", "shirts"),
    ("OuterClothing/Armor/leather_jerkin", "leather", "armor"),
    ("OuterClothing/Armor/gambeson", "gambeson", "armor"),
    ("OuterClothing/Armor/hauberk", "hauberk", "armor"),
)


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
    for side in ("l", "r"):
        arm = Image.open(PARTS / f"{side}_arm{sex}.png").convert("RGBA")
        mask = ImageChops.lighter(mask, arm.getchannel("A"))
    return mask


def front_and_back_sleeves(body, arms):
    result = Image.new("RGBA", body.size)
    for direction in (0, 1):
        origin = (direction % 2 * 32, direction // 2 * 32)
        box = (*origin, origin[0] + 32, origin[1] + 32)
        tile = body.crop(box)
        tile.putalpha(ImageChops.multiply(tile.getchannel("A"), arms.crop(box)))
        result.paste(tile, origin)
    return result


def main():
    source = Path(sys.argv[1]) / "icons/roguetown/clothing/onmob"
    helpers = {
        group: read_dmi(source / "helpers" / f"sleeves_{group}.dmi")
        for group in ("shirts", "armor")
    }
    rags = read_dmi(source / "shirts.dmi")

    for asset, source_state, group in CONFIG:
        destination = CLOTHING / f"{asset}_sleeves.rsi"
        destination.mkdir(parents=True, exist_ok=True)
        meta = {
            "version": 1,
            "license": "CC-BY-SA-3.0",
            "copyright": "Converted from Twilight Axis icons/roguetown/clothing/onmob (https://github.com/Twilight-Fortress-SS13/Twilight-Axis)",
            "size": {"x": 32, "y": 32},
            "states": [
                {"name": "equipped-SLEEVES", "directions": 4},
                {"name": "equipped-SLEEVES_f", "directions": 4},
            ],
        }
        # Male sleeves are the base state, masked against mm.dmi arms.
        # Female sleeves use the _f clothing cut and fm.dmi arms.
        for state_suffix, clothing_suffix, arm_suffix in (
            ("", "", ""),
            ("_f", "_f", "_f"),
        ):
            body_slot = "INNERCLOTHING" if group == "shirts" else "OUTERCLOTHING"
            body = Image.open(CLOTHING / f"{asset}.rsi" / f"equipped-{body_slot}{clothing_suffix}.png").convert("RGBA")
            sleeves = front_and_back_sleeves(body, arm_mask(arm_suffix))
            for side in ("r", "l"):
                sleeve = directional_state(helpers[group], f"{side}_{source_state}{clothing_suffix}")
                if source_state == "rags":
                    sleeve = Image.alpha_composite(sleeve, directional_state(rags, f"{side}_rags{clothing_suffix}"))
                sleeves = Image.alpha_composite(sleeves, sleeve)
            sleeves.save(destination / f"equipped-SLEEVES{state_suffix}.png")
        (destination / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
