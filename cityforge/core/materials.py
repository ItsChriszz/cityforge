# SPDX-License-Identifier: GPL-3.0-or-later
"""Centralised, reusable procedural material library.

Every visible surface of a CityForge asset refers to a material *key*
(``concrete``, ``brick_red``, ``dark_glass``, ...).  This module owns the
mapping key -> bpy material and guarantees reuse: the same key always resolves
to the same shareable material object, so Blender never accumulates hundreds
of duplicated materials across a generated city.

All materials are node-based and engine-agnostic (Principled BSDF +
procedural texture nodes work in Cycles, Eevee and Eevee Next).
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Optional

import bpy

from ..utils import get_logger

_log = get_logger()

_PREFIX = "CF_"          # namespace to recognise library materials in files
_MAX_CACHE = 120         # safety ceiling; the catalog stays below this

# ---------------------------------------------------------------------------
# Node-graph builders
# ---------------------------------------------------------------------------


def _new_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def _nodes(mat: bpy.types.Material):
    nt = mat.node_tree
    out = nt.nodes["Material Output"]
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return nt, out, bsdf


def _noise(nt, scale: float, detail: float = 4.0) -> bpy.types.Node:
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail
    return tex


def _bump(nt, bsdf, source_socket, strength: float) -> None:
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(source_socket, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def _simple(
    name: str,
    color: tuple,
    roughness: float,
    metallic: float = 0.0,
    noise_scale: float = 0.0,
    noise_strength: float = 0.06,
    variation: float = 0.0,
    emit: float = 0.0,
    emit_color: tuple = (1.0, 1.0, 1.0, 1.0),
) -> Callable[[bpy.types.Material], None]:
    _BASE_COLORS[name] = tuple(color[:3])

    def build(mat: bpy.types.Material) -> None:
        nt, out, bsdf = _nodes(mat)
        if noise_scale:
            tex = _noise(nt, noise_scale)
            tex.inputs["Detail"].default_value = 6.0
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            vr = variation
            ramp.color_ramp.elements[0].color = tuple(
                max(0.0, c * (1.0 - vr)) for c in color[:3]) + (1,)
            ramp.color_ramp.elements[1].color = tuple(
                min(1.0, c * (1.0 + vr * 0.5)) for c in color[:3]) + (1,)
            nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
            nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
            _bump(nt, bsdf, tex.outputs["Fac"], noise_strength)
        else:
            bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        if metallic:
            bsdf.inputs["Metallic"].default_value = metallic
        if emit:
            bsdf.inputs["Emission Strength"].default_value = emit
            bsdf.inputs["Emission Color"].default_value = emit_color
    return build


def _glass(name: str, color: tuple, roughness: float, tint: float = 0.6) -> Callable:
    _BASE_COLORS[name] = tuple(color[:3])

    def build(mat: bpy.types.Material) -> None:
        nt, out, bsdf = _nodes(mat)
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Transmission Weight"].default_value = tint
        bsdf.inputs["IOR"].default_value = 1.45
        # interior facing surface is simpler; keep an emitter for fake lit glass
    return build


def _brick(name: str, base: tuple, mortar: tuple, rough: float = 0.8) -> Callable:
    def build(mat: bpy.types.Material) -> None:
        nt, out, bsdf = _nodes(mat)
        tex = nt.nodes.new("ShaderNodeTexBrick")
        tex.offset = 0.5
        tex.inputs["Scale"].default_value = 18.0
        tex.inputs["Mortar Size"].default_value = 0.012
        tex.inputs["Mortar Smooth"].default_value = 0.2
        tex.inputs["Brick Width"].default_value = 0.28
        tex.inputs["Row Height"].default_value = 0.075
        tex.inputs["Color1"].default_value = base
        tex.inputs["Color2"].default_value = tuple(
            c * 0.82 + 0.04 for c in base[:3]) + (1,)
        tex.inputs["Mortar"].default_value = mortar
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = rough
        _bump(nt, bsdf, tex.outputs["Fac"], 0.4)
    return build


def _asphalt(name: str) -> Callable[[bpy.types.Material], None]:
    def build(mat: bpy.types.Material) -> None:
        nt, out, bsdf = _nodes(mat)
        tex = _noise(nt, 60.0, 2.5)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.08, 0.08, 0.085, 1)
        ramp.color_ramp.elements[1].color = (0.16, 0.16, 0.165, 1)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.85
        _bump(nt, bsdf, tex.outputs["Fac"], 0.15)
    return build


def _grass(name: str) -> Callable[[bpy.types.Material], None]:
    def build(mat: bpy.types.Material) -> None:
        nt, out, bsdf = _nodes(mat)
        tex = _noise(nt, 12.0, 6.0)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.11, 0.33, 0.09, 1)
        ramp.color_ramp.elements[1].color = (0.32, 0.55, 0.18, 1)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 1.0
    return build


def _emission(name: str, color: tuple, strength: float) -> Callable:
    def build(mat: bpy.types.Material) -> None:
        nt, out, bsdf = _nodes(mat)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = color
        em.inputs["Strength"].default_value = strength
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return build


# ---------------------------------------------------------------------------
# Catalog of material keys
# ---------------------------------------------------------------------------

# text colour constants
_CONC = (0.62, 0.61, 0.585, 1)
_WHITEC = (0.82, 0.81, 0.775, 1)
_DARKC = (0.34, 0.34, 0.35, 1)
_WOOD = (0.42, 0.29, 0.16, 1)
_GRIME = (0.13, 0.13, 0.135, 1)

# keys that accept a colour override (painted family); glass tints too
_PAINTABLE = {
    "concrete", "white_concrete", "dark_concrete", "painted_metal",
    "car_paint", "taxi_yellow", "sign", "sign_cream", "sign_green",
    "sign_dark", "wood", "roof_tiles", "roof_metal", "awning_red",
    "awning_green", "awning_brown", "awning_black", "brick_red",
    "brick_brown", "brick_multicolor", "glass", "reflective_glass",
    "dark_glass", "blue_tinted_glass", "grey_glass", "green_glass",
}

# registry of the catalogue's base colours for tint scaling
_BASE_COLORS: Dict[str, tuple] = {}


_CATALOG: Dict[str, Callable[[bpy.types.Material], None]] = {    # concrete family
    "concrete": _simple("concrete", _CONC, 0.75, noise_scale=8.0,
                        noise_strength=0.12, variation=0.35),
    "white_concrete": _simple("white_concrete", _WHITEC, 0.7, noise_scale=7.0,
                              noise_strength=0.10, variation=0.25),
    "dark_concrete": _simple("dark_concrete", _DARKC, 0.78, noise_scale=9.0,
                             noise_strength=0.14, variation=0.3),
    # brick family
    "brick_red": _brick("brick_red", (0.5, 0.16, 0.115, 1), (0.62, 0.60, 0.57, 1)),
    "brick_multicolor": _brick("brick_multicolor", (0.45, 0.14, 0.10, 1),
                               (0.62, 0.60, 0.57, 1)),
    "brick_brown": _brick("brick_brown", (0.36, 0.22, 0.13, 1), (0.58, 0.56, 0.53, 1)),
    # glass family
    "glass": _glass("glass", (0.85, 0.90, 0.92, 1), 0.04),
    "reflective_glass": _glass("reflective_glass", (0.70, 0.74, 0.80, 1), 0.02),
    "dark_glass": _glass("dark_glass", (0.20, 0.24, 0.26, 1), 0.05),
    "blue_tinted_glass": _glass("blue_tinted_glass", (0.45, 0.62, 0.80, 1), 0.03),
    # metals
    "metal": _simple("metal", (0.70, 0.71, 0.72, 1), 0.35, metallic=0.9),
    "painted_metal": _simple("painted_metal", (0.30, 0.32, 0.35, 1), 0.45,
                             noise_scale=20.0, noise_strength=0.05, metallic=0.4,
                             variation=0.2),
    "dark_metal": _simple("dark_metal", (0.09, 0.10, 0.11, 1), 0.4, metallic=0.8),
    "steel_frame": _simple("steel_frame", (0.35, 0.36, 0.38, 1), 0.3, metallic=1.0),
    # ground surfaces
    "asphalt": _asphalt("asphalt"),
    "road_marking": _simple("road_marking", (0.85, 0.85, 0.83, 1), 0.6),
    "road_marking_yellow": _simple("road_marking_yellow", (0.85, 0.65, 0.10, 1), 0.6),
    "sidewalk": _simple("sidewalk", (0.66, 0.65, 0.62, 1), 0.8, noise_scale=4.0,
                        noise_strength=0.1, variation=0.18),
    "park_path": _simple("park_path", (0.62, 0.61, 0.58, 1), 0.85),
    "curb": _simple("curb", (0.55, 0.55, 0.53, 1), 0.75, noise_scale=25.0,
                    noise_strength=0.08, variation=0.2),
    # nature
    "grass": _grass("grass"),
    "soil": _simple("soil", (0.22, 0.15, 0.09, 1), 0.95, noise_scale=14.0,
                    noise_strength=0.25, variation=0.3),
    "trunk": _simple("trunk", (0.28, 0.19, 0.11, 1), 0.9, noise_scale=30.0,
                     noise_strength=0.4, variation=0.4),
    "leaves_spring": _simple("leaves_spring", (0.35, 0.62, 0.17, 1), 0.8,
                             noise_scale=40.0, noise_strength=0.25, variation=0.5),
    "leaves_summer": _simple("leaves_summer", (0.16, 0.46, 0.10, 1), 0.8,
                             noise_scale=40.0, noise_strength=0.25, variation=0.5),
    "leaves_autumn": _simple("leaves_autumn", (0.66, 0.36, 0.07, 1), 0.8,
                             noise_scale=40.0, noise_strength=0.25, variation=0.5),
    "leaves_winter": _simple("leaves_winter", (0.36, 0.30, 0.22, 1), 0.9,
                             noise_scale=40.0, noise_strength=0.2, variation=0.3),
    "pine": _simple("pine", (0.05, 0.30, 0.12, 1), 0.85, noise_scale=30.0,
                    noise_strength=0.3, variation=0.4),
    # roofs
    "roof_tar": _simple("roof_tar", (0.14, 0.145, 0.15, 1), 0.9, noise_scale=11.0,
                        noise_strength=0.2, variation=0.3),
    "roof_tiles": _simple("roof_tiles", (0.35, 0.14, 0.12, 1), 0.75, noise_scale=6.0,
                          noise_strength=0.15, variation=0.25),
    "roof_metal": _simple("roof_metal", (0.42, 0.44, 0.46, 1), 0.4, metallic=0.9,
                          noise_scale=30.0, noise_strength=0.1),
    # building features
    "wood": _simple("wood", _WOOD, 0.7, noise_scale=20.0, noise_strength=0.08,
                    variation=0.3),
    "grime_metal": _simple("grime_metal", _GRIME, 0.55, metallic=0.5,
                           noise_scale=25.0, noise_strength=0.1),
    "sign": _simple("sign", (0.85, 0.14, 0.12, 1), 0.35,
                    emit=0.0, variation=0.1),
    "sign_cream": _simple("sign_cream", (0.86, 0.80, 0.66, 1), 0.35, variation=0.1),
    "sign_green": _simple("sign_green", (0.10, 0.42, 0.20, 1), 0.35, variation=0.1),
    "sign_dark": _simple("sign_dark", (0.06, 0.22, 0.14, 1), 0.35,
                         variation=0.1),
    "sign_text": _simple("sign_text", (0.92, 0.88, 0.78, 1), 0.4, emit=0.5,
                         emit_color=(1.0, 0.95, 0.85, 1.0)),
    "sign_highway_green": _simple("sign_highway_green",
                                  (0.06, 0.32, 0.16, 1), 0.4),
    "sign_warning": _simple("sign_warning", (0.95, 0.65, 0.05, 1), 0.4),
    "sign_construction": _simple("sign_construction",
                                 (0.95, 0.5, 0.05, 1), 0.4),
    "sign_blue": _simple("sign_blue", (0.05, 0.15, 0.45, 1), 0.4),
    "sign_black": _simple("sign_black", (0.04, 0.04, 0.045, 1), 0.4),
    # storefront glazing: mostly opaque dark glass so the hollow interior
    # never reads as a black hole
    "storefront_glass": _simple("storefront_glass", (0.36, 0.46, 0.50, 1),
                                0.22),
    # business awning colours
    "awning_green": _simple("awning_green", (0.13, 0.36, 0.19, 1), 0.55,
                            variation=0.15),
    "awning_brown": _simple("awning_brown", (0.38, 0.24, 0.13, 1), 0.6,
                            variation=0.15),
    "awning_black": _simple("awning_black", (0.07, 0.07, 0.075, 1), 0.5,
                            variation=0.1),
    "awning_red": _simple("awning_red", (0.52, 0.10, 0.09, 1), 0.55,
                          variation=0.15),
    # skyscraper glass family
    "grey_glass": _glass("grey_glass", (0.55, 0.57, 0.60, 1), 0.05),
    "green_glass": _glass("green_glass", (0.42, 0.62, 0.52, 1), 0.04),
    "crown_light": _emission("crown_light", (0.80, 0.88, 1.0, 1), 4.0),
    "pond_water": _simple("pond_water", (0.16, 0.38, 0.47, 1), 0.1,
                          noise_scale=2.0, noise_strength=0.04),
    "vehicle_glass": _simple("vehicle_glass", (0.10, 0.13, 0.17, 1), 0.12),
    # lit things
    "lamp_street": _emission("lamp_street", (1.0, 0.93, 0.75, 1), 6.0),
    "window_lit": _emission("window_lit", (1.0, 0.85, 0.62, 1), 2.2),
    "traffic_red": _emission("traffic_red", (1.0, 0.1, 0.08, 1), 5.0),
    "traffic_amber": _emission("traffic_amber", (1.0, 0.62, 0.05, 1), 5.0),
    "traffic_green": _emission("traffic_green", (0.1, 0.95, 0.2, 1), 5.0),
    "traffic_engine_off": _simple("traffic_engine_off", (0.05, 0.05, 0.05, 1), 0.3),
    # vehicles
    "car_paint": _simple("car_paint", (0.55, 0.06, 0.05, 1), 0.25, metallic=0.6,
                         variation=0.15),
    "taxi_yellow": _simple("taxi_yellow", (0.9, 0.7, 0.05, 1), 0.3, metallic=0.3),
    "rubber": _simple("rubber", (0.03, 0.03, 0.035, 1), 0.95),
    "holo_white": _simple("holo_white", (0.95, 0.95, 0.95, 1), 0.05),
    "water": _glass("water", (0.35, 0.55, 0.65, 1), 0.08, tint=0.9),
}

# keys accepted by "material_*" parameters exposed to the UI / AI
MATERIAL_KEYS: List[str] = sorted(_CATALOG.keys())

# publish the palette into params (single source of truth for the UI)
from . import params as _params_mod  # noqa: E402  (no circular import risk:
# params has no bpy/materials dependency)
_params_mod.PALETTE_BY_KEY.update(_BASE_COLORS)


def catalog_base_color(key: str):
    """The catalogue's base colour for a material key (None if unknown)."""
    base = _BASE_COLORS.get(key)
    if base:
        return tuple(base[:3])
    return None


