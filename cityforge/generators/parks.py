# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural park generator.

A park is a complete environment: boundary, path network from entrances to
destinations, grass/flower landscaping, water features, facilities (benches,
lights, bins, playgrounds, sports courts...) and vegetation.

Structure: ONE terrain mesh (ground, paths, plazas, water, court markings)
plus CHILD OBJECTS for trees, bushes, hedges, and facilities built from the
existing vegetation/props builders.  The terrain object is the tracked
CityForge asset; children are parented to it so exports keep the group
together (and can be ungrouped for individual use).

Determinism: every placement draws from rngs derived from the park seed.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import bpy

from ..core.params import GenerationParams
from ..core.randomization import chance, jitter, make_rng, pick_weighted
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset", "PARK_TYPES"]

# ---------------------------------------------------------------------------
# park type presets: (size w×l, tree density, facility set, water, character)
# ---------------------------------------------------------------------------

PARK_TYPES: Dict[str, Dict] = {
    "neighbourhood_park": dict(
        size=(26.0, 34.0), trees=6, bushes=6, flowers=2, benches=4,
        lights=4, bins=2, water=False, playground=False, sports=False,
        picnic=True, fenced=False, paths="loop"),
    "community_park": dict(
        size=(44.0, 56.0), trees=12, bushes=10, flowers=4, benches=7,
        lights=6, bins=3, water=True, playground=True, sports=False,
        picnic=True, fenced=False, paths="loop"),
    "city_park": dict(
        size=(80.0, 110.0), trees=26, bushes=18, flowers=7, benches=13,
        lights=12, bins=6, water=True, playground=True, sports=True,
        picnic=True, fenced=False, paths="network"),
    "urban_plaza": dict(
        size=(30.0, 30.0), trees=4, bushes=4, flowers=4, benches=8,
        lights=8, bins=3, water=True, playground=False, sports=False,
        picnic=False, fenced=False, paths="plaza"),
    "botanical_garden": dict(
        size=(48.0, 60.0), trees=16, bushes=22, flowers=12, benches=6,
        lights=5, bins=3, water=True, playground=False, sports=False,
        picnic=False, fenced=True, paths="network"),
    "waterfront_park": dict(
        size=(60.0, 40.0), trees=14, bushes=10, flowers=4, benches=9,
        lights=9, bins=4, water=True, waterfront=True, playground=False,
        sports=False, picnic=True, fenced=False, paths="loop"),
    "dog_park": dict(
        size=(34.0, 40.0), trees=6, bushes=2, flowers=0, benches=3,
        lights=3, bins=4, water=False, playground=False, sports=False,
        picnic=False, fenced=True, dog_area=True, paths="simple"),
    "playground_park": dict(
        size=(30.0, 38.0), trees=7, bushes=5, flowers=2, benches=5,
        lights=5, bins=2, water=False, playground=True, sports=False,
        picnic=True, fenced=True, paths="simple"),
    "sports_park": dict(
        size=(70.0, 90.0), trees=10, bushes=4, flowers=0, benches=8,
        lights=14, bins=5, water=False, playground=False, sports=True,
        picnic=False, fenced=True, paths="network"),
    "formal_garden": dict(
        size=(36.0, 46.0), trees=10, bushes=16, flowers=14, benches=6,
        lights=6, bins=2, water=True, fountain=True, playground=False,
        sports=False, picnic=False, fenced=True, paths="formal"),
    "forest_park": dict(
        size=(90.0, 120.0), trees=48, bushes=26, flowers=4, benches=4,
        lights=2, bins=2, water=True, playground=False, sports=False,
        picnic=True, fenced=False, paths="simple"),
}

PARK_TYPE_KEYS = sorted(PARK_TYPES.keys())


# ---------------------------------------------------------------------------
# boundary shapes
# ---------------------------------------------------------------------------

def _boundary(width: float, length: float, shape: str, rng) -> List[Tuple[
        float, float]]:
    """Closed polygon (CCW) of the park outline."""
    hw, hl = width / 2, length / 2
    if shape == "square":
        hw = hl = min(hw, hl)
        return [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)]
    if shape == "circular":
        pts = []
        r = min(hw, hl)
        for i in range(24):
            a = 2 * math.pi * i / 24
            rr = r * rng.uniform(0.96, 1.04) if shape == "irregular" else r
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        return pts
    if shape == "irregular":
        pts = []
        for i in range(14):
            a = 2 * math.pi * i / 14
            rr_x = hw * rng.uniform(0.72, 1.0)
            rr_y = hl * rng.uniform(0.72, 1.0)
            pts.append((rr_x * math.cos(a), rr_y * math.sin(a)))
        return pts
    return [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)]


