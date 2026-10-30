# SPDX-License-Identifier: GPL-3.0-or-later
"""Asset organisation: collections, naming, custom properties, provenance.

Every generated object is created through :func:`create_asset`, which links it
to the right CityForge collection and stores a full generation-time parameter
back-up as custom properties, so assets can be regenerated or inspected later.
"""

from __future__ import annotations

import datetime
import json
from typing import Any, Dict, Optional, Tuple

import bpy

from ..core.params import GenerationParams
from ..utils import get_logger
from ..utils.naming import collection_name, sanitize_name

_log = get_logger()

ROOT_NAME = "CityForge_Assets"

CATEGORY_TREE: Dict[str, Tuple[str, ...]] = {
    "RESIDENTIAL": ("Buildings", "Residential"),
    "COMMERCIAL": ("Buildings", "Commercial"),
    "OFFICE": ("Buildings", "Offices"),
    "INDUSTRIAL": ("Buildings", "Industrial"),
    "MIXED": ("Buildings", "Mixed"),
    "SKYSCRAPER": ("Buildings", "Offices"),
    "HOUSE": ("Buildings", "Residential"),
    "SHOP": ("Buildings", "Commercial"),
    "WAREHOUSE": ("Buildings", "Industrial"),
    "PARKING_STRUCTURE": ("Buildings", "Parking"),
    "ROAD": ("Roads",),
    "SIDEWALK": ("Roads",),
    "VEHICLE": ("Vehicles",),
    "NPC": ("Characters",),
    "PARK": ("Parks",),
    "TREE": ("Vegetation",),
    "BUSH": ("Vegetation",),
    "STREETLIGHT": ("Props", "Street furniture"),
    "TRAFFIC_SIGN": ("Props", "Street furniture"),
    "TRAFFIC_LIGHT": ("Props", "Street furniture"),
    "BENCH": ("Props", "Street furniture"),
    "BUS_STOP": ("Props", "Street furniture"),
    "PARKING_METER": ("Props", "Street furniture"),
    "GARBAGE_BIN": ("Props", "Street furniture"),
    "FENCE": ("Props", "Street furniture"),
    "BOLLARD": ("Props", "Street furniture"),
    "HYDRANT": ("Props", "Street furniture"),
    "PLANTER": ("Props", "Street furniture"),
    "BARRIER": ("Props", "Street furniture"),
    "PARK": ("Props", "Street furniture"),
}


def ensure_root() -> bpy.types.Collection:
    root = bpy.data.collections.get(ROOT_NAME) or bpy.data.collections.new(ROOT_NAME)
    if root.name not in bpy.context.scene.collection.children:
        try:
            bpy.context.scene.collection.children.link(root)
        except RuntimeError:
            pass  # already linked in another scene; fine
    return root


def category_collection(asset_type: str) -> bpy.types.Collection:
    """Find/create the nested collection for an asset type, e.g.

    CityForge_Assets/Buildings/Residential
    """
    ensure_root()
    path = CATEGORY_TREE.get(asset_type, ("Other",))
    parent = bpy.context.scene.collection.children.get(ROOT_NAME) or ensure_root()
    for part in path:
        child = bpy.data.collections.get(part) or bpy.data.collections.new(part)
        if child.name not in parent.children:
            parent.children.link(child)
        parent = child
    return parent


def generated_registry(scene) -> Dict[str, Any]:
    if "cityforge_generated" not in scene:
        scene["cityforge_generated"] = {}
    return scene["cityforge_generated"]


def _store_params(obj: bpy.types.Object, params: GenerationParams) -> None:
    obj["cityforge_params"] = json.dumps(params.to_dict(), default=str)
    obj["cityforge_asset_type"] = params.asset_type
    obj["cityforge_style"] = params.style
    obj["cityforge_seed"] = int(params.seed)
    obj["cityforge_detail_level"] = params.detail_level
    obj["cityforge_generated_at"] = datetime.datetime.now().isoformat(
        timespec="seconds")
    obj["cityforge_version"] = "1.0.0"


def get_stored_params(obj: bpy.types.Object) -> Optional[GenerationParams]:
    raw = obj.get("cityforge_params")
    if not raw:
        return None
    try:
        return GenerationParams.from_dict(json.loads(raw))
    except (ValueError, TypeError, KeyError) as exc:
        _log.warning("stored parameters unreadable on %s: %s", obj.name, exc)
        return None


def create_root_asset(name: str, params: GenerationParams,
                      poly_count: int) -> bpy.types.Object:
    """Create a root EMPTY for grouped assets (construction animations)."""
    from ..utils.naming import sanitize_name
    empty = bpy.data.objects.new(sanitize_name(name) + "_root", None)
    empty.empty_display_size = 0.5
    empty.empty_display_type = 'PLAIN_AXES'
    category_collection(params.asset_type).objects.link(empty)
    _store_params(empty, params)
    empty["cityforge_polygons"] = int(poly_count)
    registry = generated_registry(bpy.context.scene)
    registry[empty.name] = {
        "asset_type": params.asset_type,
        "seed": int(params.seed),
        "style": params.style,
        "detail": params.detail_level,
        "polygons": int(poly_count),
        "created": empty.get("cityforge_generated_at", ""),
    }
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except RuntimeError:
        pass
    empty.select_set(True)
    bpy.context.view_layer.objects.active = empty
    return empty


def create_asset(name: str, mesh, params: GenerationParams,
                 poly_count: int) -> bpy.types.Object:
    """Create a mesh object, link it in the right collection and label it."""
    obj = bpy.data.objects.new(sanitize_name(name), mesh)
    category_collection(params.asset_type).objects.link(obj)

    _store_params(obj, params)
    obj["cityforge_polygons"] = int(poly_count)
    obj["cityforge_dimensions"] = [round(float(d), 3) for d in obj.dimensions] \
        if mesh else [0, 0, 0]

    registry = generated_registry(bpy.context.scene)
    registry[obj.name] = {
        "asset_type": params.asset_type,
        "seed": int(params.seed),
        "style": params.style,
        "detail": params.detail_level,
        "polygons": int(poly_count),
        "created": obj.get("cityforge_generated_at", ""),
    }

    # Ensure a consistent, Unity-friendly origin: centre-bottom at ground.
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)

    try:
        bpy.ops.object.select_all(action='DESELECT')
    except RuntimeError:
        pass
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


def delete_asset(obj: bpy.types.Object) -> None:
    """Unlink and delete a generated asset and its mesh (data only owner)."""
    registry = generated_registry(bpy.context.scene)
    registry.pop(obj.name, None)
    bpy.data.objects.remove(obj, do_unlink=True)


def count_generated(scene) -> int:
    return len(generated_registry(scene))


def list_generated(scene) -> list:
    """All objects still present in this scene that CityForge generated."""
    out = []
    for obj in scene.objects:
        if obj.get("cityforge_params"):
            out.append(obj)
    return out


def find_asset(name: str):
    return bpy.context.scene.objects.get(name)
