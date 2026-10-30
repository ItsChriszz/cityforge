# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene property groups mirroring GenerationParams.

The UI edits these Blender properties; generators receive a flat validated
GenerationParams produced by :func:`collect_params`.
"""

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, StringProperty)

from .core import params as P


def _enum_from(names, icons=None):
    items = []
    for i, n in enumerate(names):
        items.append((n, n.replace("_", " ").title(),
                      n.replace("_", " "), icons[i] if icons else "NONE", i))
    return items


# Main asset-type selector groups (kept short for a clean UI)
ASSET_TYPE_ITEMS = [
    ("RESIDENTIAL", "Residential Building", "Apartment buildings", "HOME", 0),
    ("COMMERCIAL", "Commercial Building", "Shops and stores", "SHOP", 1),
    ("OFFICE", "Office Building", "Offices and towers", "TEXT", 2),
    ("INDUSTRIAL", "Industrial", "Warehouses and industry", "MODIFIER", 3),
    ("MIXED", "Mixed Use", "Retail + residential", "SEQ_STRIP_DUPLICATE", 4),
    ("SKYSCRAPER", "Skyscraper", "Tall towers", "SORT_ASC", 5),
    ("HOUSE", "House", "Detached houses", "BLANK1", 6),
    ("SHOP", "Shop", "Small retail lots", "BLANK1", 7),
    ("WAREHOUSE", "Warehouse", "Logistics buildings", "PACKAGE", 8),
    ("ROAD", "Road", "Road segments", "MESH_PLANE", 9),
    ("SIDEWALK", "Sidewalk", "Sidewalk sections", "MESH_GRID", 10),
    ("CROSSWALK", "Crosswalk Piece", "Modular pedestrian crossing",
     "MESH_GRID", 11),
    ("TREE", "Tree", "Trees", "OUTLINER_OB_MESH", 11),
    ("BUSH", "Bush", "Shrubs and bushes", "OUTLINER_OB_FORCE_FIELD", 12),
    ("STREETLIGHT", "Streetlight", "Street lights", "LIGHT_POINT", 13),
    ("TRAFFIC_SIGN", "Traffic Sign", "Signs", "KEY_DES", 14),
    ("TRAFFIC_LIGHT", "Traffic Light", "Signal heads",
     "RESTRICT_COLOR_ON", 15),
    ("BENCH", "Bench", "Benches", "OBJECT_HIDDEN", 16),
    ("BUS_STOP", "Bus Stop", "Shelter stops", "SEQUENCE", 17),
    ("VEHICLE", "Vehicle", "Cars and trucks", "MESH_CUBE", 18),
    ("NPC", "Character (NPC)", "Low-poly people", "USER", 19),
    ("PARK", "Park", "Procedural park environments",
     "OUTLINER_OB_GROUP_INSTANCE", 20),
    ("CROSSWALK", "Crosswalk Piece", "Modular crossing road piece",
     "MESH_GRID", 21),
    ("INTERSECTION", "Intersection", "4-way crossing pad", "MESH_PLANE", 22),
    ("ROUNDABOUT", "Roundabout", "Ring road + island", "MESH_CIRCLE", 23),
    ("HEDGE", "Hedge", "Clipped hedge rows", "OUTLINER_OB_FORCE_FIELD", 24),
    ("FLOWERBED", "Flower Bed", "Blooming planters", "OUTLINER_OB_FORCE_FIELD", 25),
    ("BICYCLE", "Bicycle", "Pedal bikes", "NONE", 26),
    ("MOTORCYCLE", "Motorcycle", "Two-wheelers", "NONE", 27),
    ("TRACK", "Rail Track", "Straight rail track", "NONE", 28),
    ("TRACK_CURVED", "Curved Track", "Curved rail track", "NONE", 29),
    ("PLATFORM", "Rail Platform", "Platforms with shelter", "NONE", 30),
    ("STATION", "Rail Station", "Station building", "NONE", 31),
    ("RAIL_SIGNAL", "Rail Signal", "Track signals", "NONE", 32),
    ("CATENARY", "Catenary Post", "Overhead line posts", "NONE", 33),
    ("TRAIN_PASSENGER", "Passenger Train", "Rail carriage", "NONE", 34),
    ("TRAIN_FREIGHT", "Freight Wagon", "Cargo wagon", "NONE", 35),
    ("TRAM", "Tram", "Street tram", "NONE", 36),
    ("METRO_CAR", "Metro Car", "Metro carriage", "NONE", 37),
    ("MONORAIL", "Monorail", "Beam + car", "NONE", 38),
    ("DOCK", "Dock", "Pier on piles", "NONE", 39),
    ("CRANE", "Port Crane", "Gantry container crane", "NONE", 40),
    ("CONTAINER", "Container", "Shipping container", "NONE", 41),
    ("CONTAINER_STACK", "Container Stack", "Stacked containers", "NONE", 42),
    ("BOAT_SMALL", "Small Boat", "Rowboat / skiff", "NONE", 43),
    ("FISHING_BOAT", "Fishing Boat", "Working boat", "NONE", 44),
    ("SAILBOAT", "Sailboat", "Sailing yacht", "NONE", 45),
    ("YACHT", "Yacht", "Motor yacht", "NONE", 46),
    ("CARGO_SHIP", "Cargo Ship", "Container ship", "NONE", 47),
    ("FERRY", "Ferry", "Passenger ferry", "NONE", 48),
]


def style_update(self, context):
    """When the style changes, populate style-typical building defaults."""
    from .core.materials import catalog_base_color
    gp = context.scene.cityforge_building
    profile = P.STYLE_PROFILES.get(gp.style)
    if not profile:
        return
    for src, dst in (("window_type", "window_type"),
                     ("window_spacing", "window_spacing"),
                     ("window_sill", "window_sill"),
                     ("balcony_style", "balcony_style"),
                     ("balcony_frequency", "balcony_frequency"),
                     ("roof_type", "roof_type"),
                     ("ground_floor", "ground_floor"),
                     ("material_primary", "material_primary"),
                     ("material_secondary", "material_secondary"),
                     ("material_window", "material_window"),
                     ("material_trim", "material_trim"),
                     ("floor_height", "floor_height")):
        if src in profile:
            setattr(gp, dst, profile[src])
    if profile.get("signage") and gp.ground_floor == "apartment_entrance":
        gp.ground_floor = "retail"
    # colour pickers follow the style palette (the user can still override
    # them afterwards; overriding does NOT change until they edit a picker)
    for mat_key, color_prop in (
            ("material_primary", "color_primary"),
            ("material_secondary", "color_secondary"),
            ("material_window", "color_window"),
            ("material_trim", "color_trim")):
        base = catalog_base_color(getattr(gp, mat_key))
        if base:
            setattr(gp, color_prop, (*base, 1.0))


TYPE_DEFAULTS = {
    # asset_type: (style, floors, ground_floor, form_overrides)
    "RESIDENTIAL": ("modern_residential", 8, "apartment_entrance",
                    {"residential_form": "midrise_apartments"}),
    "COMMERCIAL": ("contemporary_commercial", 2, "retail",
                   {"commercial_form": "small_retail"}),
    "OFFICE": ("contemporary_commercial", 6, "office_lobby",
               {"commercial_form": "office_building"}),
    "INDUSTRIAL": ("industrial_warehouse", 2, "loading_bay", {}),
    "MIXED": ("mixed_use_urban", 6, "retail", {}),
    "SKYSCRAPER": ("glass_curtain_tower", 32, "office_lobby",
                   {"tower_form": "box", "podium_floors": 3,
                    "crown_lighting": True}),
    "HOUSE": ("modern_residential", 2, "apartment_entrance",
              {"residential_form": "detached_house"}),
    "SHOP": ("traditional_lowrise", 2, "retail",
             {"commercial_form": "small_retail"}),
    "WAREHOUSE": ("industrial_warehouse", 2, "loading_bay", {}),
    "PARKING_STRUCTURE": ("contemporary_commercial", 3, "garage", {}),
}


def asset_type_update(self, context):
    """Apply per-type defaults so switching to 'Skyscraper' genuinely
    produces a tall building (the user can still change every value)."""
    scene = context.scene
    bp = scene.cityforge_building
    style, floors, ground, extras = TYPE_DEFAULTS.get(
        self.asset_type, (None, None, None, {}))
    if style and style in P.ARCH_STYLES:
        bp.style = style          # triggers style_update (palette sync too)
    if floors:
        bp.floors = floors
    if ground:
        bp.ground_floor = ground
    for key, value in extras.items():
        if hasattr(bp, key):
            setattr(bp, key, value)


def road_class_update(self, context):
    """Road classification presets: lanes, widths and defaults."""
    rp = context.scene.cityforge_road
    presets = {
        "highway": dict(lane_count=4, lane_width=3.7, road_width=15.5,
                        sidewalk_enabled=False, median_enabled=True,
                        median_width=2.4, median_style="raised",
                        bike_lane=False, parking_lane=False,
                        markings="full", crosswalks=False, grass_strip=True),
        "single_lane": dict(lane_count=1, lane_width=3.2, road_width=6.5,
                            sidewalk_enabled=True, median_enabled=False,
                            markings="simple"),
        "two_lane": dict(lane_count=2, lane_width=3.5, road_width=9.0,
                         sidewalk_enabled=True, median_enabled=False,
                         markings="dashed"),
        "four_lane": dict(lane_count=4, lane_width=3.4, road_width=14.0,
                          sidewalk_enabled=True, median_enabled=True,
                          median_width=1.6, median_style="raised",
                          markings="full"),
        "one_way": dict(lane_count=2, lane_width=3.3, road_width=7.5,
                        sidewalk_enabled=True, median_enabled=False,
                        markings="full"),
    }
    for key, value in presets.get(rp.road_class, {}).items():
        try:
            setattr(rp, key, value)
        except (TypeError, AttributeError):
            pass


LEVEL_FLAGS = {
    "1": (True, False, False),
    "2": (True, True, False),
    "3": (True, True, True),
}


def level_update(self, context):
    """Map the single Level selector onto the engine's level gates."""
    flags = LEVEL_FLAGS.get(self.building_level, (True, True, True))
    gp = context.scene.cityforge_building
    gp.arch_level_1, gp.arch_level_2, gp.arch_level_3 = flags


