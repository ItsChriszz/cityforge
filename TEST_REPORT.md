# CityForge — Test Report (expansion round)

All commands were actually executed. Results quoted verbatim from the runs.

## Static checks
- `python3 -m py_compile` across every module: **PASS** (after fixing a
  missing newline that corrupted `BUILDING_KINDS` and an orphaned `def` in
  vegetation.py).
- Enum registration: fixed `'default' can only be an integer when 'items' is
  a function` (dynamic building_kind enum) — registration now succeeds.

## Pure-Python unit tests
```
$ python3 cityforge/tests/test_validation.py
Ran 14 tests in 0.002s
OK
```

## Blender integration tests
```
$ BLENDER_USER_CONFIG=... blender -b --python cityforge/tests/run_blender_tests.py
Ran 55 tests in 13.768s
OK
```
Coverage: registration cycle, 15 styles, 5 tower forms, residential forms
uniqueness, level gating, deterministic seeds (hash equality), mesh sanity,
naming, collections, material reuse + colour variants, road classes +
markings above surface, one-way flags, all 15 sign variants grounded,
crosswalk piece compactness, traffic-light lamp visibility (no cover),
NPC professions + rig + walk clip, age height variation, rail (11 types),
port (10 types), watercraft grounding, intersections/roundabouts,
construction animation (8 parts, progressive visibility), park types with
grounded children, colour application without checkboxes, industrial
sanitization, exports (FBX + GLB).

## Targeted bug reproductions (then verified fixed)
1. Colours: `TINTED ['CF_white_concrete_e53333']` after picking red.
2. Skyscraper: `SKY_FLOORS 32 style glass_curtain_tower` after switching
   the asset type.
3. Markings: `MARKZ two_lane {0.185: 53} ABOVE_SURFACE` for all classes.
4. Sanitization: industrial + townhouse → `industrial_warehouse / auto /
   loading_bay / none`.

## Batch generation
27 additional asset types (INTERSECTION … FERRY) all generate: `BATCH_DONE
bad= 0`; watercraft correctly submerge (negative z = hull below waterline).

## Visual inspection
Rendered with Cycles (OptiX) and inspected:
- `docs/screenshots/skyline_all_styles.png` — 10 buildings; skyscrapers
  visibly taller; colours varied; no black banners.
- `docs/screenshots/commercial_variety.png` — storefronts with signage,
  awnings, mullions.
- `docs/screenshots/park_aerial.png` — clean paths, pond, plaza.
- `docs/screenshots/props_fixed.png` — connected street furniture.
- `docs/screenshots/road_classes.png` — markings on the surface, medians.
- `docs/screenshots/characters_vehicles.png` — vehicle row + NPCs.
Issues found and fixed during inspection: buried markings, z-fighting
layers, joint gaps, coplanar storefront faces, orphaned hedge definition.

## Export tests
- FBX + GLB batch (16 assets each) re-imported into Blender: dimensions
  match generation-time dimensions; origins at ground level.
- Construction animation: keyframed transforms on child parts; exported to
  FBX in the standard flow (transform animation). Unity-side playback should
  be validated in a Unity project; the exported keys are plain transform
  curves.
