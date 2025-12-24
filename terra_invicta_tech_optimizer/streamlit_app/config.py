from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = BASE_DIR / "inputs"
STATIC_DIR = BASE_DIR / "static"

CATEGORY_ICON_MAP = {
    "energy": "30px-Tech_energy_icon.png",
    "informationscience": "30px-Tech_info_icon.png",
    "lifescience": "30px-Tech_life_icon.png",
    "materials": "30px-Tech_material_icon.png",
    "militaryscience": "30px-Tech_military_icon.png",
    "socialscience": "30px-Tech_social_icon.png",
    "spacescience": "30px-Tech_space_icon.png",
    "xenology": "30px-Tech_xeno_icon.png",
    "info": "30px-Tech_info_icon.png",
    "life": "30px-Tech_life_icon.png",
    "military": "30px-Tech_military_icon.png",
    "social": "30px-Tech_social_icon.png",
    "space": "30px-Tech_space_icon.png",
    "xeno": "30px-Tech_xeno_icon.png",
}
