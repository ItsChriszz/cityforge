# SPDX-License-Identifier: GPL-3.0-or-later
"""Low-poly vehicle generator.

Classes: sedan, hatchback, suv, pickup, van, delivery_truck, bus, taxi,
sports_car.  Colours come from the params (or a seeded random look) and flow
into shared tinted material variants via `key#hex` tokens.  Orientation:
length along X, front toward +X.  Ground origin, 1 unit = 1 metre.
"""

from __future__ import annotations

from typing import Dict, Tuple

from ..core.params import GenerationParams
from ..core.randomization import chance, make_rng
from ..utils.geometry import MeshBuilder

__all__ = ["build_asset"]

# plausible car body colours (seeded random look)
_RANDOM_BODY = [
    (0.85, 0.85, 0.88), (0.10, 0.10, 0.12), (0.60, 0.02, 0.02),
    (0.05, 0.25, 0.55), (0.92, 0.92, 0.90), (0.20, 0.42, 0.20),
    (0.55, 0.55, 0.58), (0.80, 0.45, 0.05), (0.35, 0.36, 0.40),
]


def _hex(color) -> str:
    return "%02x%02x%02x" % tuple(int(max(0.0, min(1.0, c)) * 255)
                                  for c in color[:3])


def _look_tokens(params: GenerationParams, rng) -> Dict[str, str]:
    """Resolve body/roof/wheel/window material tokens from params."""
    p = params
    body_rgb = p.vehicle_color_body
    if p.vehicle_class == "taxi":
        body = "taxi_yellow"
    elif p.vehicle_random_look:
        body_rgb = rng.choice(_RANDOM_BODY)
        body = f"car_paint#{_hex(body_rgb)}"
    else:
        body = f"car_paint#{_hex(p.vehicle_color_body)}"
    if p.vehicle_random_look:
        roof_rgb = rng.choice([(0.08, 0.08, 0.09), (0.9, 0.9, 0.92),
                               body_rgb[:3]])
        roof = f"painted_metal#{_hex(roof_rgb)}"
    else:
        roof = f"painted_metal#{_hex(p.vehicle_color_roof)}"
    wheel = f"rubber#{_hex(p.vehicle_color_wheel)}"
    # vehicle windows are opaque tinted glass (no transmission): they read
    # correctly on a low-poly asset with no interior
    tint = max(0.0, min(1.0, p.window_tint))
    glass_v = 0.16 * (1.0 - tint) + 0.03
    window = f"vehicle_glass#{_hex((glass_v, glass_v * 1.05, glass_v * 1.2))}"
    return {"body": body, "roof": roof, "wheel": wheel, "window": window}


