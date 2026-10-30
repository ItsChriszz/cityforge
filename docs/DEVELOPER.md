# CityForge — Developer Documentation

## Module map

```
cityforge/
├── blender_manifest.toml     Extension manifest (Blender 4.2+ "Get Extensions")
├── __init__.py               bl_info + register/unregister entry points
├── properties.py             bpy PropertyGroups mirroring GenerationParams,
│                             UI <-> params conversion, style update callback
├── core/                     bpy-dependent engine modules
│   ├── params.py             Canonical parameter dataclass, limits, style
│   │                         profiles, auto-generated PARAM_SPECS registry.
│   │                         NO bpy imports (unit-testable headless).
│   ├── validation.py         Strict validation/normalisation (no bpy).
│   ├── randomization.py      Deterministic RNG helpers (no bpy).
│   ├── materials.py          Material catalog: key -> shared bpy material.
│   ├── generator.py          Dispatcher: GenerationParams -> bpy object.
│   ├── asset_manager.py      Collections, naming, custom props, registry.
│   ├── optimization.py       Stats, cleanup, LOD regeneration, originals.
│   ├── export_manager.py     FBX/GLB export + directory conventions.
│   └── nl_integration.py     Local prompt parser + optional GLM bridge.
├── generators/               geometry builders (return MeshBuilder + info)
│   ├── buildings.py          Facade walls, windows, balconies, roofs,
│   │                         podiums, setbacks, storefronts, roof clutter
│   ├── roads.py              Centreline sweep, profiles, markings
│   ├── vegetation.py         Trees (4 types × 4 seasons), bushes
│   ├── props.py              12 street furniture builders
│   └── vehicles.py           6 vehicle classes
├── ui/
│   ├── operators.py          All cityforge.* operators
│   └── panel.py              N-panel (CITYFORGE category)
├── presets/buildings.json    8 example presets
├── utils/
│   ├── __init__.py           Seeded RNG factory, logging, hashing
│   ├── geometry.py           MeshBuilder (the mesh construction engine)
│   └── naming.py             Asset naming scheme
└── tests/
    ├── test_validation.py    Pure-Python unit tests (validation/NL)
    └── run_blender_tests.py  24 integration tests, run inside Blender
```

## Key design decisions

### MeshBuilder (`utils/geometry.py`)
All generators accumulate faces as `(point_list, material_key, smooth)`
triples.  `MeshBuilder.finish()` welds vertices (5-decimal rounding), builds
one `bpy.types.Mesh`, resolves materials through the material library and
assigns per-face material indices **after** `mesh.validate()` (validate may
delete elements and reorder polygons, so index-based assignment must happen
afterwards; a centroid-matching fallback handles reordered meshes).

Primitive API: `add_box` (rotates about its own centre), `add_plate`,
`add_cylinder` (X/Y/Z axis, tapered), `add_sphere` (squashable),
`add_outward_face` (auto winding flip toward a hint normal).

### Wall construction (`generators/buildings.py`)
A facade wall is a `Wall` frame (origin, u-direction, outward normal,
length).  Wall-local boxes are placed with `_wall_box`, where
`depth_center` is signed (+outward) and `depth_size` is the thickness along
the normal.  Panels (`_panel`) are flush with the outer plane and
WALL_THICK (0.22 m) deep.

Each storey band is decomposed into spandrel (below sill), header (above
openings) and pier boxes with real openings between them; each opening gets
a frame ring, recessed glass, and (detail permitting) mullions/sills/
lintels.  No booleans; butted boxes weld into clean geometry.

### Determinism
Every stochastic choice draws from `random.Random(seed_from_string(salt,
seed))`.  Same seed + same parameters = bit-identical meshes (tested).

### Materials
`core/materials.py` maps string keys (`concrete`, `brick_red`,
`dark_glass`, …) to shared `bpy.types.Material`s, namespaced `CF_*` and
tagged with a `cityforge_key` custom property.  The catalog is capped
(`_MAX_CACHE`) and `purge_unused_library()` cleans orphans.

### Property flow
UI PropertyGroups (`properties.py`) → `collect_params()` →
`GenerationParams` → `validate_params()`/`normalize_params()` →
`generate_asset()` → dispatcher → generator → `asset_manager.create_asset()`
(naming, collection, custom props, selection).

### NL bridge safety model
`nl_integration.request_glm()` POSTs the prompt with a schema-constrained
system message and expects **JSON parameters only**.  The payload passes
through `normalize_params` (unknown keys rejected, ranges enforced,
types coerced) before reaching geometry code.  Nothing from the response is
`exec`'d or `eval`'d.  Without `CFGLM_ENDPOINT` the local keyword parser is
used and the add-on remains fully functional.

## Conventions

* Blender units = metres; front facade faces **-Y**; origins at ground
  centre.
* FBX export: Blender defaults (`-Y` forward, `Z` up, `apply_unit_scale`)
  → Unity imports facing +Z at 1:1 scale.
* GLB: `export_yup=True`.
* Custom properties on every asset: `cityforge_params` (JSON), `cityforge_seed`,
  `cityforge_asset_type`, `cityforge_style`, `cityforge_detail_level`,
  `cityforge_generated_at`, `cityforge_polygons`, `cityforge_version`,
  `cityforge_info`.

## Running the tests

```bash
python3 cityforge/tests/test_validation.py          # headless, fast
blender -b --python cityforge/tests/run_blender_tests.py
```

The Blender suite covers registration, all 10 styles, deterministic seeds,
mesh sanity, naming, collections, material reuse, LOD/optimisation, export
round-trips and invalid-input rejection.

## Adding a new architectural style

1. Add the style id to `ARCH_STYLES` and a profile to `STYLE_PROFILES`
   (`core/params.py`).
2. Add a wall-articulation entry to `_TYPE_WALL_STYLE` in
   `generators/buildings.py` (pier/spandrel roles).
3. If it needs bespoke behaviour, branch on `ctx.style` in the relevant
   builder (see `_ground_floor` / `_roof_for_building`).
4. Add a preset to `presets/buildings.json` (optional).

## Adding a new prop

1. Add the type id to `PROP_TYPES` (`core/params.py`) and
   `CATEGORY_TREE`/naming prefix.
2. Write a `_builder(mb, rng, params, seg)` in `generators/props.py` and
   register it in `_BUILDERS`.
3. UI: add an enum entry in `properties.ASSET_TYPE_ITEMS` and a settings
   branch in `ui/panel.py` if it needs exposed parameters.