def kind_items(self, context):
    """Dynamic enum: building kinds for the selected category (+ Auto)."""
    items = [("auto", "Auto (style default)", "Use the style's defaults",
              "NONE", 0)]
    cat = self.building_category
    for i, kind in enumerate(P.BUILDING_CATEGORIES.get(cat, [])):
        label = P.BUILDING_KINDS[kind]["label"]
        items.append((kind, label, kind.replace("_", " "), "NONE", i + 1))
    return items


def kind_update(self, context):
    """Apply the chosen building-kind preset (massing, style, floors)."""
    gp = context.scene.cityforge_building
    kind = gp.building_kind
    if not kind or kind == "auto":
        return
    preset = P.BUILDING_KINDS.get(kind)
    if not preset:
        return
    if preset.get("asset_type"):
        # set the type first (its update applies type defaults), then the
        # kind preset overrides the details
        context.scene.cityforge.asset_type = preset["asset_type"]
    for key, value in preset.items():
        if key == "label" or not hasattr(gp, key):
            continue
        try:
            setattr(gp, key, value)
        except (TypeError, AttributeError):
            pass


def form_update(self, context):
    """Apply residential/commercial form massing presets on selection."""
    gp = context.scene.cityforge_building
    if gp.residential_form not in ("auto", ""):
        preset = P.RESIDENTIAL_FORM_PRESETS.get(gp.residential_form, {})
    elif gp.commercial_form not in ("auto", ""):
        preset = P.COMMERCIAL_FORM_PRESETS.get(gp.commercial_form, {})
    else:
        return
    for key, value in preset.items():
        if hasattr(gp, key):
            try:
                setattr(gp, key, value)
            except (TypeError, AttributeError):
                pass


