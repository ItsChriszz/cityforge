# SPDX-License-Identifier: GPL-3.0-or-later
"""Road & sidewalk generator with road classification.

Classes: highway, single_lane, two_lane, four_lane, one_way.  The class
drives lane count/width, medians (painted / raised / planted), highway
barriers instead of sidewalks, and one-way arrow markings.  All variants
are real geometry — nothing is material-only.

Conventions: the road runs along +X centred on the origin; curvature bends
the centreline toward +Y.  1 unit = 1 metre.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ..core.params import GenerationParams
from ..core.randomization import make_rng
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]

SEG_LEN = 3.0


def resolve_class(params: GenerationParams) -> Dict:
    """Normalise class-dependent road parameters."""
    p = params
    lane_w = max(2.5, min(5.0, p.lane_width or 3.5))
    lanes = max(1, int(p.lane_count or 2))
    info = {
        "lanes": lanes, "lane_w": lane_w,
        "median": bool(p.median_enabled), "median_w": max(0.4, p.median_width),
        "median_style": p.median_style or "raised",
        "sidewalk": bool(p.sidewalk_enabled), "sidewalk_w": p.sidewalk_width,
        "barrier_only": False, "one_way": p.road_direction != "two_way",
        "dir_sign": 1.0 if p.road_direction != "one_way_negative" else -1.0,
    }
    if p.road_class == "highway":
        info.update(lanes=max(4, lanes), lane_w=3.7, median=True,
                    sidewalk=False, barrier_only=True, crosswalks=False)
    elif p.road_class == "single_lane":
        info.update(lanes=1)
    elif p.road_class == "four_lane":
        info.update(lanes=4, median=True)
    elif p.road_class == "one_way":
        info.update(one_way=True, lanes=max(2, lanes))
    # carriageway width: honour an explicit road_width, else derive
    car_total = p.road_width if (p.road_width and p.road_width != 9.0) \
        else lanes * lane_w + 0.8
    if info["median"]:
        car_total += info["median_w"] + 0.4
    info["car_total"] = max(3.0, car_total)
    return info


def _centerline(segment_count: int, length: float, curvature_deg: float
                ) -> List[Tuple[float, float]]:
    n = max(2, int(segment_count))
    if curvature_deg <= 0.01:
        return [(-length / 2 + length * i / n, 0.0) for i in range(n + 1)]
    radius = length / math.radians(curvature_deg)
    pts: List[Tuple[float, float]] = []
    for i in range(n + 1):
        t = -length / 2 + length * i / n
        angle = t / radius
        pts.append((t, radius * (1.0 - math.cos(angle))))
    return pts


def _normal_of(p0, p1) -> Tuple[float, float]:
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = math.hypot(dx, dy) or 1.0
    return (-dy / ln, dx / ln)


def _profile(width: float, sidewalk: float, curb_h: float, grass: bool,
             median: Dict, class_info: Dict) -> Tuple[List, List[str]]:
    """Cross-section (offset, z) points centre→right→left + material per quad.

    Vertical faces (curbs, median walls, barriers) are two points sharing an
    offset, so every sweep quad is unique (validate-safe).
    """
    car_total = width
    car = car_total / 2
    csw = car + sidewalk if class_info["sidewalk"] else car + 0.4
    prof: List[Tuple[float, float]] = []

    if class_info["barrier_only"]:
        # highway: grass shoulder + concrete barrier instead of sidewalk
        prof += [(car + 2.0, -0.03), (car + 2.0, 0.02), (car + 0.5, 0.02),
                 (car + 0.5, curb_h + 0.28), (car + 0.2, curb_h + 0.30),
                 (car, curb_h - 0.01)]
    elif class_info["sidewalk"]:
        csw2 = car + sidewalk + 2.0
        if grass:
            prof += [(csw2, -0.03), (csw2, 0.02), (csw, 0.02)]
        prof += [(csw, curb_h), (car, curb_h), (car, curb_h - 0.01)]
    else:  # bare shoulders
        prof += [(car + 1.0, -0.03), (car + 1.0, 0.02), (car, 0.02),
                 (car, curb_h), (car, curb_h - 0.01)]

    if class_info["median"]:
        mw = class_info["median_w"] / 2
        rise = curb_h + 0.14 if class_info["median_style"] != "painted" \
            else curb_h + 0.005
        prof += [
            (mw, curb_h + 0.03),          # carriageway meets the median
            (mw, rise),                   # median curb (vertical, right)
            (-mw, rise),                  # median top
            (-mw, curb_h + 0.03),         # median curb (vertical, left)
        ]
    else:
        prof += [(0.0, curb_h + 0.03)]    # crown

    # mirrored tail (skip duplicating the centre point)
    tail: List[Tuple[float, float]] = []
    for (off, z) in reversed(prof):
        if off == 0.0:
            continue
        tail.append((-off, z))
    all_pts = prof + tail

    # material per quad
    n = len(all_pts)
    mats: List[str] = []
    med_mat = {"raised": "concrete", "planted": "grass",
               "painted": "asphalt"}.get(class_info["median_style"],
                                         "concrete")
    sidewalk = class_info["sidewalk_w"] if class_info["sidewalk"] else 0.0
    grass_on = class_info["sidewalk"] and sidewalk > 0
    for i in range(n - 1):
        o0, z0 = all_pts[i]
        o1, z1 = all_pts[i + 1]
        vertical = abs(o0 - o1) < 1e-6
        if vertical:
            mats.append("curb")
            continue
        am = (abs(o0) + abs(o1)) / 2
        if class_info["median"] and abs(am) < class_info["median_w"] / 2:
            mats.append(med_mat)
            continue
        if class_info["barrier_only"]:
            mats.append("asphalt" if am < car else "grass")
            continue
        if class_info["sidewalk"]:
            if am < car - 0.01:
                mats.append("asphalt")            # carriageway
            elif grass_on and am > car + sidewalk + 0.05:
                mats.append("grass")              # outer verge
            else:
                mats.append("sidewalk")
            continue
        mats.append("asphalt" if am < car + 0.01 else "grass")
    return all_pts, mats


def _emit(mb, prof_a, prof_b, base_a, base_b, normal, mats
          ) -> None:
    """Sweep two (offset, z) profiles between base_a and base_b."""
    if len(prof_a) != len(prof_b):
        return

    def world(base, off_z):
        return (base[0] + normal[0] * off_z[0],
                base[1] + normal[1] * off_z[0], off_z[1])

    for i in range(len(prof_a) - 1):
        pa0 = world(base_a, prof_a[i])
        pa1 = world(base_a, prof_a[i + 1])
        pb0 = world(base_b, prof_b[i])
        pb1 = world(base_b, prof_b[i + 1])
        vertical = abs(prof_a[i][0] - prof_a[i + 1][0]) < 1e-6
        if vertical:
            s = 1.0 if (prof_a[i][0] + prof_a[i + 1][0]) >= 0 else -1.0
            hint = (normal[0] * s, normal[1] * s, 0.0)
        else:
            hint = (0.0, 0.0, 1.0)
        mb.add_outward_face([pa0, pa1, pb1, pb0],
                            mats[i] if i < len(mats) else "asphalt", hint)


# the road surface height (crown) for the current profile
MARKING_LIFT = 0.005


def _surface_z(params: GenerationParams) -> float:
    return max(0.05, min(0.35, params.curb_height)) + 0.03


def _plate(mb, x0, y0, dx, dy, off, w, lnz, mat, z=None):
    if z is None:
        z = 0.185
    nx, ny = -dy, dx
    pts = [
        (x0 + nx * off, y0 + ny * off, z),
        (x0 + nx * off + dy * w, y0 + ny * off - dx * w, z),
        (x0 + dx * lnz + nx * off + dy * w,
         y0 + dy * lnz + ny * off - dx * w, z),
        (x0 + dx * lnz + nx * off, y0 + dy * lnz + ny * off, z),
    ]
    mb.add_outward_face(pts, mat, (0, 0, 1))


def _arrow(mb, x, y, dx, dy, direction, z=None):
    """One-way direction arrow painted on the lane (shaft + head blades)."""
    if z is None:
        z = 0.185
    s = direction
    _plate(mb, x, y, dx, dy, 0.0, 0.14, 1.4 * s, "road_marking", z=z)
    hx, hy = x + dx * 0.7 * s, y + dy * 0.7 * s
    for side in (-1, 1):
        nx, ny = -dy * side, dx * side
        mb.add_outward_face([
            (hx - dx * 0.7 * s + nx * 0.02, hy - dy * 0.7 * s + ny * 0.02, z),
            (hx - dx * 0.7 * s + nx * 0.34, hy - dy * 0.7 * s + ny * 0.34, z),
            (hx + dx * 0.55 * s, hy + dy * 0.55 * s, z),
            (hx + dx * 0.7 * s, hy + dy * 0.7 * s, z)],
            "road_marking", (0, 0, 1))


def _markings(mb, params: GenerationParams, centerline, class_info: Dict,
              median_on: bool) -> None:
    style = params.road_markings
    if style == "none":
        return
    car_total = class_info["car_total"]
    lanes = class_info["lanes"]
    lane_w = class_info["lane_w"]
    half = car_total / 2
    # markings sit ON the carriageway surface (crown) + a small lift
    mz = _surface_z(params) + MARKING_LIFT

    if median_on and class_info["median_style"] == "painted":
        # double yellow center lines flanking the painted median
        for side in (-1, 1):
            i = 0
            while i < len(centerline) - 1:
                x0, y0 = centerline[i]
                x1, y1 = centerline[i + 1]
                seg = math.hypot(x1 - x0, y1 - y0) or 1.0
                dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
                _plate(mb, x0, y0, dx, dy,
                       side * (class_info["median_w"] / 2 + 0.15), 0.10, seg,
                       "road_marking_yellow", z=mz)
                i += 1

    if not class_info["one_way"] and lanes >= 2 and not median_on:
        # dashed centre line
        for i in range(len(centerline) - 1):
            x0, y0 = centerline[i]
            x1, y1 = centerline[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0) or 1.0
            dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
            if style == "simple":
                _plate(mb, x0, y0, dx, dy, 0.0, 0.10, seg, "road_marking",
                       z=mz)
                continue
            f = 0.0
            while f < seg:
                lnz = min(3.0, seg - f)
                _plate(mb, x0 + dx * f, y0 + dy * f, dx, dy, 0.0, 0.12, lnz,
                       "road_marking", z=mz)
                f += 5.0

    if class_info["one_way"]:
        # lane dividers between same-direction lanes + direction arrows
        per_lane_line = [(lanes - 1 - k) * lane_w - half + lane_w
                         for k in range(lanes - 1)]
        for off in per_lane_line:
            for i in range(len(centerline) - 1):
                x0, y0 = centerline[i]
                x1, y1 = centerline[i + 1]
                seg = math.hypot(x1 - x0, y1 - y0) or 1.0
                dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
                _plate(mb, x0, y0, dx, dy, off, 0.10, seg, "road_marking",
                       z=mz)
        road_len = (abs(centerline[0][0]) + abs(centerline[-1][0])) / 2
        # arrows every 12 m on each lane centre, kept inside the endpoints
        lane_centres = [half - (k + 0.5) * lane_w for k in range(lanes)]
        travelled = 0.0
        for i in range(len(centerline) - 1):
            x0, y0 = centerline[i]
            x1, y1 = centerline[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0) or 1.0
            dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
            f = 0.0
            while f < seg:
                if (travelled + f) % 12.0 < SEG_LEN \
                        and abs(x0 + dx * f) < road_len / 2 - 4.0:
                    for lc in lane_centres:
                        _arrow(mb, x0 + dx * f, y0 + dy * f, dx, dy,
                               class_info["dir_sign"], z=mz)
                    f += 6.0
                else:
                    f += SEG_LEN
            travelled += seg

    # edge lines
    for side_mid in (-1, 1):
        for i in range(len(centerline) - 1):
            x0, y0 = centerline[i]
            x1, y1 = centerline[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0) or 1.0
            dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
            off = side_mid * (half - 0.18)
            _plate(mb, x0, y0, dx, dy, off, 0.10, seg, "road_marking", z=mz)

    if params.crosswalks and not class_info.get("barrier_only"):
        for end in (0, len(centerline) - 1):
            cx_, cy_ = centerline[end]
            inward = 1.0 if end == 0 else -1.0
            walk_zone = car_total / 2 - 0.1
            for i in range(7):
                y = cy_ - walk_zone + (i + 0.5) * walk_zone * 2 / 7
                x0 = cx_
                x1 = cx_ + inward * 1.8
                mb.add_outward_face([
                    (x0, y - 0.22, mz), (x1, y - 0.22, mz),
                    (x1, y + 0.22, mz), (x0, y + 0.22, mz)],
                    "road_marking", (0, 0, 1))


def _build_sidewalk(mb, params: GenerationParams) -> None:
    """Sidewalk-only section without the carriageway."""
    length = params.road_length
    w = max(1.0, params.sidewalk_width)
    d = 0.14
    mb.add_box((0, 0, d / 2), (length, w, d), "sidewalk")
    mb.add_box((0, -w / 2 + 0.15, d / 2 + 0.02), (length, 0.3, d + 0.04),
               "curb")
    n_joints = max(1, int(length / 1.5))
    for i in range(n_joints):
        x = -length / 2 + (i + 0.5) * (length / n_joints)
        mb.add_plate((x, 0, d + 0.001), (0.02, w - 0.3, 0.002), "concrete",
                     (0, 0, 1))


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "road")
    mb = MeshBuilder()
    if params.asset_type == "SIDEWALK":
        _build_sidewalk(mb, params)
        info = {
            "style": "sidewalk", "length": params.road_length,
            "faces": mb.face_count, "polys_estimated": mb.poly_count(),
        }
        return mb, info
    if params.asset_type == "CROSSWALK":
        _crosswalk_piece(mb, params)
        info = {
            "style": "crosswalk", "length": 7.0,
            "faces": mb.face_count, "polys_estimated": mb.poly_count(),
        }
        return mb, info
    if params.asset_type == "INTERSECTION":
        _intersection_piece(mb, params)
        info = {
            "style": "intersection", "faces": mb.face_count,
            "polys_estimated": mb.poly_count(),
        }
        return mb, info
    if params.asset_type == "ROUNDABOUT":
        _roundabout_piece(mb, params)
        info = {
            "style": "roundabout", "faces": mb.face_count,
            "polys_estimated": mb.poly_count(),
        }
        return mb, info

    cls_info = resolve_class(params)
    length = params.road_length
    curb_h = max(0.05, min(0.35, params.curb_height))
    seg_count = max(4, int(length / SEG_LEN))
    profile, mats = _profile(
        cls_info["car_total"],
        params.sidewalk_width if cls_info["sidewalk"] else 0.0,
        curb_h, params.grass_strip, cls_info, cls_info)

    centerline = _centerline(seg_count, length, params.road_curvature)
    for i in range(len(centerline) - 1):
        p0, p1 = centerline[i], centerline[i + 1]
        nx, ny = _normal_of(p0, p1)
        _emit(mb, profile, profile, (p0[0], p0[1]), (p1[0], p1[1]),
              (nx, ny), mats)

    _markings(mb, params, centerline, cls_info, cls_info["median"])
    if cls_info.get("barrier_only"):
        _highway_furniture(mb, params, centerline, cls_info)
    info = {
        "style": params.road_class, "length": length,
        "lanes": cls_info["lanes"], "median": cls_info["median"],
        "one_way": cls_info["one_way"],
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
    }
    return mb, info


def _highway_furniture(mb, params: GenerationParams, centerline,
                       cls_info: Dict) -> None:
    """Guardrails, roadside lighting and an overhead gantry sign."""
    car = cls_info["car_total"] / 2 + 0.55
    n = len(centerline)
    # guardrails: posts every 8 m + twin rail bands following the curve
    for i in range(0, n - 1, 2):
        p0, p1 = centerline[i], centerline[min(i + 2, n - 1)]
        nx, ny = _normal_of(p0, p1)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        seg_ln = math.hypot(dx, dy) or 1.0
        ang = math.atan2(dy, dx)
        for side in (-1, 1):
            off = car * side
            px, py = p0[0] + nx * off, p0[1] + ny * off
            mb.add_box((px, py, 0.35), (0.12, 0.12, 0.7), "grime_metal",
                       rot_z=ang)
            # rail band between this post and the next
            mx = (p0[0] + p1[0]) / 2 + nx * off
            my = (p0[1] + p1[1]) / 2 + ny * off
            mb.add_box((mx, my, 0.62), (seg_ln + 0.2, 0.06, 0.3),
                       "grime_metal", rot_z=ang)
    # roadside lighting every 30 m, alternating sides
    step = max(2, int(30.0 / SEG_LEN * 2))
    for i in range(0, n - 1, step):
        p0 = centerline[i]
        nx, ny = _normal_of(p0, centerline[min(i + 1, n - 1)])
        side = 1 if (i // step) % 2 == 0 else -1
        px, py = p0[0] + nx * (car + 1.4) * side, \
            p0[1] + ny * (car + 1.4) * side
        mb.add_cylinder((px, py, 4.5), 0.11, 9.0, 8, "grime_metal")
        mb.add_box((px - nx * side * 1.1, py - ny * side * 1.1, 8.9),
                   (2.2, 0.12, 0.12), "grime_metal",
                   rot_z=math.atan2(ny, nx))
        mb.add_box((px - nx * side * 2.0, py - ny * side * 2.0, 8.55),
                   (0.9, 0.34, 0.14), "dark_metal",
                   rot_z=math.atan2(ny, nx))
    # overhead gantry sign at one third of the road
    gi = max(1, n // 3)
    p0, p1 = centerline[gi], centerline[min(gi + 1, n - 1)]
    nx, ny = _normal_of(p0, p1)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for side in (-1, 1):
        px, py = p0[0] + nx * (car + 0.9) * side, \
            p0[1] + ny * (car + 0.9) * side
        mb.add_cylinder((px, py, 3.4), 0.14, 6.8, 8, "steel_frame")
    mx = p0[0]
    my = p0[1]
    mb.add_box((mx, my, 6.4), (1.4, cls_info["car_total"] + 1.2, 1.3),
               "sign_highway_green", rot_z=ang - math.pi / 2)
    mb.add_box((mx, my, 5.75), (1.0, cls_info["car_total"] + 0.9, 0.12),
               "holo_white", rot_z=ang - math.pi / 2)


def _intersection_piece(mb, params: GenerationParams) -> None:
    """Four-way intersection: two crossing carriageways + corner sidewalks."""
    cls_info = resolve_class(params)
    total = cls_info["car_total"] + 2 * (params.sidewalk_width if
                                         cls_info["sidewalk"] else 0)
    curb_h = max(0.05, min(0.35, params.curb_height))
    # full pad (asphalt) + 4 corner sidewalk aprons
    mb.add_box((0, 0, 0.02), (total, total, 0.08), "asphalt")
    sw = params.sidewalk_width if cls_info["sidewalk"] else 0
    if sw > 0.05:
        car = cls_info["car_total"] / 2
        cs = (total - cls_info["car_total"]) / 2  # apron depth
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx = sx * (car + cs / 2)
                cy = sy * (car + cs / 2)
                mb.add_box((cx, cy, 0.02 + curb_h * 0.5),
                           (cs, cs, curb_h), "sidewalk")
    # stop-line bars on each approach + zebra crossings
    mz = _surface_z(params) + MARKING_LIFT
    car = cls_info["car_total"] / 2
    for approach in range(4):
        # crosswalk bars across each approach
        for i in range(6):
            off = -car + 0.3 + (i + 0.5) * (cls_info["car_total"] - 0.6) / 6
            if approach == 0:
                mb.add_outward_face([(off - 0.22, car + 0.4, mz + 0.002),
                                     (off + 0.22, car + 0.4, mz + 0.002),
                                     (off + 0.22, car + 1.8, mz + 0.002),
                                     (off - 0.22, car + 1.8, mz + 0.002)],
                                    "road_marking", (0, 0, 1))
            elif approach == 1:
                mb.add_outward_face([(off - 0.22, -car - 1.8, mz + 0.002),
                                     (off + 0.22, -car - 1.8, mz + 0.002),
                                     (off + 0.22, -car - 0.4, mz + 0.002),
                                     (off - 0.22, -car - 0.4, mz + 0.002)],
                                    "road_marking", (0, 0, 1))
            elif approach == 2:
                mb.add_outward_face([(car + 0.4, off - 0.22, mz + 0.002),
                                     (car + 0.4, off + 0.22, mz + 0.002),
                                     (car + 1.8, off + 0.22, mz + 0.002),
                                     (car + 1.8, off - 0.22, mz + 0.002)],
                                    "road_marking", (0, 0, 1))
            else:
                mb.add_outward_face([(-car - 1.8, off - 0.22, mz + 0.002),
                                     (-car - 1.8, off + 0.22, mz + 0.002),
                                     (-car - 0.4, off + 0.22, mz + 0.002),
                                     (-car - 0.4, off - 0.22, mz + 0.002)],
                                    "road_marking", (0, 0, 1))


def _roundabout_piece(mb, params: GenerationParams) -> None:
    """Roundabout: ring carriageway + planted centre island + 4 approaches."""
    cls_info = resolve_class(params)
    island_r = max(3.0, params.median_width * 2.0 + 2.0)
    ring_w = cls_info["car_total"]
    outer_r = island_r + ring_w + 0.6
    seg_n = 40
    mz = _surface_z(params) + MARKING_LIFT
    # ring road (annulus)
    for i in range(seg_n):
        a0 = 2 * math.pi * i / seg_n
        a1 = 2 * math.pi * (i + 1) / seg_n
        r0 = island_r + 0.5
        r1 = outer_r
        mb.add_outward_face([
            (r0 * math.cos(a0), r0 * math.sin(a0), 0.02),
            (r1 * math.cos(a0), r1 * math.sin(a0), 0.02),
            (r1 * math.cos(a1), r1 * math.sin(a1), 0.02),
            (r0 * math.cos(a1), r0 * math.sin(a1), 0.02)],
            "asphalt", (0, 0, 1))
        # ring markings (dashed circle)
        if i % 3 == 0:
            rm = (r0 + r1) / 2
            mb.add_outward_face([
                ((rm - 0.06) * math.cos(a0), (rm - 0.06) * math.sin(a0), 0.025),
                ((rm + 0.06) * math.cos(a0), (rm + 0.06) * math.sin(a0), 0.025),
                ((rm + 0.06) * math.cos(a1), (rm + 0.06) * math.sin(a1), 0.025),
                ((rm - 0.06) * math.cos(a1), (rm - 0.06) * math.sin(a1), 0.025)],
                "road_marking", (0, 0, 1))
    # centre island (raised, planted)
    mb.add_cylinder((0, 0, 0.09), island_r, 0.18, seg_n, "grass")
    mb.add_cylinder((0, 0, 0.0), island_r + 0.3, 0.2, seg_n, "curb")
    # 4 approach stubs (short road pieces meeting the ring)
    sw = params.sidewalk_width if cls_info["sidewalk"] else 0
    for k, ang in enumerate((0.0, math.pi / 2, math.pi, -math.pi / 2)):
        approach_len = 8.0
        cx = math.cos(ang) * (outer_r + approach_len / 2 - 0.5)
        cy = math.sin(ang) * (outer_r + approach_len / 2 - 0.5)
        road_w = cls_info["car_total"]
        mb.add_box((cx, cy, 0.02),
                   (approach_len if k % 2 == 0 else road_w,
                    road_w if k % 2 == 0 else approach_len, 0.08), "asphalt")


def _crosswalk_piece(mb, params: GenerationParams) -> None:
    """Small modular crosswalk road piece: standard surface + zebra only."""
    length = 7.0
    cls_info = resolve_class(params)
    curb_h = max(0.05, min(0.35, params.curb_height))
    profile, mats = _profile(cls_info["car_total"],
                             params.sidewalk_width if cls_info["sidewalk"]
                             else 0.0, curb_h, params.grass_strip,
                             cls_info, cls_info)
    centerline = _centerline(2, length, 0.0)
    for i in range(len(centerline) - 1):
        p0, p1 = centerline[i], centerline[i + 1]
        nx, ny = _normal_of(p0, p1)
        _emit(mb, profile, profile, (p0[0], p0[1]), (p1[0], p1[1]),
              (nx, ny), mats)
    # zebra bars centred on the piece
    mz = _surface_z(params) + MARKING_LIFT
    zone = cls_info["car_total"] / 2 - 0.1
    for i in range(7):
        y = -zone + (i + 0.5) * zone * 2 / 7
        mb.add_outward_face([
            (-1.1, y - 0.24, mz + 0.002), (1.1, y - 0.24, mz + 0.002),
            (1.1, y + 0.24, mz + 0.002), (-1.1, y + 0.24, mz + 0.002)],
            "road_marking", (0, 0, 1))
