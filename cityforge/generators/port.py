# SPDX-License-Identifier: GPL-3.0-or-later
"""Port and waterfront generator.

Modular assets: wooden/concrete docks, container cranes, shipping containers
and stacks, and watercraft (small boat, fishing boat, sailboat, yacht, cargo
ship, ferry).  Watercraft sit with the waterline at z = 0 (the hull below).
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..core.params import GenerationParams
from ..core.randomization import chance, make_rng
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]

CONTAINER_COLORS = [(0.75, 0.16, 0.10), (0.10, 0.32, 0.55), (0.16, 0.45, 0.20),
                    (0.78, 0.55, 0.08), (0.60, 0.60, 0.62)]


def _hex(color) -> str:
    return "%02x%02x%02x" % tuple(int(max(0, min(255, c * 255))) for c in color[:3])


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "port")
    mb = MeshBuilder()
    t = params.asset_type
    seg = {"low": 6, "medium": 10, "high": 12}.get(params.detail_level, 10)
    length = max(4.0, params.road_length or 20.0)

    if t == "DOCK":
        # deck on piles, edge bollards
        mb.add_box((0, 0, -0.05), (length, 4.0, 0.3), "wood")
        n_piles = max(2, int(length / 3.0))
        for i in range(n_piles):
            x = -length / 2 + (i + 0.5) * (length / n_piles)
            for y in (-1.6, 1.6):
                mb.add_cylinder((x, y, -0.75), 0.16, 1.2, seg, "wood")
        for x in (-length / 2 + 0.5, length / 2 - 0.5):
            mb.add_cylinder((x, 1.7, 0.28), 0.13, 0.4, seg, "dark_metal")
    elif t == "CRANE":
        # container gantry crane: 4 legs + portal + boom + cabin + trolley
        span = 14.0
        h = 16.0
        for sx in (-span / 2, span / 2):
            for sy in (-2.5, 2.5):
                mb.add_box((sx, sy, h / 2), (0.7, 0.7, h), "steel_frame")
        mb.add_box((0, 0, h + 0.4), (2.2, span + 2, 1.0), "steel_frame")
        mb.add_box((0, 0, h + 1.4), (2.0, span, 1.2), "sign_blue")
        # boom out over the water
        mb.add_box((0, -(span / 2 + 8), h - 1.0), (1.6, 16, 0.9),
                   "steel_frame")
        mb.add_box((0, -(span / 2 + 12), h - 2.4), (0.3, 0.3, 2.6),
                   "steel_frame")
        mb.add_box((0, -3.5, h - 1.8), (1.6, 1.4, 1.4), "grime_metal")
        # spreader cables
        mb.add_box((0, -(span / 2 + 8), h - 4.2), (0.08, 0.08, 4.4),
                   "dark_metal")
        mb.add_box((0, -(span / 2 + 8), h - 5.2), (2.2, 2.2, 0.3),
                   "dark_metal")
    elif t == "CONTAINER":
        mb.add_box((0, 0, 1.3), (6.0, 2.4, 2.6),
                   f"painted_metal#{_hex(rng.choice(CONTAINER_COLORS))}")
        for k in range(6):
            mb.add_box((-2.2 + k * 0.88, 1.22, 1.3), (0.06, 0.03, 2.2),
                       "dark_metal")
    elif t == "CONTAINER_STACK":
        cols = int(params.park_width or 3) if params.park_width else 3
        for i in range(3):
            for j in range(2):
                x = (i - 1) * 6.3
                y = (j - 0.5) * 2.6
                n_high = int(rng.uniform(1, 4))
                for k in range(n_high):
                    col = f"painted_metal#{_hex(rng.choice(CONTAINER_COLORS))}"
                    mb.add_box((x, y, 1.3 + k * 2.6), (6.0, 2.4, 2.6), col)
    elif t in ("BOAT_SMALL", "FISHING_BOAT", "SAILBOAT", "YACHT",
               "CARGO_SHIP", "FERRY"):
        _watercraft(mb, rng, params, t, seg)
    else:
        _watercraft(mb, rng, params, "BOAT_SMALL", seg)

    info = {
        "style": t.lower(),
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


def _watercraft(mb, rng, params, kind, seg):
    if kind == "BOAT_SMALL":
        _hull(mb, 3.2, 1.4, 0.7, "car_paint#" + _hex((0.85, 0.75, 0.35)))
        mb.add_box((0, 0, 0.72), (1.2, 0.9, 0.35), "holo_white")
        mb.add_box((-1.0, 0, 0.95), (0.6, 0.7, 0.4), "holo_white")
    elif kind == "FISHING_BOAT":
        _hull(mb, 6.5, 2.4, 1.0, "car_paint#" + _hex((0.15, 0.35, 0.55)))
        mb.add_box((0.6, 0, 1.15), (1.8, 1.7, 0.9), "holo_white")
        mb.add_box((-1.6, 0, 1.3), (1.0, 1.2, 0.5), "dark_metal")
        # mast + boom
        mb.add_cylinder((-0.5, 0, 2.6), 0.06, 3.0, 6, "steel_frame")
    elif kind == "SAILBOAT":
        _hull(mb, 7.5, 2.2, 1.1, "holo_white")
        mb.add_cylinder((0, 0, 4.5), 0.07, 9.0, 8, "steel_frame")
        # sail (plate)
        mb.add_plate((1.4, 0, 4.6), (5.2, 0.02, 6.4), "holo_white", (0, 1, 0))
    elif kind == "YACHT":
        _hull(mb, 14.0, 4.2, 1.8, "holo_white")
        mb.add_box((-2.0, 0, 2.0), (6.5, 3.2, 1.4), "holo_white")
        mb.add_box((-2.0, 0, 2.75), (5.2, 2.6, 0.5), "vehicle_glass")
        mb.add_box((2.6, 0, 1.9), (2.2, 2.2, 0.9), "dark_metal")
    elif kind == "CARGO_SHIP":
        length, width = 42.0, 9.0
        _hull(mb, length, width, 3.2, "car_paint#" + _hex((0.15, 0.25, 0.40)))
        mb.add_box((-length * 0.28, 0, 4.2), (10.0, width * 0.8, 2.6),
                   "holo_white")
        mb.add_box((-length * 0.28, 0, 5.8), (6.0, width * 0.6, 1.2),
                   "holo_white")
        # container rows on deck
        col = "painted_metal#" + _hex(rng.choice(CONTAINER_COLORS))
        for i in range(5):
            for j in range(2):
                mb.add_box((-length * 0.05 + i * 6.3, (j - 0.5) * 2.7, 4.8),
                           (6.0, 2.4, 2.6), col)
    elif kind == "FERRY":
        length, width = 30.0, 8.0
        _hull(mb, length, width, 2.6, "holo_white")
        mb.add_box((0, 0, 3.0), (length * 0.82, width * 0.94, 1.8),
                   "holo_white")
        mb.add_box((-3.0, 0, 4.6), (length * 0.4, width * 0.7, 1.4),
                   "sign_blue")
        mb.add_plate((length * 0.28, 0, 3.2), (width * 0.7, 0.02, 0.9),
                     "vehicle_glass", (1, 0, 0))
        for s in (-1, 1):
            mb.add_cylinder((length * 0.2, s * 1.6, 6.1), 0.12, 1.4, seg,
                            "dark_metal")


def _hull(mb, length: float, width: float, depth: float, body_mat: str):
    """Simple hull: tapered deck box + keel wedge; the waterline sits at 0."""
    freeboard = depth * 0.35
    hull_top = freeboard
    hull_bottom = -depth * 0.65
    mb.add_box((0, 0, (hull_top + hull_bottom) / 2),
               (length, width, hull_top - hull_bottom), body_mat)
    # bow taper (two angled plates faked with an extra wedge box)
    mb.add_box((length / 2 - width * 0.3, 0, (hull_top + hull_bottom) / 2),
               (width * 0.7, width * 0.5, hull_top - hull_bottom), body_mat)
    # deck
    mb.add_box((0, 0, hull_top + 0.02), (length * 0.96, width * 0.92, 0.06),
               "wood")