def _point_in_poly(x, y, poly) -> bool:
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def _point_dist_to_poly(x, y, poly) -> float:
    best = 1e9
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        ln2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ln2))
        px, py = ax + t * dx, ay + t * dy
        best = min(best, math.hypot(x - px, y - py))
    return best


def _rect_in_poly(rect, poly) -> bool:
    x0, y0, x1, y1 = rect
    for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        if not _point_in_poly(cx, cy, poly):
            return False
    return True


# ---------------------------------------------------------------------------
# asset assembly
# ---------------------------------------------------------------------------

def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    """Build the park terrain mesh; child objects are created by
    :func:`build_children` afterwards (called by the dispatcher)."""
    rng = make_rng(params.seed, "park")
    ptype = params.park_type if params.park_type in PARK_TYPES \
        else "community_park"
    preset = PARK_TYPES[ptype]
    w = max(8.0, params.park_width or preset["size"][0])
    l = max(8.0, params.park_length or preset["size"][1])
    shape = params.park_shape
    if shape == "auto":
        shape = pick_weighted(rng, [("rectangular", 4.0), ("square", 2.0),
                                    ("circular", 1.5), ("irregular", 2.0)])
    poly = _boundary(w, l, shape, rng)
    det = params.detail_level
    q = {"low": 0.55, "medium": 1.0, "high": 1.6}.get(det, 1.0)

    mb = MeshBuilder()

    # --- ground plate (grass base, slightly above z=0 to avoid z-fighting
    # with world ground planes) ------------------------------------------
    _polygon_mesh(mb, poly, "grass", z=0.02)

    # --- entrances -------------------------------------------------------
    n_entrances = max(1, int(params.park_entrances))
    entrances: List[Tuple[float, float]] = []
    for i in range(n_entrances):
        edge = i % 4
        t = rng.uniform(-0.35, 0.35)
        if edge == 0:
            entrances.append((t * w, -l / 2))
        elif edge == 1:
            entrances.append((w / 2, t * l))
        elif edge == 2:
            entrances.append((t * w, l / 2))
        else:
            entrances.append((-w / 2, t * l))

    # --- destinations ----------------------------------------------------
    dests: List[Tuple[float, float]] = []
    cx, cy = 0.0, 0.0
    if preset.get("fountain") or (params.park_water and preset.get("water")
                                  and shape in ("square", "rectangular")):
        pass
    # central plaza (most parks)
    plaza_r = min(w, l) * 0.14
    dests.append((0.0, 0.0))
    # water feature as destination
    water_center = None
    if preset.get("water") and params.park_water:
        water_center = (jitter(rng, 0, w * 0.2), jitter(rng, 0, l * 0.2))
        dests.append(water_center)
    # playground / sports as destinations
    if preset.get("playground"):
        pg = (jitter(rng, w * 0.22, w * 0.08), jitter(rng, l * 0.25,
                                                      l * 0.08))
        if _point_dist_to_poly(*pg, poly) > 6.0:
            dests.append(pg)
    if preset.get("sports"):
        sp = (-w * 0.22, jitter(rng, -l * 0.2, l * 0.2))
        if _point_dist_to_poly(*sp, poly) > 12.0:
            dests.append(sp)

    # --- paths: entrances -> plaza -> destinations -----------------------
    # each path gets its own z-layer (no two slabs share a height, so
    # overlapping segments can never z-fight)
    path_w = max(0.9, params.park_path_width)
    density = max(0.0, min(1.0, params.park_path_density))
    for layer, (ex, ey) in enumerate(entrances):
        mid = _bend_to(rng, (ex, ey), (0, 0), min(w, l) * 0.3)
        _path(mb, (ex, ey), mid, (0, 0), path_w, poly,
              z=0.02 + layer * 0.008)
    # connect plaza to each destination (paths to water stop at the rim)
    for di, (dx_, dy_) in enumerate(dests[1:]):
        target = (dx_, dy_)
        if water_center and abs(dx_ - water_center[0]) < 0.01 \
                and abs(dy_ - water_center[1]) < 0.01:
            pond_r = min(w, l) * 0.14
            ln = math.hypot(dx_, dy_) or 1.0
            stop = (pond_r + path_w + 0.6) / ln
            target = (dx_ * (1.0 - stop), dy_ * (1.0 - stop))
        mid = _bend_to(rng, (0, 0), target, min(w, l) * 0.2)
        _path(mb, (0, 0), mid, target, path_w, poly,
              z=0.02 + (len(entrances) + di) * 0.008)
    # perimeter/loop path
    if preset.get("paths") in ("loop", "network") and density > 0.3:
        inset = min(w, l) * 0.28
        loop_poly = _boundary(max(2, w - 2 * inset), max(2, l - 2 * inset),
                              "rectangular", rng)
        layer0 = 0.02 + (len(entrances) + len(dests)) * 0.008
        for i in range(len(loop_poly)):
            a = loop_poly[i]
            b = loop_poly[(i + 1) % len(loop_poly)]
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            _path(mb, a, mid, b, path_w * 0.75, poly,
                  z=layer0 + i * 0.008)
    # plaza pavement: triangle-fan disc (avoids ngon triangulation artifacts)
    mb.add_cylinder((0, 0, 0.02), plaza_r, 0.045, 24, "sidewalk",
                    cap_top=False)
    for i in range(24):
        a0 = 2 * math.pi * i / 24
        a1 = 2 * math.pi * (i + 1) / 24
        mb.add_outward_face([
            (0.0, 0.0, 0.048),
            (plaza_r * math.cos(a0), plaza_r * math.sin(a0), 0.048),
            (plaza_r * math.cos(a1), plaza_r * math.sin(a1), 0.048)],
            "sidewalk", (0, 0, 1))

    # --- water feature ---------------------------------------------------
    if water_center:
        r = min(w, l) * rng.uniform(0.12, 0.18)
        _pond(mb, water_center, r, params)

    # --- flower beds / hedges near plaza & entrances ----------------------
    flowers = int(preset.get("flowers", 2) * q)
    for i in range(flowers):
        a = 2 * math.pi * (i + rng.uniform(0, 1)) / max(1, flowers)
        rr = plaza_r + rng.uniform(1.2, plaza_r * 2.2)
        pos = (math.cos(a) * rr, math.sin(a) * rr)
        if _point_dist_to_poly(*pos, poly) > 2.0:
            _flower_bed(mb, rng, pos)

    # --- sports courts (flat pads + markings) -----------------------------
    if preset.get("sports") and params.park_sports:
        pad = (w * 0.22, l * 0.25)
        if _rect_in_poly((pad[0] - 8, pad[1] - 7, pad[0] + 8, pad[1] + 7),
                         poly):
            _basketball_court(mb, rng, pad)
        pad2 = (-w * 0.24, -l * 0.26)
        if _rect_in_poly((pad2[0] - 10, pad2[1] - 7, pad2[0] + 10,
                          pad2[1] + 7), poly):
            _soccer_field(mb, rng, pad2)

    # --- retaining walls at height edges (plaza podium effect) ------------
    if shape == "irregular":
        for i in range(0, len(poly), 3):
            ax, ay = poly[i]
            bx, by = poly[(i + 1) % len(poly)]
            if rng.random() < 0.4:
                _low_wall(mb, (ax, ay), (bx, by), 0.5, "concrete")

    info = {
        "style": ptype,
        "width": w,
        "length": l,
        "shape": shape,
        "entrances": len(entrances),
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
        "park_children": _child_spec(params, preset, poly, plaza_r,
                                     water_center, q),
    }
    return mb, info


