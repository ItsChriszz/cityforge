# SPDX-License-Identifier: GPL-3.0-or-later
"""UI operators: generate, variations, randomise, optimise, export, prompts."""

from __future__ import annotations

import json
import os
import random
from typing import List, Optional

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty

from ..core import (
    asset_manager,
    export_manager,
    generator,
    materials as matlib,
    nl_integration,
    optimization,
    randomization,
)
from ..core import params as P
from ..core.validation import ValidationError, normalize_params
from .. import properties as props_mod
from ..utils import get_logger

_log = get_logger()


def _params_from_context(context) -> P.GenerationParams:
    params = props_mod.collect_params(context)
    return params


class CF_OT_generate(bpy.types.Operator):
    """Generate an asset from the current CityForge settings."""
    bl_idname = "cityforge.generate"
    bl_label = "Generate Asset"
    bl_options = {'REGISTER', 'UNDO'}

    variations: IntProperty(
        name="Variations",
        description="Number of variations to create (1 = only the current "
                    "settings)",
        default=1, min=1, max=50)

    def execute(self, context):
        n_fail = 0
        created: List[str] = []
        for i in range(max(1, self.variations)):
            params = _params_from_context(context)
            if i > 0:
                params.seed = int(randomization.variation_seed(
                    params.seed, i))
            try:
                payload, issues = normalize_params({
                    k: v for k, v in params.to_dict().items()
                    if k in P.PARAM_KEYS and k not in ("variation",)})
                if issues:
                    self.report({'WARNING'},
                                f"settings adjusted: {'; '.join(issues[:3])}")
                validated = P.GenerationParams.from_dict(payload)
                validated.variation = i
                validated.seed = params.seed
                obj = generator.generate_asset(validated)
            except ValidationError as exc:
                self.report({'ERROR'}, f"invalid settings: {exc}")
                return {'CANCELLED'}
            except Exception as exc:  # surfaced to the log, never hidden
                _log.exception("generation failed")
                self.report({'ERROR'}, f"generation failed: {exc}")
                n_fail += 1
                continue
            if obj is not None:
                created.append(obj.name)
        if created:
            extra = f" (+{len(created) - 1} more)" if len(created) > 1 else ""
            self.report({'INFO'}, f"created {created[0]}{extra}")
        elif n_fail == 0:
            self.report({'WARNING'}, "nothing was generated")
        return {'FINISHED'}


class CF_OT_generate_variations(bpy.types.Operator):
    """Generate several randomised variations of the current asset."""
    bl_idname = "cityforge.generate_variations"
    bl_label = "Generate Variations"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.cityforge
        bpy.ops.cityforge.generate(variations=max(1, s.variation_count))
        return {'FINISHED'}


class CF_OT_regenerate_selected(bpy.types.Operator):
    """Rebuild the selected asset with its stored parameters."""
    bl_idname = "cityforge.regenerate_selected"
    bl_label = "Regenerate Selected"
    bl_options = {'REGISTER', 'UNDO'}

    seed_bump: IntProperty(
        name="Seed Offset",
        description="Add this to the stored seed for a fresh variant",
        default=0)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and bool(
            asset_manager.get_stored_params(context.active_object))

    def execute(self, context):
        obj = context.active_object
        params = asset_manager.get_stored_params(obj)
        if params is None:
            self.report({'ERROR'}, "selected object is not a CityForge asset")
            return {'CANCELLED'}
        params.seed = int(params.seed) + int(self.seed_bump)
        new_obj = generator.generate_asset(params)
        if new_obj is None:
            self.report({'ERROR'}, "regeneration failed")
            return {'CANCELLED'}
        asset_manager.delete_asset(obj)
        self.report({'INFO'}, f"regenerated as {new_obj.name}")
        return {'FINISHED'}


