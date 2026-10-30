# CityForge — Progress Log

## Round 3 (expansion) — current state

### Completed
- **Audit** (`EXPANSION_AUDIT.md`): full feature status matrix; 6 root causes
  confirmed by reproduction.
- **Colour system fixed**: the pickers are now always active and are synced
  to the style palette on style changes (style_update + apply_style_defaults
  via the shared PALETTE_BY_KEY registry). `use_custom_colors` gating removed.
  Verified: red primary → `CF_white_concrete_e53333` on the building.
- **Skyscraper height fixed**: `asset_type_update` applies per-type defaults
  (SKYSCRAPER → 32 floors, glass_curtain_tower, podium 3, crown lighting);
  verified SKY_FLOORS=32; user control preserved.
- **Category sanitization** (`sanitize_category`): industrial builds can no
  longer produce residential styles/forms/balconies/retail; residential
  clears commercial forms. Verified by test.
- **Building categories**: `BUILDING_KINDS` (31 kinds) + `BUILDING_CATEGORIES`
  (8 categories) with a two-level UI selector (category → kind) and
  preset application (`kind_update`). Includes school, hospital, hotel,
  bank, fire station, barn, distribution centre, strip mall and more.
- **Black banners**: `sign_dark` is now deep green; sign boards render with
  readable 3D text where a business exists.
- **Foundations**: every building gets a plinth; every door gets steps.
- **Road markings**: were buried 1.5 cm under the asphalt (z=0.165 vs
  surface 0.18) — all markings now sit on the surface + 5 mm. Verified for
  all 4 classes.
- **Traffic lights**: the glass cover plate removed; red/amber/green lamps
  sit proud of the housing (amber added).
- **15 sign variants** with dedicated materials + the Signs UI list.
- **Crosswalk road piece** (CROSSWALK): compact 7 m modular piece.
- **Highway furniture**: guardrails (posts + rails), roadside lighting,
  overhead green gantry sign.
- **Level selector**: single Level 1/2/3 enum replacing the checkboxes
  (mapped onto the same engine gates; tests updated).
- **Construction animation**: `build_building(parts_mode=True)` stages the
  build into foundation / podium / floor_NN / roof / equipment parts; the
  generator instantiates the parts as children of a root with
  hide + rise keyframes; play/stop operators; duration control.
  Verified: 8 parts, all animated, progressive visibility (1 part at f6 →
  5 at f80).
- **NPC professions** (18) with outfits/headwear/coat/accessory logic, ages
  (child/teen/adult/senior) with real proportion changes, facial hair,
  hairstyle variants; **rigging** (`rig_character`: 17 Unity-named bones,
  region-based vertex groups, armature parent) + **animation clips**
  (idle/walk/wave, cyclic).
- **Rail module** (`generators/rail.py`): straight/curved track, platform,
  station, signal, catenary, passenger/freight/tram/metro/monorail.
- **Port module** (`generators/port.py`): dock, gantry crane, containers,
  stacks, 6 watercraft (boat/fishing/sail/yacht/cargo/ferry) with the
  waterline at z=0.
- **More road infra**: INTERSECTION (4-way + aprons + crossings),
  ROUNDABOUT (ring + planted island + approaches).
- **More vehicles**: BICYCLE, MOTORCYCLE.
- **More vegetation**: HEDGE, FLOWERBED standalone assets.
- **UI**: two-level building selector, level selector, NPC profession/age/
  rig controls, construction-animation playback buttons, 30+ asset-type
  entries.
- **Tests**: 14 pure-Python + 55 Blender tests, all passing.

### In progress / remaining
- Curved-road intersections (roundabout connects, but curved approach
  trimming is approximate).
- Rigged NPCs: 3 clips (idle/walk/wave); more clips trivial to add.
- Unity-side rig mapping should be validated in a real Unity project.
- The UI "recent assets" list is provided by the Dashboard counters;
  a clickable recent list is future work.
