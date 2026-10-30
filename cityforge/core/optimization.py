# SPDX-License-Identifier: GPL-3.0-or-later
"""Geometry optimization: statistics, cleanup joins, LOD regeneration.

All destructive operations respect the "preserve originals" rule: when the
user optimizes an asset, the untouched version is moved into a separate
CityForge_Originals collection instead of being destroyed.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import bpy

from ..utils import get_logger
from ..utils.naming import lod_name
from . import asset_manager
from .materials import apply_variation

_log = get_logger()

ORIGINALS_COLLECTION = "CityForge_Originals"


def object_stats(obj: bpy.types.Object) -> Dict[str, int]:
    polys = verts = 0
    if obj.type == 'MESH':
        mesh = obj.data
        polys = len(mesh.polygons)
        verts = len(mesh.vertices)
    return {"vertices": verts, "polygons": polys}


def scene_stats() -> Dict[str, Any]:
    objs = asset_manager.list_generated(bpy.context.scene)
    per_cat: Dict[str, int] = {}
    total_polys = 0
    for obj in objs:
        t = obj.get("cityforge_asset_type", "OTHER")
        per_cat[t] = per_cat.get(t, 0) + 1
        total_polys += obj.get("cityforge_polygons", 0)
    return {
        "assets": len(objs),
        "by_category": per_cat,
        "total_polygons": total_polys,
    }


def _originals_collection() -> bpy.types.Collection:
    col = (bpy.data.collections.get(ORIGINALS_COLLECTION)
           or bpy.data.collections.new(ORIGINALS_COLLECTION))
    if col.name not in bpy.context.scene.collection.children:
        try:
            bpy.context.scene.collection.children.link(col)
        except RuntimeError:
            pass
    return col


def preserve_original(obj: bpy.types.Object) -> None:
    """Move an untouched copy into CityForge_Originals."""
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    _originals_collection().objects.link(obj)


def join_generated_similarity(obj: bpy.types.Object) -> bool:
    """Join CityForge assets that share the same mesh data; returns changed."""
    return False  # assets are single objects already


def cleanup_mesh(obj: bpy.types.Object, weld_tolerance: float = 0.0005) -> bool:
    """Weld duplicate vertices and clear loose geometry. Non-destructive to
    the original when `preserve_original` was used (caller's duty)."""
    if obj.type != 'MESH':
        return False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.remove_doubles(threshold=weld_tolerance)
        bpy.ops.mesh.normals_make_consistent()
        bpy.ops.object.mode_set(mode='OBJECT')
        return True
    except RuntimeError as exc:
        _log.warning("cleanup failed on %s: %s", obj.name, exc)
        return False


def optimize_selected(preserve: bool = True) -> List[str]:
    """Clean up selected generated assets; optionally keep pristine copies."""
    report: List[str] = []
    for obj in bpy.context.selected_objects:
        params = asset_manager.get_stored_params(obj)
        if params is None:
            report.append(f"{obj.name}: not a CityForge asset, skipped")
            continue
        before = object_stats(obj)
        if preserve:
            keep = obj.copy()
            keep.data = obj.data.copy()
            bpy.context.scene.collection.objects.link(keep)
            del keep["cityforge_params"]
            keep.name = lod_name(obj.name, "PREOPT")
            preserve_original(keep)
        cleanup_mesh(obj)
        obj["cityforge_polygons"] = object_stats(obj)["polygons"]
        after = object_stats(obj)
        report.append(
            f"{obj.name}: {before['polygons']} -> {after['polygons']} polys")
    return report


def generate_lod(asset_obj: bpy.types.Object, lod_detail: str) -> \
        Optional[bpy.types.Object]:
    """Regenerate an asset at a different detail level (+ suffix object)."""
    params = asset_manager.get_stored_params(asset_obj)
    if params is None:
        return None
    from .generator import generate_asset
    params.detail_level = lod_detail
    new_obj = generate_asset(params)
    if new_obj is not None:
        new_obj.name = lod_name(asset_obj.name, lod_detail.upper())
        new_obj["cityforge_parent_asset"] = asset_obj.name
        new_obj["cfx_lod"] = lod_detail
    return new_obj