class CF_OT_delete_generated(bpy.types.Operator):
    """Delete the selected CityForge asset (or all generated assets)."""
    bl_idname = "cityforge.delete_generated"
    bl_label = "Delete Generated Asset"
    bl_options = {'REGISTER', 'UNDO'}

    all_assets: BoolProperty(name="All CityForge Assets", default=False)

    def execute(self, context):
        if self.all_assets:
            objs = asset_manager.list_generated(context.scene)
        elif context.active_object and asset_manager.get_stored_params(
                context.active_object):
            objs = [context.active_object]
        else:
            self.report({'ERROR'},
                        "no CityForge asset selected and 'All Assets' is off")
            return {'CANCELLED'}
        for obj in objs:
            asset_manager.delete_asset(obj)
        self.report({'INFO'}, f"deleted {len(objs)} asset(s)")
        return {'FINISHED'}


class CF_OT_randomize_settings(bpy.types.Operator):
    """Randomise the building settings dialog for a new look."""
    bl_idname = "cityforge.randomize_settings"
    bl_label = "Randomize Settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        s = scene.cityforge
        rng = random.Random(s.seed * 31 + 7)
        bp = scene.cityforge_building
        bp.style = rng.choice(P.ARCH_STYLES)
        bp.width = round(rng.uniform(6.0, 40.0))
        bp.depth = round(rng.uniform(6.0, 30.0))
        bp.floors = rng.randint(1, 30)
        s.seed = rng.randint(0, 10 ** 6)
        self.report({'INFO'}, f"settings randomised (seed {s.seed})")
        return {'FINISHED'}


class CF_OT_generate_lods(bpy.types.Operator):
    """Create LOW / MEDIUM / HIGH LOD copies of the selected asset."""
    bl_idname = "cityforge.generate_lods"
    bl_label = "Generate LODs"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and bool(
            asset_manager.get_stored_params(context.active_object))

    def execute(self, context):
        obj = context.active_object
        made = []
        for lod in ("low", "medium", "high"):
            new = optimization.generate_lod(obj, lod)
            if new:
                made.append(new.name)
        self.report({'INFO'}, f"LODs created: {', '.join(made)}")
        return {'FINISHED'}


class CF_OT_optimize(bpy.types.Operator):
    """Clean up geometry of the selected CityForge assets."""
    bl_idname = "cityforge.optimize"
    bl_label = "Optimize Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preserve = context.scene.cityforge.preserve_originals
        targets = [o for o in context.selected_objects
                   if asset_manager.get_stored_params(o)]
        if not targets:
            self.report({'ERROR'}, "select a generated asset first")
            return {'CANCELLED'}
        if preserve:
            for obj in list(targets):
                keep = obj.copy()
                keep.data = obj.data.copy()
                context.scene.collection.objects.link(keep)
                del keep["cityforge_params"]
                keep["cityforge_original"] = True
                keep.name = obj.name + "_PREOPT"
                optimization.preserve_original(obj)
        report = optimization.optimize_selected(preserve=False)
        for line in report:
            _log.info(line)
        self.report({'INFO'}, "; ".join(report) or "nothing to clean")
        return {'FINISHED'}


class CF_OT_apply_materials(bpy.types.Operator):
    """Re-apply the shared CityForge material library to selected assets."""
    bl_idname = "cityforge.apply_materials"
    bl_label = "Apply Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        n = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            for slot in list(obj.data.materials):
                if slot is None:
                    continue
                key = slot.get("cityforge_key")
                if key:
                    idx = obj.data.materials.find(slot.name)
                    if idx >= 0:
                        obj.data.materials[idx] = matlib.get_material(key)
                        n += 1
        self.report({'INFO'}, f"re-applied materials on {n} slots")
        return {'FINISHED'}


class CF_OT_purge_materials(bpy.types.Operator):
    """Remove unreferenced CityForge materials."""
    bl_idname = "cityforge.purge_materials"
    bl_label = "Purge Unused Materials"

    def execute(self, context):
        removed = matlib.purge_unused_library()
        stats = matlib.library_stats()
        self.report({'INFO'},
                    f"purged {removed}; {stats['materials']} in use")
        return {'FINISHED'}