def get_material(key: str, variation: int = 0,
                 color=None) -> bpy.types.Material:
    """Return a (shared) material for `key`, creating it on first use.

    `color` (rgba or rgb 0..1) produces a colour variant, cached by
    (key, colour) so identical colours always share one material.
    """
    if key not in _CATALOG:
        _log.warning("unknown material key %r, falling back to concrete", key)
        key = "concrete"
    if color is not None and key in _PAINTABLE:
        hexkey = "%02x%02x%02x" % tuple(int(max(0.0, min(1.0, c)) * 255)
                                        for c in color[:3])
        name = f"{_PREFIX}{key}_{hexkey}"
        mat = bpy.data.materials.get((name, None))
        if mat is not None:
            return mat
        mat = _new_material(name)
        _CATALOG[key](mat)
        _apply_tint(mat, key, color)
        mat["cityforge_key"] = key
        mat["cityforge_variation"] = int(variation)
        mat["cityforge_color"] = [color[0], color[1], color[2]]
        return mat
    if variation:
        name = f"{_PREFIX}{key}_v{variation:02d}"
    else:
        name = f"{_PREFIX}{key}"
    mat = bpy.data.materials.get((name, None))
    if mat is not None:
        return mat
    mat = _new_material(name)
    _CATALOG[key](mat)
    mat["cityforge_key"] = key           # custom prop so identification survives .blend save
    mat["cityforge_variation"] = int(variation)
    return mat


