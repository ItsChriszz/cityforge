# SPDX-License-Identifier: GPL-3.0-or-later
"""CityForge sidebar panel (N-panel tab 'CITYFORGE')."""

from __future__ import annotations

import bpy

from ..core import asset_manager, optimization
from ..core.params import ASSET_TYPES
from . import operators as ops


class CF_PT_main(bpy.types.Panel):
    bl_label = "CityForge"
    bl_idname = "CF_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CITYFORGE"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        s = scene.cityforge
        stats = optimization.scene_stats()

        # ----- dashboard -------------------------------------------------
        box = layout.box()
        box.label(text="Dashboard", icon='INFO')
        col = box.column(align=True)
        col.label(text="CityForge 1.0.0 - assets in scene: "
                       f"{stats['assets']}", icon='BLANK1')
        col.label(text=f"Generated polygons: {stats['total_polygons']:,}",
                  icon='BLANK1')
        cat = ", ".join(f"{k}: {v}" for k, v in
                        sorted(stats["by_category"].items())) or "none"
        col.label(text=f"Categories: {cat}", icon='BLANK1')

        # natural language
        prompt_box = layout.box()
        prompt_box.label(text="Description (natural language)", icon='TEXT')
        col = prompt_box.column(align=True)
        col.prop(s, "prompt", text="")
        col.operator(ops.CF_OT_apply_prompt.bl_idname,
                     text="Apply Description")

        # ----- generator -------------------------------------------------
        gen = layout.box()
        gen.label(text="Asset Generator", icon='OUTLINER')
        gen.prop(s, "asset_type", text="Type")
        gen.prop(s, "seed")
        gen.prop(s, "detail_level", text="Detail")
        gen.prop(s, "variation_count")

        at = s.asset_type
        is_building = any(t in at for t in
                          ("RESID", "COMMERCIAL", "OFFICE", "MIXED", "SKY",
                           "SHOP", "WARE", "INDUSTRIAL", "PARKING", "HOUSE"))
        is_road = at in ("ROAD", "SIDEWALK")
        is_veg = at in ("TREE", "BUSH")
        is_vehicle = at == "VEHICLE"
        is_prop = not (is_building or is_road or is_veg or is_vehicle)

        bp = scene.cityforge_building
        rp = scene.cityforge_road
        vp = scene.cityforge_veg
        pp = scene.cityforge_prop
        veh = scene.cityforge_vehicle

        if is_building:
            self._draw_building(gen, bp)
        elif at == "PARK":
            self._draw_park(gen, scene.cityforge_park)
        elif at == "NPC":
            self._draw_npc(gen, scene.cityforge_npc)
        elif is_road:
            self._draw_road(gen, rp)
        elif is_veg:
            self._draw_vegetation(gen, vp)
        elif is_vehicle:
            self._draw_vehicle(gen, veh)
        else:
            self._draw_prop(gen, pp, at)

        # ----- generation controls -------------------------------------
        ctl = layout.box()
        ctl.label(text="Generation", icon='MOD_BUILD')
        row = ctl.row(align=True)
        row.operator(ops.CF_OT_generate.bl_idname, icon='PLAY', text="Generate")
        row.operator(ops.CF_OT_generate.bl_idname,
                     text="x5").variations = 5
        row.operator(ops.CF_OT_generate.bl_idname,
                     text="x10").variations = 10
        row = ctl.row(align=True)
        row.operator(ops.CF_OT_generate_variations.bl_idname,
                     text="Random Variations")
        row.operator(ops.CF_OT_randomize_settings.bl_idname, text="Randomize")
        row = ctl.row(align=True)
        row.operator(ops.CF_OT_regenerate_selected.bl_idname)
        row.operator(ops.CF_OT_delete_generated.bl_idname, icon='X')
        row.operator(ops.CF_OT_delete_generated.bl_idname,
                     text="All").all_assets = True

        # menus row: presets
        row = ctl.row(align=True)
        menu_text = "Presets"
        row.menu(ops.CF_MT_presets_menu.bl_idname, text=menu_text)
        row.operator(ops.CF_OT_generate_lods.bl_idname, text="Make LODs")

        # ----- optimization ---------------------------------------------
        opt = layout.box()
        opt.label(text="Optimization", icon='MESH_CIRCLE')
        opt.prop(s, "preserve_originals")
        row = opt.row(align=True)
        row.operator(ops.CF_OT_optimize.bl_idname, icon='EDITMODE_HLT')
        row.operator(ops.CF_OT_apply_materials.bl_idname)
        row.operator(ops.CF_OT_purge_materials.bl_idname, text="Purge")

        # ----- export -----------------------------------------------------
        expo = layout.box()
        expo.label(text="Export", icon='EXPORT')
        expo.prop(scene.cityforge_export, "export_dir")
        expo.prop(scene.cityforge_export, "export_format")
        row = expo.row(align=True)
        row.operator(ops.CF_OT_export_selected.bl_idname, icon='PACKAGE')
        row.operator(ops.CF_OT_batch_export.bl_idname, text="Batch All")

    # ---------------------------------------------------------------
    def _draw_building(self, layout, bp):
        col = layout.column(align=True)
        col.label(text="Building Settings", icon='MESH_CUBE')
        col.prop(bp, "building_category")
        col.prop(bp, "building_kind")
        col.prop(bp, "style")
        col.prop(bp, "building_level", text="Level")
        col.prop(bp, "construction_animation")
        if bp.construction_animation:
            row = col.row(align=True)
            row.prop(bp, "construction_duration", text="Duration (s)")
            row.operator(ops.CF_OT_construction_play.bl_idname, text="",
                         icon='PLAY')
            row.operator(ops.CF_OT_construction_stop.bl_idname, text="",
                         icon='PAUSE')
        col.separator()
        col.label(text="Form")
        col.prop(bp, "residential_form")
        col.prop(bp, "commercial_form")
        col.prop(bp, "tower_form")
        col.prop(bp, "facade_grid")
        col.prop(bp, "crown_lighting")
        col.separator()
        row = col.row(align=True)
        row.prop(bp, "width")
        row.prop(bp, "depth")
        row = col.row(align=True)
        row.prop(bp, "floors")
        row.prop(bp, "floor_height")
        col.label(text=f"Footprint {bp.width:.0f}m x {bp.depth:.0f}m,  "
                       f"Height ~{bp.floors * bp.floor_height:.0f}m")
        col.separator()
        col.label(text="Facade")
        col.prop(bp, "window_type", text="Windows")
        row = col.row(align=True)
        row.prop(bp, "window_width")
        row.prop(bp, "window_height")
        row = col.row(align=True)
        row.prop(bp, "window_spacing")
        row.prop(bp, "window_sill")
        row = col.row(align=True)
        row.prop(bp, "frame_thickness")
        row.prop(bp, "window_light", text="")
        col.prop(bp, "mullions")
        col.separator()
        col.label(text="Balconies")
        col.prop(bp, "balcony_style")
        row = col.row(align=True)
        row.prop(bp, "balcony_frequency")
        row.prop(bp, "balcony_depth")
        col.separator()
        col.label(text="Roof")
        col.prop(bp, "roof_type")
        col.prop(bp, "rooftop_terrace")
        col.prop(bp, "roof_extras")
        col.separator()
        col.label(text="Ground Floor & Structure")
        col.prop(bp, "ground_floor")
        col.prop(bp, "business_category")
        if bp.business_category != "random":
            col.prop(bp, "business_name")
        col.prop(bp, "podium_floors")
        if bp.podium_floors:
            col.prop(bp, "podium_width")
        col.prop(bp, "columns")
        col.separator()
        col.label(text="Materials")
        col.prop(bp, "use_random_palette")
        if not bp.use_random_palette:
            col.prop(bp, "use_custom_colors")
            if bp.use_custom_colors:
                col.prop(bp, "color_primary")
                col.prop(bp, "color_secondary")
                row = col.row(align=True)
                row.prop(bp, "color_window")
                row.prop(bp, "color_trim")
        col.prop(bp, "material_primary")
        col.prop(bp, "material_secondary")
        row = col.row(align=True)
        row.prop(bp, "material_window")
        row.prop(bp, "material_trim")

    def _draw_park(self, layout, pk):
        col = layout.column(align=True)
        col.label(text="Park Settings", icon='OUTLINER_OB_GROUP_INSTANCE')
        col.prop(pk, "park_type")
        row = col.row(align=True)
        row.prop(pk, "park_width")
        row.prop(pk, "park_length")
        col.prop(pk, "park_shape")
        col.prop(pk, "park_entrances")
        col.separator()
        col.label(text="Layout")
        row = col.row(align=True)
        row.prop(pk, "park_path_density", text="Path Density")
        row.prop(pk, "park_path_width", text="Path Width")
        row = col.row(align=True)
        row.prop(pk, "park_tree_density", text="Trees")
        row.prop(pk, "park_bush_density", text="Bushes")
        row = col.row(align=True)
        row.prop(pk, "park_seating_density", text="Seating")
        row.prop(pk, "park_light_density", text="Lights")
        col.prop(pk, "park_water")
        col.prop(pk, "park_sports")
        col.prop(pk, "park_fenced")
        col.prop(pk, "park_name")

    def _draw_npc(self, layout, np):
        col = layout.column(align=True)
        col.label(text="Character Settings", icon='USER')
        col.prop(np, "npc_profession")
        col.prop(np, "npc_style")
        col.prop(np, "npc_gender")
        col.prop(np, "npc_age")
        col.prop(np, "npc_height")
        col.prop(np, "npc_accessories")
        col.prop(np, "npc_rigged")
        if np.npc_rigged:
            col.prop(np, "npc_clip", text="Clip")

    def _draw_road(self, layout, rp):
        col = layout.column(align=True)
        col.label(text="Road Settings", icon='MESH_PLANE')
        col.prop(rp, "road_class", text="Road Type")
        col.prop(rp, "road_direction")
        row = col.row(align=True)
        row.prop(rp, "lane_count")
        row.prop(rp, "lane_width")
        col.prop(rp, "road_width")
        col.prop(rp, "road_length")
        col.prop(rp, "curvature")
        col.separator()
        col.label(text="Median")
        col.prop(rp, "median_enabled")
        if rp.median_enabled:
            row = col.row(align=True)
            row.prop(rp, "median_width")
            row.prop(rp, "median_style", text="")
        col.separator()
        col.label(text="Sides")
        col.prop(rp, "sidewalk_enabled")
        if rp.sidewalk_enabled:
            row = col.row(align=True)
            row.prop(rp, "sidewalk_width")
            row.prop(rp, "curb_height")
        col.prop(rp, "bike_lane")
        col.prop(rp, "parking_lane")
        col.prop(rp, "grass_strip")
        col.prop(rp, "crosswalks")
        col.prop(rp, "markings", text="Markings")

    def _draw_vegetation(self, layout, vp):
        col = layout.column(align=True)
        col.label(text="Vegetation Settings", icon='OUTLINER_OB_MESH')
        col.prop(vp, "tree_type")
        col.prop(vp, "season")
        row = col.row(align=True)
        row.prop(vp, "tree_height")
        row.prop(vp, "trunk_radius")
        col.prop(vp, "canopy_radius")
        row = col.row(align=True)
        row.prop(vp, "branch_count")
        row.prop(vp, "leaf_density")

    def _draw_vehicle(self, layout, veh):
        col = layout.column(align=True)
        col.label(text="Vehicle Settings", icon='MESH_CUBE')
        col.prop(veh, "vehicle_class")
        row = col.row(align=True)
        row.prop(veh, "vehicle_width")
        row.prop(veh, "vehicle_length")
        col.prop(veh, "vehicle_scale")
        col.prop(veh, "window_tint")
        col.prop(veh, "vehicle_random_look")
        if not veh.vehicle_random_look:
            col.prop(veh, "vehicle_color_body")
            col.prop(veh, "vehicle_color_roof")
            col.prop(veh, "vehicle_color_wheel")

    def _draw_prop(self, layout, pp, at):
        col = layout.column(align=True)
        col.label(text="Prop Settings", icon='OBJECT_HIDDEN')
        if at == "TRAFFIC_SIGN":
            col.prop(pp, "sign_variants")
        elif at == "FENCE":
            col.prop(pp, "fence_type")
            col.prop(pp, "fence_length")
        else:
            col.prop(pp, "prop_style")
            col.prop(pp, "prop_height", text="Prop Height")


class CF_PT_regen_help(bpy.types.Panel):
    bl_label = "Quick Help"
    bl_idname = "CF_PT_help"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CITYFORGE"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="1. Pick an asset type", icon='DOT')
        col.label(text="2. Adjust settings or load a preset", icon='DOT')
        col.label(text="3. Press Generate", icon='DOT')
        col.label(text="4. Generate variations if wanted", icon='DOT')
        col.label(text="5. Export (FBX/GLB) for Unity", icon='DOT')

        obj = context.active_object
        if obj is not None and asset_manager.get_stored_params(obj):
            box = layout.box()
            box.label(text="Selected Asset", icon='OUTLINER_OB_MESH')
            col = box.column(align=True)
            col.label(text=f"Name: {obj.name}")
            col.label(text=f"Type: {obj.get('cityforge_asset_type', '?')}")
            col.label(text=f"Seed: {obj.get('cityforge_seed', '?')}")
            col.label(text=f"Detail: {obj.get('cityforge_detail_level', '?')}")
            col.label(text="Polys: "
                           f"{obj.get('cityforge_polygons', '?'):,}")
            col.label(text=f"Created: {obj.get('cityforge_generated_at', '?')}")


CLASSES = [
    CF_PT_main,
    CF_PT_regen_help,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
