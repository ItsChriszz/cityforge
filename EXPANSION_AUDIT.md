# CityForge — Expansion Audit

Status key: **IMPLEMENTED** (working, verified) · **PARTIAL** (exists, incomplete) ·
**BROKEN** (exists, does not work correctly) · **MISSING** (not implemented).

Verified against the source at the start of the expansion round. Confirmed bug
reproductions are marked 🐛.

## Building generation

| Area | Status | Notes |
|---|---|---|
| Facade engine (piers/spandrels/frames/glass/mullions/sills/lintels) | IMPLEMENTED | real openings, watertight, welded |
| 15 architectural styles | IMPLEMENTED | distinct massing/articulation/materials |
| Residential forms (detached/townhouse/low/mid/high-rise) | IMPLEMENTED | unique geometry per form |
| Commercial forms (retail/restaurant/cafe/pub/office/shopping/mixed) | IMPLEMENTED | storefront variants |
| Roof types (flat/parapet/sloped/gable/hip/terrace) | IMPLEMENTED | + HVAC/vents/tanks/bulkheads/antennas |
| Balconies (metal/concrete/glass) | IMPLEMENTED | bay-aligned, seeded patterns |
| Podiums + setbacks + tower forms | IMPLEMENTED | box/tapered/setback/tapered_setback/crown |
| Facade grids (vertical/horizontal/ortho) | IMPLEMENTED | curtain-wall rhythm |
| Crown lighting | IMPLEMENTED | emissive parapet band + corner columns |
| 🐛 Colour selection has no effect | BROKEN | colours only apply when a hidden
      `use_custom_colors` checkbox is enabled; the pickers do not follow the
      style palette, so users see no reaction. Fix: always apply the pickers,
      sync them from the style, keep a random-palette override. |
| 🐛 Skyscrapers not taller than ordinary buildings | BROKEN | the SKYSCRAPER
      asset type does not change floor count or height — the user's floor
      setting (default 5) is used unchanged. Fix: type presets drive
      floors/height per category. |
| Building categories (institutional/public/agricultural/hospitality/
      healthcare/education) | MISSING | only residential/commercial/industrial/
      office/mixed/towers exist today |
| 🐛 Black banner-like surfaces | BROKEN | the `sign_dark` material (pub/bar
      sign boards) is near-pure black and the storefront header band reads as
      a black banner; signs without text render as dark slabs. Fix: replace
      sign_dark with a deep green/navy + trim, ensure signage text renders. |
| 🐛 Houses missing ground floors / foundations | BROKEN | buildings start at
      z=0 with no plinth; the detached-house form shows an apparent missing
      bottom storey. Fix: foundation slab + entrance steps for all buildings. |
| 🐛 Industrial categories can produce residential forms | BROKEN | form/state
      leaks across category switches (e.g. townhouse preset applied, then
      INDUSTRIAL chosen). Fix: category presets + validation clamps. |
| Construction animation | MISSING | |
| Building Levels 1–3 as a single selector | PARTIAL | three independent
      checkboxes exist and gate geometry correctly; needs the single-selector
      UX and per-category stage tuning |

## Roads & traffic

| Area | Status | Notes |
|---|---|---|
| Road classes (highway/single/two/four/one-way) | IMPLEMENTED | per-class profiles |
| 🐛 Lane/centre markings not visible | BROKEN | marking plates at z=0.165 are
      BELOW the asphalt surface (z=0.18) — buried. Fix: place markings on the
      road surface. |
| Curved-road sweep | IMPLEMENTED | centreline sample + per-segment sweep |
| Medians (painted/raised/planted) | IMPLEMENTED | |
| One-way arrows | PARTIAL | exist but were buried (same z bug) and never
      visually verified; fix + verify |
| Highway furniture (guardrails, lighting, gantry signs) | MISSING | |
| Intersections | MISSING | |
| Roundabouts | MISSING | |
| Ramps / bridges / tunnels | MISSING | |
| 🐛 Traffic light colours obscured | BROKEN | a glass cover plate is drawn
      OVER the emissive lamps; remove it / expose the lamps |
| Sign category (15 sign types) | PARTIAL | 6 sign variants exist; no text
      capability, no sizes, no dedicated category |
| Modular crosswalk piece | MISSING | crosswalks only exist embedded in roads |

## Vehicles / characters

| Area | Status | Notes |
|---|---|---|
| 9 vehicle classes | IMPLEMENTED | sedan/hatchback/suv/pickup/van/delivery/
      bus/taxi/sports |
| Vehicle colours/tint/scale/random look | IMPLEMENTED | token tints, verified |
| Motorcycles / bicycles | MISSING | |
| Emergency / construction vehicles | MISSING | |
| Watercraft | MISSING | |
| Aircraft | MISSING | |
| NPC generator (styles/builds/hair/accessories) | IMPLEMENTED | 4 clothing
      styles, grounded, deterministic |
| NPC professions | MISSING | |
| NPC rigging + animation clips | MISSING | |

## Parks / vegetation / ports / rail

| Area | Status | Notes |
|---|---|---|
| 11 park types + layout graph + facilities | IMPLEMENTED | verified clean |
| Trees/bushes (4 types × 4 seasons) | IMPLEMENTED | grounded, closed canopies |
| Hedges / flowerbeds as standalone assets | PARTIAL | flower beds exist only
      inside parks |
| Rail / trams / platforms / stations | MISSING | |
| Ports / docks / cranes / containers | MISSING | |

## Core systems

| Area | Status | Notes |
|---|---|---|
| MeshBuilder engine | IMPLEMENTED | weld, tokens, validate-safe indices |
| Material library (49 keys + tints) | IMPLEMENTED | shared, purged, tinted |
| Deterministic RNG | IMPLEMENTED | verified bit-identical rebuilds |
| Asset manager (collections/custom props/registry) | IMPLEMENTED | |
| Optimization (cleanup, budgets, LOD) | IMPLEMENTED | originals preserved |
| Export FBX/GLB + round-trip | IMPLEMENTED | verified by re-import |
| NL prompt (local parser + GLM bridge) | IMPLEMENTED | strict validation |
| UI panel | PARTIAL | flat asset-type list; needs category/kind selectors,
      recent assets |
| Tests (14 python + 43 Blender) | IMPLEMENTED | all passing |
| Rigging / animation export | MISSING | |

## Confirmed root causes to fix first

1. `properties.collect_params` gates colours behind `use_custom_colors`
   (default False) → colours appear dead.
2. `roads._markings` uses hardcoded z=0.165/0.166 — below the asphalt
   surface (0.18) → buried markings.
3. `props._traffic_light` draws a glass cover plate over the lamps.
4. Asset type changes do not apply type defaults (floors/style), so
   "skyscraper" builds with 5 floors.
5. No foundation plinth on buildings; houses lack entrance steps.
6. Category state (forms/styles) leaks across asset-type switches.
