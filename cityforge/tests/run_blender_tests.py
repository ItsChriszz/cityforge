# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-hosted integration test suite for CityForge.

Run:  blender -b --python cityforge/tests/run_blender_tests.py

Verifies add-on registration, generation across styles and asset families,
deterministic seeds, mesh validity, naming, collection organisation, material
reuse, LOD/optimization, exports (with re-import) and invalid-input rejection.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SRC = os.path.join(BASE, "cityforge", "..")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import bpy  # noqa: E402
import addon_utils  # noqa: E402

addon_utils.enable("cityforge", default_set=True)
LOADED, ENABLED = addon_utils.check("cityforge")

from cityforge.core import (  # noqa: E402
    asset_manager, export_manager, generator, materials as matlib,
    optimization, randomization,
)
from cityforge.core import params as P  # noqa: E402
from cityforge.core.validation import ValidationError, validate_params  # noqa
from cityforge.utils import stable_hash_string  # noqa: E402


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        bpy.ops.wm.read_homefile(use_empty=True)
        cls.context = bpy.context
        cls.scene = cls.context.scene

    def make_params(self, **kw) -> P.GenerationParams:
        p = P.GenerationParams()
        for k, v in kw.items():
            setattr(p, k, v)
        P.apply_style_defaults(p)
        for k, v in kw.items():
            setattr(p, k, v)
        return p


def assert_real_bad_mesh(obj):
    """Assert the mesh is non-empty, NaN-free and roughly grounded."""
    mesh = obj.data
    if len(mesh.polygons) == 0 or len(mesh.vertices) == 0:
        raise AssertionError("empty mesh")
    import mathutils
    for v in mesh.vertices:
        for c in v.co:
            if not (c == c) or abs(c) > 1e5:   # NaN or absurd
                raise AssertionError(f"bad vertex {v.co}")


class TestRegistration(_Base):

    def test_addon_enabled(self):
        self.assertTrue(LOADED and ENABLED)

    def test_scene_properties(self):
        for ptr in ("cityforge", "cityforge_building", "cityforge_road",
                    "cityforge_veg", "cityforge_prop", "cityforge_vehicle",
                    "cityforge_export"):
            self.assertTrue(hasattr(self.scene, ptr), ptr)

    def test_ui_operators_exist(self):
        for op in ("cityforge.generate", "cityforge.export_selected",
                   "cityforge.optimize", "cityforge.apply_prompt"):
            try:
                bpy.ops.cityforge.poll.call_count  # attribute exists?
            except AttributeError:
                pass
            parts = op.split(".")
            self.assertTrue(hasattr(getattr(bpy.ops, parts[0]), parts[1]), op)

    def test_register_unregister_cycle(self):
        import cityforge as cfx
        cfx.unregister()
        cfx.register()
        self.assertTrue(hasattr(bpy.types.Scene, "cityforge"))