class CityForgeBuildingProps(bpy.types.PropertyGroup):
    # massing
    width: FloatProperty(
        name="Width", description="Building width along X (metres)",
        default=P.LIMITS["width"][2], min=P.LIMITS["width"][0],
        max=P.LIMITS["width"][1])
    depth: FloatProperty(
        name="Depth", description="Building depth along Y (metres)",
        default=P.LIMITS["depth"][2], min=P.LIMITS["depth"][0],
        max=P.LIMITS["depth"][1])
    floors: IntProperty(
        name="Floors", description="Number of storeys",
        default=int(P.LIMITS["floors"][2]), min=int(P.LIMITS["floors"][0]),
        max=int(P.LIMITS["floors"][1]))
    floor_height: FloatProperty(
        name="Floor Height", description="Storey height (metres)",
        default=P.LIMITS["floor_height"][2], min=P.LIMITS["floor_height"][0],
        max=P.LIMITS["floor_height"][1])
    style: EnumProperty(
        name="Architectural Style",
        description="Determines geometry, materials and proportions",
        items=_enum_from(P.ARCH_STYLES),
        default=P.ARCH_STYLES[0], update=style_update)

    window_type: EnumProperty(
        name="Window Type", description="Window shape across the facade",
        items=_enum_from(P.WINDOW_TYPES), default=P.WINDOW_TYPES[0])
    window_spacing: FloatProperty(
        name="Window Spacing", description="Bay spacing between windows",
        default=P.LIMITS["window_spacing"][2], min=P.LIMITS["window_spacing"][0],
        max=P.LIMITS["window_spacing"][1])
    window_width: FloatProperty(
        name="Window Width", default=P.LIMITS["window_width"][2],
        min=P.LIMITS["window_width"][0], max=P.LIMITS["window_width"][1])
    window_height: FloatProperty(
        name="Window Height", default=P.LIMITS["window_height"][2],
        min=P.LIMITS["window_height"][0], max=P.LIMITS["window_height"][1])
    window_sill: FloatProperty(
        name="Window Sill", description="Height of the sill above the slab",
        default=P.LIMITS.get("window_sill", (0.5, 2.5, 0.9))[2],
        min=0.2, max=2.5)
    frame_thickness: FloatProperty(
        name="Frame Thickness", default=P.LIMITS["frame_thickness"][2],
        min=P.LIMITS["frame_thickness"][0], max=P.LIMITS["frame_thickness"][1])
    window_light: EnumProperty(
        name="Window Lighting", description="Interior lighting states",
        items=_enum_from(P.WINDOW_LIGHT_STATES),
        default=P.WINDOW_LIGHT_STATES[2])
    mullions: BoolProperty(
        name="Window Mullions", description="Divide large panes with mullions",
        default=True)

    balcony_style: EnumProperty(
        name="Balcony Style", items=_enum_from(P.BALCONY_TYPES),
        default=P.BALCONY_TYPES[2])
    balcony_frequency: FloatProperty(
        name="Balcony Frequency", description="Share of bays with a balcony",
        default=0.5, min=0.0, max=1.0)
    balcony_depth: FloatProperty(
        name="Balcony Depth", default=P.LIMITS["balcony_depth"][2],
        min=P.LIMITS["balcony_depth"][0], max=P.LIMITS["balcony_depth"][1])

    roof_type: EnumProperty(
        name="Roof Type", items=_enum_from(P.ROOF_TYPES),
        default=P.ROOF_TYPES[1])
    roof_extras: IntProperty(
        name="Roof Equipment", description="HVAC units, vents, bulkhead, tank",
        default=int(P.LIMITS["roof_extras"][2]), min=int(P.LIMITS["roof_extras"][0]),
        max=int(P.LIMITS["roof_extras"][1]))
    rooftop_terrace: BoolProperty(
        name="Rooftop Terrace", default=False)

    ground_floor: EnumProperty(
        name="Ground Floor", items=_enum_from(P.GROUND_FLOOR_TYPES),
        default=P.GROUND_FLOOR_TYPES[2])
    podium_floors: IntProperty(
        name="Podium Floors", default=0, min=0, max=6)
    podium_width: FloatProperty(
        name="Podium Extra Width", description="Podium overhang per side",
        default=2.5, min=0.0, max=10.0)
    columns: BoolProperty(
        name="Corner Columns", description="Pilaster columns on corners",
        default=True)
    entrance: EnumProperty(
        name="Entrance Position",
        items=[("center", "Center", "Middle of the facade", "NONE", 0),
               ("corner", "Corner", "Near the side edge", "NONE", 1)],
        default="center")

    material_primary: EnumProperty(
        name="Primary Material", items=_enum_from([
            "concrete", "white_concrete", "dark_concrete", "brick_red",
            "brick_multicolor", "brick_brown", "dark_metal", "wood"]),
        default="white_concrete")
    material_secondary: EnumProperty(
        name="Secondary Material", items=_enum_from([
            "concrete", "white_concrete", "dark_concrete", "dark_metal",
            "painted_metal", "brick_red", "brick_multicolor", "brick_brown",
            "dark_glass", "grey_glass", "green_glass", "grime_metal",
            "wood"]),
        default="dark_concrete")
    material_window: EnumProperty(
        name="Window Material", items=_enum_from([
            "glass", "reflective_glass", "dark_glass", "blue_tinted_glass",
            "grey_glass", "green_glass"]),
        default="glass")
    material_trim: EnumProperty(
        name="Trim / Frame Material", items=_enum_from([
            "painted_metal", "dark_metal", "metal", "steel_frame", "wood"]),
        default="dark_metal")
    use_custom_colors: BoolProperty(
        name="Custom Colours",
        description="Tint primary/secondary/window/trim with the colour "
                    "pickers below", default=False)

    # architectural level gates (hidden; driven by the building_level selector)
    arch_level_1: BoolProperty(default=True)
    arch_level_2: BoolProperty(default=True)
    arch_level_3: BoolProperty(default=True)

    # architectural levels (single selector; drives the level gates)
    building_level: EnumProperty(
        name="Detail Level",
        description="Level 1 = basic structure, Level 2 = +facade detail, "
                    "Level 3 = complete (roof equipment, awnings, ornaments)",
        items=[("1", "Level 1 — Basic", "Foundation, walls, basic windows, "
               "roof, entrance — low polygons", "NONE", 0),
               ("2", "Level 2 — Enhanced", "+ facade detail, balconies, "
                "signage boards", "NONE", 1),
               ("3", "Level 3 — Complete", "+ roof equipment, awnings, "
                "ornaments, full detail", "NONE", 2)],
        default="3",
        update=level_update)

    # construction animation (optional)
    construction_animation: BoolProperty(
        name="Construction Animation",
        description="Generate the building as staged parts with a "
                    "rise-and-reveal animation (exportable to Unity)",
        default=False)
    construction_duration: FloatProperty(
        name="Duration (s)", description="Animation length in seconds",
        default=12.0, min=2.0, max=120.0)

    # diversity forms
    building_category: EnumProperty(
        name="Category", description="Building category",
        items=_enum_from(list(P.BUILDING_CATEGORIES.keys())),
        default=list(P.BUILDING_CATEGORIES.keys())[0],
        update=kind_update)
    building_kind: EnumProperty(
        name="Building Kind", description="Specific building archetype",
        items=kind_items, default=0, update=kind_update)
    residential_form: EnumProperty(
        name="Residential Form",
        description="Distinct residential building forms",
        items=_enum_from(P.RESIDENTIAL_FORMS), default=P.RESIDENTIAL_FORMS[0],
        update=form_update)
    commercial_form: EnumProperty(
        name="Commercial Form",
        description="Distinct commercial building forms",
        items=_enum_from(P.COMMERCIAL_FORMS), default=P.COMMERCIAL_FORMS[0],
        update=form_update)
    tower_form: EnumProperty(
        name="Tower Form", description="Skyscraper massing shape",
        items=_enum_from(P.TOWER_FORMS), default=P.TOWER_FORMS[0])
    facade_grid: EnumProperty(
        name="Facade Grid", description="Curtain-wall mullion rhythm",
        items=_enum_from(P.FACADE_GRIDS), default=P.FACADE_GRIDS[0])
    crown_lighting: BoolProperty(
        name="Crown Lighting",
        description="Emissive parapet band + corner light columns",
        default=False)

    # business identity
    business_category: EnumProperty(
        name="Business", description="Commercial ground-floor identity",
        items=_enum_from(P.BUSINESS_CATEGORIES),
        default=P.BUSINESS_CATEGORIES[0])
    business_name: StringProperty(
        name="Business Name",
        description="Manual sign text; empty = auto-generate from the "
                    "business category (local, seeded)", default="", maxlen=48)

    # colours
    use_random_palette: BoolProperty(
        name="Random Palette",
        description="Seeded coherent architectural colour palette "
                    "(overrides the explicit colours)", default=False)
    color_primary: FloatVectorProperty(
        name="Primary Colour", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.82, 0.81, 0.775, 1.0))
    color_secondary: FloatVectorProperty(
        name="Secondary Colour", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.34, 0.34, 0.35, 1.0))
    color_window: FloatVectorProperty(
        name="Window Glass Colour", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.45, 0.62, 0.80, 1.0))
    color_trim: FloatVectorProperty(
        name="Trim Colour", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.09, 0.10, 0.11, 1.0))


