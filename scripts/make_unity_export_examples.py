# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate example Unity-ready exports (FBX + GLB) into examples/Unity_Export.

Run:  blender -b --python scripts/make_unity_export_examples.py
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import bpy  # noqa: E402
import addon_utils  # noqa: E402

addon_utils.enable("cityforge", default_set=True)

from cityforge.core import export_manager, generator  # noqa: E402
from cityforge.core import params as P  # noqa: E402

OUT = os.path.join(BASE, "examples", "Unity_Export")

bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
scene.cityforge_export.export_dir = OUT + "/"

SPECS = [
    ("RESIDENTIAL", "modern_residential", 20, 15, 8, "apartment_entrance", 1),
    ("OFFICE", "glass_office_tower", 24, 20, 14, "office_lobby", 2),
    ("RESIDENTIAL", "brick_residential", 13, 11, 4, "apartment_entrance", 3),
    ("WAREHOUSE", "industrial_warehouse", 26, 20, 2, "loading_bay", 4),
    ("MIXED", "mixed_use_urban", 16, 14, 6, "retail", 5),
    ("HOUSE", "suburban_house", 10, 8, 2, "apartment_entrance", 6),
    ("SHOP", "traditional_lowrise", 12, 10, 3, "retail", 7),
    ("SKYSCRAPER", "modern_highrise", 26, 24, 26, "office_lobby", 8),
]

for (atype, style, w, d, floors, gf, seed) in SPECS:
    p = P.GenerationParams(asset_type=atype, style=style, width=w, depth=d,
                           floors=floors, ground_floor=gf, seed=seed)
    P.apply_style_defaults(p)
    generator.generate_asset(p)

for atype, seed in (("ROAD", 20), ("SIDEWALK", 21), ("TREE", 22),
                    ("BUSH", 23), ("STREETLIGHT", 24), ("BENCH", 25),
                    ("TRAFFIC_SIGN", 26), ("VEHICLE", 27)):
    p = P.GenerationParams(asset_type=atype, seed=seed)
    generator.generate_asset(p)

scene.cityforge_export.export_format = "FBX"
results = export_manager.export_all_cityforge(bpy.context)
fbx_ok = sum(1 for _n, m in results if m.startswith("exported"))

scene.cityforge_export.export_format = "GLB"
results2 = export_manager.export_all_cityforge(bpy.context)
glb_ok = sum(1 for _n, m in results2 if m.startswith("exported"))

print("UNITY_EXPORT_EXAMPLES fbx=%d glb=%d" % (fbx_ok, glb_ok))