def _apply_tint(mat: bpy.types.Material, key: str, color) -> None:
    """Tint a freshly built material toward `color`."""
    import itertools
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        return
    base_in = bsdf.inputs["Base Color"]
    base = _BASE_COLORS.get(key, (1.0, 1.0, 1.0))
    scale = [max(0.05, min(2.5, (color[i] / max(1e-3, base[i]))))
             for i in range(3)]
    if base_in.links:
        node = base_in.links[0].from_node
        if node.type == "VALTORGB":   # colour ramp: scale both stops
            for el in node.color_ramp.elements:
                c = el.color
                el.color = (min(1.0, c[0] * scale[0]),
                            min(1.0, c[1] * scale[1]),
                            min(1.0, c[2] * scale[2]), c[3])
        elif hasattr(node, "inputs") and "Color1" in node.inputs:
            # brick texture: scale brick colours, keep the mortar neutral
            for cname in ("Color1", "Color2"):
                c = node.inputs[cname].default_value
                node.inputs[cname].default_value = (
                    min(1.0, c[0] * scale[0]), min(1.0, c[1] * scale[1]),
                    min(1.0, c[2] * scale[2]), c[3])
    else:
        c = base_in.default_value
        base_in.default_value = (color[0], color[1], color[2],
                                 c[3] if len(c) > 3 else 1.0)