class CityForgeRoadProps(bpy.types.PropertyGroup):
    road_class: EnumProperty(
        name="Road Type", description="Classification presets lane count, "
        "width and defaults",
        items=_enum_from(P.ROAD_CLASSES), default=P.ROAD_CLASSES[2],
        update=road_class_update)
    road_direction: EnumProperty(
        name="Direction",
        items=[("two_way", "Two-way", "Traffic both directions", "NONE", 0),
               ("one_way_positive", "One-way +X", "One-way, forward "
                "arrow markings", "NONE", 1),
               ("one_way_negative", "One-way -X", "One-way, backward "
                "arrow markings", "NONE", 2)],
        default="two_way")
    road_width: FloatProperty(
        name="Road Width", default=P.LIMITS["road_width"][2],
        min=P.LIMITS["road_width"][0], max=P.LIMITS["road_width"][1])
    road_length: FloatProperty(
        name="Length", default=P.LIMITS["road_length"][2],
        min=P.LIMITS["road_length"][0], max=P.LIMITS["road_length"][1])
    curvature: FloatProperty(
        name="Curvature (deg)", description="Total bend across the length",
        default=0.0, min=0.0, max=90.0)
    lane_count: IntProperty(
        name="Lanes", default=int(P.LIMITS["lane_count"][2]),
        min=int(P.LIMITS["lane_count"][0]), max=int(P.LIMITS["lane_count"][1]))
    lane_width: FloatProperty(
        name="Lane Width", default=P.LIMITS["lane_width"][2],
        min=P.LIMITS["lane_width"][0], max=P.LIMITS["lane_width"][1])
    median_enabled: BoolProperty(name="Central Median", default=False)
    median_width: FloatProperty(
        name="Median Width", default=P.LIMITS["median_width"][2],
        min=P.LIMITS["median_width"][0], max=P.LIMITS["median_width"][1])
    median_style: EnumProperty(
        name="Median Style",
        items=_enum_from(P.MEDIAN_STYLES), default=P.MEDIAN_STYLES[1])
    sidewalk_enabled: BoolProperty(name="Sidewalks", default=True)
    sidewalk_width: FloatProperty(
        name="Sidewalk Width", default=P.LIMITS["sidewalk_width"][2],
        min=P.LIMITS["sidewalk_width"][0], max=P.LIMITS["sidewalk_width"][1])
    curb_height: FloatProperty(
        name="Curb Height", default=P.LIMITS["curb_height"][2],
        min=P.LIMITS["curb_height"][0], max=P.LIMITS["curb_height"][1])
    bike_lane: BoolProperty(name="Bicycle Lane", default=False)
    parking_lane: BoolProperty(name="Parking Lane", default=False)
    grass_strip: BoolProperty(name="Grass Verge", default=True)
    crosswalks: BoolProperty(name="Crosswalks", default=True)
    markings: EnumProperty(
        name="Markings", items=_enum_from(P.ROAD_MARKING_STYLES),
        default=P.ROAD_MARKING_STYLES[1])