def build_asset(params: GenerationParams) -> Tuple[MeshBuilder, Dict]:
    rng = make_rng(params.seed, "vehicle")
    mb = MeshBuilder()
    tokens = _look_tokens(params, rng)
    wheel_seg = {"low": 8, "medium": 10, "high": 12}.get(params.detail_level, 8)
    cls = params.vehicle_class
    if params.asset_type in ("BICYCLE", "MOTORCYCLE"):
        cls = params.asset_type.lower()
    length = params.vehicle_length
    width = params.vehicle_width
    body_color = tokens["body"]
    roof_color = tokens["roof"]
    window_mat = tokens["window"]
    wheel_mat = tokens["wheel"]
    detail = params.detail_level != "low"

    if cls == "bus":
        body_h, ground = 2.9, 0.45
        mb.add_box((0, 0, ground + body_h / 2), (length, width, body_h),
                   body_color)
        for s in (-1, 1):
            mb.add_plate((0, s * (width / 2 + 0.002),
                          ground + body_h * 0.62),
                         (length * 0.86, 0.02, body_h * 0.3), window_mat,
                         (0, s, 0))
        mb.add_plate((length / 2 + 0.001, 0, ground + body_h * 0.62),
                     (width * 0.8, 0.02, body_h * 0.42), window_mat, (1, 0, 0))
        wheels = [(-length / 2 + 0.9, 1), (-length / 2 + 0.9, -1),
                  (length / 2 - 0.9, 1), (length / 2 - 0.9, -1)]
        wheel_r = 0.5
    elif cls == "delivery_truck":
        body_h, ground = 2.4, 0.55
        cargo_len = length * 0.62
        cab_len = length - cargo_len
        mb.add_box((length / 2 - cab_len / 2, 0, ground + body_h / 2),
                   (cab_len, width, body_h), body_color)
        mb.add_box((-length / 2 + cargo_len / 2, 0,
                    ground + (body_h + 0.35) / 2),
                   (cargo_len, width * 1.01, body_h + 0.35), "white_concrete")
        mb.add_plate((-length / 2 + 0.02, 0, ground + body_h * 0.75),
                     (0.02, width * 0.95, body_h * 0.55), window_mat,
                     (-1, 0, 0))
        wheels = [(length / 2 - cab_len * 0.45, 1),
                  (length / 2 - cab_len * 0.45, -1),
                  (-length / 2 + cargo_len * 0.28, 1),
                  (-length / 2 + cargo_len * 0.28, -1),
                  (-length / 2 + cargo_len * 0.78, 1),
                  (-length / 2 + cargo_len * 0.78, -1)]
        wheel_r = 0.55
    elif cls == "van":
        body_h, ground = 2.1, 0.4
        mb.add_box((0, 0, ground + body_h / 2), (length, width, body_h),
                   body_color)
        mb.add_box((0, 0, ground + body_h + 0.03), (length * 0.9, width * 0.98,
                   0.06), roof_color)
        mb.add_plate((length / 2 + 0.001, 0, ground + body_h * 0.7),
                     (width * 0.86, 0.02, body_h * 0.4), window_mat, (1, 0, 0))
        for s in (-1, 1):
            mb.add_plate((0, s * (width / 2 + 0.002),
                          ground + body_h * 0.72),
                         (length * 0.5, 0.02, body_h * 0.34), window_mat,
                         (0, s, 0))
        wheels = [(length * 0.32, 1), (length * 0.32, -1),
                  (-length * 0.32, 1), (-length * 0.32, -1)]
        wheel_r = 0.42
    elif cls == "suv":
        body_h, ground = 0.95, 0.5
        cabin_h = 0.72
        mb.add_box((0, 0, ground + body_h / 2), (length, width, body_h),
                   body_color)
        cab_len = length * 0.62
        cab_z = ground + body_h + cabin_h / 2
        mb.add_box((length * 0.02, 0, cab_z), (cab_len, width * 0.92,
                   cabin_h), body_color)
        mb.add_box((length * 0.02, 0, cab_z + 0.1),
                   (cab_len * 0.96, width * 0.9, cabin_h * 0.62), window_mat)
        mb.add_box((0, 0, ground + body_h + cabin_h + 0.05),
                   (cab_len * 0.96, width * 0.9, 0.05), roof_color)
        # roof rails
        for s in (-1, 1):
            mb.add_box((length * 0.02, s * width * 0.42,
                        ground + body_h + cabin_h + 0.14),
                       (cab_len * 0.9, 0.05, 0.07), roof_color)
        wheels = [(length * 0.33, 1), (length * 0.33, -1),
                  (-length * 0.33, 1), (-length * 0.33, -1)]
        wheel_r = 0.44
    elif cls == "pickup":
        body_h, ground = 0.85, 0.52
        mb.add_box((length * 0.14, 0, ground + body_h / 2),
                   (length * 0.72, width, body_h), body_color)
        cab_len = length * 0.34
        cabin_h = 0.7
        cab_z = ground + body_h + cabin_h / 2
        mb.add_box((length * 0.26, 0, cab_z), (cab_len, width * 0.94,
                   cabin_h), body_color)
        mb.add_box((length * 0.26, 0, cab_z + 0.08),
                   (cab_len * 0.94, width * 0.9, cabin_h * 0.55), window_mat)
        # bed walls (open box) between cab and tail
        bed_front = length * 0.5 - cab_len / 2
        wall_h = 0.5
        for s in (-1, 1):
            mb.add_box((length * 0.14, s * (width / 2 - 0.05),
                        ground + body_h + wall_h / 2),
                       (length * 0.72 - 0.1, 0.06, wall_h), body_color)
        mb.add_box((-length * 0.5 + 0.05, 0, ground + body_h + wall_h / 2),
                   (0.06, width - 0.1, wall_h), body_color)
        mb.add_box((length * 0.02, 0, ground + body_h + 0.02),
                   (length * 0.72 - 0.1, width - 0.12, 0.04), "dark_metal")
        wheels = [(length * 0.30, 1), (length * 0.30, -1),
                  (-length * 0.28, 1), (-length * 0.28, -1)]
        wheel_r = 0.46
    elif cls == "sports_car":
        body_h, ground = 0.48, 0.3
        cabin_h = 0.46
        mb.add_box((0, 0, ground + body_h / 2), (length, width, body_h),
                   body_color)
        cab_len = length * 0.34
        mb.add_box((-length * 0.06, 0, ground + body_h + cabin_h / 2 - 0.02),
                   (cab_len, width * 0.82, cabin_h), body_color)
        mb.add_box((-length * 0.06, 0, ground + body_h + cabin_h / 2),
                   (cab_len * 0.9, width * 0.8, cabin_h * 0.7), window_mat)
        # spoiler
        if detail:
            mb.add_box((-length / 2 + 0.1, 0, ground + body_h + 0.22),
                       (0.24, width * 0.86, 0.05), roof_color)
            for s in (-1, 1):
                mb.add_box((-length / 2 + 0.16, s * width * 0.36,
                            ground + body_h + 0.11),
                           (0.08, 0.05, 0.22), roof_color)
        wheels = [(length * 0.32, 1), (length * 0.32, -1),
                  (-length * 0.32, 1), (-length * 0.32, -1)]
        wheel_r = 0.33
    if cls in ("bicycle", "BICYCLE"):
        _bicycle(mb, rng, params, wheel_seg)
    elif cls in ("motorcycle", "MOTORCYCLE"):
        _motorcycle(mb, rng, params, wheel_seg)
    else:  # sedan / hatchback / taxi
        body_h = 0.62 if cls != "hatchback" else 0.75
        ground = 0.36
        cabin_h = 0.62
        cabin_len = length * (0.52 if cls == "hatchback" else 0.42)
        mb.add_box((0, 0, ground + body_h / 2), (length, width, body_h),
                   body_color)
        cab_z = ground + body_h + cabin_h / 2
        mb.add_box((length * (0.10 if cls == "hatchback" else 0.04), 0, cab_z),
                   (cabin_len, width * 0.86, cabin_h), body_color)
        mb.add_box((length * (0.10 if cls == "hatchback" else 0.04), 0,
                    cab_z + 0.06),
                   (cabin_len * 0.96, width * 0.87, cabin_h * 0.5), window_mat)
        mb.add_box((length * (0.10 if cls == "hatchback" else 0.04), 0,
                    ground + body_h + cabin_h + 0.03),
                   (cabin_len * 0.94, width * 0.86, 0.05), roof_color)
        wheels = [(length * 0.31, 1), (length * 0.31, -1),
                  (-length * 0.31, 1), (-length * 0.31, -1)]
        wheel_r = 0.34

    # lights (front white, rear red) — cars & trucks only
    if detail and cls not in ("bicycle", "motorcycle"):
        mb.add_plate((length / 2 + 0.006, width * 0.3,
                      ground + body_h * 0.72),
                     (0.01, 0.3, 0.1), "holo_white", (1, 0, 0))
        mb.add_plate((length / 2 + 0.006, -width * 0.3,
                      ground + body_h * 0.72),
                     (0.01, 0.3, 0.1), "holo_white", (1, 0, 0))
        mb.add_plate((-length / 2 - 0.004, width * 0.3,
                      ground + body_h * 0.72),
                     (0.01, 0.3, 0.1), "sign", (-1, 0, 0))
        mb.add_plate((-length / 2 - 0.004, -width * 0.3,
                      ground + body_h * 0.72),
                     (0.01, 0.3, 0.1), "sign", (-1, 0, 0))
    if cls == "taxi" and detail:
        mb.add_box((0, 0, ground + body_h + cabin_h + 0.14),
                   (0.4, 0.24, 0.12), "taxi_yellow")

    # wheels (tyre + recessed rim) — cars & trucks; bikes build their own
    if cls not in ("bicycle", "motorcycle"):
        for wx, side in wheels:
            mb.add_cylinder((wx, side * (width / 2 - 0.12), wheel_r), wheel_r,
                            0.24, wheel_seg, wheel_mat, axis='Y',
                            top_radius=wheel_r)
            mb.add_cylinder((wx, side * (width / 2 - 0.20), wheel_r),
                            wheel_r * 0.5, 0.1, max(6, wheel_seg - 2),
                            "metal", axis='Y')

    scale = max(0.5, min(2.0, params.vehicle_scale or 1.0))
    info = {
        "style": cls,
        "faces": mb.face_count,
        "polys_estimated": mb.poly_count(),
        "scale": scale,
    }
    return mb, info