class CF_OT_apply_prompt(bpy.types.Operator):
    """Interpret the plain-language description into settings, then generate."""
    bl_idname = "cityforge.apply_prompt"
    bl_label = "Apply Description"
    bl_options = {'REGISTER', 'UNDO'}

    generate_after: BoolProperty(name="Generate After Parse", default=True)
    use_glm_bridge: BoolProperty(
        name="Use GLM Bridge",
        description="POST the prompt to the configured GLM endpoint "
                    "(CFGLM_ENDPOINT). Falls back to the local keyword "
                    "parser otherwise", default=False)

    _MAPPING = {"primary": "material_primary",
                "secondary": "material_secondary",
                "windows": "material_window",
                "trim": "material_trim",
                "accent": "material_accent"}

    def execute(self, context):
        prompt = context.scene.cityforge.prompt.strip()
        if not prompt:
            self.report({'ERROR'}, "enter a description first")
            return {'CANCELLED'}
        raw_params: Optional[dict] = None
        source = "local parser"
        if self.use_glm_bridge:
            if not nl_integration.bridge_configured():
                self.report(
                    {'WARNING'},
                    "GLM bridge not configured (CFGLM_ENDPOINT missing); "
                    "using the local parser")
            else:
                try:
                    raw_params, _dump = nl_integration.request_glm(prompt)
                    source = "GLM bridge"
                except RuntimeError as exc:
                    self.report({'ERROR'}, str(exc))
                    return {'CANCELLED'}

        if raw_params is None:
            raw_params, notes = nl_integration.local_parse(prompt)

        # flatten the nested materials dict onto material_* keys
        mats = raw_params.pop("materials", {}) or {}
        for k, v in mats.items():
            flat = self._MAPPING.get(k)
            if flat and isinstance(v, str):
                raw_params[flat] = v

        try:
            clean, issues = normalize_params(raw_params)
            if issues:
                _log.warning("%s parameter issues: %s", source, issues)
        except ValidationError as exc:
            self.report({'ERROR'},
                        f"{source}: parameters rejected: {exc}")
            _log.warning("%s produced invalid parameters", source)
            return {'CANCELLED'}

        if not clean:
            self.report({'WARNING'},
                        f"{source}: nothing usable found; defaults kept")
            return {'FINISHED'}

        current = _params_from_context(context)
        merged = P.GenerationParams.from_dict({**current.to_dict(), **clean})
        props_mod.sync_from_params(context, merged)
        self.report({'INFO'},
                    f"applied from {source}: " + ", ".join(sorted(clean)))
        if self.generate_after:
            bpy.ops.cityforge.generate()
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# presets
# ---------------------------------------------------------------------------

_PRESET_PATH = os.path.join(os.path.dirname(__file__), "..", "presets",
                            "buildings.json")


class CF_OT_load_preset(bpy.types.Operator):
    """Load one of the bundled building presets."""
    bl_idname = "cityforge.load_preset"
    bl_label = "Load Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: StringProperty(name="Preset")

    def execute(self, context):
        try:
            with open(os.path.abspath(_PRESET_PATH), "r",
                      encoding="utf-8") as fh:
                presets = json.load(fh)
        except (OSError, ValueError) as exc:
            self.report({'ERROR'}, f"presets file unreadable: {exc}")
            return {'CANCELLED'}
        if self.preset not in presets:
            self.report({'ERROR'}, f"unknown preset {self.preset!r}")
            return {'CANCELLED'}
        data = dict(presets[self.preset])
        try:
            clean, issues = normalize_params(data)
            if issues:
                _log.warning("preset issues: %s", issues)
        except ValidationError as exc:
            self.report({'ERROR'}, f"preset file corrupt: {exc}")
            return {'CANCELLED'}
        current = _params_from_context(context)
        merged = P.GenerationParams.from_dict({**current.to_dict(), **clean})
        props_mod.sync_from_params(context, merged)
        self.report({'INFO'}, f"loaded preset '{self.preset}'")
        return {'FINISHED'}