class CityForgeVegProps(bpy.types.PropertyGroup):
    tree_type: EnumProperty(
        name="Tree Type", items=_enum_from(P.TREE_TYPES),
        default=P.TREE_TYPES[0])
    season: EnumProperty(
        name="Season", items=_enum_from(P.TREE_SEASONS),
        default=P.TREE_SEASONS[1])
    tree_height: FloatProperty(
        name="Height", default=P.LIMITS["tree_height"][2],
        min=P.LIMITS["tree_height"][0], max=P.LIMITS["tree_height"][1])
    trunk_radius: FloatProperty(
        name="Trunk Radius", default=P.LIMITS["trunk_radius"][2],
        min=P.LIMITS["trunk_radius"][0], max=P.LIMITS["trunk_radius"][1])
    canopy_radius: FloatProperty(
        name="Canopy Radius", default=P.LIMITS["canopy_radius"][2],
        min=P.LIMITS["canopy_radius"][0], max=P.LIMITS["canopy_radius"][1])
    branch_count: IntProperty(
        name="Branches", default=int(P.LIMITS["branch_count"][2]),
        min=int(P.LIMITS["branch_count"][0]), max=int(P.LIMITS["branch_count"][1]))
    leaf_density: FloatProperty(
        name="Leaf Density", description="Canopy blob count factor",
        default=0.7, min=0.0, max=1.0)


class CityForgePropProps(bpy.types.PropertyGroup):
    prop_height: FloatProperty(
        name="Height", default=P.LIMITS["prop_height"][2],
        min=P.LIMITS["prop_height"][0], max=P.LIMITS["prop_height"][1])
    prop_style: EnumProperty(
        name="Style", description="Visual styling family",
        items=_enum_from(["modern", "classic", "industrial"]),
        default="modern")
    fence_type: EnumProperty(
        name="Fence Type", items=_enum_from(P.FENCE_TYPES),
        default=P.FENCE_TYPES[0])
    fence_length: FloatProperty(
        name="Fence Length", default=10.0, min=1.0, max=100.0)
    sign_variants: EnumProperty(
        name="Sign Variant", description="Traffic sign type",
        items=_enum_from(P.SIGN_TYPES),
        default="stop")