# -- child placement plan (executed by build_children) ----------------------

def _child_spec(params, preset, poly, plaza_r, water_center, q) -> Dict:
    """Everything placed as separate objects, resolved against the layout."""
    rng = make_rng(params.seed, "park_children")
    spec: Dict[str, list] = {"trees": [], "bushes": [], "props": []}
    w = params.park_width or preset["size"][0]
    l = params.park_length or preset["size"][1]

    def free_spot(min_dist_from_center, tries=24):
        for _ in range(tries):
            x = rng.uniform(-w / 2 + 1.2, w / 2 - 1.2)
            y = rng.uniform(-l / 2 + 1.2, l / 2 - 1.2)
            if _point_dist_to_poly(x, y, poly) < 1.4:
                continue
            if math.hypot(x, y) < min_dist_from_center:
                continue
            if water_center and math.hypot(x - water_center[0],
                                           y - water_center[1]) < 4.0:
                continue
            return (x, y)
        return None

    # trees: grid-jitter for even coverage, density controlled
    n_trees = int(preset.get("trees", 6) * q *
                  max(0.2, params.park_tree_density))
    for _i in range(n_trees):
        spot = free_spot(plaza_r + 2.0)
        if spot:
            tt = pick_weighted(rng, [("deciduous", 5.0), ("evergreen", 3.0),
                                     ("poplar", 1.0)])
            season = params.season if params.season != "summer" else \
                pick_weighted(rng, [("summer", 6.0), ("spring", 2.0),
                                    ("autumn", 2.0)])
            spec["trees"].append({
                "pos": spot, "tree_type": tt, "season": season,
                "height": rng.uniform(6.5, 11.0),
                "canopy": rng.uniform(2.2, 3.6)})
    # bushes
    n_bushes = int(preset.get("bushes", 6) * q *
                   max(0.2, params.park_bush_density))
    for _i in range(n_bushes):
        spot = free_spot(plaza_r + 1.0)
        if spot:
            spec["bushes"].append({"pos": spot})
    # benches along the plaza + paths, lights, bins
    n_benches = int(preset.get("benches", 4) * q *
                    max(0.2, params.park_seating_density))
    for i in range(n_benches):
        a = 2 * math.pi * i / max(1, n_benches)
        spec["props"].append({"type": "BENCH",
                              "pos": (math.cos(a) * (plaza_r + 1.6),
                                      math.sin(a) * (plaza_r + 1.6)),
                              "rot": a + math.pi / 2})
    n_lights = int(preset.get("lights", 4) * q *
                   max(0.2, params.park_light_density))
    for i in range(n_lights):
        a = 2 * math.pi * (i + 0.5) / max(1, n_lights)
        rr = plaza_r * 2.1
        spec["props"].append({"type": "STREETLIGHT",
                              "pos": (math.cos(a) * rr, math.sin(a) * rr),
                              "rot": a + math.pi / 2,
                              "kw": {"prop_height": 3.4}})
    n_bins = int(preset.get("bins", 2) * q)
    for i in range(n_bins):
        spot = free_spot(plaza_r + 0.5)
        if spot:
            spec["props"].append({"type": "GARBAGE_BIN", "pos": spot})
    if preset.get("dog_area"):
        spot = free_spot(plaza_r)
        if spot:
            spec["props"].append({"type": "BARRIER", "pos": spot})
    if preset.get("picnic"):
        for _i in range(2):
            spot = free_spot(plaza_r + 3.0)
            if spot:
                spec["props"].append({"type": "BENCH", "pos": spot})
    return spec