class CF_MT_presets_menu(bpy.types.Menu):
    bl_label = "CityForge Presets"
    bl_idname = "CITYFORGE_MT_presets"

    def draw(self, context):
        try:
            with open(os.path.abspath(_PRESET_PATH), "r",
                      encoding="utf-8") as fh:
                presets = json.load(fh)
        except (OSError, ValueError):
            self.layout.label(text="presets file unreadable", icon='ERROR')
            return
        for name in sorted(presets):
            self.layout.operator(
                CF_OT_load_preset.bl_idname,
                text=name.replace("_", " ").title()).preset = name


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

class CF_OT_export_selected(bpy.types.Operator):
    """Export the selected assets to FBX/GLB for Unity."""
    bl_idname = "cityforge.export_selected"
    bl_label = "Export Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            self.report({'ERROR'}, "select at least one mesh")
            return {'CANCELLED'}
        results = export_manager.export_selected(context)
        ok = sum(1 for _n, msg in results if msg.startswith("exported"))
        for _n, msg in results:
            if not msg.startswith("exported"):
                self.report({'ERROR'}, msg)
        self.report({'INFO'}, f"exported {ok}/{len(results)} asset(s)")
        return {'FINISHED'}


class CF_OT_batch_export(bpy.types.Operator):
    """Export every CityForge asset in this scene."""
    bl_idname = "cityforge.batch_export"
    bl_label = "Batch Export All Assets"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        results = export_manager.export_all_cityforge(context)
        ok = sum(1 for _n, m in results if m.startswith("exported"))
        for _n, m in results:
            if not m.startswith("exported"):
                self.report({'WARNING'}, m)
        self.report({'INFO'}, f"exported {ok}/{len(results)} asset(s)")
        return {'FINISHED'}


class CF_OT_construction_play(bpy.types.Operator):
    """Play the construction animation of the selected animated building."""
    bl_idname = "cityforge.construction_play"
    bl_label = "Play Construction"
    bl_options = {'REGISTER', 'UNDO'}

    restart: BoolProperty(name="Restart", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.get("cityforge_construction")

    def execute(self, context):
        obj = context.active_object
        meta = obj.get("cityforge_construction")
        frames = int(meta.get("duration_frames", 120)) if meta else 120
        context.scene.frame_start = 1
        context.scene.frame_end = max(2, frames)
        if self.restart:
            context.scene.frame_current = 1
        bpy.ops.screen.animation_play()
        self.report({'INFO'}, f"playing {frames} frames")
        return {'FINISHED'}


class CF_OT_construction_stop(bpy.types.Operator):
    """Stop playback and reset to the completed building."""
    bl_idname = "cityforge.construction_stop"
    bl_label = "Stop / Show Complete"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.get("cityforge_construction")

    def execute(self, context):
        if bpy.ops.screen.animation_cancel.poll():
            bpy.ops.screen.animation_cancel()
        meta = context.active_object.get("cityforge_construction") or {}
        context.scene.frame_set(int(meta.get("duration_frames", 1)) + 2)
        return {'FINISHED'}


CLASSES = [
    CF_OT_generate,
    CF_OT_generate_variations,
    CF_OT_regenerate_selected,
    CF_OT_delete_generated,
    CF_OT_randomize_settings,
    CF_OT_generate_lods,
    CF_OT_optimize,
    CF_OT_apply_materials,
    CF_OT_purge_materials,
    CF_OT_apply_prompt,
    CF_OT_load_preset,
    CF_MT_presets_menu,
    CF_OT_export_selected,
    CF_OT_batch_export,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
