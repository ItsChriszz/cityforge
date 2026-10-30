# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural building generator.

Buildings are assembled from real architectural volume, not textured cubes:

* every storey is separated by visible slab/spandrel bands,
* each facade is built from wall panels with actual openings, window frames,
  recessed glass, sills and lintels,
* balconies, podiums, setbacks, storefronts, entrance portals, parapets and
  roof furniture (HVAC units, vents, water tanks, bulkheads, antennas) are
  modelled as solid geometry.

Facade walls are composed from butted boxes (piers / spandrels / headers), so
they remain watertight without boolean operations; shared vertices weld in
:meth:`cityforge.utils.geometry.MeshBuilder.finish`.

Conventions used consistently across the add-on:
* a building's front facade faces -Y (Blender's front view),
* origin = centre of the ground footprint at z = 0,
* 1 Blender unit = 1 metre.

Wall-local convention (used by :func:`_wall_box`):
* ``depth_size`` is the box thickness measured along the wall's outward
  normal,
* ``depth_center`` positions the box centre: 0 = outer wall plane,
  negative values sit inside the building, positive values stick out.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ..core.params import DET_LEVELS, GenerationParams, STYLE_PROFILES
from ..core.randomization import chance, jitter, make_rng, pick_weighted
from ..utils import get_logger
from ..utils.geometry import MeshBuilder
from ..utils.naming import asset_name

_log = get_logger()

__all__ = ["build_building", "estimate_polys"]

# ---------------------------------------------------------------------------
# detail-quality table: how LOW / MEDIUM / HIGH change construction
# ---------------------------------------------------------------------------

DETAIL_QUALITY = {
    "low":    {"cyl": 6,  "sphere": (6, 4),  "mullions": False,
               "sills": False, "lintels": False, "roof_extras": 0.35,
               "awning": False},
    "medium": {"cyl": 10, "sphere": (8, 5),  "mullions": True,
               "sills": True,  "lintels": True,  "roof_extras": 0.8,
               "awning": True},
    "high":   {"cyl": 14, "sphere": (12, 8), "mullions": True,
               "sills": True,  "lintels": True,  "roof_extras": 1.0,
               "awning": True},
}

WALL_THICK = 0.22      # facade panel depth
ROOF_THICK = 0.26
PARAPET_H = 0.55

_TYPE_WALL_STYLE = {
    #                       style:         (piers,       spandrels)
    "modern_residential":      ("primary", "secondary"),
    "contemporary_commercial": ("secondary", "dark_metal"),
    "glass_office_tower":      ("dark_metal", "dark_metal"),
    "concrete_apartment":      ("primary", "secondary"),
    "brick_residential":       ("primary", "secondary"),
    "industrial_warehouse":    ("secondary", "primary"),
    "mixed_use_urban":         ("primary", "secondary"),
    "suburban_house":          ("primary", "primary"),
    "traditional_lowrise":     ("primary", "secondary"),
    "modern_highrise":         ("secondary", "dark_glass"),
    # modern skyscrapers: full glazing with metal frames
    "glass_curtain_tower":     ("steel_frame", "dark_metal"),
    "modern_office_skyscraper": ("dark_metal", "dark_glass"),
    "contemporary_residential_tower": ("primary", "secondary"),
    "mixed_use_tower":         ("primary", "secondary"),
    "futuristic_tower":        ("steel_frame", "grey_glass"),
}

_TOWER_STYLES = set(_TYPE_WALL_STYLE) & {
    "glass_office_tower", "modern_highrise", "glass_curtain_tower",
    "modern_office_skyscraper", "contemporary_residential_tower",
    "mixed_use_tower", "futuristic_tower",
}


def _from_role(role: str, p: GenerationParams) -> str:
    """Map a style role word ('primary' / 'secondary') to a material key."""
    if role == "primary":
        return p.material_primary
    if role == "secondary":
        return p.material_secondary
    return role  # direct material keys like "dark_metal"


# ---------------------------------------------------------------------------
# per-building derived state
# ---------------------------------------------------------------------------

class Ctx:

    def __init__(self, p: GenerationParams):
        self.p = p
        self.style = p.style if p.style in STYLE_PROFILES else "modern_residential"
        self.profile = STYLE_PROFILES[self.style]
        self.q = DETAIL_QUALITY.get(p.detail_level, DETAIL_QUALITY["medium"])
        self.rng = make_rng(p.seed, "building")

        pier_role, spandrel_role = _TYPE_WALL_STYLE[self.style]
        self.pier_mat = _from_role(pier_role, p)
        self.spandrel_mat = _from_role(spandrel_role, p)

        # jittered per-building dimensions (keeps the user's ratios)
        self.width = jitter(self.rng, p.width, p.width * 0.04)
        self.depth = jitter(self.rng, p.depth, p.depth * 0.06)
        self.floor_h = jitter(self.rng, p.floor_height, p.floor_height * 0.04)
        self.h_ground = (self.floor_h * 1.35
                         if p.ground_floor in ("retail", "office_lobby",
                                               "loading_bay", "garage")
                         else self.floor_h)
        self.win_w = jitter(self.rng, p.window_width, 0.08)
        self.win_h = jitter(self.rng, p.window_height, 0.08)
        self.spacing = max(self.win_w + 0.55,
                           jitter(self.rng, p.window_spacing, 0.15))
        self.sill = max(0.35, jitter(self.rng, p.window_sill, 0.10))
        self.curtain = p.window_type == "curtain_wall"

        # colour pipeline: tokens ("key#hex") flow through MeshBuilder and
        # resolve to shared tinted variants at finish time.  The pickers are
        # ALWAYS active; they are synced to the style palette by the UI, so
        # generation matches the style until the user picks a colour.
        cmap = {}
        if getattr(p, "use_random_palette", False):
            from ..core.materials import generate_palette
            cmap = generate_palette(self.rng)
        else:
            cmap = {"primary": tuple(p.color_primary),
                    "secondary": tuple(p.color_secondary),
                    "window": tuple(p.color_window),
                    "trim": tuple(p.color_trim)}
        from ..core.materials import color_to_hex
        def tok(key, role):
            if key and role in cmap:
                return f"{key}#{color_to_hex(cmap[role])}"
            return key
        self.color_tokens = {
            "primary": tok(p.material_primary, "primary"),
            "secondary": tok(p.material_secondary, "secondary"),
            "window": tok(p.material_window, "window"),
            "trim": tok(p.material_trim, "trim"),
        }

        pier_role, spandrel_role = _TYPE_WALL_STYLE[self.style]
        self.pier_mat = _from_role(pier_role, p)
        self.spandrel_mat = _from_role(spandrel_role, p)
        # swap in tinted tokens for the roles that carry user colours
        if cmap:
            if self.pier_mat == p.material_primary:
                self.pier_mat = self.color_tokens["primary"]
            if self.spandrel_mat == p.material_secondary:
                self.spandrel_mat = self.color_tokens["secondary"]
        # architectural levels (validated by params.apply_arch_levels)
        self.l1 = p.arch_level_1
        self.l2 = p.arch_level_2 and p.arch_level_1
        self.l3 = p.arch_level_3 and p.arch_level_1
        # tower shape / facade rhythm / crown lighting (skyscrapers)
        self.tower_form = p.tower_form
        self.facade_grid = p.facade_grid
        self.crown_lighting = p.crown_lighting
        # construction-animation staging: builders route their geometry into
        # named parts via this tag (see PartRouter)
        self.current_part = "main"
        # business identity for commercial ground floors (seeded, local)
        if p.asset_type in ("COMMERCIAL", "MIXED", "SHOP") or \
                p.ground_floor in ("retail", "office_lobby"):
            self.business_category, self.business_name = resolve_business(
                self)
        else:
            self.business_category, self.business_name = "", ""
        if p.detail_level == "low":
            # LOW detail: simplify the facade density as well
            self.spacing += 0.6
            self.win_w *= 1.05

    # -- storey helpers (floor index 0 = ground floor) ----------------------
    def floor_base(self, idx: int) -> float:
        if idx <= 0:
            return 0.0
        return self.h_ground + (idx - 1) * self.floor_h

    def floor_top(self, idx: int) -> float:
        base = self.floor_base(idx)
        return base + (self.h_ground if idx == 0 else self.floor_h)

    def total_h(self) -> float:
        return self.floor_top(self.p.floors - 1)