class CityForgeParkProps(bpy.types.PropertyGroup):
    park_type: EnumProperty(
        name="Park Type", description="Layout preset",
        items=_enum_from(P.PARK_TYPES_LIST), default=P.PARK_TYPES_LIST[1])
    park_width: FloatProperty(
        name="Width", default=P.LIMITS["park_width"][2],
        min=P.LIMITS["park_width"][0], max=P.LIMITS["park_width"][1])
    park_length: FloatProperty(
        name="Length", default=P.LIMITS["park_length"][2],
        min=P.LIMITS["park_length"][0], max=P.LIMITS["park_length"][1])
    park_shape: EnumProperty(
        name="Shape", items=_enum_from(["auto", "rectangular", "square",
                                        "circular", "irregular"]),
        default="auto")
    park_entrances: IntProperty(
        name="Entrances", default=3, min=1, max=8)
    park_path_density: FloatProperty(
        name="Path Density", default=0.6, min=0.0, max=1.0)
    park_path_width: FloatProperty(
        name="Path Width", default=P.LIMITS["park_path_width"][2],
        min=P.LIMITS["park_path_width"][0], max=P.LIMITS["park_path_width"][1])
    park_tree_density: FloatProperty(
        name="Tree Density", default=1.0, min=0.0, max=3.0)
    park_bush_density: FloatProperty(
        name="Bush Density", default=1.0, min=0.0, max=3.0)
    park_seating_density: FloatProperty(
        name="Seating Density", default=1.0, min=0.0, max=3.0)
    park_light_density: FloatProperty(
        name="Lighting Density", default=1.0, min=0.0, max=3.0)
    park_water: BoolProperty(name="Water Features", default=True)
    park_sports: BoolProperty(name="Sports Facilities", default=True)
    park_fenced: BoolProperty(name="Fenced", default=False)
    park_name: StringProperty(
        name="Park Name", description="Entrance sign text (empty = auto)",
        default="", maxlen=48)


class CityForgeVehicleProps(bpy.types.PropertyGroup):
    vehicle_class: EnumProperty(
        name="Class", description="Body type of the vehicle",
        items=_enum_from(P.VEHICLE_CLASSES), default="sedan")
    vehicle_width: FloatProperty(
        name="Width", default=P.LIMITS["vehicle_width"][2],
        min=P.LIMITS["vehicle_width"][0], max=P.LIMITS["vehicle_width"][1])
    vehicle_length: FloatProperty(
        name="Length", default=P.LIMITS["vehicle_length"][2],
        min=P.LIMITS["vehicle_length"][0], max=P.LIMITS["vehicle_length"][1])
    vehicle_scale: FloatProperty(
        name="Size Scale", default=1.0, min=0.5, max=2.0)
    vehicle_random_look: BoolProperty(
        name="Random Appearance",
        description="Seeded random colours and details", default=False)
    vehicle_color_body: FloatVectorProperty(
        name="Body Colour", subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.55, 0.06, 0.05, 1.0))
    vehicle_color_roof: FloatVectorProperty(
        name="Roof Colour", subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.10, 0.10, 0.11, 1.0))
    vehicle_color_wheel: FloatVectorProperty(
        name="Wheel Colour", subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.03, 0.03, 0.035, 1.0))
    window_tint: FloatProperty(
        name="Window Tint", description="0 = clear, 1 = black",
        default=0.6, min=0.0, max=1.0)


class CityForgeNPCProps(bpy.types.PropertyGroup):
    npc_style: EnumProperty(
        name="Clothing Style", description="Outfit family",
        items=_enum_from(P.NPC_STYLES), default=P.NPC_STYLES[0])
    npc_gender: EnumProperty(
        name="Build", description="Body build variation",
        items=_enum_from(P.NPC_GENDERS), default=P.NPC_GENDERS[0])
    npc_age: EnumProperty(
        name="Age", description="Age range (changes proportions & height)",
        items=_enum_from(P.NPC_AGES), default=P.NPC_AGES[2])
    npc_profession: EnumProperty(
        name="Profession", description="Profession outfit & accessories",
        items=_enum_from(P.NPC_PROFESSIONS), default=P.NPC_PROFESSIONS[0])
    npc_height: FloatProperty(
        name="Height", description="Metres (varies with seeded jitter)",
        default=P.LIMITS["npc_height"][2], min=P.LIMITS["npc_height"][0],
        max=P.LIMITS["npc_height"][1])
    npc_accessories: BoolProperty(
        name="Accessories", description="Bags, helmets, caps, backpacks",
        default=True)
    npc_rigged: BoolProperty(
        name="Rig + Animation",
        description="Add a humanoid armature with an animation clip "
                    "(Unity-compatible bone names)", default=False)
    npc_clip: EnumProperty(
        name="Clip", description="Animation clip to bake",
        items=_enum_from(P.NPC_CLIPS), default=P.NPC_CLIPS[0])


class CityForgeExportProps(bpy.types.PropertyGroup):
    export_dir: StringProperty(
        name="Export Directory",
        description="Directory for exported asset files (FBX/GLB)",
        default="//CityForge_Export/", subtype='DIR_PATH',
        maxlen=1024)
    export_format: EnumProperty(
        name="Format",
        items=[("FBX", "FBX", "Autodesk FBX", "NONE", 0),
               ("GLB", "GLB", "Binary glTF", "NONE", 1)])
    apply_transforms: BoolProperty(
        name="Apply Transforms", description="Bake object transforms on export",
        default=True)


