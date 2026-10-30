# SPDX-License-Identifier: GPL-3.0-or-later
"""Generation dispatcher: turns validated parameters into Blender objects.

Handles type routing (building / road / vegetation / prop / vehicle), polygon
budget fallback and asset-manager integration.
"""

from __future__ import annotations

from typing import Optional

import bpy

from ..core.params import (
    BUILDING_TYPES,
    GenerationParams,
    PORT_ASSET_TYPES,
    PROP_TYPES,
    RAIL_ASSET_TYPES,
    ROAD_INFRA_TYPES,
    ROAD_TYPES,
    TYPE_DEFAULT_STYLE,
    VEGETATION_TYPES,
)
from ..utils import get_logger
from ..utils.naming import asset_name
from . import asset_manager
from .materials import apply_variation

_log = get_logger()

__all__ = ["generate_asset", "regenerate_asset"]


def generate_asset(params: GenerationParams) -> Optional[bpy.types.Object]:
    """Generate one asset and link it into the CityForge collection tree.

    Returns the created object, or None on failure (after logging).
    """
    params = _prepare(params)

    keep_normals_engine = bpy.context.scene.render.engine

    if params.asset_type in BUILDING_TYPES:
        from ..generators import buildings
        if params.construction_animation:
            router, info = buildings.build_building(params, parts_mode=True)
            return _build_construction_animation(params, router, info)
        else:
            mb, info = buildings.build_building(params)
            mesh, _mats = mb.finish("CFBuilding")
    elif params.asset_type in ROAD_TYPES:
        from ..generators import roads
        mb, info = roads.build_asset(params)
        mesh, _mats = mb.finish("CFRoad")
    elif params.asset_type in VEGETATION_TYPES:
        from ..generators import vegetation
        mb, info = vegetation.build_asset(params)
        mesh, _mats = mb.finish("CFTree")
    elif params.asset_type in PROP_TYPES:
        from ..generators import props
        mb, info = props.build_asset(params)
        mesh, _mats = mb.finish("CFProp")
    elif params.asset_type in RAIL_ASSET_TYPES:
        from ..generators import rail
        mb, info = rail.build_asset(params)
        mesh, _mats = mb.finish("CFRail")
    elif params.asset_type in PORT_ASSET_TYPES:
        from ..generators import port
        mb, info = port.build_asset(params)
        mesh, _mats = mb.finish("CFPort")
    elif params.asset_type in ROAD_INFRA_TYPES:
        from ..generators import roads
        mb, info = roads.build_asset(params)
        mesh, _mats = mb.finish("CFRoad")
    elif params.asset_type in ("BICYCLE", "MOTORCYCLE"):
        from ..generators import vehicles
        params.vehicle_class = params.asset_type.lower()
        mb, info = vehicles.build_asset(params)
        mesh, _mats = mb.finish("CFVehicle")
    elif params.asset_type == "VEHICLE":
        from ..generators import vehicles
        mb, info = vehicles.build_asset(params)
        mesh, _mats = mb.finish("CFVehicle")
    elif params.asset_type == "NPC":
        from ..generators import characters
        mb, info = characters.build_asset(params)
        mesh, _mats = mb.finish("CFCharacter")
        obj = asset_manager.create_asset(
            asset_name("NPC", info.get("style", "npc"), params.seed),
            mesh, params, mb.poly_count())
        from ..core.materials import apply_variation as _av
        _av(obj, params.seed)
        if params.npc_rigged:
            arm = characters.rig_character(obj, params)
            characters.add_animation_clip(arm, params.npc_clip or "idle")
        obj["cityforge_info"] = {
            k: (v if isinstance(v, (int, float, str)) else str(v))
            for k, v in info.items()}
        return obj
    elif params.asset_type == "PARK":
        from ..generators import parks
        mb, info = parks.build_asset(params)
        mesh, _mats = mb.finish("CFPark")
    else:
        _log.error("asset type %s has no generator", params.asset_type)
        return None

    poly_count = mb.poly_count()

    # polygon budget: progressively fall back to cheaper construction rather
    # than shipping an unbudgeted mesh
    if poly_count > params.poly_budget and params.detail_level != "low":
        cheaper = {"high": "medium", "medium": "low"}.get(params.detail_level)
        _log.info("poly budget exceeded (%d > %d); regenerating at %s detail",
                  poly_count, params.poly_budget, cheaper)
        params.detail_level = cheaper
        return generate_asset(params)
    if poly_count > params.poly_budget and params.detail_level == "low" \
            and not params.extra.get("_tier2_done"):
        # second fallback tier: denser window spacing, no balconies
        params.extra["_tier2_done"] = True
        params.window_spacing = max(3.0, params.window_spacing * 1.8)
        params.balcony_style = "none"
        params.roof_extras = 0
        params.podium_floors = 0
        _log.info("tier-2 budget fallback: reduced detail levels")
        obj = generate_asset(params)
        if obj is not None:
            obj["cityforge_budget_warning"] = True
        return obj
    if poly_count > params.poly_budget:
        _log.warning("asset exceeds poly budget even at low detail "
                     "(%d > %d)", poly_count, params.poly_budget)

    name = asset_name(params.asset_type, info.get("style",
                      params.asset_type.lower()), params.seed)
    obj = asset_manager.create_asset(name, mesh, params, poly_count)
    apply_variation(obj, params.seed)
    obj["cityforge_info"] = {
        k: (v if isinstance(v, (int, float, str)) else str(v))
        for k, v in info.items()}
    # parks instantiate their vegetation/props as parented children
    if params.asset_type == "PARK" and info.get("park_children"):
        from ..generators import parks
        parks.build_children(params, info["park_children"], obj)
        obj["cityforge_park_children"] = len(obj.children)
    # commercial buildings get readable sign text (joined into the mesh)
    if params.asset_type in BUILDING_TYPES and info.get("business_name"):
        from ..generators import buildings as buildings_mod
        buildings_mod.apply_signage_text(obj, params, info)
        poly_count = len(obj.data.polygons)
        obj["cityforge_polygons"] = poly_count
    # vehicle scale applies at object level so meshes stay shared
    if params.asset_type == "VEHICLE" and info.get("scale"):
        s = float(info["scale"])
        if abs(s - 1.0) > 1e-3:
            obj.scale = (s, s, s)
    return obj

