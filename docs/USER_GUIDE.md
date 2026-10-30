# CityForge — User Guide

## Workflow

1. **Open the sidebar** — `N` key in the 3D viewport → CITYFORGE tab.
2. **Pick an asset type** — buildings (9 types), roads/sidewalks, vegetation,
   street furniture (12 props) or vehicles.
3. **Adjust settings** — only the settings relevant to the selected category
   are shown. Loading a **Preset** fills everything at once.
4. **Generate** — the asset appears at the origin and is filed into the
   matching `CityForge_Assets` sub-collection.
5. **Iterate** — change the seed for a different look; `Generate ×5/×10` or
   *Random Variations* produce batches; *Randomize Settings* invents a whole
   new configuration.
6. **Inspect** — selecting a generated asset shows its type, seed, detail
   level, polygon count and creation time in the Quick Help panel.
7. **Regenerate** — *Regenerate Selected* rebuilds the asset from its saved
   parameters (optionally with a seed offset for a fresh variant).
8. **Export** — FBX or GLB into the configured export directory.

## Building settings reference

### Massing
* **Width / Depth** — footprint in metres (3–120).
* **Floors** (1–60) and **Floor Height** (2.2–6 m). Total height and
  footprint are displayed live.
* **Architectural Style** — 10 styles; each changes geometry, proportions,
  facade articulation and material palette (not just colours).

### Facade
* **Window Type** — rectangular, tall, wide, ribbon, curtain wall, arched,
  strip, picture.
* **Window Width/Height/Spacing/Sill** — the facade generator builds real
  openings: piers, spandrels, recessed frames, glass, mullions, sills and
  lintels.
* **Window Lighting** — *Random* lights a subset of interiors (emissive),
  *Always Lit / Always Dark* force states.
* **Frame Thickness** — window frame member thickness.

### Balconies
* **Style** — none / metal / concrete / glass.
* **Frequency** — share of window bays that receive a balcony (patterns are
  seeded; whole floors are skipped for rhythmic facades).
* **Depth** — platform projection.

### Roof
* **Type** — flat, flat + parapet, sloped (single pitch), gable, hip,
  terrace.
* **Roof Equipment** — HVAC units, vents, duct pipes, stair bulkhead, water
  tank on legs, antenna (style-dependent, seeded placement).
* **Rooftop Terrace** — railing ring + planters instead of clutter.

### Ground floor
* **retail / office lobby** — glass storefront with mullions, recessed door,
  canopy, sign board (signage for styles that support it).
* **apartment entrance** — taller windows + entrance portal with canopy.
* **loading bay** — roller doors with ribbed shutters + clerestory strip.
* **garage** — open columned band (parking structures).
* **Podium floors** — for towers: a wider storefront base with a parapet deck.
* **Corner columns** — pilaster strips for commercial/industrial styles.

### Materials
Primary, secondary, window and trim materials are chosen from the shared
CityForge library (procedural nodes, reused between assets — never
duplicated per object).

## Detail levels

| Level | Intended use | Construction |
|---|---|---|
| LOW | distant buildings, large populations | no mullions/sills/lintels, sparse roof clutter, coarser cylinders, sparser windows |
| MEDIUM | ordinary city buildings | full window assemblies, standard roof furniture |
| HIGH | hero/close-up assets | finest segmentation, all detail elements |

Polygon budgets: ~25k / ~120k / ~300k. If an asset exceeds the budget the
generator automatically rebuilds it at a lower level (and, if still over,
with sparser windows and no balconies), flagging the object with
`cityforge_budget_warning`.

**Generate LODs** creates `_LOD_LOW`, `_LOD_MEDIUM`, `_LOD_HIGH` copies of
the selected asset.

**Optimize Geometry** welds duplicate vertices, removes loose geometry and
consistent-ifies normals. With *Preserve Originals* enabled, the untouched
copy is moved to the `CityForge_Originals` collection (`_PREOPT` suffix) —
nothing is ever destroyed.

## Roads & sidewalks

* Width 3–40 m, length 5–500 m, curvature 0–90°, 1–6 lanes.
* Real curb faces, raised sidewalks, grass verges, crown camber.
* Lane markings: dashed center, continuous edge lines, zebra crosswalks;
  *Markings* preset selects none/simple/dashed/full.
* Optional bicycle lane, parking lane toggles.
* Sidewalk asset: standalone slab with curb edge and paving joints.

## Vegetation

* Trees: deciduous / evergreen / poplar / palm; height, trunk radius, canopy
  radius, branch count, leaf density.
* **Season** — spring / summer / autumn / winter foliage (deciduous trees
  go bare in winter with twig geometry on higher detail levels).
* Bushes: multi-blob shrubs sized independently of trees.

## Street furniture & vehicles

Streetlights (single/double arm), traffic lights (with emissive heads),
traffic signs (6 variants), benches, bus stops (glass shelter + timetable),
parking meters, garbage bins, fences (chain link / metal panels / wooden /
concrete), bollards, hydrants, planters, barriers — all seeded and
deterministic.

Vehicles: sedan, hatchback, van, truck, bus, taxi with per-instance colour
variation.

## Export

* Set the export directory (default `//CityForge_Export/`).
* Pick FBX or GLB.
* **Export Selected** — exports selected meshes; **Batch All** — every
  CityForge asset in the scene.
* Category sub-folders are created automatically and files are never
  overwritten.

## Tips

* Same seed + same settings = identical asset (deterministic).
* Big batches: pick LOW detail + *Random Variations*; export the whole
  batch with *Batch All*.
* Materials blow up file size? *Purge Unused Materials* removes library
  materials that lost all users.
