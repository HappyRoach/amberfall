"""Use the Twilight Axis regular male body, restore leg order, and align eyes.

Usage: python Tools/fix_twilight_human_sprites.py C:/Projects/Twilight-Axis
"""

import json
import sys
from pathlib import Path

from PIL import Image

from dmi_static_to_rsi import read_dmi


ROOT = Path(__file__).resolve().parents[1] / "Resources/Textures"
PARTS = ROOT / "_Amberfall/Mobs/Human/parts.rsi"
EYES_SOURCE = ROOT / "Mobs/Customization/eyes.rsi"
EYES_DESTINATION = ROOT / "_Amberfall/Mobs/Human/eyes.rsi"


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


def shift_down_one_pixel(image, directions):
    result = Image.new("RGBA", image.size)
    for direction in range(directions):
        x = direction % 2 * 32
        y = direction // 2 * 32
        tile = image.crop((x, y, x + 32, y + 31))
        result.paste(tile, (x, y + 1))
    return result


def main():
    source = Path(sys.argv[1]) / "icons/roguetown/mob/bodies"
    male = read_dmi(source / "m/mm.dmi")
    male_states = {
        # mm.dmi is the regular male body; its full-body state is named "mt".
        "full": "mt",
        "head_m": "head",
        "torso_m": "chest",
        "l_arm": "l_arm",
        "r_arm": "r_arm",
        "l_hand": "l_hand",
        "r_hand": "r_hand",
    }
    for target, state in male_states.items():
        directional_state(male, state).save(PARTS / f"{target}.png")

    for sex, path in (("", "m/mm.dmi"), ("_f", "f/fm.dmi")):
        dmi = read_dmi(source / path)
        for side in ("l", "r"):
            leg = directional_state(dmi, f"{side}_leg")
            above = directional_state(dmi, f"{side}_leg_above")
            Image.alpha_composite(leg, above).save(PARTS / f"{side}_leg{sex}.png")
            if side == "r":
                # This right leg frame must be drawn above the left leg when facing sideways.
                above.save(PARTS / f"r_leg_above{sex}.png")

    parts_meta_path = PARTS / "meta.json"
    parts_meta = json.loads(parts_meta_path.read_text(encoding="utf-8"))
    parts_meta["copyright"] = (
        "Converted from Twilight Axis icons/roguetown/mob/bodies/m/mm.dmi and f/fm.dmi; "
        "https://github.com/Twilight-Fortress-SS13/Twilight-Axis"
    )
    for state_name in ("r_leg_above", "r_leg_above_f"):
        if not any(state["name"] == state_name for state in parts_meta["states"]):
            parts_meta["states"].append({"name": state_name, "directions": 4})
    parts_meta_path.write_text(json.dumps(parts_meta, indent=2) + "\n", encoding="utf-8")

    EYES_DESTINATION.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((EYES_SOURCE / "meta.json").read_text(encoding="utf-8"))
    metadata["copyright"] += "; female eyes and no_eyes shifted one pixel down for Twilight Axis human heads"
    for state in metadata["states"]:
        name = state["name"]
        image = Image.open(EYES_SOURCE / f"{name}.png").convert("RGBA")
        if name == "eyes":
            # mm.dmi has its eye sockets one pixel above fm.dmi.
            # Keep male eyes as the base state and use a separate female state.
            shift_down_one_pixel(image, state.get("directions", 1)).save(EYES_DESTINATION / "eyes_f.png")
        elif name == "no_eyes":
            image = shift_down_one_pixel(image, state.get("directions", 1))
        image.save(EYES_DESTINATION / f"{name}.png")
    metadata["states"].append({"name": "eyes_f", "directions": 4})
    (EYES_DESTINATION / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
