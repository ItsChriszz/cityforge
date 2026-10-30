# SPDX-License-Identifier: GPL-3.0-or-later
"""Low-level mesh construction helpers.

`MeshBuilder` accumulates polygons (with per-face material names) without
touching bpy per-vertex, then materialises everything into a single
`bpy.types.Mesh` in one pass.  This is dramatically faster than creating one
object per widget and keeps each generated asset as one draw call for Unity.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import bpy
from mathutils import Vector

Vec = Tuple[float, float, float]


def _rot_z(p: Vec, angle: float) -> Vec:
    if not angle:
        return p
    c, s = math.cos(angle), math.sin(angle)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])


def _circle(center: Vec, rx: float, ry: float, segments: int) -> List[Vec]:
    return [
        (center[0] + rx * math.cos(i / segments * 2 * math.pi),
         center[1] + ry * math.sin(i / segments * 2 * math.pi),
         center[2])
        for i in range(segments)
    ]


class MeshBuilder:
    """Collective geometry builder; positions are welded on finish()."""

    def __init__(self) -> None:
        self._faces: List[Tuple[List[Vec], str, bool]] = []

    # ---------------------------------------------------------------- nuance
    @property
    def face_count(self) -> int:
        return len(self._faces)

    def poly_count(self) -> int:
        """Approximate triangle count of the accumulated geometry."""
        return sum(max(2, len(pts) - 2) for pts, _m, _s in self._faces)

    def material_names(self) -> List[str]:
        return sorted({mat for (_pts, mat, _s) in self._faces})

    # ------------------------------------------------------------- polygons
    def add_face(self, points, material: str, smooth: bool = False) -> None:
        """Add a polygon; winding is taken as given (callers are responsible)."""
        pts = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
        if len(pts) >= 3:
            self._faces.append((pts, material, smooth))

    def add_outward_face(self, points, material: str, outward, smooth: bool = False) -> None:
        """Add polygon, flipping winding so its normal points toward `outward`."""
        pts = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
        if len(pts) < 3:
            return
        if len(outward) == 2:
            outward = (outward[0], outward[1], 0.0)
        a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
        n = (b - a).cross(c - a)
        if n.dot(Vector(outward)) < 0:
            pts.reverse()
        self._faces.append((pts, material, smooth))

    # ------------------------------------------------------------ primitives
    def add_box(self, center: Vec, size: Vec, material: str, rot_z: float = 0.0) -> None:
        """Cuboid (axis-aligned or rotated around Z), outward faces included."""
        cx, cy, cz = center
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        raw: List[Tuple[List[Vec], Vec]] = [
            ([(cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
              (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)], (0, 0, 1)),
            ([(cx - hx, cy - hy, cz - hz), (cx - hx, cy + hy, cz - hz),
              (cx + hx, cy + hy, cz - hz), (cx + hx, cy - hy, cz - hz)], (0, 0, -1)),
            ([(cx + hx, cy - hy, cz - hz), (cx + hx, cy + hy, cz - hz),
              (cx + hx, cy + hy, cz + hz), (cx + hx, cy - hy, cz + hz)], (1, 0, 0)),
            ([(cx - hx, cy - hy, cz - hz), (cx - hx, cy - hy, cz + hz),
              (cx - hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz - hz)], (-1, 0, 0)),
            ([(cx - hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz + hz),
              (cx + hx, cy + hy, cz + hz), (cx + hx, cy + hy, cz - hz)], (0, 1, 0)),
            ([(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
              (cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz)], (0, -1, 0)),
        ]
        if rot_z:
            def rz(p: Vec) -> Vec:
                q = _rot_z((p[0] - cx, p[1] - cy, 0.0), rot_z)
                return (cx + q[0], cy + q[1], p[2])

            raw = [([rz(p) for p in pts], _rot_z(out, rot_z))
                   for pts, out in raw]
        for pts, outward in raw:
            self.add_outward_face(pts, material, outward)

    def add_plate(self, center: Vec, size: Vec, material: str, normal: Vec,
                  rot_z: float = 0.0) -> None:
        """Zero-thickness rectangle facing `normal` (signs, markings, panes)."""
        axis = max(range(3), key=lambda i: abs(normal[i]))
        cx, cy, cz = center
        sx, sy, sz = size
        if axis == 0:
            pts = [(cx, cy - sy / 2, cz - sz / 2), (cx, cy - sy / 2, cz + sz / 2),
                   (cx, cy + sy / 2, cz + sz / 2), (cx, cy + sy / 2, cz - sz / 2)]
        elif axis == 1:
            pts = [(cx - sx / 2, cy, cz - sz / 2), (cx + sx / 2, cy, cz - sz / 2),
                   (cx + sx / 2, cy, cz + sz / 2), (cx - sx / 2, cy, cz + sz / 2)]
        else:
            pts = [(cx - sx / 2, cy - sy / 2, cz), (cx + sx / 2, cy - sy / 2, cz),
                   (cx + sx / 2, cy + sy / 2, cz), (cx - sx / 2, cy + sy / 2, cz)]
        if rot_z:
            def rpz(p: Vec) -> Vec:
                q = _rot_z((p[0] - cx, p[1] - cy, 0.0), rot_z)
                return (cx + q[0], cy + q[1], p[2])
            pts = [rpz(p) for p in pts]
            normal = _rot_z(normal, rot_z)
        self.add_outward_face(pts, material, normal)

    @staticmethod
    def _axis_rot(p: Vec, axis: str) -> Vec:
        if axis == 'Y':      # lay the tube along Y (rotate -90° about X)
            return (p[0], -p[2], p[1])
        if axis == 'X':      # lay the tube along X (rotate +90° about Z)
            return (p[1], p[0], p[2])
        return p

    _AXIS_VECTORS = {
        'Z': (0.0, 0.0, 1.0), 'Y': (0.0, 1.0, 0.0), 'X': (1.0, 0.0, 0.0)}

    def add_cylinder(self, center: Vec, radius: float, height: float,
                     segments: int, material: str, top_radius: Optional[float] = None,
                     axis: str = 'Z', cap_top: bool = True, cap_bottom: bool = True,
                     rim_scale: float = 1.0) -> None:
        """Cylindrical cone along X, Y or Z; centre is at mid-height."""
        tr = top_radius if top_radius is not None else radius
        segments = max(3, int(segments))
        ex, ey, ez = self._AXIS_VECTORS[axis]
        base = (center[0] - ex * height / 2,
                center[1] - ey * height / 2,
                center[2] - ez * height / 2)
        # unit tangents in the circular plane perpendicular to the axis
        if axis == 'Z':
            t1, t2 = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
        elif axis == 'Y':
            t1, t2 = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
        else:
            t1, t2 = (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)

        def ring(z_frac: float, r: float) -> List[Vec]:
            c = (base[0] + ex * height * z_frac,
                 base[1] + ey * height * z_frac,
                 base[2] + ez * height * z_frac)
            return [(c[0] + t1[0] * r * math.cos(a) + t2[0] * r * math.sin(a),
                     c[1] + t1[1] * r * math.cos(a) + t2[1] * r * math.sin(a),
                     c[2] + t1[2] * r * math.cos(a) + t2[2] * r * math.sin(a))
                    for a in [2 * math.pi * i / segments
                              for i in range(segments)]]

        bottom, top = ring(0.0, radius), ring(1.0, tr)
        for i in range(segments):
            j = (i + 1) % segments
            am = 2 * math.pi * (i + 0.5) / segments
            radial = (t1[0] * math.cos(am) + t2[0] * math.sin(am),
                      t1[1] * math.cos(am) + t2[1] * math.sin(am),
                      t1[2] * math.cos(am) + t2[2] * math.sin(am))
            self.add_outward_face([bottom[i], bottom[j], top[j], top[i]],
                                  material, radial)
        if cap_bottom:
            self.add_face(list(reversed(bottom)), material)
        if cap_top:
            self.add_face(top, material)

    def add_sphere(self, center: Vec, radius: float, segments: int, rings: int,
                   material: str, squash: float = 1.0) -> None:
        """Lat/long sphere, optionally squashed along Z (tree canopies)."""
        segments, rings = max(4, segments), max(2, rings)
        for ri in range(rings):
            v0, v1 = math.pi * ri / rings, math.pi * (ri + 1) / rings
            for si in range(segments):
                a0, a1 = 2 * math.pi * si / segments, 2 * math.pi * (si + 1) / segments

                def pt(theta: float, phi: float) -> Vec:
                    return (center[0] + radius * math.sin(phi) * math.cos(theta),
                            center[1] + radius * math.sin(phi) * math.sin(theta),
                            center[2] + radius * math.cos(phi) * squash)

                quad = [pt(a0, v1), pt(a1, v1), pt(a1, v0), pt(a0, v0)]
                mt, mp = (a0 + a1) / 2, (v0 + v1) / 2
                self.add_outward_face(quad, material, (
                    math.sin(mp) * math.cos(mt),
                    math.sin(mp) * math.sin(mt),
                    math.cos(mp)))

    def add_loft(self, profile_bottom, profile_top, material: str,
                 smooth: bool = False) -> None:
        """Loft between two n-point closed profiles (same vertex count)."""
        n = len(profile_bottom)
        for i in range(n):
            j = (i + 1) % n
            self.add_outward_face(
                [profile_bottom[i], profile_bottom[j], profile_top[j], profile_top[i]],
                material, (profile_top[i][0] - profile_bottom[i][0],
                           profile_top[i][1] - profile_bottom[i][1], 0.4), smooth)

    # --------------------------------------------------------- materialised
    def finish(self, name: str) -> Tuple[bpy.types.Mesh, List[str]]:
        """Create the Blender mesh with real shared materials attached.

        Material tokens may carry a colour suffix ``key#rrggbb``; the suffix
        selects a shared tinted variant.  Returns (mesh, material_order).
        """
        from ..core import materials as matlib

        ordered_mats = self.material_names()
        mesh = bpy.data.meshes.new(name)
        verts: List[Vector] = []
        faces: List[List[int]] = []
        face_mat_idx: List[int] = []
        face_smooth: List[bool] = []
        lookup: Dict[Tuple[float, float, float], int] = {}
        centroids: List[Tuple[float, float, float]] = []
        mat_index = {m: i for i, m in enumerate(ordered_mats)}
        for points, material, smooth in self._faces:
            indices: List[int] = []
            for p in points:
                key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
                idx = lookup.get(key)
                if idx is None:
                    idx = len(verts)
                    lookup[key] = idx
                    verts.append(Vector(key))
                # collapse repeated points (e.g. sphere poles) into triangles
                # so mesh.validate() never has to delete the face and shift
                # polygon order (which would misalign material indices)
                if not indices or indices[-1] != idx:
                    indices.append(idx)
            if len(indices) >= 3 and indices[0] == indices[-1]:
                indices.pop()
            if len(indices) < 3:
                continue
            acc = [0.0, 0.0, 0.0]
            for idx in indices:
                v = verts[idx]
                acc[0] += v.x
                acc[1] += v.y
                acc[2] += v.z
            n = len(indices)
            centroids.append((acc[0] / n, acc[1] / n, acc[2] / n))
            faces.append(indices)
            face_mat_idx.append(mat_index[material])
            face_smooth.append(smooth)

        mesh.from_pydata(verts, [], faces)
        # validate may delete/repair elements and reorder polygons, so any
        # index-based assignment must happen after this point
        mesh.validate(verbose=False)

        if len(mesh.polygons) == len(face_mat_idx):
            # order preserved 1:1
            mesh.polygons.foreach_set("material_index", face_mat_idx)
            for poly, smooth in zip(mesh.polygons, face_smooth):
                poly.use_smooth = smooth
        else:
            # map surviving polygons back to source faces by centroid
            cent_map: Dict[Tuple[float, float, float], int] = {}
            for i, c in enumerate(centroids):
                cent_map[(round(c[0], 4), round(c[1], 4), round(c[2], 4))] = i
            for poly in mesh.polygons:
                c = poly.center
                src = cent_map.get((round(c.x, 4), round(c.y, 4),
                                    round(c.z, 4)))
                if src is not None:
                    poly.material_index = face_mat_idx[src]
                    poly.use_smooth = face_smooth[src]
        for mi, token in enumerate(ordered_mats):
            key, _, hexcol = token.partition('#')
            if hexcol:
                color = (int(hexcol[0:2], 16) / 255.0,
                         int(hexcol[2:4], 16) / 255.0,
                         int(hexcol[4:6], 16) / 255.0, 1.0)
                mesh.materials.append(matlib.get_material(key, color=color))
            else:
                mesh.materials.append(matlib.get_material(key))
        mesh.update()
        return mesh, ordered_mats
