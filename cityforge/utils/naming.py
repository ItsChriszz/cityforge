# SPDX-License-Identifier: GPL-3.0-or-later
"""Consistent object naming helpers for CityForge assets."""

import re

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_\-]+")

CATEGORY_PREFIX = {
    "RESIDENTIAL": "Res",
    "COMMERCIAL": "Com",
    "OFFICE": "Off",
    "INDUSTRIAL": "Ind",
    "MIXED": "Mix",
    "SKYSCRAPER": "Sky",
    "HOUSE": "Hou",
    "SHOP": "Shp",
    "WAREHOUSE": "Whs",
    "ROAD": "Rd",
    "SIDEWALK": "Sw",
    "STREET_FURNITURE": "Frn",
    "TREE": "Tre",
    "BUSH": "Bsh",
    "VEHICLE": "Veh",
    "STREETLIGHT": "Lgt",
    "TRAFFIC_SIGN": "Sgn",
    "BENCH": "Bch",
    "PARKING": "Prk",
    "PARK": "Par",
    "NPC": "Npc",
    "PROP": "Prp",
}


def sanitize_name(raw: str) -> str:
    cleaned = _SANITIZE_RE.sub("_", raw.strip())
    return cleaned or "Asset"


def asset_name(category: str, style: str, seed: int) -> str:
    """Deterministically name an asset, e.g. ResModern_0042137."""
    prefix = CATEGORY_PREFIX.get(category, "As")
    return f"{prefix}{sanitize_name(style)}_{abs(seed) % 10000000:07d}"


def variation_name(base: str, index: int) -> str:
    return f"{base}_v{index:02d}"


def lod_name(base: str, lod: str) -> str:
    """Standardised LOD suffix, e.g. ResModern_0042137_LOD_MED."""
    return f"{base}_LOD_{lod}"


def collection_name(category: str) -> str:
    return {
        "BUILDING": "Buildings",
        "ROAD": "Roads",
        "SIDWALK": "Roads",
        "SIDEWALK": "Roads",
        "VEGETATION": "Vegetation",
        "PROP": "Props",
        "VEHICLE": "Vehicles",
    }.get(category, "Other")
