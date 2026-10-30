# SPDX-License-Identifier: GPL-3.0-or-later
"""Visual test collection: generate & render every major asset category.

Run: blender -b --python scripts/generate_samples.py
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import bpy  # noqa: E402
import mathutils  # noqa: E402

RENDER = "--no-render" not in sys.argv


def setup():
    bpy.ops.wm.read_homefile(use_empty=True)
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = \
        (0.42, 0.5, 0.62, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    for name, rot, energy in (("Sun", (0.6, 0.1, 0.6), 2.2),
                              ("Sun2", (-0.5, -0.3, 2.4), 0.9)):
        light = bpy.data.lights.new(name, 'SUN')
        ob = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(ob)
        ob.rotation_euler = rot
        light.energy = energy
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons.get("cycles")
    for dtype in ("OPTIX", "CUDA"):
        try:
            prefs.preferences.compute_device_type = dtype
            prefs.preferences.get_devices()
            if any(d.type == dtype for d in prefs.preferences.devices):
                print("RENDER_DEVICE", dtype)
                break
        except Exception:
            continue
    scene.cycles.samples = 40
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 640
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    bpy.ops.mesh.primitive_plane_add(size=600)
    return cam


def render(cam, filepath, cam_pos, look_at, lens=38, res=(1200, 640)):
    cam.location = cam_pos
    direction = mathutils.Vector(look_at) - mathutils.Vector(cam_pos)
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    bpy.context.scene.render.resolution_x, \
        bpy.context.scene.render.resolution_y = res
    out = os.path.join(BASE, "docs", "screenshots", filepath)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("RENDERED", filepath)


def main():
    from cityforge.core import generator, params as P
    cam = setup()

    # ---- commercial variety row FIRST (so the skyline never shadows it) --
    x = 0.0
    for form, seed in [("small_retail", 41), ("restaurant", 42),
                       ("cafe", 43), ("pub", 44), ("shopping_building", 45)]:
        p = P.GenerationParams(asset_type="COMMERCIAL",
                               style="contemporary_commercial", seed=seed,
                               commercial_form=form)
        P.apply_style_defaults(p)
        P.apply_form_defaults(p)
        P.apply_arch_levels(p)
        obj = generator.generate_asset(p)
        obj.location = (x, -90, 0)
        x += max(p.width, 10) / 2 + 8
    if RENDER:
        render(cam, "commercial_variety.png", (x / 2 - 4, -165, 13),
               (x / 2 - 4, -88, 3.5), lens=30, res=(1300, 420))

    # ---- skyline row: old + new styles --------------------------------
    x = 0.0
    skyline = []
    specs = [
        ("RESIDENTIAL", "modern_residential", 20, 15, 6, None, 1, {}),
        ("OFFICE", "glass_office_tower", 24, 20, 14, None, 2, {}),
        ("RESIDENTIAL", "brick_residential", 13, 11, 4, None, 3, {}),
        ("WAREHOUSE", "industrial_warehouse", 28, 20, 2, None, 4, {}),
        ("MIXED", "mixed_use_urban", 16, 14, 6, None, 5, {}),
        ("SKYSCRAPER", "glass_curtain_tower", 24, 22, 30, None, 6,
         {"tower_form": "box", "crown_lighting": True}),
        ("SKYSCRAPER", "modern_office_skyscraper", 26, 24, 26, None, 7, {}),
        ("SKYSCRAPER", "contemporary_residential_tower", 20, 18, 22, None, 8,
         {}),
        ("MIXED", "mixed_use_tower", 24, 20, 24, None, 9,
         {"podium_floors": 3}),
        ("SKYSCRAPER", "futuristic_tower", 22, 20, 34, None, 10, {}),
    ]
    for (atype, style, w, d, floors, _gf, seed, extra) in specs:
        p = P.GenerationParams(asset_type=atype, style=style, width=w,
                               depth=d, floors=floors, seed=seed,
                               detail_level="medium")
        P.apply_style_defaults(p)
        for k, v in extra.items():
            setattr(p, k, v)
        P.apply_arch_levels(p)
        obj = generator.generate_asset(p)
        if obj is None:
            print("FAIL_GEN", style)
            continue
        obj.location = (x, 0, 0)
        skyline.append(obj)
        x += max(w, 14) / 2 + 13
    print("SKYLINE", len(skyline), "objects")
    mid = sum(o.location.x for o in skyline) / len(skyline)
    if RENDER:
        render(cam, "skyline_all_styles.png", (mid + 8, -300, 90),
               (mid, 0, 24), lens=28, res=(1500, 620))

    # ---- park ----------------------------------------------------------
    pk = P.GenerationParams(asset_type="PARK", seed=70,
                            park_type="community_park")
    obj = generator.generate_asset(pk)
    obj.location = (x + 160, 220, 0)
    if RENDER:
        render(cam, "park_aerial.png", (obj.location.x, 150, 65),
               (obj.location.x, 220, 0), lens=42, res=(1100, 700))

    # ---- characters + vehicles ------------------------------------------
    vx = 0.0
    for cls_i, cls in enumerate(["sedan", "suv", "pickup", "van",
                                 "delivery_truck", "bus", "taxi",
                                 "sports_car"]):
        v = generator.generate_asset(P.GenerationParams(
            asset_type="VEHICLE", seed=90 + cls_i, vehicle_class=cls,
            vehicle_random_look=True))
        v.location = (vx, -40, 0)
        vx += 3.6
    for i in range(12):
        npc = generator.generate_asset(P.GenerationParams(
            asset_type="NPC", seed=200 + i, npc_style="random"))
        npc.location = (i * 1.6 - 8, -36 + (i % 3) * 1.2, 0)
        npc.rotation_euler = (0, 0, 3.14159 / 2)
    if RENDER:
        render(cam, "characters_vehicles.png", (vx / 2, -52, 3.2),
               (vx / 2, -38, 1.0), lens=40, res=(1300, 380))

    # ---- road classes ----------------------------------------------------
    rx = 0.0
    for i, cls in enumerate(["highway", "single_lane", "two_lane",
                             "four_lane", "one_way"]):
        r = generator.generate_asset(P.GenerationParams(
            asset_type="ROAD", seed=60 + i, road_class=cls,
            road_length=44.0))
        r.location = (-90, rx, 0)
        rx += r.dimensions.y + 4.0
    if RENDER:
        render(cam, "road_classes.png", (-90, -34, 80),
               (-90, rx / 2 - 6, 0), lens=40, res=(1100, 900))

    # save the collection blend
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(BASE, "examples", "CityForge_Samples.blend"))
    print("SAVED_BLEND")


main()
