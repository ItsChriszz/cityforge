# SPDX-License-Identifier: GPL-3.0-or-later
"""Export manager: FBX / GLB export with the documented Unity conventions.

Conventions:
* 1 Blender unit = 1 Unity metre; no scaling is applied on export.
* Assets are modelled facing -Y in Blender. Blender's FBX exporter default
  (forward = -Y, up = Z) maps this so that Unity imports the object facing
  +Z. Do NOT add manual rotation fixes after import.
* Origins sit at the centre of the ground footprint (z = 0).

Files are written into <export_dir>/<Category>/<name>.fbx|glb where Category
is Buildings / Roads / Props / Vegetation / Vehicles.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import bpy

from ..utils import get_logger
from . import asset_manager

_log = get_logger()

_CATEGORY_DIRS = {
    "BUILDING": "Buildings",
    "ROAD": "Roads",
    "SIDEWALK": "Roads",
    "VEGETATION": "Vegetation",
    "VEHICLE": "Vehicles",
    "PROP": "Props",
    "OTHER": "Props",
}

_EXPORT_EXTS = {"FBX": ".fbx", "GLB": ".glb"}


def _category_dir(asset_type: str) -> str:
    if asset_type in ("TREE", "BUSH"):
        return "Vegetation"
    if asset_type in ("ROAD", "SIDEWALK", "CROSSWALK"):
        return "Roads"
    if asset_type == "VEHICLE":
        return "Vehicles"
    if asset_type == "PARK":
        return "Parks"
    if asset_type == "NPC":
        return "Characters"
    if asset_type in ("STREETLIGHT", "TRAFFIC_SIGN", "TRAFFIC_LIGHT",
                      "BENCH", "BUS_STOP", "PARKING_METER", "GARBAGE_BIN",
                      "FENCE", "BOLLARD", "HYDRANT", "PLANTER", "BARRIER"):
        return "Props"
    return "Buildings"


def resolve_export_dir(context) -> str:
    export = context.scene.cityforge_export
    path = bpy.path.abspath(export.export_dir) or os.getcwd()
    if not path:
        path = "//CityForge_Export/"
    return os.path.normpath(path)


def unique_export_path(export_dir: str, category_dir_name: str, name: str,
                       fmt: str) -> str:
    """
    Resolve the final file path, ensuring the category folder exists without
    overwriting (duplicate names get _NN suffixes).
    """
    category_dir = os.path.join(export_dir, category_dir_name)
    os.makedirs(category_dir, exist_ok=True)
    ext = _EXPORT_EXTS[fmt]
    path = os.path.join(category_dir, name + ext)
    n = 1
    while os.path.exists(path):
        path = os.path.join(category_dir, f"{name}_{n:02d}{ext}")
        n += 1
    return path


def export_asset(context, obj: bpy.types.Object, fmt: Optional[str] = None
                 ) -> Tuple[Optional[str], str]:
    """Export one object; returns (path, status_message)."""
    fmt = fmt or context.scene.cityforge_export.export_format
    if obj.type != 'MESH':
        return None, f"{obj.name} is not a mesh"
    export_dir = resolve_export_dir(context)
    asset_type = obj.get("cityforge_asset_type", "OTHER")
    path = unique_export_path(export_dir, _category_dir(asset_type),
                              obj.name, fmt)

    # export ONLY this object
    prev_active = context.view_layer.objects.active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    try:
        if fmt == "FBX":
            bpy.ops.export_scene.fbx(
                filepath=path, use_selection=True,
                apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
                axis_forward='-Y', axis_up='Z', bake_space_transform=False,
                use_mesh_modifiers=True,
                mesh_smooth_type='OFF', use_tspace=False)
        elif fmt == "GLB":
            bpy.ops.export_scene.gltf(
                filepath=path, export_format='GLB', use_selection=True,
                export_yup=True, export_apply=True)
        else:
            return None, f"unknown export format {fmt}"
    except (RuntimeError, OSError) as exc:
        return None, f"export failed for {obj.name}: {exc}"
    finally:
        bpy.ops.object.select_all(action='DESELECT')
        if prev_active:
            prev_active.select_set(True)
            context.view_layer.objects.active = prev_active

    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None, f"export wasted nothing for {obj.name}: no file written"
    return path, f"exported {obj.name} -> {path} ({os.path.getsize(path)} B)"


def export_selected(context) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for obj in context.selected_objects:
        path, msg = export_asset(context, obj)
        out.append((obj.name, msg))
    return out


def export_all_cityforge(context) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for obj in asset_manager.list_generated(context.scene):
        out.append((obj.name, export_asset(context, obj)[1]))
    return out
