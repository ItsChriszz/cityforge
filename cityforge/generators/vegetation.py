# SPDX-License-Identifier: GPL-3.0-or-later
"""Vegetation generator: trees and bushes.

Trunk with taper, optional branches, canopy assembled from overlapping
spheres.  Season controls leaf material; LOW detail collapses to a single
blob canopy.  Deterministic for identical seeds.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..core.params import GenerationParams
from ..core.randomization import chance, jitter, make_rng
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]

_SEASON = {
    "spring": "leaves_spring", "summer": "leaves_summer",
    "autumn": "leaves_autumn", "winter": "leaves_winter",
}


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "veg")
    mb = MeshBuilder()
    seg = {"low": 6, "medium": 10, "high": 14}.get(params.detail_level, 8)
    sphere_seg, sphere_rings = {"low": (7, 4), "medium": (10, 6),
                                "high": (12, 8)}.get(params.detail_level,
                                                     (8, 5))

    if params.asset_type == "BUSH":
        _bush(mb, rng, params, sphere_seg, sphere_rings)
    elif params.asset_type == "HEDGE":
        _hedge(mb, rng, params, seg, sphere_seg, sphere_rings)
    elif params.asset_type == "FLOWERBED":
        _flowerbed(mb, rng, params, seg)
    else:
        _tree(mb, rng, params, seg, sphere_seg, sphere_rings)

    info = {
        "style": params.tree_type,
        "season": params.season,
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


def _leaf_material(params: GenerationParams) -> str:
    if params.tree_type == "evergreen":
        return "pine"
    if params.season == "winter" and params.tree_type == "deciduous":
        return "leaves_winter"
    return _SEASON.get(params.season, "leaves_summer")


def _hedge(mb, rng, params: GenerationParams, seg, sphere_seg, rings) -> None:
    """Clipped hedge: a long planted box with rounded foliage blobs."""
    length = max(1.0, params.fence_length if params.fence_length else 6.0)
    h = 0.9
    d = 0.7
    leaf = _leaf_material(params)
    mb.add_box((0, 0, h * 0.32), (length, d, h * 0.64), leaf)
    n = max(2, int(length / 1.2))
    for i in range(n + 1):
        x = -length / 2 + length * i / n
        mb.add_sphere((x, 0, h * 0.62), d * 0.62, seg, rings, leaf,
                      squash=0.72)
    mb.add_box((0, 0, 0.02), (length + 0.2, d + 0.2, 0.08), "soil")


def _flowerbed(mb, rng, params: GenerationParams, seg) -> None:
    """Standalone flower bed with seasonal blooms."""
    x, y = 0.0, 0.0
    mb.add_box((x, y, 0.18), (1.8, 1.1, 0.36), "concrete")
    mb.add_box((x, y, 0.38), (1.55, 0.9, 0.1), "soil")
    cols = [(0.9, 0.2, 0.25), (0.95, 0.75, 0.15), (0.8, 0.3, 0.7),
            (0.95, 0.95, 0.9)]
    n = 8 if params.detail_level != "low" else 5
    for i in range(n):
        fx = x + rng.uniform(-0.68, 0.68)
        fy = y + rng.uniform(-0.38, 0.38)
        col = "painted_metal#" + "%02x%02x%02x" % tuple(
            int(c * 255) for c in rng.choice(cols))
        mb.add_cylinder((fx, fy, 0.5), 0.06, 0.26, 5, "leaves_summer")
        mb.add_sphere((fx, fy, 0.68), 0.1, seg, 4, col)


def _bush(mb, rng, params: GenerationParams, seg, rings) -> None:
    """Closed-looking shrub: one grounded main sphere plus overlapping
    satellite blobs that fill the silhouette (no hollow top, no floaters)."""
    r = max(0.3, params.canopy_radius * 0.45)
    leaf_mat = _leaf_material(params)
    main_r = r * 0.85
    # main body, slightly sunk into the ground for a planted look
    mb.add_sphere((0, 0, main_r * 0.8), main_r, seg, rings, leaf_mat,
                  squash=0.8)
    # satellites: guaranteed top fill + sides, all intersecting the body
    n_fill = {"low": 2, "medium": 4, "high": 6}.get(params.detail_level, 4)
    # crown fill on top (kept mostly inside the core blob: no dark creases)
    mb.add_sphere((0, 0, main_r * 1.08), main_r * 0.55, seg, rings,
                  leaf_mat, squash=0.72)
    angles = [2 * math.pi * i / max(1, n_fill - 1) for i in range(n_fill - 1)]
    for i, a in enumerate(angles):
        off = main_r * 0.55
        bx = math.cos(a) * off
        by = math.sin(a) * off
        br = main_r * rng.uniform(0.5, 0.68)
        mb.add_sphere((bx, by, main_r * 0.62 + br * 0.3), br, seg, rings,
                      leaf_mat, squash=0.78)


def _tree(mb, rng, params: GenerationParams, seg, sphere_seg, rings) -> None:
    h = max(1.5, params.tree_height)
    trunk_r = max(0.05, params.trunk_radius)
    leaf_mat = _leaf_material(params)

    winter_bare = (params.season == "winter" and params.tree_type ==
                   "deciduous")
    if params.tree_type == "evergreen":
        n_blobs = 3
    elif winter_bare:
        n_blobs = 0
    else:
        n_blobs = max(3, int(3 + 7 * params.leaf_density))

    # canopy occupies the top of the tree; the trunk always reaches INTO it
    canopy_c = h * 0.78
    canopy_r = max(0.5, params.canopy_radius)
    trunk_top_z = canopy_c - canopy_r * 0.45

    # trunk (tapered cylinder), top buried inside the canopy volume
    top_r = trunk_r * (0.35 if params.tree_type != "palm" else 0.8)
    mb.add_cylinder((0, 0, trunk_top_z / 2), trunk_r, trunk_top_z, seg,
                    "trunk", top_radius=top_r)
    # root flare (fully above ground)
    mb.add_cylinder((0, 0, trunk_r * 0.45), trunk_r * 1.5, trunk_r * 0.9,
                    seg, "trunk", top_radius=trunk_r)

    # branches: short stubs that start inside the trunk and END INSIDE the
    # canopy core (hidden by foliage on all types that have a canopy)
    n_branches = max(0, int(params.branch_count))
    for i in range(n_branches):
        if params.tree_type == "evergreen":
            break  # cones would leave them exposed; trunk is enough
        a = 2 * math.pi * i / max(1, n_branches) + rng.uniform(-0.25, 0.25)
        # rise slightly above the trunk top, stay within the core blob
        # radius (canopy_r) so foliage always envelops the tips
        z0 = trunk_top_z - trunk_r * 2.0
        seg_len = canopy_r * 0.32
        steps = 2 if params.detail_level == "low" else 3
        bx = by = 0.0
        br = trunk_r * 0.55
        for k in range(steps):
            z = z0 + (trunk_top_z - z0) * (k + 1) / steps + k * 0.12
            bx += math.cos(a) * seg_len / steps
            by += math.sin(a) * seg_len / steps
            mb.add_cylinder((bx, by, z), br, seg_len * 0.6,
                            max(4, seg // 3), "trunk", top_radius=br * 0.7)
            br *= 0.75

    # canopy blobs
    if params.tree_type == "evergreen":
        # stacked cones as a stylised conifer, base overlapping the trunk
        levels = 3 if params.detail_level == "low" else 4
        base_z = trunk_top_z - canopy_r * 0.2
        for li in range(levels):
            z0 = base_z + li * (h - base_z - 0.5) / levels
            layer_h = (h - base_z) / levels + 0.4
            r = canopy_r * (1.0 - 0.62 * li / max(1, levels))
            mb.add_cylinder((0, 0, z0 + layer_h / 2), r, layer_h, seg,
                            leaf_mat, top_radius=r * 0.15)
    else:
        # blob cluster centred on the canopy; guaranteed overlap with the
        # trunk top plus a crown blob on top
        blobs = [
            (0.0, 0.0, canopy_c, canopy_r),                        # core
            (canopy_r * 0.42, canopy_r * 0.25, canopy_c - canopy_r * 0.18,
             canopy_r * 0.72),
            (-canopy_r * 0.38, -canopy_r * 0.20, canopy_c - canopy_r * 0.14,
             canopy_r * 0.68),
            (canopy_r * 0.10, -canopy_r * 0.42, canopy_c + canopy_r * 0.02,
             canopy_r * 0.62),
            (-canopy_r * 0.18, canopy_r * 0.40, canopy_c - canopy_r * 0.05,
             canopy_r * 0.58),
            (-canopy_r * 0.30, canopy_r * 0.12, canopy_c + canopy_r * 0.22,
             canopy_r * 0.52),
            (canopy_r * 0.30, -canopy_r * 0.18, canopy_c + canopy_r * 0.26,
             canopy_r * 0.46),
        ]
        for i, (bx, by, bz, br) in enumerate(blobs[:n_blobs]):
            squash = 0.78 + rng.uniform(-0.06, 0.06)
            mb.add_sphere((bx, by, bz), max(0.3, br), sphere_seg, rings,
                          leaf_mat, squash=squash)
    if winter_bare and params.detail_level != "low":
        # bare canopy hint: tiny twigs
        for i in range(6):
            a = 2 * math.pi * i / 6
            for k in (1, 2):
                mb.add_cylinder((math.cos(a) * k * 0.5,
                                 math.sin(a) * k * 0.5,
                                 trunk_top_z + k * 0.5), 0.04, 1.1, 5,
                                "trunk")