def _podium_floors(ctx: Ctx) -> int:
    p = ctx.p
    allow = ctx.style in ("glass_office_tower", "modern_highrise",
                          "mixed_use_urban", "contemporary_commercial")
    if p.podium_floors > 0 and allow:
        return min(p.podium_floors, max(0, p.floors - 1))
    return 0


def _podium_scale(ctx: Ctx) -> float:
    pw = max(1.5, ctx.p.podium_width or 2.5)
    return 1.0 + 2.0 * pw / max(0.5, min(ctx.width, ctx.depth))


def _ctx_segments(ctx: Ctx) -> List[Tuple[int, int, float]]:
    """Tower segments (first_floor, count, width_scale) — podium excluded.

    Honours the tower form: box (single mass), setback (few big steps),
    tapered (many small steps), tapered_setback (mixed), crown (taper).
    """
    n = ctx.p.floors
    podium = _podium_floors(ctx)
    remaining = n - podium
    out: List[Tuple[int, int, float]] = []
    if remaining <= 0:
        return out
    form = getattr(ctx, "tower_form", "box")
    tall = ctx.style in ("glass_office_tower", "modern_highrise",
                         "glass_curtain_tower", "modern_office_skyscraper",
                         "contemporary_residential_tower", "mixed_use_tower",
                         "futuristic_tower")
    if not tall or remaining < 8:
        out.append((podium, remaining, 1.0))
        return out
    if form == "tapered" or form == "crown":
        steps = 6 if form == "tapered" else 4
        chunk = max(2, remaining // steps)
        made = 0
        for _i in range(steps):
            count = min(chunk, remaining - made)
            if count <= 0:
                break
            scale = 1.0 - (0.38 * made / max(1, remaining))
            out.append((podium + made, count, scale))
            made += count
        if remaining - made > 0:
            out.append((podium + made, remaining - made,
                        1.0 - 0.38 * made / max(1, remaining)))
    elif form == "tapered_setback":
        step_scales = (1.0, 0.9, 0.9, 0.78, 0.78, 0.64)
        chunk = max(2, remaining // len(step_scales))
        made = 0
        for scale in step_scales:
            count = min(chunk, remaining - made)
            if count <= 0:
                break
            out.append((podium + made, count, scale))
            made += count
        if remaining - made > 0:
            out.append((podium + made, remaining - made, 0.64))
    elif form == "setback" or ctx.style in ("glass_office_tower",
                                            "modern_highrise"):
        cut1 = max(3, int(remaining * 0.55))
        cut2 = max(1, int(remaining * 0.80))
        out.append((podium, cut1, 1.0))
        out.append((podium + cut1, cut2 - cut1, 0.86))
        if remaining - cut2 > 0:
            out.append((podium + cut2, remaining - cut2, 0.72))
    else:  # box
        out.append((podium, remaining, 1.0))
    return out


# ---------------------------------------------------------------------------
# wall-space helpers
# ---------------------------------------------------------------------------

class PartRouter:
    """MeshBuilder facade that routes every call into one of several named
    part builders (used for construction-animation staging).

    The active part is selected by ``ctx.current_part``; builders only need
    to set that field, and every add_* call is routed transparently."""

    def __init__(self):
        self.parts: Dict[str, MeshBuilder] = {}
        self.current = "main"

    def _t(self) -> MeshBuilder:
        if self.current not in self.parts:
            self.parts[self.current] = MeshBuilder()
        return self.parts[self.current]

    # routed API (mirrors MeshBuilder)
    def add_face(self, *a, **k):
        self._t().add_face(*a, **k)

    def add_outward_face(self, *a, **k):
        self._t().add_outward_face(*a, **k)

    def add_box(self, *a, **k):
        self._t().add_box(*a, **k)

    def add_plate(self, *a, **k):
        self._t().add_plate(*a, **k)

    def add_cylinder(self, *a, **k):
        self._t().add_cylinder(*a, **k)

    def add_sphere(self, *a, **k):
        self._t().add_sphere(*a, **k)

    def add_loft(self, *a, **k):
        self._t().add_loft(*a, **k)

    # aggregates
    @property
    def face_count(self) -> int:
        return sum(part.face_count for part in self.parts.values())

    @property
    def polys_estimated(self) -> int:
        return self.poly_count()

    def poly_count(self) -> int:
        return sum(part.poly_count() for part in self.parts.values())

    def material_names(self) -> List[str]:
        names = set()
        for part in self.parts.values():
            names.update(part.material_names())
        return sorted(names)

    def finish(self, name: str):
        raise NotImplementedError(
            "PartRouter has no single mesh; iterate parts instead")


class Wall:
    """Facade plane: origin at (u=0, outer face, base), u-axis direction,
    outward normal, length."""

    def __init__(self, origin: Tuple[float, float, float],
                 u: Tuple[float, float], outward: Tuple[float, float],
                 length: float):
        self.origin = origin
        self.u = u
        self.outward = outward
        self.length = length
        self.rot = math.atan2(u[1], u[0])


def _wall_box(mb, wall: Wall, u_center: float, z_center: float,
              width: float, height: float, depth_size: float,
              material: str, depth_center: float = -WALL_THICK / 2) -> None:
    """Box in wall-local coordinates.

    Positive ``depth_center`` sticks out from the facade; negative recesses.
    ``depth_size`` is the box thickness along the normal.
    """
    ox, oy, _oz = wall.origin
    cx = ox + wall.u[0] * u_center + wall.outward[0] * depth_center
    cy = oy + wall.u[1] * u_center + wall.outward[1] * depth_center
    mb.add_box((cx, cy, z_center), (width, depth_size, height), material,
               rot_z=wall.rot)


def _panel(mb, wall: Wall, u_center: float, z_center: float,
           width: float, height: float, material: str) -> None:
    """Wall panel: WALL_THICK thick, outer face flush with the facade plane."""
    _wall_box(mb, wall, u_center, z_center, width, height, WALL_THICK,
              material)


def _wall_face(mb, wall: Wall, u0: float, z0: float, u1: float, z1: float,
               material: str, depth: float = 0.0) -> None:
    """Zero-thickness rectangle parallel to the facade plane.

    `depth` offsets the rectangle inward (positive = behind the plane), so
    stacked faces never z-fight."""
    ox, oy, _oz = wall.origin
    ox -= wall.outward[0] * depth
    oy -= wall.outward[1] * depth
    p0 = (ox + wall.u[0] * u0, oy + wall.u[1] * u0, z0)
    p1 = (ox + wall.u[0] * u1, oy + wall.u[1] * u1, z0)
    p2 = (ox + wall.u[0] * u1, oy + wall.u[1] * u1, z1)
    p3 = (ox + wall.u[0] * u0, oy + wall.u[1] * u0, z1)
    mb.add_outward_face([p0, p1, p2, p3], material, wall.outward)


def _openings_for_width(length: float, ctx: Ctx) -> List[Tuple[float, float]]:
    """Opening spans (u0, u1) along one wall for the current window grid."""
    w = ctx.win_w
    usable = length - 1.0
    if usable <= w or w <= 0:
        return []
    if ctx.curtain:
        bays = max(1, int(usable / max(1.2, ctx.spacing)))
        span = usable / bays
        return [(0.5 + i * span + 0.02, 0.5 + (i + 1) * span - 0.02)
                for i in range(bays)]
    gap = ctx.spacing - w
    if gap < 0.25:
        return []
    n = int((usable + gap) // (w + gap))
    if n < 1:
        return []
    total = n * w + (n - 1) * gap
    start = (length - total) / 2.0
    return [(start + i * (w + gap), start + i * (w + gap) + w)
            for i in range(n)]


def _lit_material(ctx: Ctx) -> str:
    p = ctx.p
    glass_token = ctx.color_tokens.get("window", p.material_window)
    if p.window_light == "always_lit":
        return "window_lit"
    if p.window_light == "always_dark":
        return glass_token
    return "window_lit" if chance(ctx.rng, 0.34) else glass_token


def _window_assembly(mb, ctx: Ctx, wall: Wall, u0: float, u1: float,
                     v0: float, v1: float) -> None:
    """Frame ring + recessed glass + sill/lintel (+ mullions) in an opening."""
    w = u1 - u0
    h = v1 - v0
    if w <= 0.05 or h <= 0.05:
        return
    cz = (v0 + v1) / 2.0
    uc = (u0 + u1) / 2.0
    fr = min(0.09, max(0.03, ctx.p.frame_thickness))
    frame_mat = ctx.color_tokens.get("trim", ctx.p.material_trim)

    # frame ring recessed slightly so it reads as part of the reveal
    fr_depth = WALL_THICK * 0.75
    fr_center = -0.02 - fr_depth / 2
    for u_c in (u0 + fr / 2, u1 - fr / 2):
        _wall_box(mb, wall, u_c, cz, fr, h, fr_depth, frame_mat,
                  depth_center=fr_center)
    for z_c in (v0 + fr / 2, v1 - fr / 2):
        _wall_box(mb, wall, uc, z_c, w, fr, fr_depth, frame_mat,
                  depth_center=fr_center)

    # glass sits near the wall's inner surface: a real reveal
    gw = w - 2 * fr
    gh = h - 2 * fr
    if gw > 0.02 and gh > 0.02:
        _wall_box(mb, wall, uc, cz, gw, gh, 0.03, _lit_material(ctx),
                  depth_center=-0.13)
        if ctx.q["mullions"] and ctx.l2 and gw > 1.0:
            if ctx.curtain:
                _curtain_grid(mb, ctx, wall, u0 + fr, v0 + fr, gw, gh,
                              frame_mat)
            else:
                mull_n = 1 if gw < 2.0 else 2
                for k in range(1, mull_n + 1):
                    mu = u0 + fr + gw * k / (mull_n + 1)
                    _wall_box(mb, wall, mu, cz, 0.035, gh, 0.06, frame_mat,
                              depth_center=-0.06)
    if ctx.q["sills"] and ctx.l2 and v0 > 0.5:
        _wall_box(mb, wall, uc, v0 - 0.02, w + 0.14, 0.06, 0.05, frame_mat,
                  depth_center=0.02)
    if ctx.q["lintels"] and ctx.l2 and not ctx.curtain:
        _wall_box(mb, wall, uc, v1 + 0.04, w + 0.06, 0.08, 0.02, frame_mat,
                  depth_center=0.01)


def _curtain_grid(mb, ctx: Ctx, wall: Wall, u0: float, v0: float,
                  gw: float, gh: float, frame_mat: str) -> None:
    """Curtain-wall mullion/transom rhythm (facade_grid parameter)."""
    grid = ctx.facade_grid
    if grid == "auto":
        grid = ("vertical" if ctx.style in ("glass_curtain_tower",
                                            "futuristic_tower")
                else "horizontal" if ctx.style ==
                "contemporary_residential_tower" else "ortho")
    do_v = grid in ("vertical", "ortho")
    do_h = grid in ("horizontal", "ortho")
    cz = v0 + gh / 2
    if do_v:
        step = 0.9
        n = max(1, int(gw / step) - 1)
        for k in range(1, n + 1):
            mu = u0 + gw * k / (n + 1)
            _wall_box(mb, wall, mu, cz, 0.05, gh, 0.07, frame_mat,
                      depth_center=-0.05)
    if do_h:
        # transom band across the middle of tall panes
        if gh > 1.6:
            _wall_box(mb, wall, u0 + gw / 2, cz, gw, 0.05, 0.07, frame_mat,
                      depth_center=-0.05)


def _floor_band(mb, ctx: Ctx, wall: Wall, z0: float, z1: float,
                band_type: str = "window", solid: bool = False) -> None:
    """One storey band: spandrel + header strips + piers + window assemblies."""
    h = z1 - z0
    if h < 0.2:
        return

    if solid:
        _panel(mb, wall, wall.length / 2, (z0 + z1) / 2, wall.length, h,
               ctx.pier_mat)
        return

    sill_h = max(0.25, min(ctx.sill, h - 0.6))
    if ctx.curtain and band_type == "window":
        sill_h = 0.35
    if band_type == "strip":
        sill_h = max(1.9, h - 1.0)
    if band_type in ("tall", "picture"):
        sill_h = 0.75

    opening_h = max(0.5, min(ctx.win_h, h - sill_h - 0.25))
    if ctx.curtain:
        opening_h = h - sill_h - 0.35
    if opening_h <= 0.2:
        _panel(mb, wall, wall.length / 2, (z0 + z1) / 2, wall.length, h,
               ctx.pier_mat)
        return

    op_z0 = z0 + sill_h
    op_z1 = op_z0 + opening_h
    op_cz = (op_z0 + op_z1) / 2.0

    if sill_h > 0.02:
        # spandrel under the opening row = visible slab band
        _panel(mb, wall, wall.length / 2, z0 + sill_h / 2, wall.length,
               sill_h, ctx.spandrel_mat)
    top_h = z1 - op_z1
    if top_h > 0.02:
        _panel(mb, wall, wall.length / 2, z1 - top_h / 2, wall.length,
               top_h, ctx.spandrel_mat)

    openings = _openings_for_width(wall.length, ctx)
    if not openings:
        if sill_h < 0.02:
            _panel(mb, wall, wall.length / 2, op_cz, wall.length,
                   opening_h, ctx.pier_mat)
        return
    u_cursor = 0.0
    for (o0, o1) in openings:
        if o0 > u_cursor + 0.02:
            _panel(mb, wall, (u_cursor + o0) / 2, op_cz, o0 - u_cursor,
                   opening_h, ctx.pier_mat)
        _window_assembly(mb, ctx, wall, o0, o1, op_z0, op_z1)
        u_cursor = o1
    if wall.length > u_cursor + 0.02:
        _panel(mb, wall, (u_cursor + wall.length) / 2, op_cz,
               wall.length - u_cursor, opening_h, ctx.pier_mat)


# ---------------------------------------------------------------------------
# balconies
# ---------------------------------------------------------------------------

def _balcony(mb, ctx: Ctx, wall: Wall, z: float, u0: float, u1: float) -> None:
    """Platform slab + railings for one balcony."""
    depth = max(0.5, ctx.p.balcony_depth)
    w = u1 - u0
    cu = (u0 + u1) / 2.0
    thick = 0.05
    top_rail = 1.02
    rail_mat = "metal"

    platform_mat = ("concrete" if ctx.p.balcony_style in ("concrete", "glass")
                    else ctx.p.material_secondary)
    # platform slab from the facade out to `depth`
    _wall_box(mb, wall, cu, z + 0.05, w + 0.12, 0.10, depth,
              platform_mat, depth_center=depth / 2)
    # front railing
    if ctx.p.balcony_style == "glass":
        _wall_box(mb, wall, cu, z + top_rail / 2 + 0.08, w, top_rail - 0.02,
                  0.04, ctx.color_tokens.get("window",
                                             ctx.p.material_window),
                  depth_center=depth - 0.02)
        _wall_box(mb, wall, cu, z + top_rail + 0.08, w + thick, 0.06,
                  0.06, rail_mat, depth_center=depth + 0.01)
    else:
        n_posts = max(2, int(w / 0.85) + 1)
        for i in range(n_posts):
            u = u0 + w * i / (n_posts - 1)
            _wall_box(mb, wall, u, z + top_rail / 2 + 0.08, thick, top_rail,
                      0.05, rail_mat, depth_center=depth - 0.02)
        _wall_box(mb, wall, cu, z + top_rail + 0.05, w, thick, 0.06,
                  rail_mat, depth_center=depth + 0.01)
        _wall_box(mb, wall, cu, z + 0.18, w * 0.98, thick, 0.06,
                  rail_mat, depth_center=depth + 0.01)
    # side rails at the balcony edges
    for s in (u0, u1):
        ox, oy, _oz = wall.origin
        cx = ox + wall.u[0] * s + wall.outward[0] * (depth / 2)
        cy = oy + wall.u[1] * s + wall.outward[1] * (depth / 2)
        mb.add_box((cx, cy, z + top_rail / 2 + 0.08), (0.05, depth, top_rail),
                   rail_mat, rot_z=wall.rot)


def build_balconies(mb, ctx: Ctx, wall: Wall, floor_idx: int) -> None:
    p = ctx.p
    if p.balcony_style == "none" or not ctx.l2:
        return
    freq = max(0.0, min(1.0, p.balcony_frequency))
    # sometimes balconies appear only on every other floor for pattern
    step = 2 if chance(ctx.rng, 0.3) else 1
    if step == 2 and floor_idx % 2 == 1 and p.floors > 2:
        return
    # platform top aligns with the window sill line so each balcony serves
    # the bay it attaches to
    sill = 0.75 if p.window_type in ("tall", "picture") else ctx.sill
    if ctx.curtain:
        sill = 0.35
    z = ctx.floor_base(floor_idx) + sill
    for (u0, u1) in _openings_for_width(wall.length, ctx):
        if chance(ctx.rng, freq):
            _balcony(mb, ctx, wall, z, u0, u1)


# ---------------------------------------------------------------------------
# ground-floor archetypes
# ---------------------------------------------------------------------------

def _door(mb, ctx: Ctx, wall: Wall, u_center: float, z0: float,
          w: float = 1.0, h: float = 2.05) -> None:
    """Entry door: portal surround, recessed panel, glass, canopy, steps.

    `z0` must be the ground line so the door never floats."""
    door_mat = ctx.color_tokens.get("trim", ctx.p.material_trim)
    h = max(2.0, h)
    _panel(mb, wall, u_center, z0 + h / 2, w + 0.26, h + 0.16, ctx.pier_mat)
    _wall_box(mb, wall, u_center, z0 + h / 2, w, h, 0.04, door_mat,
              depth_center=-0.04)
    if ctx.style not in ("suburban_house", "brick_residential"):
        _wall_box(mb, wall, u_center, z0 + h * 0.70, w * 0.5, h * 0.26, 0.03,
                  ctx.color_tokens.get("window", ctx.p.material_window),
                  depth_center=-0.08)
    # entrance steps in front of the door (complete, grounded entrance)
    _entrance_steps(mb, ctx, wall, u_center)
    if ctx.q["awning"] and ctx.l3:
        _wall_box(mb, wall, u_center, z0 + h + 0.24, w, h, 0.09,
                  "dark_metal", depth_center=0.55)


# business-category palette: (sign material, awning material, accent trim)
BUSINESS_PALETTES = {
    "restaurant": ("sign", "awning_green", "painted_metal"),
    "cafe": ("sign_cream", "awning_brown", "painted_metal"),
    "pub": ("sign_dark", "awning_black", "grime_metal"),
    "bar": ("sign_dark", "awning_black", "grime_metal"),
    "retail_shop": ("sign", "awning_red", "painted_metal"),
    "grocery_store": ("sign_green", "awning_green", "painted_metal"),
    "convenience_store": ("sign", "awning_red", "painted_metal"),
    "office": ("sign_cream", "dark_metal", "dark_metal"),
    "other": ("sign", "awning_red", "painted_metal"),
}


def resolve_business(ctx: Ctx) -> Tuple[str, str]:
    """Pick the business category + name (seeded, local, no API).

    Returns (category, name).  Empty name -> generated from category lists.
    """
    p = ctx.p
    category = p.business_category or "random"
    if category == "random":
        category = pick_weighted(ctx.rng, [
            ("restaurant", 2.0), ("cafe", 2.0), ("pub", 1.0), ("bar", 1.0),
            ("retail_shop", 2.5), ("grocery_store", 1.5),
            ("convenience_store", 1.5), ("office", 1.5), ("other", 1.0)])
    if p.business_name.strip():
        return category, p.business_name.strip()
    from ..utils.business_names import generate_business_name
    return category, generate_business_name(ctx.rng, category)


def _sign_material(ctx: Ctx) -> str:
    if ctx.business_category in BUSINESS_PALETTES:
        return BUSINESS_PALETTES[ctx.business_category][0]
    return pick_weighted(ctx.rng, [("sign", 0.55), ("sign_cream", 0.30),
                                   (ctx.p.material_trim, 0.15)])


def _awning_material(ctx: Ctx) -> str:
    if ctx.business_category in BUSINESS_PALETTES:
        return BUSINESS_PALETTES[ctx.business_category][1]
    return ctx.p.material_secondary


def _storefront_band(mb, ctx: Ctx, wall: Wall, z0: float, z1: float) -> None:
    """Glass commercial front: mullions, door, header, sign, awning."""
    p = ctx.p
    mull_mat = ctx.color_tokens.get("trim", p.material_trim)
    margin = 0.7
    glass_z0 = z0 + 0.15
    head_z = z1 - 0.18
    if head_z - glass_z0 < 1.0:
        _panel(mb, wall, wall.length / 2, (z0 + z1) / 2, wall.length,
               z1 - z0, ctx.pier_mat)
        return

    _panel(mb, wall, wall.length / 2, z1 - 0.09, wall.length, 0.18,
           ctx.spandrel_mat)
    _panel(mb, wall, wall.length / 2, z0 + 0.075, wall.length, 0.15,
           ctx.spandrel_mat)

    gw = wall.length - 2 * margin
    # storefront glazing with the interior surface 6 cm behind it: no
    # coplanar faces, no z-fighting, visible depth
    _wall_face(mb, wall, margin, glass_z0, wall.length - margin, head_z,
               "storefront_glass")
    _wall_face(mb, wall, margin + 0.05, glass_z0, wall.length - margin - 0.05,
               head_z, "concrete", depth=0.06)

    n = max(2, int(gw / 1.4))
    for i in range(n + 1):
        u = margin + (wall.length - 2 * margin) * i / n
        _wall_box(mb, wall, u, (glass_z0 + head_z) / 2, 0.07,
                  head_z - glass_z0 + 0.05, 0.08, mull_mat,
                  depth_center=0.02)
    _wall_box(mb, wall, wall.length / 2, head_z - 0.03, gw, 0.08, 0.08,
              mull_mat, depth_center=0.02)
    _panel(mb, wall, wall.length / 2, head_z + 0.05, wall.length - 0.4,
           0.10, ctx.pier_mat)

    du = wall.length * ctx.rng.uniform(0.35, 0.65)
    _door(mb, ctx, wall, du, z0 + 0.02, 1.0, head_z - z0 - 0.3)

    if ctx.profile.get("signage") and ctx.l2:
        sw = min(wall.length * 0.55, 6.0)
        sign_mat = _sign_material(ctx)
        _wall_box(mb, wall, wall.length / 2, z1 + 0.42, sw, 0.14, 0.14,
                  sign_mat, depth_center=0.07)
    if ctx.q["awning"] and ctx.l3:
        _wall_box(mb, wall, wall.length / 2, z1 - 0.06, gw, 0.07, 0.65,
                  _awning_material(ctx), depth_center=0.32)


def _loading_bay_band(mb, ctx: Ctx, wall: Wall, z0: float, z1: float) -> None:
    """Industrial ground floor: roller doors + clerestory window strip."""
    p = ctx.p
    span = wall.length
    h = z1 - z0
    bay_w = min(4.2, span / 2.6)
    door_h = min(h - 0.45, 4.2)
    n_bays = max(1, int((span - 1.0) / (bay_w + 1.2)))
    gap = (span - n_bays * bay_w) / max(1, n_bays + 1)
    for i in range(n_bays):
        u0 = gap + i * (bay_w + gap)
        u1 = u0 + bay_w
        cu = (u0 + u1) / 2
        _panel(mb, wall, cu, z0 + door_h / 2, bay_w + 0.18, door_h + 0.18,
               ctx.pier_mat)
        _wall_box(mb, wall, cu, z0 + door_h / 2, bay_w, door_h, 0.02,
                  p.material_secondary, depth_center=-0.07)
        if p.detail_level != "low":
            n_ribs = max(2, int(door_h / 0.4))
            for k in range(n_ribs):
                rz = z0 + door_h * (k + 0.5) / n_ribs
                _wall_box(mb, wall, cu, rz, bay_w - 0.12, 0.03, 0.02,
                          p.material_secondary, depth_center=-0.045)
    # clerestory strip windows near the top of the tall ground floor
    strip_top, strip_bot = z1 - 0.35, z1 - 1.15
    if strip_bot > z0 + door_h + 0.3:
        save = (ctx.win_w, ctx.win_h, ctx.sill, ctx.curtain)
        try:
            ctx.win_w = min(1.5, span / 7)
            ctx.win_h = strip_top - strip_bot
            ctx.sill = strip_bot - z0
            ctx.curtain = False
            _floor_band(mb, ctx, wall, z0, z1, "strip", solid=False)
        finally:
            ctx.win_w, ctx.win_h, ctx.sill, ctx.curtain = save


def _apartment_ground_band(mb, ctx: Ctx, wall: Wall, z0: float, z1: float,
                           front: bool) -> None:
    """Residential ground floor: taller windows and entrance door(s)."""
    save = (ctx.win_w, ctx.win_h, ctx.sill)
    try:
        ctx.win_w = 1.5
        ctx.win_h = min(z1 - z0 - 1.6, 2.0)
        ctx.sill = 0.95
        _floor_band(mb, ctx, wall, z0, z1, "tall", solid=not front)
        if front:
            if ctx.p.residential_form == "townhouse" or ctx.style == \
                    "brick_residential" and ctx.p.width <= 8.0:
                # one private entrance per ~6 m of frontage
                n_doors = max(1, int(wall.length / 6.0))
                for di in range(n_doors):
                    du = wall.length * (di + 0.5) / n_doors
                    _door(mb, ctx, wall, du, z0, 1.0, 2.2)
            else:
                openings = _openings_for_width(wall.length, ctx)
                if openings:
                    idx = len(openings) // 2
                    du = (openings[idx][0] + openings[idx][1]) / 2
                    _door(mb, ctx, wall, du, z0, 1.1, 2.2)
    finally:
        ctx.win_w, ctx.win_h, ctx.sill = save


def _garage_band(mb, ctx: Ctx, wall: Wall, z0: float, z1: float,
                 front: bool) -> None:
    """Parking structure band: open slots between chunky columns."""
    h = z1 - z0
    if not front:
        _panel(mb, wall, wall.length / 2, (z0 + z1) / 2, wall.length, h,
               "concrete")
        return
    n = max(2, int((wall.length - 1.0) / 3.4))
    for i in range(n + 1):
        u = wall.length * i / n
        _panel(mb, wall, u, (z0 + z1) / 2, 0.42, h, "concrete")
    # slab band across the top of the open front
    _wall_box(mb, wall, wall.length / 2, z1 - 0.10, wall.length, 0.2,
              WALL_THICK + 0.06, ctx.spandrel_mat, depth_center=+0.03)


def _ground_floor(mb, ctx: Ctx, wall: Wall, z0: float, z1: float,
                  front: bool) -> None:
    gtype = ctx.p.ground_floor
    if gtype in ("retail", "office_lobby"):
        _storefront_band(mb, ctx, wall, z0, z1)
    elif gtype == "loading_bay":
        _loading_bay_band(mb, ctx, wall, z0, z1)
    elif gtype == "garage":
        _garage_band(mb, ctx, wall, z0, z1, front)
    elif gtype == "none":
        _floor_band(mb, ctx, wall, z0, z1, "window", solid=True)
    else:
        _apartment_ground_band(mb, ctx, wall, z0, z1, front)


# ---------------------------------------------------------------------------
# roofs
# ---------------------------------------------------------------------------

def _roof_material(ctx: Ctx) -> str:
    if ctx.style in ("suburban_house", "brick_residential",
                     "traditional_lowrise"):
        return "roof_tiles"
    if ctx.style == "industrial_warehouse":
        return "roof_metal"
    return "roof_tar"


def _roof_flat(mb, ctx: Ctx, w: float, d: float, z_top: float) -> None:
    """Flat roof slab; parapet for roof_type='flat_parapet'."""
    mat = _roof_material(ctx)
    mb.add_box((0, 0, z_top + ROOF_THICK / 2),
               (w + 0.08, d + 0.08, ROOF_THICK), mat)
    if ctx.p.roof_type == "flat_parapet":
        t = 0.18
        for sy in (-1, 1):
            mb.add_box((0, sy * d / 2, z_top + ROOF_THICK + PARAPET_H / 2),
                       (w + 2 * t, t, PARAPET_H), ctx.pier_mat)
        for sx in (-1, 1):
            mb.add_box((sx * w / 2, 0, z_top + ROOF_THICK + PARAPET_H / 2),
                       (t, d, PARAPET_H), ctx.pier_mat)


def _roof_sloped(mb, ctx: Ctx, w: float, d: float, z_top: float,
                 pitch: float) -> None:
    """Single-pitched roof (warehouse)."""
    mat = _roof_material(ctx)
    rise = d * max(0.04, min(0.2, pitch))
    hw, hd = w / 2 + 0.10, d / 2 + 0.10
    mb.add_outward_face([(-hw, -hd, z_top), (hw, -hd, z_top),
                         (hw, hd, z_top + rise), (-hw, hd, z_top + rise)],
                        mat, (0, 0, 1))
    for s in (1, -1):
        mb.add_outward_face([(s * w / 2, -d / 2, z_top),
                             (s * w / 2, d / 2, z_top + rise),
                             (s * w / 2, d / 2, z_top),
                             (s * w / 2, -d / 2, z_top)],
                            ctx.pier_mat, (s, 0, 0))
    mb.add_box((0, -hd + 0.05, z_top - 0.06), (w + 0.3, 0.1, 0.24), mat)


def _roof_gable(mb, ctx: Ctx, w: float, d: float, z_top: float,
                pitch: float) -> None:
    """Two slopes + gable end walls; ridge runs along X."""
    mat = _roof_material(ctx)
    pitch = max(0.25, min(0.85, pitch))
    rise = (d / 2) * pitch
    hw = w / 2 + 0.35
    hd = d / 2 + 0.35
    z_ridge = z_top + rise
    # front slope: from south eave to the ridge
    mb.add_outward_face([(-hw, -hd, z_top), (hw, -hd, z_top),
                         (hw, 0, z_ridge), (-hw, 0, z_ridge)],
                        mat, (0, -2, 1))
    mb.add_outward_face([(-hw, hd, z_top), (hw, hd, z_top),
                         (hw, 0, z_ridge), (-hw, 0, z_ridge)],
                        mat, (0, 2, 1))
    for s in (1, -1):
        mb.add_outward_face([(s * hw, -d / 2 - 0.2, z_top),
                             (s * hw, d / 2 + 0.2, z_top),
                             (s * hw, 0, z_ridge)],
                            ctx.pier_mat, (s, 0, 0))
    mb.add_box((0, 0, z_ridge + 0.02), (w + 0.7, 0.18, 0.10), mat)


def _roof_hip(mb, ctx: Ctx, w: float, d: float, z_top: float,
              pitch: float) -> None:
    """Hip roof: front/back trapezoids + side triangles meeting the ridge."""
    mat = _roof_material(ctx)
    pitch = max(0.3, min(0.9, pitch))
    rise = (d / 2) * pitch * 0.7
    hw = w / 2 + 0.30
    hd = d / 2 + 0.30
    z_ridge = z_top + rise
    lr = w * 0.4
    mb.add_outward_face([(-hw, -hd, z_top), (hw, -hd, z_top),
                         (lr / 2, 0, z_ridge), (-lr / 2, 0, z_ridge)],
                        mat, (0, -2, 1))
    mb.add_outward_face([(-hw, hd, z_top), (hw, hd, z_top),
                         (lr / 2, 0, z_ridge), (-lr / 2, 0, z_ridge)],
                        mat, (0, 2, 1))
    mb.add_outward_face([(hw, -hd, z_top), (hw, hd, z_top),
                         (lr / 2, 0, z_ridge)], mat, (2, 0, 1))
    mb.add_outward_face([(-hw, -hd, z_top), (-hw, hd, z_top),
                         (-lr / 2, 0, z_ridge)], mat, (-2, 0, 1))


def _roof_terrace(mb, ctx: Ctx, w: float, d: float, z_top: float) -> None:
    """Rooftop terrace: railing ring + planters."""
    t, ph = 0.07, 1.05
    mat = "steel_frame"
    for s in (1, -1):
        mb.add_box((0, s * (d / 2 + 0.08), z_top + ROOF_THICK + ph / 2),
                   (w + 0.2, t, ph), mat)
        mb.add_box((s * (w / 2 + 0.08), 0, z_top + ROOF_THICK + ph / 2),
                   (t, d + 0.2, ph), mat)
    for i in range(3):
        pu = (i - 1) * w * 0.28
        mb.add_box((pu, -d * 0.3, z_top + ROOF_THICK + 0.25),
                   (0.8, 0.6, 0.5), "concrete")


def _roof_extras(mb, ctx: Ctx, w: float, d: float, z_top: float) -> None:
    """HVAC units, vents, water tank, stair bulkhead, antenna (level 3)."""
    if not ctx.l3:
        return
    seg = ctx.q["cyl"]
    extras_factor = ctx.q["roof_extras"]
    n_hvac = max(0, int(ctx.rng.uniform(1, 4) * extras_factor))
    for _ in range(n_hvac):
        bx = ctx.rng.uniform(-w / 2 + 1.2, w / 2 - 1.2)
        by = ctx.rng.uniform(-d / 2 + 1.2, d / 2 - 1.2)
        size = ctx.rng.uniform(1.1, 1.9)
        unit_h = ctx.rng.uniform(0.7, 1.1)
        mb.add_box((bx, by, z_top + ROOF_THICK + unit_h / 2),
                   (size, size * 0.8, unit_h), "dark_metal")
        mb.add_cylinder((bx + size * 0.15, by, z_top + ROOF_THICK + unit_h
                         + 0.12), size * 0.28, 0.24, seg, "grime_metal")
    if extras_factor > 0.3 and w * d > 40 and chance(ctx.rng, 0.6):
        pipe_y = ctx.rng.uniform(-d / 4, d / 4)
        mb.add_cylinder((-w * 0.2, pipe_y, z_top + ROOF_THICK + 0.45), 0.22,
                        w * 0.45, seg, "grime_metal", axis='X')
    if extras_factor >= 0.8:
        bx = -w / 2 + min(w, d) / 3
        by = d * 0.20
        bh = 2.3
        mb.add_box((bx, by, z_top + ROOF_THICK + bh / 2), (2.0, 2.2, bh),
                   ctx.pier_mat)
        mb.add_box((bx, by, z_top + ROOF_THICK + bh + 0.08), (2.1, 2.3, 0.16),
                   "concrete")
        mb.add_box((bx + 1.02, by, z_top + ROOF_THICK + 1.0), (0.04, 0.9, 1.9),
                   "dark_metal")
    if ctx.style in ("industrial_warehouse", "concrete_apartment",
                     "mixed_use_urban") and extras_factor > 0.5:
        tx = w / 2 - max(w, d) / 4
        ty = d / 2 - max(w, d) / 4
        tank_r = 1.1
        mb.add_box((tx, ty, z_top + ROOF_THICK + 0.15), (tank_r * 2.2,
                   tank_r * 2.2, tank_r * 0.28), "dark_concrete")
        mb.add_box((tx, ty, z_top + ROOF_THICK + 2.1), (tank_r * 2.0,
                   tank_r * 2.0, tank_r * 0.8), "painted_metal")
        mb.add_cylinder((tx, ty, z_top + ROOF_THICK + 1.3), tank_r, 2.4, seg,
                        "painted_metal")
        for sx, sy in ((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)):
            mb.add_box((tx + sx, ty + sy, z_top + 0.5 + ROOF_THICK),
                       (0.1, 0.1, 1.0), "steel_frame")
    n_vents = max(0, int(ctx.p.roof_extras * extras_factor * 0.4))
    for _ in range(n_vents):
        vx = ctx.rng.uniform(-w / 2 + 1.5, w / 2 - 1.5)
        vy = ctx.rng.uniform(-d / 2 + 1.5, d / 2 - 1.5)
        mb.add_cylinder((vx, vy, z_top + ROOF_THICK + 0.25), 0.14, 0.5, seg,
                        "grime_metal")
    if ctx.style in ("glass_office_tower", "modern_highrise") \
            and chance(ctx.rng, 0.5):
        ah = ctx.rng.uniform(2.5, 5.5)
        mb.add_cylinder((0, 0, z_top + ROOF_THICK + ah / 2), 0.08, ah, 6,
                        "steel_frame", cap_bottom=False)
        for k in (-1, 1):
            mb.add_box((0, 0, z_top + ROOF_THICK + ah * 0.75 + k * 0.4),
                       (1.4, 0.05, 0.05), "steel_frame")


def _crown_lighting(mb, ctx: Ctx, w: float, d: float, z_top: float) -> None:
    """Architectural crown lighting: emissive parapet band + corner strips."""
    band_h = 0.28
    t = 0.12
    z = z_top + ROOF_THICK
    mat = "crown_light"
    # emissive band recessed into the parapet top, all four sides
    mb.add_box((0, d / 2 + 0.02, z + PARAPET_H * 0.55), (w + 2 * t, 0.05,
               band_h * 0.5), mat)
    mb.add_box((0, -d / 2 - 0.02, z + PARAPET_H * 0.55), (w + 2 * t, 0.05,
               band_h * 0.5), mat)
    mb.add_box((w / 2 + 0.02, 0, z + PARAPET_H * 0.55), (0.05, d + 2 * t,
               band_h * 0.5), mat)
    mb.add_box((-w / 2 - 0.02, 0, z + PARAPET_H * 0.55), (0.05, d + 2 * t,
               band_h * 0.5), mat)
    # corner light columns rising slightly above the parapet
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        mb.add_box((sx * (w / 2 + 0.04), sy * (d / 2 + 0.04),
                    z + PARAPET_H * 0.7), (0.09, 0.09, PARAPET_H * 1.3), mat)


# ---------------------------------------------------------------------------
# podium, corner columns, segment assembly
# ---------------------------------------------------------------------------

def _foundation(mb, ctx: Ctx, w: float, d: float) -> None:
    """Foundation plinth: a visible base frame around the ground floor so
    buildings never appear to float or lack their bottom course."""
    ph = 0.24
    t = 0.14
    mat = "concrete" if ctx.style not in ("industrial_warehouse",) \
        else "dark_concrete"
    mb.add_box((0, d / 2 + t / 2 - 0.02, ph / 2), (w + 2 * t, t + 0.04, ph),
               mat)
    mb.add_box((0, -d / 2 - t / 2 + 0.02, ph / 2), (w + 2 * t, t + 0.04, ph),
               mat)
    mb.add_box((w / 2 + t / 2 - 0.02, 0, ph / 2), (t + 0.04, d + 2 * t, ph),
               mat)
    mb.add_box((-w / 2 - t / 2 + 0.02, 0, ph / 2), (t + 0.04, d + 2 * t, ph),
               mat)


def _entrance_steps(mb, ctx: Ctx, wall: Wall, u_center: float,
                    depth: float = 0.75) -> None:
    """Two entrance steps in front of a door so the entrance is complete."""
    w = 1.6
    for step_i, (dz, dd) in enumerate(((0.08, depth), (0.16, depth * 0.7))):
        _wall_box(mb, wall, u_center, dz / 2 + 0.001, w, dz + 0.002, dd,
                  "concrete", depth_center=dd / 2)


def _corner_columns(mb, ctx: Ctx, w: float, d: float, z0: float, z1: float,
                    mat: Optional[str] = None) -> None:
    mat = mat or ctx.pier_mat
    t = 0.34
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        mb.add_box((sx * (w / 2 - t / 2), sy * (d / 2 - t / 2), (z0 + z1) / 2),
                   (t, t, z1 - z0), mat)


def _seg_walls(w: float, d: float, z0: float) -> List[Wall]:
    return [
        Wall((-w / 2, -d / 2, z0), (1, 0, 0), (0, -1, 0), w),    # front (-Y)
        Wall((w / 2, d / 2, z0), (-1, 0, 0), (0, 1, 0), w),      # back  (+Y)
        Wall((-w / 2, d / 2, z0), (0, -1, 0), (-1, 0, 0), d),    # left  (-X)
        Wall((w / 2, -d / 2, z0), (0, 1, 0), (1, 0, 0), d),      # right (+X)
    ]


def _build_podium(mb, ctx: Ctx, podium_n: int, z_stop: float) -> None:
    """Podium levels (retail-style base) around the tower."""
    p = ctx.p
    w = ctx.width * _podium_scale(ctx)
    d = ctx.depth * _podium_scale(ctx)
    each_h = z_stop / max(1, podium_n)
    zf = 0.0
    for f in range(podium_n):
        z0, z1 = zf, zf + each_h
        for wi, wall in enumerate(_seg_walls(w, d, z0)):
            if f == 0 and p.ground_floor == "garage":
                _garage_band(mb, ctx, wall, z0, z1, True)
            elif f == 0:
                _storefront_band(mb, ctx, wall, z0, z1)
            else:
                _floor_band(mb, ctx, wall, z0, z1,
                            "window" if wi % 2 else "strip")
        zf = z1
    mb.add_box((0, 0, z_stop - ROOF_THICK / 2),
               (w + 0.1, d + 0.1, ROOF_THICK), "concrete")
    # parapet ring around the podium roof
    t = 0.18
    for sy in (-1, 1):
        mb.add_box((0, sy * d / 2, z_stop + PARAPET_H / 2),
                   (w + 2 * t, t, PARAPET_H), "concrete")
    for sx in (-1, 1):
        mb.add_box((sx * w / 2, 0, z_stop + PARAPET_H / 2), (t, d, PARAPET_H),
                   "concrete")


def _build_segment(mb, ctx: Ctx, first_floor: int, n_floors: int,
                   scale: float, stage=None) -> None:
    """Walls (and balconies) for one setback segment of the tower."""
    p = ctx.p
    w, d = ctx.width * scale, ctx.depth * scale
    for k in range(n_floors):
        idx = first_floor + k
        z0, z1 = ctx.floor_base(idx), ctx.floor_top(idx)
        if stage is not None:
            stage(f"floor_{idx:02d}")
        for wi, wall in enumerate(_seg_walls(w, d, z0)):
            if idx == 0:
                _ground_floor(mb, ctx, wall, z0, z1, front=(wi == 0))
            else:
                band = "ribbon" if p.window_type == "ribbon" else "window"
                _floor_band(mb, ctx, wall, z0, z1, band)
            build_balconies(mb, ctx, wall, idx)
    top_z = ctx.floor_top(first_floor + n_floors - 1)
    if p.columns and ctx.style in ("industrial_warehouse",
                                   "glass_office_tower", "modern_highrise",
                                   "contemporary_commercial"):
        _corner_columns(mb, ctx, w, d, ctx.floor_base(first_floor), top_z)


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------

def build_building(params: GenerationParams,
                   parts_mode: bool = False) -> Tuple[MeshBuilder, Dict]:
    """Construct the building geometry.

    With ``parts_mode`` returns a PartRouter whose named parts
    (foundation / podium / floor_N / roof / equipment / signage) can be
    instantiated as separate objects for the construction animation.
    Otherwise returns a single MeshBuilder as before.
    """
    ctx = Ctx(params)
    mb = PartRouter() if parts_mode else MeshBuilder()

    def stage(name: str) -> None:
        if parts_mode:
            mb.current = name

    podium_n = _podium_floors(ctx)
    stage("foundation")
    _foundation(mb, ctx, ctx.width, ctx.depth)
    if podium_n:
        stage("podium")
        _build_podium(mb, ctx, podium_n, ctx.floor_base(podium_n))

    for (first, count, scale) in _ctx_segments(ctx):
        if count <= 0:
            continue
        _build_segment(mb, ctx, first, count, scale, stage)

    top_scale = _ctx_segments(ctx)[-1][2] if _ctx_segments(ctx) else 1.0
    top_z = ctx.total_h()
    w = ctx.width * top_scale
    d = ctx.depth * top_scale
    rtype = params.roof_type
    stage("roof")
    if rtype == "gable":
        _roof_gable(mb, ctx, w, d, top_z,
                    ctx.profile.get("roof_pitch", 0.5))
    elif rtype == "hip":
        _roof_hip(mb, ctx, w, d, top_z,
                  ctx.profile.get("roof_pitch", 0.55))
    elif rtype == "sloped":
        _roof_sloped(mb, ctx, w, d, top_z,
                     ctx.profile.get("roof_pitch", 0.08))
    else:
        _roof_flat(mb, ctx, w, d, top_z)
        if rtype == "terrace":
            _roof_terrace(mb, ctx, w, d, top_z)
        elif params.floors >= 2:
            stage("equipment")
            _roof_extras(mb, ctx, w, d, top_z)
        if ctx.crown_lighting and ctx.style in (
                "glass_curtain_tower", "modern_office_skyscraper",
                "contemporary_residential_tower", "mixed_use_tower",
                "futuristic_tower", "modern_highrise"):
            stage("equipment")
            _crown_lighting(mb, ctx, w, d, top_z)

    info = {
        "width": round(ctx.width, 3),
        "depth": round(ctx.depth, 3),
        "height": round(top_z, 3),
        "style": ctx.style,
        "podium": podium_n,
        "h_ground": round(ctx.h_ground, 3),
        "business_category": ctx.business_category,
        "business_name": ctx.business_name,
        "has_signage": bool(ctx.profile.get("signage")) and ctx.l2,
        "sign_material": _sign_material(ctx) if (
            ctx.profile.get("signage") and ctx.l2) else "",
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


def apply_signage_text(obj, params: GenerationParams, info: Dict) -> bool:
    """Convert the business name into real text geometry on the sign board.

    Returns True when a sign was added.  The text is centred on the front
    facade sign band, extruded, given a contrasting shared material and
    joined into the building mesh.
    """
    import bpy
    import mathutils

    name = (info.get("business_name") or "").strip()
    if not name or not info.get("has_signage"):
        return False
    sign_w = min(info["width"] * 0.55, 6.0)
    text_h = min(0.5, sign_w * 1.55 / max(3, len(name)))
    z = info.get("h_ground", info["height"] / params.floors) + 0.42

    curve = bpy.data.curves.new("CFSignText", type='FONT')
    curve.body = name
    curve.size = text_h
    curve.align_x = 'CENTER'
    curve.extrude = 0.015
    text_obj = bpy.data.objects.new("CFSignText", curve)
    bpy.context.scene.collection.objects.link(text_obj)
    # front facade faces -Y: rotate the XY-plane text upright, face -Y
    text_obj.rotation_euler = (math.pi / 2, 0.0, 0.0)
    text_obj.location = (0.0, -info["depth"] / 2 - 0.09, z)
    bpy.context.view_layer.update()

    # readable contrast: emissive cream text works on any sign colour
    from ..core import materials as matlib
    text_obj.data.materials.append(matlib.get_material("sign_text"))

    # convert to mesh and join into the building
    deps = bpy.context.evaluated_depsgraph_get()
    text_mesh = bpy.data.meshes.new_from_object(
        text_obj.evaluated_get(deps))
    text_mesh_obj = bpy.data.objects.new("CFSignTextMesh", text_mesh)
    bpy.context.scene.collection.objects.link(text_mesh_obj)
    text_mesh_obj.location = text_obj.location
    text_mesh_obj.rotation_euler = text_obj.rotation_euler
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action='DESELECT')
    text_mesh_obj.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    obj["cityforge_business"] = name
    return True


def estimate_polys(params: GenerationParams) -> int:
    """Cheap upper-bound estimate so batch operations can pre-filter."""
    ctx = Ctx(params)
    windows = 0
    for (first, count, scale) in _ctx_segments(ctx):
        if count <= 0:
            continue
        per_long = len(_openings_for_width(ctx.width * scale, ctx))
        per_short = len(_openings_for_width(ctx.depth * scale, ctx))
        windows += (per_long * 2 + per_short * 2) * count
    base = params.floors * 60 + windows * 30
    if _podium_floors(ctx):
        base += _podium_floors(ctx) * 200
    return int(base)