class CityForgeSettings(bpy.types.PropertyGroup):
    asset_type: EnumProperty(
        name="Asset Type", description="What to generate",
        items=ASSET_TYPE_ITEMS, default="RESIDENTIAL",
        update=asset_type_update)
    seed: IntProperty(
        name="Seed",
        description="Deterministic random seed: same seed, same result",
        default=1, min=0, max=P.LIMITS["seed"][1])
    detail_level: EnumProperty(
        name="Detail Level",
        description="LOW for distant assets, HIGH for hero assets",
        items=_enum_from(P.DET_LEVELS), default="medium")
    variation_count: IntProperty(
        name="Variations", description="Number of variations for batch buttons",
        default=5, min=1, max=50)
    preserve_originals: BoolProperty(
        name="Preserve Originals",
        description="Keep unoptimized copies in CityForge_Originals",
        default=True)
    prompt: StringProperty(
        name="Description",
        description="Describe the asset in plain language (needs GLM bridge "
                    "or the local parser)",
        default="", maxlen=1000)


# ---------------------------------------------------------------------------
# <-> GenerationParams conversion
# ---------------------------------------------------------------------------

_BUILDING_MAP = (
    ("width", "width"), ("depth", "depth"), ("floors", "floors"),
    ("floor_height", "floor_height"), ("style", "style"),
    ("window_type", "window_type"), ("window_spacing", "window_spacing"),
    ("window_width", "window_width"), ("window_height", "window_height"),
    ("window_sill", "window_sill"), ("frame_thickness", "frame_thickness"),
    ("window_light", "window_light"), ("mullions", "mullions"),
    ("balcony_style", "balcony_style"),
    ("balcony_frequency", "balcony_frequency"),
    ("balcony_depth", "balcony_depth"), ("roof_type", "roof_type"),
    ("roof_extras", "roof_extras"), ("rooftop_terrace", "rooftop_terrace"),
    ("ground_floor", "ground_floor"), ("podium_floors", "podium_floors"),
    ("podium_width", "podium_width"), ("columns", "columns"),
    ("entrance", "entrance"), ("material_primary", "material_primary"),
    ("material_secondary", "material_secondary"),
    ("material_window", "material_window"),
    ("material_trim", "material_trim"),
    ("arch_level_1", "arch_level_1"), ("arch_level_2", "arch_level_2"),
    ("arch_level_3", "arch_level_3"),
    ("building_level", "building_level"),
    ("construction_animation", "construction_animation"),
    ("construction_duration", "construction_duration"),
    ("building_category", "building_category"),
    ("building_kind", "building_kind"),
    ("residential_form", "residential_form"),
    ("commercial_form", "commercial_form"),
    ("tower_form", "tower_form"), ("facade_grid", "facade_grid"),
    ("crown_lighting", "crown_lighting"),
    ("business_category", "business_category"),
    ("business_name", "business_name"),
    ("use_random_palette", "use_random_palette"),
    ("use_custom_colors", "use_custom_colors"),
    ("color_primary", "color_primary"),
    ("color_secondary", "color_secondary"),
    ("color_window", "color_window"), ("color_trim", "color_trim"),
)

_ROAD_MAP = (
    ("road_width", "road_width"), ("road_length", "road_length"),
    ("road_curvature", "curvature"), ("lane_count", "lane_count"),
    ("lane_width", "lane_width"),
    ("road_class", "road_class"), ("road_direction", "road_direction"),
    ("median_enabled", "median_enabled"), ("median_width", "median_width"),
    ("median_style", "median_style"),
    ("sidewalk_width", "sidewalk_width"), ("curb_height", "curb_height"),
    ("sidewalk_enabled", "sidewalk_enabled"),
    ("bike_lane", "bike_lane"), ("parking_lane", "parking_lane"),
    ("grass_strip", "grass_strip"), ("crosswalks", "crosswalks"),
    ("road_markings", "markings"),
)

_VEG_MAP = (
    ("tree_type", "tree_type"), ("season", "season"),
    ("tree_height", "tree_height"), ("trunk_radius", "trunk_radius"),
    ("canopy_radius", "canopy_radius"), ("branch_count", "branch_count"),
    ("leaf_density", "leaf_density"),
)

_PROP_MAP = (
    ("prop_style", "prop_style"), ("prop_height", "prop_height"),
    ("fence_type", "fence_type"), ("fence_length", "fence_length"),
)

_VEHICLE_MAP = (
    ("vehicle_class", "vehicle_class"),
    ("vehicle_width", "vehicle_width"),
    ("vehicle_length", "vehicle_length"),
    ("vehicle_scale", "vehicle_scale"),
    ("vehicle_random_look", "vehicle_random_look"),
    ("vehicle_color_body", "vehicle_color_body"),
    ("vehicle_color_roof", "vehicle_color_roof"),
    ("vehicle_color_wheel", "vehicle_color_wheel"),
    ("window_tint", "window_tint"),
)

_NPC_MAP = (
    ("npc_style", "npc_style"), ("npc_gender", "npc_gender"),
    ("npc_age", "npc_age"), ("npc_profession", "npc_profession"),
    ("npc_height", "npc_height"), ("npc_accessories", "npc_accessories"),
    ("npc_rigged", "npc_rigged"), ("npc_clip", "npc_clip"),
)

