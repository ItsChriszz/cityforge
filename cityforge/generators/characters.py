# SPDX-License-Identifier: GPL-3.0-or-later
"""Low-poly procedural character (NPC) generator.

Compact humanoid figures for city simulation: blocky-but-readable people with
varied builds, clothing styles and colours, hair, and optional accessories.

Design notes:
* Body proportions vary by seed (height, shoulder width, build); the
  "female"/"male" options bias build proportions without relying on
  stereotypes (they are subtle silhouette differences only).
* Clothing styles change silhouette + colours: casual (t-shirt & long
  pants), business (jacket & trousers), construction (hi-vis vest &
  helmet), pedestrian (coat).
* LOW/MEDIUM/HIGH detail controls segmentation and clothing layers.
* Ground origin at the feet; 1 unit = 1 metre; Y+ is the facing direction.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..core.params import GenerationParams
from ..core.randomization import chance, make_rng, pick_weighted
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]

_SKIN = [
    (0.86, 0.67, 0.55), (0.76, 0.57, 0.44), (0.62, 0.44, 0.32),
    (0.45, 0.31, 0.22), (0.30, 0.20, 0.14),
]
_HAIR = [
    (0.12, 0.08, 0.05), (0.30, 0.19, 0.10), (0.55, 0.42, 0.25),
    (0.85, 0.75, 0.55), (0.15, 0.15, 0.16), (0.55, 0.10, 0.05),
    (0.65, 0.65, 0.66),
]
_PALETTE_CASUAL = [(0.85, 0.35, 0.25), (0.25, 0.45, 0.70), (0.95, 0.85, 0.30),
                   (0.30, 0.62, 0.40), (0.90, 0.90, 0.92), (0.55, 0.30, 0.60),
                   (0.95, 0.55, 0.15)]
_PALETTE_BUSINESS = [(0.16, 0.18, 0.24), (0.30, 0.33, 0.40), (0.55, 0.56, 0.60),
                     (0.10, 0.12, 0.15), (0.42, 0.46, 0.52)]
_PALETTE_CONSTRUCTION = [(0.95, 0.55, 0.05), (0.85, 0.85, 0.10), (0.90, 0.90, 0.90)]
_PALETTE_PEDESTRIAN = [(0.45, 0.35, 0.28), (0.25, 0.28, 0.35), (0.60, 0.58, 0.52),
                       (0.20, 0.32, 0.28)]

_CLOTH_KEY = "painted_metal"   # matte painted family reads as fabric

# profession registry: palette + headwear + coat/backpack flags
PROFESSIONS: Dict[str, Dict] = {
    "lawyer": dict(palette="business", hat=None, coat=True),
    "accountant": dict(palette="business", hat=None, coat=True),
    "banker": dict(palette="business", hat=None, coat=True),
    "business": dict(palette="business", hat=None, coat=False),
    "chef": dict(palette=[(0.92, 0.92, 0.90)], hat="toque", coat=True),
    "doctor": dict(palette=[(0.94, 0.94, 0.96)], hat=None, coat=True),
    "nurse": dict(palette=[(0.75, 0.85, 0.92)], hat=None, coat=True),
    "construction": dict(palette="construction", hat="helmet", coat=False),
    "teacher": dict(palette="casual", hat=None, coat=False),
    "student": dict(palette="casual", hat=None, coat=False, backpack=True),
    "police": dict(palette=[(0.10, 0.14, 0.30)], hat="police_cap", coat=True),
    "firefighter": dict(palette=[(0.35, 0.08, 0.06)], hat="fire_helmet",
                        coat=True),
    "farmer": dict(palette=[(0.30, 0.30, 0.35)], hat="straw_hat", coat=False),
    "fisherman": dict(palette=[(0.85, 0.55, 0.10)], hat="rain_hat",
                      coat=True),
    "retail": dict(palette=[(0.20, 0.45, 0.65)], hat=None, coat=False),
    "delivery": dict(palette=[(0.85, 0.30, 0.10)], hat="cap", coat=False),
    "mechanic": dict(palette=[(0.25, 0.30, 0.35)], hat="cap", coat=False),
    "cyclist": dict(palette=[(0.95, 0.40, 0.10)], hat="cycle_helmet",
                    coat=False),
}


def _hex(color) -> str:
    return "%02x%02x%02x" % tuple(int(max(0.0, min(1.0, c)) * 255)
                                  for c in color[:3])


def _cloth(params: GenerationParams, rng, role: str) -> str:
    styles = {
        "casual": _PALETTE_CASUAL, "business": _PALETTE_BUSINESS,
        "construction": _PALETTE_CONSTRUCTION,
        "pedestrian": _PALETTE_PEDESTRIAN,
    }
    style = params.npc_style
    if style == "random":
        style = pick_weighted(rng, [("casual", 4.0), ("business", 2.0),
                                    ("construction", 1.0),
                                    ("pedestrian", 3.0)])
    palette = styles.get(style, _PALETTE_CASUAL)
    return f"{_CLOTH_KEY}#{_hex(rng.choice(palette))}"


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "npc")
    mb = MeshBuilder()
    seg = {"low": 6, "medium": 8, "high": 10}.get(params.detail_level, 8)

    # age & build variation (genuine proportion changes, not just scale)
    age = getattr(params, "npc_age", "adult")
    age_scale = {"child": 0.62, "teen": 0.85, "adult": 1.0,
                 "senior": 0.94}.get(age, 1.0)
    senior_stoop = 0.03 if age == "senior" else 0.0
    h = max(1.0, params.npc_height * age_scale * rng.uniform(0.94, 1.06))
    gender = params.npc_gender
    if gender == "random":
        gender = "female" if rng.random() < 0.5 else "male"
    # subtle build variation (no stereotypes, just silhouette variety)
    build_w = rng.uniform(0.92, 1.10)
    if gender == "female":
        shoulder = 0.30 * build_w
        hip = 0.34 * build_w
    else:
        shoulder = 0.36 * build_w
        hip = 0.30 * build_w

    # profession overrides the generic clothing style when set
    prof = getattr(params, "npc_profession", "random")
    prof_def = PROFESSIONS.get(prof) if prof not in (None, "", "random") \
        else None
    style = params.npc_style
    if prof_def:
        style = {"business": "business"}.get(
            prof_def["palette"], "casual") if isinstance(
            prof_def["palette"], str) else "casual"
    if style == "random":
        style = pick_weighted(rng, [("casual", 4.0), ("business", 2.0),
                                    ("construction", 1.0),
                                    ("pedestrian", 3.0)])

    skin = f"painted_metal#{_hex(rng.choice(_SKIN))}"
    hair_c = f"painted_metal#{_hex(rng.choice(_HAIR))}"
    shirt = _cloth(params, rng, "shirt")
    pants = _cloth(params, rng, "pants")
    shoes = f"painted_metal#{_hex((0.12, 0.11, 0.11))}"

    if prof_def:
        pal = prof_def["palette"]
        if isinstance(pal, str):
            pal = {"business": _PALETTE_BUSINESS,
                   "casual": _PALETTE_CASUAL,
                   "construction": _PALETTE_CONSTRUCTION}.get(
                pal, _PALETTE_CASUAL)
        shirt = f"{_CLOTH_KEY}#{_hex(rng.choice(pal))}"
        pants = f"{_CLOTH_KEY}#{_hex(rng.choice(pal))}"

    # proportions (fractions of height)
    leg_h = h * 0.46
    torso_h = h * 0.30
    head_h = h * 0.13
    neck_z = leg_h + torso_h - senior_stoop * h

    # legs
    leg_w = 0.09 * build_w
    for s in (-1, 1):
        mb.add_box((s * hip * 0.55, 0, leg_h / 2), (leg_w, leg_w, leg_h),
                   pants)
        mb.add_box((s * hip * 0.55, 0.01, 0.045), (leg_w * 1.15, 0.22,
                   0.09), shoes)
    # torso: tapered via two stacked boxes (chest + hips)
    mb.add_box((0, 0, leg_h + torso_h * 0.28), (hip * 2.05, 0.19, torso_h
               * 0.56), shirt)
    mb.add_box((0, 0, leg_h + torso_h * 0.74), (shoulder * 2.05, 0.21,
               torso_h * 0.52), shirt)
    if (style == "business" or (prof_def and prof_def.get("coat"))) \
            and params.detail_level != "low":
        # jacket / lab-coat lapel strip
        coat_c = f"painted_metal#{_hex((0.92, 0.92, 0.94))}" if prof_def else \
            f"painted_metal#{_hex((0.08, 0.08, 0.10))}"
        mb.add_box((0, -0.115, leg_h + torso_h * 0.62), (0.03, 0.015,
                   torso_h * 0.7), coat_c)
    if style == "construction" or (prof_def and prof == "construction"):
        # hi-vis vest over torso
        mb.add_box((0, 0, leg_h + torso_h * 0.55), (shoulder * 2.2, 0.24,
                   torso_h * 0.6), f"painted_metal#{_hex((0.95, 0.5, 0.05))}")
    # arms
    arm_w = 0.075 * build_w
    arm_len = torso_h * 1.15
    for s in (-1, 1):
        mb.add_box((s * (shoulder + arm_w / 2), 0, leg_h + torso_h
                    - arm_len / 2 + 0.02), (arm_w, arm_w, arm_len), shirt)
        mb.add_box((s * (shoulder + arm_w / 2), 0, leg_h + torso_h
                    - arm_len + 0.02), (arm_w * 1.1, arm_w * 1.1, 0.08),
                   skin)
    # head + neck
    mb.add_box((0, 0, neck_z + 0.03), (0.07, 0.07, 0.06), skin)
    head_r = head_h * 0.42
    mb.add_sphere((0, 0, neck_z + head_h * 0.62), head_r, seg, seg // 2,
                  skin)
    # hair: short / long / bald by seed
    hair_style = rng.choice(("short", "long", "short", "bald"))
    hair_len = {"short": 0.5, "long": 0.85, "bald": 0.0}[hair_style]
    if hair_len > 0:
        mb.add_sphere((0, 0, neck_z + head_h * 0.62 + head_r * 0.32),
                      head_r * 1.04, seg, seg // 2, hair_c, squash=hair_len)
        if hair_style == "long":
            mb.add_box((0, head_r * 0.75, neck_z + head_h * 0.30),
                       (head_r * 1.5, 0.08, head_r * 1.5), hair_c)
    # facial hair (male option only)
    if gender == "male" and chance(rng, 0.3) and hair_style != "bald":
        mb.add_box((0, -head_r * 0.82, neck_z + head_h * 0.42),
                   (head_r * 1.1, 0.04, head_r * 0.5), hair_c)

    # headwear & accessories
    hat = prof_def.get("hat") if prof_def else None
    if hat == "toque":
        mb.add_cylinder((0, 0, neck_z + head_h * 1.05), head_r * 1.02,
                        head_r * 0.9, seg, "holo_white")
    elif hat == "helmet" or hat == "fire_helmet":
        hc = (0.95, 0.55, 0.05) if hat == "helmet" else (0.85, 0.12, 0.08)
        mb.add_sphere((0, 0, neck_z + head_h * 0.95), head_r * 1.25, seg,
                      seg // 2, f"painted_metal#{_hex(hc)}", squash=0.6)
    elif hat == "police_cap":
        mb.add_cylinder((0, 0, neck_z + head_h * 1.0), head_r * 1.05,
                        head_r * 0.5, seg,
                        f"painted_metal#{_hex((0.10, 0.14, 0.30))}")
        mb.add_box((0, -head_r * 0.9, neck_z + head_h * 0.95),
                   (head_r * 1.4, 0.16, 0.03),
                   f"painted_metal#{_hex((0.10, 0.14, 0.30))}")
    elif hat in ("cap", "rain_hat", "straw_hat", "cycle_helmet"):
        hc = {"cap": (0.85, 0.30, 0.10), "rain_hat": (0.85, 0.55, 0.10),
              "straw_hat": (0.85, 0.72, 0.35),
              "cycle_helmet": (0.95, 0.40, 0.10)}[hat]
        brim = 0.35 if hat in ("cap", "straw_hat") else 0.1
        mb.add_sphere((0, 0, neck_z + head_h * 1.0), head_r * 1.15, seg,
                      seg // 2, f"painted_metal#{_hex(hc)}", squash=0.45)
        if brim > 0.1:
            mb.add_box((0, -head_r * (1.0 + brim), neck_z + head_h * 0.92),
                       (head_r * 1.8, head_r * 2 * brim, 0.02),
                       f"painted_metal#{_hex(hc)}")

    # accessories
    if params.npc_accessories:
        wants_backpack = prof_def.get("backpack") if prof_def else False
        if wants_backpack or chance(rng, 0.3):
            mb.add_box((0, 0.16, leg_h + torso_h * 0.6), (shoulder * 1.4,
                       0.10, torso_h * 0.8),
                       f"painted_metal#{_hex(rng.choice(_PALETTE_CASUAL))}")
        if style == "business" and chance(rng, 0.3):
            mb.add_box((shoulder + arm_w / 2 + 0.05, 0, leg_h * 0.72),
                       (0.22, 0.06, 0.28),
                       f"painted_metal#{_hex((0.12, 0.10, 0.09))}")
        if prof == "doctor" or prof == "nurse":
            mb.add_box((shoulder + arm_w / 2 + 0.03, 0, leg_h * 0.55),
                       (0.03, 0.02, 0.24),
                       f"painted_metal#{_hex((0.95, 0.35, 0.35))}")

    info = {
        "style": style,
        "profession": prof if prof and prof != "random" else "",
        "build": gender,
        "age": age,
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


# ---------------------------------------------------------------------------
# rigging + animation clips
# ---------------------------------------------------------------------------

RIG_BONES = [
    # (name, parent, head (x,y,z as fraction of h), tail)
    ("Hips", None, (0, 0, 0.52), (0, 0, 0.58)),
    ("Spine", "Hips", (0, 0, 0.58), (0, 0, 0.70)),
    ("Chest", "Spine", (0, 0, 0.70), (0, 0, 0.82)),
    ("Neck", "Chest", (0, 0, 0.82), (0, 0, 0.86)),
    ("Head", "Neck", (0, 0, 0.86), (0, 0, 0.98)),
    ("LeftShoulder", "Chest", (0.05, 0, 0.80), (0.14, 0, 0.79)),
    ("LeftArm", "LeftShoulder", (0.14, 0, 0.79), (0.24, 0, 0.66)),
    ("LeftForeArm", "LeftArm", (0.24, 0, 0.66), (0.33, 0, 0.55)),
    ("RightShoulder", "Chest", (-0.05, 0, 0.80), (-0.14, 0, 0.79)),
    ("RightArm", "RightShoulder", (-0.14, 0, 0.79), (-0.24, 0, 0.66)),
    ("RightForeArm", "RightArm", (-0.24, 0, 0.66), (-0.33, 0, 0.55)),
    ("LeftUpLeg", "Hips", (0.09, 0, 0.50), (0.09, 0, 0.27)),
    ("LeftLeg", "LeftUpLeg", (0.09, 0, 0.27), (0.09, 0, 0.05)),
    ("LeftFoot", "LeftLeg", (0.09, 0, 0.05), (0.09, 0.09, 0.01)),
    ("RightUpLeg", "Hips", (-0.09, 0, 0.50), (-0.09, 0, 0.27)),
    ("RightLeg", "RightUpLeg", (-0.09, 0, 0.27), (-0.09, 0, 0.05)),
    ("RightFoot", "RightLeg", (-0.09, 0, 0.05), (-0.09, 0.09, 0.01)),
]

# vertex-region -> bone weights (simple box regions per body part)
_BONE_REGIONS = [
    ("Head", lambda v, h: v.z > h * 0.84),
    ("Chest", lambda v, h: h * 0.70 <= v.z <= h * 0.84),
    ("Spine", lambda v, h: h * 0.58 <= v.z < h * 0.70),
    ("LeftArm", lambda v, h: v.x > h * 0.13 and v.z > h * 0.55),
    ("RightArm", lambda v, h: v.x < -h * 0.13 and v.z > h * 0.55),
    ("LeftUpLeg", lambda v, h: v.x > 0 and h * 0.27 <= v.z <= h * 0.55),
    ("RightUpLeg", lambda v, h: v.x < 0 and h * 0.27 <= v.z <= h * 0.55),
    ("LeftLeg", lambda v, h: v.x > 0 and v.z < h * 0.27),
    ("RightLeg", lambda v, h: v.x < 0 and v.z < h * 0.27),
    ("Hips", lambda v, h: abs(v.x) <= h * 0.13 and h * 0.46 <= v.z < h * 0.58),
]


def rig_character(obj: bpy.types.Object, params: GenerationParams) -> \
        bpy.types.Object:
    """Build a Unity-compatible humanoid armature, assign vertex weights by
    body region and parent the character mesh to it.  Returns the armature
    object (the mesh becomes its child)."""
    import bpy
    import mathutils

    h = max(0.5, params.npc_height)
    arm_data = bpy.data.armatures.new(obj.name + "_rig")
    arm_obj = bpy.data.objects.new(obj.name + "_rig", arm_data)
    for c in obj.users_collection:
        c.objects.link(arm_obj)
        break
    bpy.context.view_layer.objects.active = arm_obj
    arm_data.show_axes = False

    # edit-mode bone construction
    bpy.ops.object.mode_set(mode='EDIT')
    edits = arm_data.edit_bones
    made = {}
    for (name, parent, head, tail) in RIG_BONES:
        eb = edits.new(name)
        eb.head = mathutils.Vector((head[0] * h, head[1] * h, head[2] * h))
        eb.tail = mathutils.Vector((tail[0] * h, tail[1] * h, tail[2] * h))
        eb.roll = 0.0
        made[name] = eb
    for (name, parent, head, tail) in RIG_BONES:
        if parent:
            made[name].parent = made[parent]
            # keep the child connected for limbs, detached for the spine chain
            made[name].use_connect = parent in ("Spine", "Chest", "Neck",
                                                "Head")
    bpy.ops.object.mode_set(mode='OBJECT')

    # vertex groups by body region (deterministic region weights, better
    # than blind auto-weights for blocky procedural meshes)
    for gname in (name for (name, _p, _h, _t) in RIG_BONES):
        obj.vertex_groups.new(name=gname)
    import mathutils as mu
    for v in obj.data.vertices:
        assigned = False
        for (gname, test) in _BONE_REGIONS:
            if test(v.co, h):
                obj.vertex_groups[gname].add([v.index], 1.0, 'REPLACE')
                assigned = True
                break
        if not assigned:
            obj.vertex_groups["Hips"].add([v.index], 1.0, 'REPLACE')

    mod = obj.modifiers.new("Rig", 'ARMATURE')
    mod.object = arm_obj
    obj.parent = arm_obj
    arm_obj["cityforge_rig"] = "cityforge_humanoid_v1"
    return arm_obj


def add_animation_clip(arm_obj: bpy.types.Object, clip: str,
                       frames: int = 32) -> None:
    """Create a pose animation clip on the armature (walk/idle/wave)."""
    import bpy
    import math
    import random

    rng = random.Random(hash(clip) & 0xFFFF)
    scene = bpy.context.scene
    scene.frame_set(1)

    pb = arm_obj.pose.bones
    fps = scene.render.fps or 24

    def key(bone, rot, frame):
        pb[bone].rotation_euler = rot
        pb[bone].keyframe_insert("rotation_euler", frame=frame)

    if clip == "walk":
        scene.frame_end = frames
        for f in range(0, frames + 1, 8):
            t = f / frames * 4 * math.pi
            key("LeftUpLeg", (math.sin(t) * 0.5, 0, 0), f + 1)
            key("RightUpLeg", (math.sin(t + math.pi) * 0.5, 0, 0), f + 1)
            key("LeftLeg", (max(0.0, -math.sin(t)) * 0.6, 0, 0), f + 1)
            key("RightLeg", (max(0.0, -math.sin(t + math.pi)) * 0.6, 0, 0),
                f + 1)
            key("LeftArm", (math.sin(t + math.pi) * 0.35, 0, 0.1), f + 1)
            key("RightArm", (math.sin(t) * 0.35, 0, -0.1), f + 1)
            key("Hips", (0, 0, math.sin(t / 2) * 0.04), f + 1)
    elif clip == "wave":
        scene.frame_end = frames
        for f in range(0, frames + 1, 4):
            t = f / frames * 4 * math.pi
            key("RightArm", (0, 0, -2.2), f + 1)
            key("RightForeArm", (0, math.sin(t) * 0.4, -0.5), f + 1)
            key("Chest", (0, 0, math.sin(t) * 0.06), f + 1)
    else:  # idle
        scene.frame_end = frames
        for f in range(0, frames + 1, 8):
            t = f / frames * 2 * math.pi
            key("Chest", (math.sin(t) * 0.03, 0, 0), f + 1)
            key("Hips", (0, 0, math.sin(t) * 0.03), f + 1)
            key("LeftArm", (math.sin(t) * 0.04, 0, 0.06), f + 1)
            key("RightArm", (math.sin(t + math.pi) * 0.04, 0, -0.06), f + 1)

    if arm_obj.animation_data and arm_obj.animation_data.action:
        arm_obj.animation_data.action.name = f"CF_{clip}"
        arm_obj.animation_data.action.use_cyclic = True