def build_children(params: GenerationParams, spec: Dict,
                   parent_obj) -> int:
    """Instantiate child objects (trees, bushes, props) parented to the
    park terrain.  Returns the number of children created."""
    from . import vegetation, props as props_gen
    rng = make_rng(params.seed, "park_instantiate")
    count = 0

    def place(builder, child_params, pos, rot=0.0):
        nonlocal count
        cmb, _info = builder(child_params)
        mesh, _mats = cmb.finish("CFParkChild")
        obj = bpy.data.objects.new("CFParkChild", mesh)
        obj.location = (pos[0], pos[1], 0.0)
        obj.rotation_euler = (0, 0, rot)
        obj.parent = parent_obj
        # link into the parent's collection
        target = None
        for c in parent_obj.users_collection:
            target = c
            break
        (target or bpy.context.scene.collection).objects.link(obj)
        count += 1

    from ..core import asset_manager
    for tree_spec in spec.get("trees", []):
        tp = GenerationParams()
        tp.asset_type = "TREE"
        tp.tree_type = tree_spec["tree_type"]
        tp.season = tree_spec["season"]
        tp.tree_height = tree_spec["height"]
        tp.canopy_radius = tree_spec["canopy"]
        tp.detail_level = params.detail_level
        tp.seed = params.seed + int(tree_spec["pos"][0] * 13
                                    + tree_spec["pos"][1] * 7)
        place(vegetation.build_asset, tp, tree_spec["pos"])
    for bush_spec in spec.get("bushes", []):
        bp = GenerationParams()
        bp.asset_type = "BUSH"
        bp.detail_level = params.detail_level
        bp.seed = params.seed + int(bush_spec["pos"][0] * 11
                                    + bush_spec["pos"][1] * 5)
        place(vegetation.build_asset, bp, bush_spec["pos"])
    for prop_spec in spec.get("props", []):
        pp = GenerationParams()
        pp.asset_type = prop_spec["type"]
        pp.detail_level = params.detail_level
        pp.seed = params.seed + int(prop_spec["pos"][0] * 17
                                    + prop_spec["pos"][1] * 3)
        for k, v in prop_spec.get("kw", {}).items():
            setattr(pp, k, v)
        place(props_gen.build_asset, pp, prop_spec["pos"],
              prop_spec.get("rot", 0.0))
    return count