_PARK_MAP = (
    ("park_type", "park_type"), ("park_width", "park_width"),
    ("park_length", "park_length"), ("park_shape", "park_shape"),
    ("park_entrances", "park_entrances"),
    ("park_path_density", "park_path_density"),
    ("park_path_width", "park_path_width"),
    ("park_tree_density", "park_tree_density"),
    ("park_bush_density", "park_bush_density"),
    ("park_seating_density", "park_seating_density"),
    ("park_light_density", "park_light_density"),
    ("park_water", "park_water"), ("park_sports", "park_sports"),
    ("park_fenced", "park_fenced"), ("park_name", "park_name"),
)


def _asset_effective_type(props) -> str:
    """Expand coarse categories to concrete generator types."""
    t = props.asset_type
    return t


def collect_params(context) -> "P.GenerationParams":
    scene = context.scene
    s = scene.cityforge
    params = P.GenerationParams()
    params.asset_type = s.asset_type
    params.seed = int(s.seed)
    params.detail_level = s.detail_level
    params.variation = 0

    bp = scene.cityforge_building
    for gkey, pkey in _BUILDING_MAP:
        setattr(params, gkey, getattr(bp, pkey))
    # the level selector drives the engine's level gates
    flags = LEVEL_FLAGS.get(bp.building_level, (True, True, True))
    params.arch_level_1, params.arch_level_2, params.arch_level_3 = flags
    if params.asset_type in ("SKYSCRAPER",):
        if not params.podium_floors:
            params.podium_floors = 2
    if params.asset_type == "PARKING_STRUCTURE":
        params.ground_floor = "garage"

    rp = scene.cityforge_road
    for gkey, pkey in _ROAD_MAP:
        setattr(params, gkey, getattr(rp, pkey))

    vp = scene.cityforge_veg
    for gkey, pkey in _VEG_MAP:
        setattr(params, gkey, getattr(vp, pkey))

    pp = scene.cityforge_prop
    for gkey, pkey in _PROP_MAP:
        setattr(params, gkey, getattr(pp, pkey))

    veh = scene.cityforge_vehicle
    for gkey, pkey in _VEHICLE_MAP:
        setattr(params, gkey, getattr(veh, pkey))

    np = scene.cityforge_npc
    for gkey, pkey in _NPC_MAP:
        setattr(params, gkey, getattr(np, pkey))

    pk = scene.cityforge_park
    for gkey, pkey in _PARK_MAP:
        setattr(params, gkey, getattr(pk, pkey))

    # only LOW/MEDIUM/HIGH allowed values reach the generators
    params.poly_budget = int(
        P.DETAIL_BUDGETS.get(params.detail_level, (0, 150000))[1])
    return params


def sync_from_params(context, params: "P.GenerationParams") -> None:
    """Push a GenerationParams back into the UI property groups."""
    scene = context.scene
    s = scene.cityforge
    s.seed = int(params.seed)
    s.detail_level = params.detail_level
    s.asset_type = params.asset_type
    for group, prop_map in (
            (scene.cityforge_building, _BUILDING_MAP),
            (scene.cityforge_road, _ROAD_MAP),
            (scene.cityforge_veg, _VEG_MAP),
            (scene.cityforge_prop, _PROP_MAP),
            (scene.cityforge_vehicle, _VEHICLE_MAP),
            (scene.cityforge_npc, _NPC_MAP),
            (scene.cityforge_park, _PARK_MAP)):
        for gkey, pkey in prop_map:
            if hasattr(group, pkey) and hasattr(params, gkey):
                try:
                    setattr(group, pkey, getattr(params, gkey))
                except (TypeError, AttributeError):
                    pass
    # derive the level selector from the engine gates
    bp = scene.cityforge_building
    if not params.arch_level_2:
        bp.building_level = "1"
    elif not params.arch_level_3:
        bp.building_level = "2"
    else:
        bp.building_level = "3"


CLASSES = [
    CityForgeBuildingProps,
    CityForgeRoadProps,
    CityForgeVegProps,
    CityForgePropProps,
    CityForgeVehicleProps,
    CityForgeNPCProps,
    CityForgeParkProps,
    CityForgeExportProps,
    CityForgeSettings,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    scene = bpy.types.Scene
    scene.cityforge = bpy.props.PointerProperty(type=CityForgeSettings)
    scene.cityforge_building = bpy.props.PointerProperty(
        type=CityForgeBuildingProps)
    scene.cityforge_road = bpy.props.PointerProperty(type=CityForgeRoadProps)
    scene.cityforge_veg = bpy.props.PointerProperty(type=CityForgeVegProps)
    scene.cityforge_prop = bpy.props.PointerProperty(type=CityForgePropProps)
    scene.cityforge_vehicle = bpy.props.PointerProperty(
        type=CityForgeVehicleProps)
    scene.cityforge_npc = bpy.props.PointerProperty(type=CityForgeNPCProps)
    scene.cityforge_park = bpy.props.PointerProperty(type=CityForgeParkProps)
    scene.cityforge_export = bpy.props.PointerProperty(
        type=CityForgeExportProps)


def unregister():
    scene = bpy.types.Scene
    for ptr in ("cityforge", "cityforge_building", "cityforge_road",
                "cityforge_veg", "cityforge_prop", "cityforge_vehicle",
                "cityforge_npc", "cityforge_park", "cityforge_export"):
        if hasattr(scene, ptr):
            delattr(scene, ptr)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)