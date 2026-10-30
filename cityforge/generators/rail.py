# SPDX-License-Identifier: GPL-3.0-or-later
"""Rail and public-transport generator.

Modular pieces for city construction: straight/curved track (rails +
sleepers), platforms, station shelter, rail signal, catenary posts, and
vehicles (passenger train, freight wagon, tram, metro car, monorail).

Conventions: straight track runs along +X, centred on the origin; the two
rails sit at y = +/- gauge/2.  1 unit = 1 metre.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..core.params import GenerationParams
from ..core.randomization import chance, make_rng
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]

GAUGE = 1.435          # standard gauge
RAIL_R = 0.04
SLEEPER = (2.4, 0.24, 0.14)


def _track_segment(mb, x0, x1, with_sleepers=True, sleeper_step=0.7):
    """One straight double-rail track segment along X."""
    y = GAUGE / 2
    mb.add_box(((x0 + x1) / 2, y, 0.14), (x1 - x0, RAIL_R * 2, 0.12),
               "steel_frame")
    mb.add_box(((x0 + x1) / 2, -y, 0.14), (x1 - x0, RAIL_R * 2, 0.12),
               "steel_frame")
    if with_sleepers:
        x = x0
        while x < x1:
            mb.add_box((x + sleeper_step / 2, 0, 0.07), SLEEPER, "wood")
            x += sleeper_step


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "rail")
    mb = MeshBuilder()
    t = params.asset_type
    length = max(4.0, params.road_length if params.road_length else 20.0)
    seg = {"low": 6, "medium": 10, "high": 14}.get(params.detail_level, 10)

    if t in ("TRACK", "TRACK_CURVED"):
        if t == "TRACK":
            _track_segment(mb, -length / 2, length / 2)
            # ballast bed
            mb.add_box((0, 0, 0.02), (length, 2.6, 0.08), "soil")
        else:
            # curved: arc of segments
            radius = length / math.radians(max(5.0, params.road_curvature
                                               or 30.0))
            angle_total = length / radius
            step_n = max(8, int(length / 1.5))
            for i in range(step_n):
                a0 = angle_total * i / step_n
                a1 = angle_total * (i + 1) / step_n
                r_in = radius - 1.3
                r_out = radius + 1.3
                cx = radius - radius * math.cos(a0)
                cy = radius * math.sin(a0)
                # arc chords as boxes
                x0, y0 = radius * math.sin(a0), radius * (1 - math.cos(a0))
                x1, y1 = radius * math.sin(a1), radius * (1 - math.cos(a1))
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                seg_len = math.hypot(x1 - x0, y1 - y0) or 0.05
                ang = math.atan2(y1 - y0, x1 - x0)
                mb.add_box((mx, my, 0.14), (seg_len, RAIL_R * 2, 0.12),
                           "steel_frame", rot_z=ang)
                # offset rails
                for side in (1, -1):
                    ox0 = (radius + side * GAUGE / 2) * math.sin(a0)
                    oy0 = (radius + side * GAUGE / 2) * (1 - math.cos(a0))
                    ox1 = (radius + side * GAUGE / 2) * math.sin(a1)
                    oy1 = (radius + side * GAUGE / 2) * (1 - math.cos(a1))
                    omx, omy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
                    mb.add_box((omx, omy, 0.14),
                               (seg_len, RAIL_R * 2, 0.12), "steel_frame",
                               rot_z=ang)
                if i % 2 == 0:
                    mb.add_box((mx, my, 0.07), (0.24, 2.6, SLEEPER[2]),
                               "wood", rot_z=ang)
    elif t == "PLATFORM":
        h = 0.55
        mb.add_box((0, 0, h / 2), (length, 3.0, h), "concrete")
        # tactile edge strip + yellow safety line
        mb.add_box((0, -1.35, h + 0.01), (length, 0.4, 0.02), "road_marking")
        # shelter columns + roof
        if params.detail_level != "low":
            for x in (-length / 2 + 1.0, length / 2 - 1.0):
                mb.add_box((x, 0.9, h + 1.3), (0.1, 0.1, 2.6), "steel_frame")
            mb.add_box((0, 0.6, h + 2.7), (length * 0.6, 2.2, 0.12),
                       "dark_metal")
            mb.add_plate((0, 1.7, h + 1.5), (length * 0.55, 2.0, 0.02),
                         "glass", (0, 1, 0))
    elif t == "STATION":
        # small station building + canopy
        w, d, h = 14.0, 6.0, 3.6
        mb.add_box((0, 0, h / 2 + 0.1), (w, d, h), "brick_red")
        mb.add_box((0, 0, h + 0.15), (w + 0.6, d + 0.6, 0.3), "roof_tiles")
        mb.add_box((0, -d / 2 - 0.1, 1.2), (3.2, 0.06, 2.2), "dark_metal")
        # platform canopy
        for x in (-w / 2 + 1.2, 0, w / 2 - 1.2):
            mb.add_cylinder((x, -d / 2 - 2.2, 2.6), 0.09, 2.6, seg,
                            "steel_frame")
        mb.add_box((0, -d / 2 - 2.2, 3.9), (w + 2, 4.4, 0.15), "dark_metal")
    elif t == "RAIL_SIGNAL":
        h = 5.0
        mb.add_cylinder((0, 0, h / 2), 0.07, h, seg, "grime_metal")
        mb.add_box((0, 0.12, h - 0.6), (0.34, 0.24, 1.1), "dark_metal")
        for dz, mat in ((0.3, "traffic_red"), (0.0, "traffic_amber"),
                        (-0.3, "traffic_green")):
            mb.add_cylinder((0, 0.25, h - 0.6 + dz), 0.08, 0.04, seg, mat,
                            axis='Y')
    elif t == "CATENARY":
        # overhead wire post + arm
        h = 6.4
        mb.add_cylinder((0, 0, h / 2), 0.09, h, seg, "steel_frame")
        mb.add_box((0, 1.9, h - 0.4), (0.08, 3.8, 0.08), "steel_frame")
        mb.add_cylinder((0, GAUGE / 2, h - 0.65), 0.02, 0.001, 4,
                        "steel_frame", axis='Y')
    elif t in ("TRAIN_PASSENGER", "TRAIN_FREIGHT", "TRAM", "METRO_CAR",
               "MONORAIL"):
        _vehicle(mb, rng, params, t, seg)
    else:
        _track_segment(mb, -length / 2, length / 2)

    info = {
        "style": t.lower(),
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


def _vehicle(mb, rng, params, kind, seg):
    length = 18.0 if kind in ("TRAIN_PASSENGER", "TRAIN_FREIGHT") else \
        14.0 if kind in ("TRAM", "METRO_CAR") else 9.0
    width = 3.0 if kind != "MONORAIL" else 2.6
    height = 3.6 if kind != "TRAIN_FREIGHT" else 3.0
    body = ("car_paint#" + "%02x%02x%02x" % tuple(int(c * 255) for c in
            rng.choice([(0.85, 0.85, 0.88), (0.75, 0.15, 0.10),
                        (0.10, 0.30, 0.60)]))) if kind != "TRAIN_FREIGHT" \
        else "grime_metal"
    if kind == "MONORAIL":
        # beam + car straddling it
        mb.add_box((0, 0, 3.1), (length * 1.06, 0.9, 1.0), "concrete")
        mb.add_box((0, 0, 4.35), (length, width, 2.3), body)
        for s in (-1, 1):
            mb.add_plate((0, s * (width / 2 + 0.002), 4.9),
                         (length * 0.86, 0.9, 0.02), "vehicle_glass",
                         (0, s, 0))
        return
    base = 0.5 if kind in ("TRAM", "METRO_CAR") else 0.7
    mb.add_box((0, 0, base + height / 2), (length, width, height), body)
    # window band
    z_band = base + height * 0.72
    for s in (-1, 1):
        mb.add_plate((0, s * (width / 2 + 0.003), z_band),
                     (length * 0.9, 0.02, height * 0.28), "vehicle_glass",
                     (0, s, 0))
    mb.add_plate((length / 2 + 0.003, 0, z_band),
                 (width * 0.8, 0.02, height * 0.28), "vehicle_glass", (1, 0, 0))
    # bogies / wheels
    if kind in ("TRAIN_PASSENGER", "TRAIN_FREIGHT", "METRO_CAR"):
        for bx in (-length * 0.32, length * 0.32):
            mb.add_box((bx, 0, 0.4), (1.8, width * 0.9, 0.5), "dark_metal")
            for s in (-1, 1):
                for wy in (-GAUGE / 2, GAUGE / 2):
                    mb.add_cylinder((bx + s * 0.6, wy, 0.42), 0.42, 0.12,
                                    seg, "steel_frame", axis='Y')
    elif kind in ("TRAM",):
        n = 4
        for i in range(n):
            bx = -length / 2 + length * (i + 0.5) / n
            for s in (-1, 1):
                mb.add_cylinder((bx, s * GAUGE / 2, 0.35), 0.3, 0.1, seg,
                                "steel_frame", axis='Y')
    if kind == "TRAM":
        # pantograph
        mb.add_box((0, 0, base + height + 0.3), (0.1, 0.1, 0.7),
                   "steel_frame")