def _link(obj):
    col = bpy.context.scene.collection
    try:
        col.objects.link(obj)
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# terrain pieces
# ---------------------------------------------------------------------------

def _polygon_mesh(mb: MeshBuilder, poly, material: str, z: float = 0.0) \
        -> None:
    """Flat ground plate. Rectangular outlines become one solid slab box
    (shading-guaranteed); other shapes use Delaunay triangulation."""
    if len(poly) == 4:
        xs = sorted(set(round(p[0], 4) for p in poly))
        ys = sorted(set(round(p[1], 4) for p in poly))
        if len(xs) == 2 and len(ys) == 2:
            w = xs[1] - xs[0]
            d = ys[1] - ys[0]
            cx = (xs[0] + xs[1]) / 2
            cy = (ys[0] + ys[1]) / 2
            mb.add_box((cx, cy, z - 0.05), (w, d, 0.1), material)
            return
    import mathutils
    vs = [mathutils.Vector((float(x), float(y), 0.0)) for (x, y) in poly]
    n = len(vs)
    edges = [(i, (i + 1) % n) for i in range(n)]
    try:
        result = mathutils.geometry.delaunay_2d_cdt(vs, edges, [], 1, 0)
    except Exception:  # fall back to a fan for degenerate outlines
        _fan_mesh(mb, poly, material, z)
        return
    out_vs = result["verts"]
    for tri in result["faces"]:
        pts = [(out_vs[i].x, out_vs[i].y, z) for i in tri]
        cx = sum(p[0] for p in pts) / 3.0
        cy = sum(p[1] for p in pts) / 3.0
        if not _point_in_poly(cx, cy, poly):
            continue
        mb.add_outward_face(pts, material, (0, 0, 1))


def _fan_mesh(mb: MeshBuilder, poly, material: str, z: float) -> None:
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    for i in range(len(poly)):
        a = poly[i]
        b = poly[(i + 1) % len(poly)]
        mb.add_outward_face([(cx, cy, z), (a[0], a[1], z), (b[0], b[1], z)],
                            material, (0, 0, 1))


def _path(mb, start, mid, end, width, boundary_poly,
          material: str = "park_path", z: float = 0.02):
    """Bent path start -> mid -> end built from SOLID BOX segments.

    Each path sits on its own z-layer (the caller varies `z`), so no two
    slabs ever share a height and overlapping segments never z-fight."""
    pts = [start, mid, end]
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        if ln < 0.05:
            continue
        ang = math.atan2(dy, dx)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        # per-segment height increment: the overlapping joint boxes never
        # share a top height, so no coplanar z-fighting
        top = z + 0.075 + i * 0.0008
        mb.add_box((mx, my, (z + top) / 2),
                   (ln + width * 0.5, width, top - z),
                   material, rot_z=ang)


def _bend_to(rng, start, end, bend):
    """A bent midpoint between start and end (deterministic per rng)."""
    mx = (start[0] + end[0]) / 2
    my = (start[1] + end[1]) / 2
    dx, dy = end[0] - start[0], end[1] - start[1]
    ln = math.hypot(dx, dy) or 1.0
    off = rng.uniform(-bend, bend)
    return (mx - dy / ln * off, my + dx / ln * off)


def _pond(mb, center, r, params):
    cx, cy = center
    # rim ring (soil) + opaque water disc, offset heights to avoid
    # coplanar caps (no z-fighting)
    ring_r0, ring_r1 = r * 1.02, r * 1.18
    for i in range(24):
        a0 = 2 * math.pi * i / 24
        a1 = 2 * math.pi * (i + 1) / 24
        mb.add_outward_face([
            (cx + ring_r0 * math.cos(a0), cy + ring_r0 * math.sin(a0), 0.03),
            (cx + ring_r1 * math.cos(a0), cy + ring_r1 * math.sin(a0), 0.03),
            (cx + ring_r1 * math.cos(a1), cy + ring_r1 * math.sin(a1), 0.03),
            (cx + ring_r0 * math.cos(a1), cy + ring_r0 * math.sin(a1), 0.03)],
            "soil", (0, 0, 1))
    mb.add_cylinder((cx, cy, 0.035), r, 0.075, 24, "pond_water",
                    cap_bottom=False)