def register_base_color(key: str, color: tuple) -> None:
    _BASE_COLORS[key] = tuple(color[:3])


# ---------------------------------------------------------------------------
# coherent palette generation (seeded)
# ---------------------------------------------------------------------------

import colorsys


def generate_palette(rng) -> Dict[str, tuple]:
    """Architecturally coherent RGBA palette: neutral body, darker roof/
    trim, tinted glass.  Seeded -> same rng state gives the same palette."""
    import colorsys as _cs
    h = rng.random()
    sat = rng.uniform(0.05, 0.28)          # muted, architectural
    val = rng.uniform(0.62, 0.88)
    r, g, b = _cs.hsv_to_rgb(h, sat, val)
    primary = (r, g, b, 1.0)
    # secondary: darker + less saturated version of the same hue family
    r2, g2, b2 = _cs.hsv_to_rgb((h + rng.uniform(-0.03, 0.03)) % 1.0,
                                sat * 1.2, val * 0.45)
    secondary = (r2, g2, b2, 1.0)
    # glass: blue/green/grey family
    gh = rng.choice((0.58, 0.55, 0.42, 0.0))
    r3, g3, b3 = _cs.hsv_to_rgb(gh, 0.25, 0.72)
    window = (r3, g3, b3, 1.0)
    # trim: near-black warm or cool
    tv = rng.uniform(0.04, 0.12)
    trim = (tv, tv * 0.98, tv * 1.05, 1.0)
    return {"primary": primary, "secondary": secondary, "window": window,
            "trim": trim}


