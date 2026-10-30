# CityForge — Completed Features & Known Limitations

## Round 2 additions (quality + features)

### Geometry fixes (verified visually + by tests)
- [x] Street furniture: streetlight pole/arm/head gaps closed, industrial
      light heads connected to arms, traffic-light head bracketed, bench
      backrest supported, bus-stop posts run ground→roof (4 posts), timetable
      mounted on posts, hydrant nozzles connected, fence stray brace removed
- [x] Trees: trunk reaches into canopy, branches end inside foliage,
      evergreens without exposed stubs, ground-level root flare
- [x] Bushes: closed filled volumes (core + crown fill + satellites)
- [x] Storefront doors grounded (were floating 15 cm), door steps added
- [x] Roads: crosswalks no longer overhang the endpoints
- [x] MeshBuilder: repeated pole vertices collapsed to triangles so
      mesh.validate() never reorders polygons (this was silently corrupting
      material assignments on every asset with spheres/cylinders)
- [x] Storefront glazing de-coplaned (z-fighting fix) + proud mullions

### New features
- [x] Road classification: highway / single / two-lane / four-lane / one-way
      with medians (painted/raised/planted), barriers, one-way arrows
- [x] 5 modern skyscraper styles + tower forms (box/tapered/setback/
      tapered_setback/crown), facade grids (vertical/horizontal/ortho),
      crown lighting, grey/green glass
- [x] Residential forms (detached/townhouse/low/mid/high-rise) and commercial
      forms (small retail/restaurant/cafe/pub/office/shopping/mixed) with
      distinct massing
- [x] Architectural levels 1/2/3 (independent checkboxes, validated)
- [x] Colour system: custom colours + seeded coherent palettes via
      `key#hex` material tokens (shared tinted variants)
- [x] Vehicles: SUV, pickup, sports car, delivery truck + colours, window
      tint, size scale, random looks
- [x] Business identity: 9 categories, local seeded name generator, sign
      boards with real extruded 3D text joined into the building mesh
- [x] NPC characters: 4 clothing styles × builds × hair colours × accessories
      (LOW/MEDIUM/HIGH)
- [x] Parks: 11 types with layout graph (entrances → destinations), path
      network, ponds, flower beds, basketball/soccer courts, planters,
      grouped children (grounded), LOD support
- [x] 19 validated presets; extended test suites (14 + 43 tests)

## Completed and verified features (round 1)

### Architecture & registration
- [x] Modular add-on package (core / generators / ui / utils / presets / tests)
- [x] Registers/unregisters cleanly as a Blender extension **and** legacy add-on
- [x] Sidebar tab **CITYFORGE** with dashboard, generator, settings, generation,
      optimization and export sections; category-aware settings display
- [x] All operators functional (no placeholder buttons)

### Building generator (Phase 2/4)
- [x] 10 architectural styles with distinct massing, articulation and materials:
      modern residential, contemporary commercial, glass office tower,
      concrete apartment, brick residential, industrial warehouse,
      mixed-use urban, suburban house, traditional low-rise, modern high-rise
- [x] Real facade construction: piers, spandrels, headers, openings with
      recessed frames, glass, mullions, sills, lintels — no decal cubes
- [x] Storey separation (slab bands), corner pilasters, entrance portals with
      canopies
- [x] Ground-floor archetypes: retail/lobby storefronts (glass, mullions,
      signs, awnings), loading bays (ribbed roller doors, clerestory strips),
      garages, apartment entrances
- [x] Balconies (metal/concrete/glass) with platforms, railings, seeded
      patterns, aligned to window bays
- [x] Roofs: flat, flat+parapet, sloped, gable, hip, terrace; HVAC units,
      vents, ducts, water tanks, stair bulkheads, antennas
- [x] Setbacks + podiums for towers
- [x] 8 window types incl. curtain wall; randomized lit-window states
- [x] Deterministic seeds (bit-identical rebuilds, verified in tests);
      genuine variation across seeds

### Materials (Phase 3)
- [x] 44-key procedural material catalog (concrete/brick/glass/metal family,
      ground surfaces, foliage seasons, roofs, emissives)
- [x] Shared material instances (no duplicates), purging tool, re-apply tool
- [x] Per-object tint variation via custom property

### Roads & infrastructure (Phase 6)
- [x] Straight & curved roads with correct material zones (asphalt/sidewalk/
      curb/grass), curb faces, crown camber, edge lines, dashed center lines,
      zebra crosswalks