def _flower_bed(mb, rng, pos):
    x, y = pos
    mb.add_box((x, y, 0.18), (1.7, 1.1, 0.32), "concrete")
    mb.add_box((x, y, 0.38), (1.5, 0.9, 0.1), "soil")
    cols = [(0.9, 0.2, 0.25), (0.95, 0.75, 0.15), (0.8, 0.3, 0.7),
            (0.95, 0.95, 0.9)]
    for i in range(6):
        fx = x + rng.uniform(-0.6, 0.6)
        fy = y + rng.uniform(-0.35, 0.35)
        col = f"painted_metal#{'%02x%02x%02x' % tuple(int(c * 255) for c in rng.choice(cols))}"
        mb.add_cylinder((fx, fy, 0.47), 0.07, 0.24, 5, "leaves_summer")
        mb.add_sphere((fx, fy, 0.64), 0.1, 6, 4, col)


def _basketball_court(mb, rng, center):
    x, y = center
    # pad
    mb.add_box((x, y, 0.05), (15.0, 11.0, 0.06), "asphalt")
    # markings (white plates slightly above the pad)
    z = 0.085
    mb.add_outward_face([(x - 7.2, y - 5.2, z), (x + 7.2, y - 5.2, z),
                         (x + 7.2, y + 5.2, z), (x - 7.2, y + 5.2, z)],
                        "road_marking", (0, 0, 1))
    mb.add_outward_face([(x - 7.1, y - 5.1, z + 0.001),
                         (x + 7.1, y - 5.1, z + 0.001),
                         (x + 7.1, y + 5.1, z + 0.001),
                         (x - 7.1, y + 5.1, z + 0.001)], "asphalt", (0, 0, 1))
    # center circle + hoops
    mb.add_cylinder((x, y, z + 0.005), 1.2, 0.004, 20, "road_marking")
    for s in (-1, 1):
        mb.add_box((x + s * 7.0, 0, z + 1.5), (0.1, 1.8, 0.1), "steel_frame")
        mb.add_cylinder((x + s * 7.0, 0, z + 0.75), 0.06, 1.5, 6,
                        "steel_frame")
        mb.add_box((x + s * 6.9, 0, z + 2.6), (0.05, 1.2, 0.8),
                   "holo_white")


def _soccer_field(mb, rng, center):
    x, y = center
    mb.add_box((x, y, 0.045), (20.0, 12.0, 0.05), "grass")
    z = 0.075
    # boundary + center line (white)
    for (px0, py0, px1, py1) in (
            (x - 10, y - 6, x + 10, y - 6), (x - 10, y + 6, x + 10, y + 6),
            (x - 10, y - 6, x - 10, y + 6), (x + 10, y - 6, x + 10, y + 6),
            (x, y - 6, x, y + 6)):
        mx, my = (px0 + px1) / 2, (py0 + py1) / 2
        ln = math.hypot(px1 - px0, py1 - py0)
        ang = math.atan2(py1 - py0, px1 - px0)
        mb.add_box((mx, my, z), (ln if abs(math.cos(ang)) > 0.5 else 0.08,
                   0.08 if abs(math.cos(ang)) > 0.5 else ln, 0.01),
                   "road_marking")
    # goals
    for s in (-1, 1):
        gx = x + s * 10
        mb.add_box((gx, 0, z + 0.6), (0.08, 3.2, 0.08), "holo_white")
        for gy in (-1.6, 1.6):
            mb.add_box((gx + s * 0.4, gy, z + 0.3), (0.8, 0.06, 0.06),
                       "holo_white")
        mb.add_box((gx + s * 0.5, 0, z + 0.05), (0.9, 3.2, 0.04),
                   "steel_frame")


def _low_wall(mb, a, b, height, material):
    ax, ay = a
    bx, by = b
    mx, my = (ax + bx) / 2, (ay + by) / 2
    ln = math.hypot(bx - ax, by - ay)
    if ln < 0.4:
        return
    ang = math.atan2(by - ay, bx - ax)
    mb.add_box((mx, my, height / 2), (ln, 0.3, height), material, rot_z=ang)