def _build_construction_animation(params: GenerationParams, router, info):
    """Instantiate the staged parts and keyframe a rise-and-reveal sequence.

    Each part: hidden until its stage, then rises from below grade and
    settles.  Keyframes are plain transforms + hide flags, which export to
    FBX and play in Unity's Animation component.
    """
    import mathutils

    import bpy

    from ..utils.naming import asset_name
    from . import asset_manager
    from .materials import apply_variation

    parts = list(router.parts.items())
    poly_count = router.poly_count()
    name = asset_name(params.asset_type,
                      info.get("style", params.asset_type.lower()),
                      params.seed)
    root = asset_manager.create_root_asset(name, params, poly_count)
    apply_variation(root, params.seed)

    fps = bpy.context.scene.render.fps or 24
    duration_s = max(2.0, params.construction_duration)
    total_frames = int(duration_s * fps)
    n = max(1, len(parts))
    for i, (part_name, part) in enumerate(parts):
        mesh, _mats = part.finish("CFPart")
        part_obj = bpy.data.objects.new(f"{name}_{part_name}", mesh)
        col = None
        for c in root.users_collection:
            col = c
            break
        (col or bpy.context.scene.collection).objects.link(part_obj)
        part_obj.parent = root
        part_obj.location = (0.0, 0.0, 0.0)

        start = int(i / n * total_frames) + 1
        end = int((i + 1) / n * total_frames) + 1
        rise = min(3.0, 0.5 + info.get("height", 10) / max(1, n))
        # visibility keys
        part_obj.hide_viewport = True
        part_obj.hide_render = True
        part_obj.keyframe_insert("hide_viewport", frame=max(1, start - 1))
        part_obj.keyframe_insert("hide_render", frame=max(1, start - 1))
        part_obj.hide_viewport = False
        part_obj.hide_render = False
        part_obj.keyframe_insert("hide_viewport", frame=start)
        part_obj.keyframe_insert("hide_render", frame=start)
        # rise from below grade
        part_obj.location = (0.0, 0.0, -rise)
        part_obj.keyframe_insert("location", frame=start)
        part_obj.location = (0.0, 0.0, 0.0)
        part_obj.keyframe_insert("location", frame=max(start + 2, end))
    root["cityforge_construction"] = {
        "parts": len(parts),
        "duration_frames": total_frames,
        "fps": fps,
    }
    return root


def _prepare(params: GenerationParams) -> GenerationParams:
    """Fill implicit defaults implied by the asset type (style etc.)."""
    if params.asset_type in BUILDING_TYPES:
        if params.style == "auto" or not params.style:
            params.style = TYPE_DEFAULT_STYLE.get(
                params.asset_type, "modern_residential")
        # Architectural-level normalization is always safe (additive).
        from .params import apply_arch_levels
        apply_arch_levels(params)
        # category validation: industrial buildings must never produce
        # residential structures (and vice versa)
        from .params import sanitize_category
        sanitize_category(params)
    return params


def regenerate_asset(obj: bpy.types.Object) -> Optional[bpy.types.Object]:
    """Rebuild a previously generated object from its stored parameters."""
    old_params = asset_manager.get_stored_params(obj)
    if old_params is None:
        _log.error("%s was not generated by CityForge", obj.name)
        return None
    new_obj = generate_asset(old_params)
    if new_obj is not None:
        asset_manager.delete_asset(obj)
    return new_obj