def color_to_hex(color) -> str:
    return "%02x%02x%02x" % tuple(int(max(0.0, min(1.0, c)) * 255)
                                  for c in color[:3])


def all_library_materials() -> List[bpy.types.Material]:
    """Every material currently loaded that belongs to this library."""
    return [m for m in bpy.data.materials
            if m.get("cityforge_key") is not None]


def library_stats() -> Dict[str, int]:
    mats = all_library_materials()
    return {
        "materials": len(mats),
        "catalog_size": len(_CATALOG),
        "max_cache": _MAX_CACHE,
    }


def apply_variation(obj, primary_seed: int) -> None:
    """Give a generated asset subtle colour variation.

    Rather than duplicating materials per object (which would explode their
    count), variation is applied *per object* via object colour-driven shading:
    each CityForge material mixes the object's custom ``cityforge_tint``.
    """
    import random as _r
    rng = _r.Random(int(primary_seed) & 0xFFFFFFFF)
    tint = (rng.uniform(0.92, 1.08), rng.uniform(0.92, 1.08), rng.uniform(0.92, 1.08))
    obj["cityforge_tint"] = [tint[0], tint[1], tint[2]]
    obj.color = (tint[0] * 0.5 + 0.5, tint[1] * 0.5 + 0.5, tint[2] * 0.5 + 0.5, 1.0)


def purge_unused_library() -> int:
    """Remove library materials not referenced by any mesh. Returns removed."""
    removed = 0
    for mat in list(all_library_materials()):
        if mat.users == 0:
            bpy.data.materials.remove(mat, do_unlink=True)
            removed += 1
    return removed