- [x] Bike/parking lane toggles, marking presets, standalone sidewalk asset

### Vegetation, props, vehicles (Phase 6)
- [x] Trees: 4 types × 4 seasons, parameters for height/trunk/canopy/
      branches/leaf density; bare winter twigs; bushes
- [x] 12 street-furniture builders + parking structure via building engine
- [x] 6 vehicle classes with colour variation

### Optimization & LODs (Phase 5)
- [x] LOW / MEDIUM / HIGH detail presets with polygon budgets and automatic
      budget fallback (two tiers) + budget warning flag
- [x] LOD generation (LOW/MEDIUM/HIGH copies)
- [x] Non-destructive optimize (weld doubles, delete loose, consistent
      normals) with optional originals preserved in CityForge_Originals
- [x] Polygon counter in dashboard and per asset

### Organization (Phase 1)
- [x] `CityForge_Assets` collection tree (Buildings/<sub>, Roads, Vegetation,
      Props, Vehicles)
- [x] Custom properties: params JSON, seed, type, style, detail, timestamp,
      polygon count, version
- [x] Regeneration from stored parameters

### Export (Phase 7)
- [x] FBX and GLB export, individual and batch, category sub-folders,
      no-overwrite policy
- [x] Unity conventions: 1 unit = 1 m, -Y forward, ground-centre origins
- [x] Round-trip verified (re-imported FBX/GLB match generated dimensions)

### Natural language (Phase 9)
- [x] Local deterministic keyword parser (types, floors, dimensions, styles,
      roofs, ground floors, balconies, seeds)
- [x] GLM bridge architecture (env-configured, schema-prompted, strict
      validation, no code execution) — inactive unless configured
- [x] Add-on fully functional without any AI service

### Testing (Phase 8)
- [x] 14 pure-Python unit tests (validation, coercion, NL parsing, schema
      completeness)
- [x] 24 in-Blender integration tests (all passing) covering registration,
      styles, determinism, mesh validity, naming, collections, material
      reuse, LODs, optimization, export, prompts, invalid inputs
- [x] Visual QA via rendered screenshots; multiple geometry/material bugs
      found and fixed (box rotation origin, cylinder axes, road profile
      duplication, marking z-coordinates, bush/balcony placement)

## Known limitations

1. **Procedural materials don't transfer to Unity.** FBX/GLB carry material
   *slots* named `CF_<key>`, but Blender procedural node graphs cannot be
   exported as textures. Assign game-side materials in Unity by slot name
   (a baked-texture workflow is a possible future addition).
2. **Curved roads use per-segment profiles**; with strong curvature the
   straight segments approximate the arc and may show faint facet seams.
   Markings on curves are axis-approximated at the ends.
3. **The local prompt parser is deliberately limited** — it extracts numbers
   and keywords; it cannot understand complex design intent. That requires
   the optional GLM bridge.
4. **Interiors are not modelled** (no rooms/furniture); window "interiors"
   are dark glass or emissive panels, which is standard for C:SL-style assets.
5. **No traffic simulation or road networks** — roads are visual assets, as
   specified.
6. **Windows are not boolean holes** through walls (panels butt together);
   glass sits recessed near the inner surface, so window views are opaque
   from a few grazing angles. This keeps geometry watertight and cheap.
7. **LOD copies are separate objects** — Unity handles LOD switching
   (or use the LOD names with your own system); no automatic Unity LODGroup
   setup.
8. **Blender version**: developed against 5.2.2 LTS; the manifest declares
   minimum 4.2. The legacy `bl_info` route keeps 4.x compatibility.
9. **Palm/poplar tree types** are simplified variations of the deciduous
   builder rather than species-accurate models.
10. **Very tall buildings (60 floors) at HIGH detail** can approach ~300k
    polygons; generation takes seconds (progress feedback is via the console
    log rather than a modal progress bar).
11. **Parks** assemble terrain + children; the child objects are plain
    Blender objects parented to the terrain (Unity: FBX/GLB keep the
    hierarchy). Very large parks at HIGH detail produce many objects —
    use LOW for background parks.
12. **Storefront glazing is opaque** by design (no modelled interiors behind
    it); door recesses read as dark glass panels.
13. **NPC characters are static props** (no rigging/animation) — intended as
    city dressing for simulation visuals.