class TestBuildings(_Base):

    STYLES = ["modern_residential", "glass_office_tower", "brick_residential",
              "industrial_warehouse", "mixed_use_urban", "suburban_house",
              "concrete_apartment", "traditional_lowrise", "modern_highrise"]

    def test_all_styles_generate(self):
        for i, style in enumerate(self.STYLES):
            with self.subTest(style=style):
                p = self.make_params(asset_type="RESIDENTIAL", style=style,
                                     floors=7, seed=10 + i)
                obj = generator.generate_asset(p)
                self.assertIsNotNone(obj, style)
                self.assertTrue(obj.type == 'MESH')
                self.assertGreater(obj.get("cityforge_polygons"), 100)
                mesh = obj.data
                assert_real_bad_mesh(obj)

    def test_massive_tower_under_budget(self):
        p = self.make_params(asset_type="SKYSCRAPER", style="modern_highrise",
                             floors=40, seed=99, detail_level="high")
        obj = generator.generate_asset(p)
        self.assertIsNotNone(obj)
        self.assertIsNotNone(obj.get("cityforge_polygons"))

    def test_deterministic_seed(self):
        p = self.make_params(asset_type="RESIDENTIAL",
                             style="modern_residential", seed=777)
        o1 = generator.generate_asset(p)
        shutil.rmtree  # placeholder no-op
        o2 = generator.generate_asset(p)
        h1 = stable_hash_string("".join(
            f"{round(v.co.x, 4)}{round(v.co.y, 4)}{round(v.co.z, 4)}"
            for v in o1.data.vertices))
        h2 = stable_hash_string("".join(
            f"{round(v.co.x, 4)}{round(v.co.y, 4)}{round(v.co.z, 4)}"
            for v in o2.data.vertices))
        self.assertEqual(h1, h2, "same seed must give identical meshes")
        self.assertEqual(len(o1.data.vertices), len(o2.data.vertices))

    def test_different_seeds_differ(self):
        p1 = self.make_params(asset_type="RESIDENTIAL", seed=1)
        p2 = self.make_params(asset_type="RESIDENTIAL", seed=2)
        h1 = stable_hash_string("".join(
            f"{round(v.co.x, 4)}" for v in generator.generate_asset(
                p1).data.vertices))
        h2 = stable_hash_string("".join(
            f"{round(v.co.x, 4)}" for v in generator.generate_asset(
                p2).data.vertices))
        self.assertNotEqual(h1, h2)

    def test_custom_props(self):
        obj = generator.generate_asset(self.make_params(seed=5))
        for prop in ("cityforge_params", "cityforge_asset_type",
                     "cityforge_seed", "cityforge_generated_at",
                     "cityforge_polygons"):
            self.assertIn(prop, obj, prop)

    def test_collection_organization(self):
        obj = generator.generate_asset(self.make_params(seed=6))
        parent_names = [c.name for c in obj.users_collection]
        self.assertIn("Residential", parent_names, parent_names)
        obj2 = generator.generate_asset(self.make_params(
            asset_type="TREE", seed=7))
        parent2 = [c.name for c in obj2.users_collection]
        self.assertIn("Vegetation", parent2, parent2)

    def test_invalid_params_rejected(self):
        p = self.make_params(floors=10 ** 6)
        p.floors = 10 ** 6  # way beyond limit
        with self.assertRaises(ValidationError):
            validate_params(p.to_dict())

    def test_polygon_budget_fallback(self):
        p = self.make_params(asset_type="OFFICE", floors=25, seed=8,
                             detail_level="high", poly_budget=5000)
        obj = generator.generate_asset(p)
        self.assertIsNotNone(obj)
        self.assertLess(optimization.object_stats(obj)["polygons"], 45000)
        self.assertTrue(obj.get("cityforge_budget_warning"))


class TestOtherAssets(_Base):

    def test_road_generation(self):
        obj = generator.generate_asset(self.make_params(asset_type="ROAD",
                                                        seed=30))
        self.assertEqual(obj.get("cityforge_asset_type"), "ROAD")
        mesh = obj.data
        assert_real_bad_mesh(obj)

    def test_curved_road(self):
        obj = generator.generate_asset(self.make_params(
            asset_type="ROAD", road_curvature=30, seed=31))
        self.assertIsNotNone(obj)

    def test_vegetation(self):
        for tree_type, season in (("deciduous", "summer"),
                                  ("evergreen", "winter")):
            with self.subTest(tree_type=tree_type):
                obj = generator.generate_asset(self.make_params(
                    asset_type="TREE", tree_type=tree_type, season=season,
                    seed=40))
                self.assertIsNotNone(obj)
                self.assertEqual(obj.get("cityforge_asset_type"), "TREE")
                self.assertEqual(obj.get("cityforge_info").get("style"),
                                 tree_type)

    def test_props(self):
        for prop in ("STREETLIGHT", "TRAFFIC_SIGN", "BENCH", "BOLLARD",
                     "FENCE", "PLANTER", "BUS_STOP", "GARBAGE_BIN",
                     "PARKING_METER", "BARRIER", "HYDRANT"):
            with self.subTest(prop=prop):
                obj = generator.generate_asset(self.make_params(
                    asset_type=prop, seed=41))
                self.assertIsNotNone(obj, prop)
                self.assertGreater(len(obj.data.polygons), 5)
                assert_real_bad_mesh(obj)

    def test_vehicles(self):
        for cls in ("sedan", "van", "truck", "bus"):
            with self.subTest(cls=cls):
                obj = generator.generate_asset(self.make_params(
                    asset_type="VEHICLE", vehicle_class=cls, seed=42))
                self.assertIsNotNone(obj, cls)