def _bicycle(mb, rng, params, seg):
    """Simple bicycle: two wheels + frame tubes + handlebars + seat."""
    wheel_r = 0.34
    frame_mat = "car_paint#" + _hex((0.85, 0.35, 0.10))
    for wx in (-0.53, 0.53):
        mb.add_cylinder((wx, 0, wheel_r), wheel_r, 0.03, seg, "rubber",
                        axis='Y')
        mb.add_cylinder((wx, 0, wheel_r), wheel_r * 0.86, 0.02, seg,
                        "steel_frame", axis='Y')
    mb.add_box((0, 0, 0.5), (1.0, 0.04, 0.04), frame_mat)
    mb.add_box((0.27, 0, 0.62), (0.55, 0.04, 0.04), frame_mat, rot_z=0.5)
    mb.add_box((-0.27, 0, 0.62), (0.55, 0.04, 0.04), frame_mat, rot_z=-0.5)
    mb.add_box((0.53, 0, 0.95), (0.1, 0.44, 0.04), "steel_frame")
    mb.add_box((-0.45, 0, 0.92), (0.24, 0.07, 0.05), "dark_metal")


def _motorcycle(mb, rng, params, seg):
    wheel_r = 0.32
    body = "car_paint#" + _hex(rng.choice(_RANDOM_BODY))
    for wx in (-0.7, 0.7):
        mb.add_cylinder((wx, 0, wheel_r), wheel_r, 0.12, seg, "rubber",
                        axis='Y')
    mb.add_box((0, 0, 0.62), (1.1, 0.34, 0.42), body)
    mb.add_box((-0.25, 0, 0.92), (0.5, 0.26, 0.3), "dark_metal")
    mb.add_box((0.72, 0, 0.95), (0.5, 0.5, 0.05), "steel_frame")
    mb.add_box((0.74, 0, 0.7), (0.1, 0.4, 0.04), "dark_metal")
