# SPDX-License-Identifier: GPL-3.0-or-later
"""Street furniture & small props generator.

Each prop is a single low-poly object: streetlight, traffic light, traffic
sign, bench, bus stop, parking meter, garbage bin, fence segment, bollard,
fire hydrant, planter, parking barrier.  Deterministic from the seed.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..core.params import GenerationParams
from ..core.randomization import chance, jitter, make_rng, pick
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "prop")
    mb = MeshBuilder()
    seg = {"low": 6, "medium": 10, "high": 12}.get(params.detail_level, 8)
    builder = _BUILDERS.get(params.asset_type, _bench)
    builder(mb, rng, params, seg)
    info = {
        "style": params.prop_style if params.asset_type != "TRAFFIC_SIGN"
        else params.sign_variants,
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


# ---------------------------------------------------------------------------
# individual builders
# ---------------------------------------------------------------------------

def _streetlight(mb, rng, params, seg) -> None:
    h = max(3.0, params.prop_height)
    is_industrial = params.prop_style == "industrial"
    pole_r = 0.09 if not is_industrial else 0.12
    # pole spans ground -> arm height exactly (no gaps, no underground tail)
    mb.add_cylinder((0, 0, (h - 0.4) / 2), pole_r, h - 0.4, seg,
                    "grime_metal")
    # base plate
    mb.add_cylinder((0, 0, 0.06), pole_r * 2.0, 0.12, seg, "dark_metal")
    if is_industrial:
        # double arm cantilever through the pole top; heads overlap the arms
        for side in (-1, 1):
            mb.add_box((side * 1.0, 0, h - 0.4), (2.4, 0.08, 0.08),
                       "grime_metal")
            mb.add_box((side * 1.9, 0, h - 0.62), (1.0, 0.24, 0.10),
                       "dark_metal")
            mb.add_box((side * 2.0, 0, h - 0.70), (0.6, 0.22, 0.04),
                       "lamp_street")
    else:
        # single arm bolted to the pole top; stem connects arm to head
        mb.add_box((0.75, 0, h - 0.4), (1.5, 0.09, 0.09), "grime_metal")
        mb.add_box((1.7, 0, h - 0.62), (0.75, 0.28, 0.12), "dark_metal")
        mb.add_box((1.7, 0, h - 0.51), (0.1, 0.08, 0.14), "dark_metal")
        mb.add_box((1.85, 0, h - 0.71), (0.6, 0.22, 0.04), "lamp_street")


def _traffic_light(mb, rng, params, seg) -> None:
    h = max(2.6, params.prop_height)
    mb.add_cylinder((0, 0, h / 2), 0.08, h, seg, "dark_metal")
    # head overlaps the pole; bracket ties it on visibly
    mb.add_box((0.19, 0, h - 0.55), (0.42, 0.28, 1.15), "dark_metal")
    mb.add_box((0.10, 0, h - 0.55), (0.22, 0.10, 0.10), "grime_metal")
    # lamps sit PROUD of the head face — no cover plate hides them
    for dz, mat in ((0.35, "traffic_red"), (0.0, "traffic_amber"),
                    (-0.35, "traffic_green")):
        mb.add_cylinder((0.19, -0.155, h - 0.55 + dz), 0.095, 0.05, seg, mat,
                        axis='Y')


def _traffic_sign(mb, rng, params, seg) -> None:
    """Traffic sign with the selected variant.  Text-capable variants record
    their plate geometry in the returned info (via mb metadata)."""
    h = max(2.2, 2.4)
    mb.add_cylinder((0, 0, h / 2 - 0.05), 0.035, h - 0.1, seg, "grime_metal")
    v = params.sign_variants or "stop"
    if v == "stop":
        mb.add_box((0, 0, h - 0.42), (0.75, 0.03, 0.75), "sign")
        mb.add_box((0, 0.04, h - 0.42), (0.6, 0.01, 0.55), "sign_cream")
    elif v == "speed_limit":
        mb.add_cylinder((0, 0, h - 0.45), 0.36, 0.04, seg, "holo_white",
                        axis='Z')
        mb.add_box((0, 0, h - 0.45), (0.5, 0.02, 0.3), "sign")
    elif v == "yield":
        # inverted triangle
        mb.add_box((0, 0, h - 0.45), (0.8, 0.03, 0.55), "holo_white")
        mb.add_box((0, 0.04, h - 0.35), (0.6, 0.01, 0.28), "sign")
    elif v == "no_entry":
        mb.add_cylinder((0, 0, h - 0.45), 0.36, 0.04, seg, "sign", axis='Z')
        mb.add_box((0, 0.03, h - 0.45), (0.55, 0.01, 0.16), "holo_white")
    elif v == "one_way":
        mb.add_box((0, 0, h - 0.45), (0.9, 0.03, 0.3), "sign_black")
        mb.add_plate((0, 0.02, h - 0.45), (0.7, 0.01, 0.14), "holo_white",
                     (0, 1, 0))
        mb.add_plate((0.2, 0.02, h - 0.45), (0.2, 0.01, 0.3), "holo_white",
                     (0, 1, 0))
    elif v == "directional":
        mb.add_box((0, 0, h - 0.55), (1.1, 0.03, 0.4), "sign_blue")
        mb.add_plate((0, 0.02, h - 0.55), (0.9, 0.01, 0.22), "holo_white",
                     (0, 1, 0))
    elif v == "street_name":
        mb.add_box((0, 0, h - 0.5), (1.0, 0.03, 0.26), "holo_white")
        mb.add_box((0, 0.02, h - 0.5), (0.85, 0.012, 0.14), "sign_blue")
    elif v == "parking":
        mb.add_box((0, 0, h - 0.45), (0.6, 0.03, 0.6), "sign_blue")
        mb.add_plate((0, 0.02, h - 0.45), (0.45, 0.01, 0.45), "holo_white",
                     (0, 1, 0))
    elif v == "no_parking":
        mb.add_cylinder((0, 0, h - 0.45), 0.34, 0.04, seg, "sign_blue",
                        axis='Z')
        mb.add_box((0, 0.03, h - 0.45), (0.5, 0.01, 0.1), "sign")
        mb.add_box((0, 0.03, h - 0.45), (0.08, 0.01, 0.5), "sign")
    elif v == "pedestrian_crossing":
        mb.add_box((0, 0, h - 0.5), (0.6, 0.03, 0.75), "sign_blue")
        mb.add_box((0.0, 0.03, h - 0.62), (0.3, 0.01, 0.2), "holo_white")
        mb.add_box((0.0, 0.03, h - 0.32), (0.4, 0.01, 0.08), "holo_white")
    elif v == "construction":
        mb.add_box((0, 0, h - 0.55), (0.95, 0.03, 0.7), "sign_construction")
        mb.add_box((0, 0.03, h - 0.45), (0.6, 0.01, 0.12), "sign_black")
        mb.add_box((0, 0.03, h - 0.65), (0.6, 0.01, 0.12), "sign_black")
    elif v == "hazard":
        mb.add_box((0, 0, h - 0.5), (0.7, 0.03, 0.7), "sign_warning")
        mb.add_box((0, 0.03, h - 0.5), (0.5, 0.01, 0.5), "sign_black")
        mb.add_box((0, 0.04, h - 0.5), (0.36, 0.01, 0.36), "sign_warning")
    elif v == "warning":
        mb.add_box((0, 0, h - 0.5), (0.7, 0.03, 0.7), "sign_warning")
        mb.add_box((0, 0.03, h - 0.55), (0.4, 0.01, 0.3), "sign_black")
    elif v == "highway":
        mb.add_box((0, 0, h - 0.7), (1.4, 0.03, 0.6), "sign_highway_green")
        mb.add_plate((0, 0.02, h - 0.7), (1.1, 0.01, 0.35), "holo_white",
                     (0, 1, 0))
    elif v == "traffic_info":
        mb.add_box((0, 0, h - 0.6), (1.1, 0.03, 0.55), "sign_blue")
        mb.add_plate((0, 0.02, h - 0.6), (0.9, 0.01, 0.4), "holo_white",
                     (0, 1, 0))
    else:  # pedestrian (legacy default)
        mb.add_box((0, 0, h - 0.45), (0.55, 0.03, 0.7), "holo_white")
        mb.add_box((0.0, 0.03, h - 0.55), (0.3, 0.01, 0.2), "sign")
        mb.add_box((0.0, 0.03, h - 0.28), (0.4, 0.01, 0.08), "sign")


def _bench(mb, rng, params, seg) -> None:
    w = 1.8 if params.prop_style != "industrial" else 2.2
    wood_mat = "wood"
    metal_mat = "dark_metal"
    # legs (grounded) with back supports rising to the backrest
    for x in (-w / 2 + 0.18, w / 2 - 0.18):
        mb.add_box((x, 0, 0.22), (0.08, 0.5, 0.44), metal_mat)
        mb.add_plate((x, 0, 0.4), (0.06, 0.52, 0.05), metal_mat, (0, 1, 0))
        # back support: continuous post from seat to top of the backrest
        mb.add_box((x, 0.235, 0.63), (0.06, 0.05, 0.42), metal_mat)
    # seat slats
    n = 3 if params.detail_level == "low" else 4
    for i in range(n):
        z = 0.42 + i * 0.045
        mb.add_box((0, -0.18, z), (w, 0.075, 0.035), wood_mat)
        mb.add_box((0, 0.18, z), (w, 0.075, 0.035), wood_mat)
    # backrest slats (now carried by the support posts)
    for i in range(2):
        z = 0.62 + i * 0.15
        mb.add_box((0, 0.245, z), (w, 0.04, 0.09), wood_mat)


def _bus_stop(mb, rng, params, seg) -> None:
    w = 3.6
    d = 1.6
    h = 2.6
    metal = "grime_metal"
    glass = "glass"
    # posts: both front corners and both back corners run ground -> roof
    for x in (-w / 2, w / 2 - 0.05):
        mb.add_box((x, -d / 2 + 0.1, h / 2), (0.07, 0.07, h), metal)
        mb.add_box((x, d / 2 - 0.1, h / 2), (0.07, 0.07, h), metal)
    # roof slab rests on the post tops
    mb.add_box((0, 0, h + 0.05), (w + 0.4, d + 0.3, 0.1), metal)
    # glass back and side walls (between the posts, coplanar-safe)
    mb.add_plate((0, d / 2 - 0.1, h / 2), (w - 0.1, h * 0.94, 0.02), glass,
                 (0, 1, 0))
    mb.add_plate((-w / 2 + 0.05, 0, h / 2), (d - 0.2, h * 0.94, 0.02), glass,
                 (-1, 0, 0))
    # bench inside
    mb.add_box((0, d / 2 - 0.42, 0.47), (w * 0.62, 0.32, 0.06), "wood")
    for x in (-w * 0.31, w * 0.31):
        mb.add_box((x, d / 2 - 0.42, 0.235), (0.05, 0.3, 0.4), metal)
    # timetable plate mounted on the front-right post (street side)
    mb.add_plate((w / 2 - 0.05, -d / 2 + 0.04, 1.45), (0.5, 0.02, 0.7),
                 "holo_white", (0, -1, 0))


def _parking_meter(mb, rng, params, seg) -> None:
    h = max(1.0, params.prop_height * 0.35)
    mb.add_cylinder((0, 0, h * 0.35), 0.05, h * 0.7, seg, "painted_metal")
    mb.add_box((0, 0, h * 0.8), (0.22, 0.14, 0.34), "painted_metal")
    mb.add_plate((0, -0.071, h * 0.85), (0.14, 0.01, 0.14), "sign",
                 (0, -1, 0))


def _garbage_bin(mb, rng, params, seg) -> None:
    r = 0.30
    h = 0.95
    mb.add_cylinder((0, 0, h / 2), r, h, seg, "painted_metal")
    mb.add_cylinder((0, 0, h + 0.02), r * 1.04, 0.05, seg, "dark_metal")
    mb.add_cylinder((0, 0, 0.03), r * 1.08, 0.06, seg, "dark_metal")
    if params.detail_level != "low":
        mb.add_plate((r * 0.99, 0, h * 0.62), (0.02, 0.3, 0.08),
                     "sign_cream", (1, 0, 0))


def _fence(mb, rng, params, seg) -> None:
    length = max(1.0, params.fence_length)
    ftype = params.fence_type
    h = 1.8 if ftype != "chain_link" else 2.4
    if ftype == "chain_link":
        pole_step = 3.0
        mesh_mat = "steel_frame"
        for x in [length / 2 - pole_step * i for i in
                  range(int(length / pole_step) + 1)]:
            mb.add_cylinder((x, 0, h / 2), 0.035, h, 6, mesh_mat)
            # cap ball on each post
            mb.add_sphere((x, 0, h + 0.04), 0.05, 6, 4, mesh_mat)
        # chain-link membrane (thin plate panels)
        mb.add_plate((0, 0, h / 2 + 0.15), (length, 0.008, h - 0.3),
                     mesh_mat, (0, 0, 1))
        mb.add_box((0, 0, h + 0.03), (length + 0.1, 0.04, 0.05), mesh_mat)
        mb.add_box((0, 0, 0.12), (length + 0.1, 0.04, 0.06), mesh_mat)
    elif ftype == "metal_panels":
        mb.add_box((0, 0, h / 2), (length, 0.05, h), "grime_metal")
        n = max(2, int(length / 0.6))
        for i in range(n):
            mb.add_box((-length / 2 + length * (i + 0.5) / n, 0, h * 0.62),
                       (length / n - 0.06, 0.03, h * 0.2), "dark_metal")
    elif ftype == "wooden":
        n = max(2, int(length / 0.25))
        for i in range(n):
            x = -length / 2 + length * (i + 0.5) / n
            mb.add_box((x, 0, h * 0.55), (0.14, 0.025, h * 1.05), "wood")
        for z in (h * 0.25, h * 0.72):
            mb.add_box((0, 0.02, z), (length, 0.04, 0.07), "wood")
    else:  # concrete
        seg_count = max(2, int(length / 2.4))
        for i in range(seg_count):
            x = -length / 2 + length * (i + 0.5) / seg_count
            mb.add_box((x, 0, 0.9), (2.2, 0.16, 1.8), "concrete")
            mb.add_cylinder((x + 1.2, 0, 0.9), 0.07, 1.9, 6, "concrete")


def _bollard(mb, rng, params, seg) -> None:
    h = 0.9
    mb.add_cylinder((0, 0, h / 2), 0.10, h, seg, "dark_metal")
    mb.add_cylinder((0, 0, h - 0.02), 0.09, 0.06, seg, "sign")
    mb.add_cylinder((0, 0, 0.04), 0.13, 0.08, seg, "dark_metal")


def _hydrant(mb, rng, params, seg) -> None:
    mb.add_cylinder((0, 0, 0.28), 0.14, 0.56, seg, "sign")
    mb.add_cylinder((0, 0, 0.58), 0.16, 0.12, seg, "sign")
    mb.add_cylinder((0, 0, 0.68), 0.10, 0.14, seg, "sign")
    # side nozzles start inside the body (r=0.14) so they are connected
    mb.add_cylinder((0.0, 0.20, 0.44), 0.07, 0.12, 6, "sign", axis='Y')
    mb.add_cylinder((0.0, -0.20, 0.44), 0.07, 0.12, 6, "sign", axis='Y')
    mb.add_cylinder((0, 0, 0.02), 0.19, 0.04, seg, "sign")


def _planter(mb, rng, params, seg) -> None:
    w = 1.6
    d = 0.7
    h = 0.55
    mb.add_box((0, 0, h / 2), (w, d, h), "concrete")
    mb.add_box((0, 0, h - 0.06), (w - 0.1, d - 0.1, 0.06), "dark_concrete")
    mb.add_box((0, 0, h + 0.09), (w - 0.22, d - 0.22, 0.14), "soil")
    # a few shrub blobs
    for (bx, by) in ((-0.4, 0.0), (0.0, 0.05), (0.42, -0.02)):
        r = 0.26 + rng.uniform(0, 0.1)
        mb.add_sphere((bx, by, h + 0.25), r, seg, 4, "leaves_summer",
                      squash=0.72)


def _barrier(mb, rng, params, seg) -> None:
    # traffic barrier (segment)
    mb.add_box((0, 0, 0.32), (2.0, 0.34, 0.5), "concrete")
    mb.add_box((0, 0, 0.03), (2.0, 0.55, 0.06), "concrete")
    mb.add_plate((0, -0.18, 0.62), (2.0, 0.02, 0.2), "sign", (0, -1, 0))
    for x in (-1.0, 1.0):
        mb.add_box((x, 0, 0.28), (0.1, 0.42, 0.56), "concrete")


_BUILDERS = {
    "STREETLIGHT": _streetlight,
    "TRAFFIC_LIGHT": _traffic_light,
    "TRAFFIC_SIGN": _traffic_sign,
    "BENCH": _bench,
    "BUS_STOP": _bus_stop,
    "PARKING_METER": _parking_meter,
    "GARBAGE_BIN": _garbage_bin,
    "FENCE": _fence,
    "BOLLARD": _bollard,
    "HYDRANT": _hydrant,
    "PLANTER": _planter,
    "BARRIER": _barrier,
    "PARKING_STRUCTURE": _bench,  # parking structures are generated by the
    # building engine (ground_floor='garage'); this entry prevents KeyError
}