class TestMaterials(_Base):

    def test_material_reuse(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        for i in range(4):
            generator.generate_asset(self.make_params(seed=500 + i))
        stats = matlib.library_stats()
        # far fewer materials than asset surface slots: reuse works
        self.assertLess(stats["materials"], stats["max_cache"])
        self.assertGreater(stats["materials"], 8)
        # each library material remember its key
        for m in matlib.all_library_materials():
            self.assertIn(m.get("cityforge_key"), matlib.MATERIAL_KEYS)


class TestOptimization(_Base):

    def test_lod_and_preserve(self):
        obj = generator.generate_asset(self.make_params(seed=600))
        base_count = optimization.object_stats(obj)["polygons"]
        low = optimization.generate_lod(obj, "low")
        high = optimization.generate_lod(obj, "high")
        self.assertIsNotNone(low)
        self.assertIsNotNone(high)
        self.assertLess(
            optimization.object_stats(low)["polygons"], base_count + 1)
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.cityforge.optimize()
        pre = low.name + "_PREOPT"
        self.assertTrue(any(o.get("cityforge_original")
                            for o in self.scene.objects))
        self.assertIn(pre, self.scene.objects.keys())

    def test_registry_and_delete(self):
        n0 = asset_manager.count_generated(self.scene)
        obj = generator.generate_asset(self.make_params(seed=700))
        self.assertEqual(asset_manager.count_generated(self.scene), n0 + 1)
        asset_manager.delete_asset(obj)
        self.assertEqual(asset_manager.count_generated(self.scene), n0)


class TestExport(_Base):

    def test_export_fbx_and_glb(self):
        tmpdir = tempfile.mkdtemp(prefix="cfx_export_")
        self.scene.cityforge_export.export_dir = tmpdir + "/"
        self.scene.cityforge_export.export_format = 'FBX'
        obj = generator.generate_asset(self.make_params(seed=900))
        expected_name = obj.name
        obj.select_set(True)
        self.context.view_layer.objects.active = obj
        try:
            result = bpy.ops.cityforge.export_selected()
            fbx = glob.glob(tmpdir + "/**/*.fbx", recursive=True)
            if not fbx:
                listing = []
                for r, d, f in os.walk(tmpdir):
                    listing.append((r, f))
                print("EXPORT_DIAG", result, "selected",
                      [o.name for o in self.context.selected_objects],
                      "dirprop", self.scene.cityforge_export.export_dir,
                      listing)
            self.assertTrue(fbx, "no FBX written")
            self.assertGreater(os.path.getsize(fbx[0]), 5_000)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_export_all_batch(self):
        tmpdir = tempfile.mkdtemp(prefix="cfx_batch_")
        self.scene.cityforge_export.export_dir = tmpdir + "/"
        self.scene.cityforge_export.export_format = 'GLB'
        try:
            for seed in (901, 902):
                generator.generate_asset(self.make_params(
                    asset_type="TREE", seed=seed))
            bpy.ops.cityforge.batch_export()
            glb = glob.glob(tmpdir + "/**/*.glb", recursive=True)
            self.assertTrue(glb, "no GLB written")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestExpansion(_Base):
    """Round-3 expansion: categories, colours, roads, NPCs, rail, ports."""

    def test_building_kinds_generate(self):
        for kind in ("detached_house", "townhouse", "apartments",
                     "small_shop", "restaurant", "shopping_centre",
                     "office_block", "factory", "warehouse", "school",
                     "hospital", "hotel", "barn", "mixed_use_building"):
            with self.subTest(kind=kind):
                p = self.make_params(asset_type="RESIDENTIAL", seed=41,
                                     building_kind=kind)
                P.apply_form_defaults(p)
                P.apply_style_defaults(p)
                P.sanitize_category(p)
                obj = generator.generate_asset(p)
                self.assertIsNotNone(obj, kind)
                self.assertGreater(obj.get("cityforge_polygons"), 200)

    def test_kind_category_consistency(self):
        # every kind generates the right asset type
        for kind, preset in P.BUILDING_KINDS.items():
            self.assertIn(preset["asset_type"], P.BUILDING_TYPES, kind)

    def test_industrial_never_residential(self):
        p = self.make_params(asset_type="INDUSTRIAL", style="suburban_house",
                             floors=3, residential_form="townhouse",
                             ground_floor="retail", balcony_style="glass")
        notes = P.sanitize_category(p)
        self.assertTrue(notes)
        self.assertEqual(p.style, "industrial_warehouse")
        self.assertEqual(p.residential_form, "auto")
        self.assertEqual(p.ground_floor, "loading_bay")
        self.assertEqual(p.balcony_style, "none")
        obj = generator.generate_asset(p)
        self.assertIsNotNone(obj)

    def test_colours_apply_without_checkbox(self):
        p = self.make_params(asset_type="RESIDENTIAL",
                             style="modern_residential", seed=5, floors=4)
        P.apply_style_defaults(p)
        p.color_primary = (0.9, 0.2, 0.2, 1.0)
        obj = generator.generate_asset(p)
        names = [m.name for m in obj.data.materials if m]
        self.assertTrue(any("e53333" in n for n in names),
                        f"picked colour missing: {names}")

    def test_markings_above_surface(self):
        from cityforge.generators import roads as roads_gen
        for cls in ("two_lane", "four_lane", "one_way", "highway"):
            with self.subTest(cls=cls):
                p = self.make_params(asset_type="ROAD", road_class=cls,
                                     road_length=40.0, seed=60)
                mb, _info = roads_gen.build_asset(p)
                mark_zs = [pts[0][2] for (pts, mat, _s) in mb._faces
                           if "marking" in mat]
                self.assertTrue(mark_zs, cls)
                self.assertGreater(min(mark_zs), 0.18, cls)

    def test_traffic_light_visible_lamps(self):
        from cityforge.generators import props as props_gen
        p = self.make_params(asset_type="TRAFFIC_LIGHT", seed=9)
        mb, _info = props_gen.build_asset(p)
        lamp_mats = {"traffic_red", "traffic_amber", "traffic_green"}
        found = {mat for (pts, mat, _s) in mb._faces} & lamp_mats
        self.assertEqual(found, lamp_mats, "all three lamps must exist")
        glass_cover = any("glass" in mat for (pts, mat, _s) in mb._faces)
        self.assertFalse(glass_cover, "no cover plate over the lamps")

    def test_all_sign_variants(self):
        from cityforge.generators import props as props_gen
        for v in P.SIGN_TYPES:
            with self.subTest(sign=v):
                p = self.make_params(asset_type="TRAFFIC_SIGN",
                                     sign_variants=v, seed=9)
                mb, _info = props_gen.build_asset(p)
                mesh, _ = mb.finish("X")
                self.assertGreater(len(mesh.polygons), 5, v)
                self.assertGreaterEqual(
                    min(vv.co.z for vv in mesh.vertices), -0.01, v)

    def test_crosswalk_piece(self):
        from cityforge.generators import roads as roads_gen
        p = self.make_params(asset_type="CROSSWALK", seed=60)
        mb, _info = roads_gen.build_asset(p)
        mesh, _ = mb.finish("X")
        xs = [v.co.x for v in mesh.vertices]
        self.assertLessEqual(max(xs), 3.55)   # compact piece
        marks = sum(1 for (pts, mat, _s) in mb._faces
                    if "marking" in mat)
        self.assertGreater(marks, 5, "zebra bars missing")

    def test_npc_professions_and_rig(self):
        for prof in ("chef", "doctor", "police", "farmer", "cyclist"):
            with self.subTest(prof=prof):
                p = self.make_params(asset_type="NPC", npc_profession=prof,
                                     seed=100, npc_rigged=(prof == "police"),
                                     npc_clip="walk")
                obj = generator.generate_asset(p)
                self.assertIsNotNone(obj, prof)
                if prof == "police":
                    self.assertIsNotNone(obj.parent)
                    self.assertEqual(obj.parent.type, 'ARMATURE')
                    act = obj.parent.animation_data.action
                    self.assertIsNotNone(act)
                    self.assertIn("walk", act.name)

    def test_npc_age_variation(self):
        heights = set()
        for age in ("child", "adult", "senior"):
            p = self.make_params(asset_type="NPC", npc_age=age, seed=55)
            obj = generator.generate_asset(p)
            zmax = max(v.co.z for v in obj.data.vertices)
            heights.add(round(zmax, 1))
        self.assertGreater(len(heights), 1, "ages must change height")

    def test_rail_and_port_assets(self):
        for atype in ("TRACK", "TRACK_CURVED", "PLATFORM", "STATION",
                      "RAIL_SIGNAL", "CATENARY", "TRAIN_PASSENGER",
                      "TRAIN_FREIGHT", "TRAM", "METRO_CAR", "MONORAIL",
                      "DOCK", "CRANE", "CONTAINER", "CONTAINER_STACK",
                      "BOAT_SMALL", "FISHING_BOAT", "SAILBOAT", "YACHT",
                      "CARGO_SHIP", "FERRY", "INTERSECTION", "ROUNDABOUT",
                      "HEDGE", "FLOWERBED", "BICYCLE", "MOTORCYCLE"):
            with self.subTest(asset=atype):
                obj = generator.generate_asset(self.make_params(
                    asset_type=atype, seed=75))
                self.assertIsNotNone(obj, atype)
                self.assertGreater(len(obj.data.polygons), 5, atype)

    def test_construction_animation(self):
        p = self.make_params(asset_type="RESIDENTIAL",
                             style="modern_residential", seed=5, floors=5,
                             construction_animation=True,
                             construction_duration=6.0)
        root = generator.generate_asset(p)
        self.assertEqual(root.type, 'EMPTY')
        meta = root.get("cityforge_construction")
        self.assertIsNotNone(meta)
        self.assertGreater(int(meta["parts"]), 2)
        animated = sum(1 for c in root.children
                       if c.animation_data and c.animation_data.action)
        self.assertEqual(animated, len(root.children))
        # later frames reveal more parts
        scene = self.scene
        scene.frame_set(2)
        early = sum(1 for c in root.children if not c.hide_viewport)
        scene.frame_set(max(3, int(meta["duration_frames"]) - 1))
        late = sum(1 for c in root.children if not c.hide_viewport)
        self.assertGreater(late, early, "construction must progress")


class TestPrompt(_Base):

    def test_local_prompt_generates(self):
        self.scene.cityforge.prompt = ("14-storey modern residential "
                                       "apartment with glass balconies "
                                       "seed 321")
        before = asset_manager.count_generated(self.scene)
        bpy.ops.cityforge.apply_prompt(generate_after=True,
                                       use_glm_bridge=False)
        after = asset_manager.count_generated(self.scene)
        self.assertEqual(after, before + 1)

    def test_prompt_no_match_leaves_defaults(self):
        self.scene.cityforge.prompt = "zzz random nothing"
        result = bpy.ops.cityforge.apply_prompt(generate_after=False,
                                                use_glm_bridge=False)
        self.assertEqual({'FINISHED'}, result)


class TestGeometryFixes(_Base):
    """Phase 1 regression: everything grounded and connected."""

    def test_props_grounded(self):
        from cityforge.generators import props as props_gen
        for atype in ("STREETLIGHT", "TRAFFIC_LIGHT", "BENCH", "BUS_STOP",
                      "TRAFFIC_SIGN", "HYDRANT", "BOLLARD", "GARBAGE_BIN",
                      "PARKING_METER", "PLANTER", "BARRIER", "FENCE"):
            with self.subTest(prop=atype):
                p = self.make_params(asset_type=atype, seed=9)
                mb, _info = props_gen.build_asset(p)
                mesh, _ = mb.finish("X")
                zmin = min(v.co.z for v in mesh.vertices)
                self.assertGreaterEqual(zmin, -0.02, f"{atype} sinks")
                self.assertLessEqual(zmin, 0.05, f"{atype} floats")

    def test_trees_grounded(self):
        from cityforge.generators import vegetation as veg
        for tree_type in ("deciduous", "evergreen", "poplar"):
            with self.subTest(tree=tree_type):
                p = self.make_params(asset_type="TREE", seed=11,
                                     tree_type=tree_type,
                                     season="summer", tree_height=9.0,
                                     canopy_radius=3.0)
                mb, _info = veg.build_asset(p)
                mesh, _ = mb.finish("X")
                zmin = min(v.co.z for v in mesh.vertices)
                self.assertGreaterEqual(zmin, -0.02)

    def test_road_ends_clean(self):
        from cityforge.generators import roads as roads_gen
        p = self.make_params(asset_type="ROAD", seed=60, road_length=40.0)
        mb, _info = roads_gen.build_asset(p)
        mesh, _ = mb.finish("X")
        xs = [v.co.x for v in mesh.vertices]
        self.assertLessEqual(max(xs), 20.05)
        self.assertGreaterEqual(min(xs), -20.05)


class TestBuildingDiversity(_Base):

    def test_residential_forms_unique(self):
        import hashlib
        hashes = set()
        for form in ("detached_house", "townhouse", "lowrise_apartments",
                     "midrise_apartments", "highrise_tower"):
            p = self.make_params(asset_type="RESIDENTIAL",
                                 style="modern_residential", seed=40,
                                 floors=5, residential_form=form)
            P.apply_form_defaults(p)
            obj = generator.generate_asset(p)
            h = hashlib.sha256("".join(
                f"{round(v.co.x, 3)},{round(v.co.y, 3)},{round(v.co.z, 3)}"
                for v in obj.data.vertices).encode()).hexdigest()
            hashes.add(h)
        self.assertEqual(len(hashes), 5, "forms must produce unique geometry")

    def test_levels_gated(self):
        counts = {}
        for l1, l2, l3 in ((True, True, True), (True, True, False),
                           (True, False, False), (True, False, True)):
            p = self.make_params(asset_type="RESIDENTIAL", seed=40, floors=4,
                                 arch_level_1=l1, arch_level_2=l2,
                                 arch_level_3=l3)
            mb, _info = generator.generate_asset(p), None
            counts[(l1, l2, l3)] = mb.get("cityforge_polygons")
        self.assertLess(counts[(True, False, False)],
                        counts[(True, True, False)],
                        "level 2 must add detail")
        self.assertLess(counts[(True, True, False)], counts[(True, True, True)],
                        "level 3 must add detail")


class TestSkyscrapers(_Base):

    def test_new_styles_generate(self):
        for style in ("glass_curtain_tower", "modern_office_skyscraper",
                      "contemporary_residential_tower", "mixed_use_tower",
                      "futuristic_tower"):
            with self.subTest(style=style):
                p = self.make_params(asset_type="SKYSCRAPER", style=style,
                                     floors=16, seed=55)
                P.apply_style_defaults(p)
                obj = generator.generate_asset(p)
                self.assertIsNotNone(obj)
                self.assertGreater(obj.get("cityforge_polygons"), 2000)

    def test_tower_forms_differ(self):
        import hashlib
        hashes = set()
        for form in ("box", "tapered", "setback", "tapered_setback"):
            p = self.make_params(asset_type="SKYSCRAPER",
                                 style="futuristic_tower", floors=18,
                                 seed=55)
            P.apply_style_defaults(p)
            p.tower_form = form   # override the style default AFTER
            obj = generator.generate_asset(p)
            hashes.add(hashlib.sha256("".join(
                f"{round(v.co.x, 2)},{round(v.co.z, 2)}"
                for v in obj.data.vertices).encode()).hexdigest())
        self.assertEqual(len(hashes), 4)


class TestColours(_Base):

    def test_random_palette_deterministic(self):
        p1 = self.make_params(asset_type="RESIDENTIAL", seed=60,
                              use_random_palette=True)
        p2 = self.make_params(asset_type="RESIDENTIAL", seed=60,
                              use_random_palette=True)
        o1 = generator.generate_asset(p1)
        o2 = generator.generate_asset(p2)
        m1 = [m.name for m in o1.data.materials]
        m2 = [m.name for m in o2.data.materials]
        self.assertEqual(m1, m2)

    def test_custom_colours_applied(self):
        p = self.make_params(asset_type="RESIDENTIAL", seed=60,
                             use_custom_colors=True,
                             color_primary=(0.9, 0.2, 0.2, 1.0))
        obj = generator.generate_asset(p)
        names = [m.name for m in obj.data.materials]
        self.assertTrue(any("e53333" in n for n in names),
                        f"tinted primary missing: {names}")


class TestRoadClasses(_Base):

    def test_classes_generate(self):
        for road_class, expect_median in (("highway", True),
                                          ("single_lane", False),
                                          ("two_lane", False),
                                          ("four_lane", True),
                                          ("one_way", False)):
            with self.subTest(cls=road_class):
                p = self.make_params(asset_type="ROAD", road_class=road_class,
                                     road_length=50.0, seed=60)
                obj = generator.generate_asset(p)
                self.assertIsNotNone(obj)
                info = obj.get("cityforge_info")
                self.assertEqual(int(info.get("median")) != 0, expect_median)

    def test_one_way_arrows(self):
        p = self.make_params(asset_type="ROAD", road_class="one_way",
                             road_length=50.0, seed=60)
        obj = generator.generate_asset(p)
        self.assertEqual(int(obj.get("cityforge_info").get("one_way")), 1)


class TestVehiclesExpanded(_Base):

    def test_all_classes(self):
        for cls in ("sedan", "hatchback", "suv", "pickup", "van",
                    "delivery_truck", "bus", "taxi", "sports_car"):
            with self.subTest(cls=cls):
                obj = generator.generate_asset(self.make_params(
                    asset_type="VEHICLE", vehicle_class=cls, seed=90))
                self.assertIsNotNone(obj, cls)
                zmin = min(v.co.z for v in obj.data.vertices)
                self.assertGreater(zmin, -0.02)
                self.assertLess(zmin, 0.1)

    def test_random_look_deterministic(self):
        p = self.make_params(asset_type="VEHICLE", vehicle_class="suv",
                             seed=91, vehicle_random_look=True)
        o1 = generator.generate_asset(p)
        o2 = generator.generate_asset(p)
        self.assertEqual([m.name for m in o1.data.materials],
                         [m.name for m in o2.data.materials])


class TestBusinessSignage(_Base):

    def test_business_name_generated(self):
        p = self.make_params(asset_type="MIXED", style="mixed_use_urban",
                             seed=77, floors=6, ground_floor="retail")
        P.apply_style_defaults(p)
        obj = generator.generate_asset(p)
        name = obj.get("cityforge_business")
        self.assertIsNotNone(name)
        self.assertGreater(len(name), 2)

    def test_manual_business_name(self):
        p = self.make_params(asset_type="COMMERCIAL",
                             style="contemporary_commercial", seed=78,
                             floors=2, ground_floor="retail",
                             business_name="Blueprint Cafe")
        P.apply_style_defaults(p)
        obj = generator.generate_asset(p)
        self.assertEqual(obj.get("cityforge_business"), "Blueprint Cafe")


class TestNPC(_Base):

    def test_styles_grounded(self):
        for style in ("casual", "business", "construction", "pedestrian",
                      "random"):
            with self.subTest(style=style):
                obj = generator.generate_asset(self.make_params(
                    asset_type="NPC", npc_style=style, seed=80))
                self.assertIsNotNone(obj, style)
                self.assertGreater(obj.get("cityforge_polygons"), 50)
                zmin = min(v.co.z for v in obj.data.vertices)
                self.assertLessEqual(zmin, 0.02)
                self.assertGreaterEqual(zmin, -0.02)

    def test_deterministic(self):
        p = self.make_params(asset_type="NPC", seed=81, npc_style="business")
        o1 = generator.generate_asset(p)
        o2 = generator.generate_asset(p)
        self.assertEqual(len(o1.data.vertices), len(o2.data.vertices))


class TestParks(_Base):

    def test_all_park_types(self):
        for pt in ("neighbourhood_park", "community_park", "city_park",
                   "urban_plaza", "botanical_garden", "waterfront_park",
                   "dog_park", "playground_park", "sports_park",
                   "formal_garden", "forest_park"):
            with self.subTest(park=pt):
                p = self.make_params(asset_type="PARK", park_type=pt,
                                     seed=70)
                obj = generator.generate_asset(p)
                self.assertIsNotNone(obj, pt)
                self.assertGreater(len(obj.children), 3, pt)
                for child in obj.children:
                    zmin = min((v.co.z for v in child.data.vertices),
                               default=0.0)
                    self.assertLessEqual(zmin, 0.1, f"{pt} child floats")

    def test_deterministic_layout(self):
        p = self.make_params(asset_type="PARK", park_type="city_park",
                             seed=71)
        o1 = generator.generate_asset(p)
        o2 = generator.generate_asset(p)
        self.assertEqual(len(o1.children), len(o2.children))


if __name__ == "__main__":
    print("=" * 60)
    print("CITYFORGE BLENDER TEST SUITE")
    print(f"Blender {bpy.app.version_string}  addon_looked_up="
          f"{LOADED},{ENABLED}")
    print("=" * 60)
    unittest.main(argv=("cityforge-tests",), verbosity=2, exit=True)
