# SPDX-License-Identifier: GPL-3.0-or-later
"""Canonical parameter definitions, ranges and architectural style catalog.

This module is intentionally free of `bpy` dependencies so it can be unit
tested with plain Python outside Blender and also used as the validation
target for natural-language-supplied JSON (see core.nl_integration).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# RGBA colour tuple alias
Tuple4 = Tuple[float, float, float, float]

# ---------------------------------------------------------------------------
# Enumerations (single source of truth for enums, validation and UI)
# ---------------------------------------------------------------------------

ASSET_TYPES: List[str] = [
    "RESIDENTIAL", "COMMERCIAL", "OFFICE", "INDUSTRIAL", "MIXED",
    "SKYSCRAPER", "HOUSE", "SHOP", "WAREHOUSE",
    "ROAD", "SIDEWALK", "CROSSWALK", "INTERSECTION", "ROUNDABOUT",
    "STREETLIGHT", "TRAFFIC_SIGN", "TRAFFIC_LIGHT", "BENCH", "BUS_STOP",
    "PARKING_METER", "GARBAGE_BIN", "FENCE", "BOLLARD", "HYDRANT",
    "PLANTER", "BARRIER",
    "TREE", "BUSH", "HEDGE", "FLOWERBED",
    "VEHICLE", "BICYCLE", "MOTORCYCLE",
    "NPC",
    "PARK",
    "TRACK", "TRACK_CURVED", "PLATFORM", "STATION", "RAIL_SIGNAL",
    "CATENARY", "TRAIN_PASSENGER", "TRAIN_FREIGHT", "TRAM", "METRO_CAR",
    "MONORAIL",
    "DOCK", "CRANE", "CONTAINER", "CONTAINER_STACK", "BOAT_SMALL",
    "FISHING_BOAT", "SAILBOAT", "YACHT", "CARGO_SHIP", "FERRY",
    "PARKING_STRUCTURE",
]

VEGETATION_TYPES: List[str] = ["TREE", "BUSH", "HEDGE", "FLOWERBED"]
PROP_TYPES: List[str] = [
    "STREETLIGHT", "TRAFFIC_SIGN", "TRAFFIC_LIGHT", "BENCH", "BUS_STOP",
    "PARKING_METER", "GARBAGE_BIN", "FENCE", "BOLLARD", "HYDRANT",
    "PLANTER", "BARRIER",
    "PARKING_STRUCTURE",
]
ROAD_TYPES: List[str] = ["ROAD", "SIDEWALK", "CROSSWALK"]
ROAD_INFRA_TYPES: List[str] = ["INTERSECTION", "ROUNDABOUT"]

RAIL_ASSET_TYPES: List[str] = [
    "TRACK", "TRACK_CURVED", "PLATFORM", "STATION", "RAIL_SIGNAL",
    "CATENARY", "TRAIN_PASSENGER", "TRAIN_FREIGHT", "TRAM", "METRO_CAR",
    "MONORAIL",
]

PORT_ASSET_TYPES: List[str] = [
    "DOCK", "CRANE", "CONTAINER", "CONTAINER_STACK", "BOAT_SMALL",
    "FISHING_BOAT", "SAILBOAT", "YACHT", "CARGO_SHIP", "FERRY",
]

SIGN_TYPES: List[str] = [
    "stop", "yield", "speed_limit", "no_entry", "one_way", "directional",
    "street_name", "parking", "no_parking", "pedestrian_crossing",
    "construction", "hazard", "warning", "highway", "traffic_info",
]

BUILDING_TYPES: List[str] = [
    "RESIDENTIAL", "COMMERCIAL", "OFFICE", "INDUSTRIAL", "MIXED",
    "SKYSCRAPER", "HOUSE", "SHOP", "WAREHOUSE", "PARKING_STRUCTURE",
]

ARCH_STYLES: List[str] = [
    "modern_residential",
    "contemporary_commercial",
    "glass_office_tower",
    "concrete_apartment",
    "brick_residential",
    "industrial_warehouse",
    "mixed_use_urban",
    "suburban_house",
    "traditional_lowrise",
    "modern_highrise",
    # modern skyscraper styles (phase: skyscrapers)
    "glass_curtain_tower",
    "modern_office_skyscraper",
    "contemporary_residential_tower",
    "mixed_use_tower",
    "futuristic_tower",
]

RESIDENTIAL_FORMS: List[str] = [
    "auto", "detached_house", "townhouse", "lowrise_apartments",
    "midrise_apartments", "highrise_tower",
]

COMMERCIAL_FORMS: List[str] = [
    "auto", "small_retail", "restaurant", "cafe", "pub", "office_building",
    "shopping_building", "mixed_use",
]

TOWER_FORMS: List[str] = [
    "box", "tapered", "setback", "tapered_setback", "crown",
]

FACADE_GRIDS: List[str] = [
    "auto", "vertical", "horizontal", "ortho",
]

BUSINESS_CATEGORIES: List[str] = [
    "random", "restaurant", "cafe", "pub", "bar", "retail_shop",
    "grocery_store", "convenience_store", "office", "other",
]

NPC_STYLES: List[str] = [
    "random", "casual", "business", "construction", "pedestrian",
]

NPC_GENDERS: List[str] = ["random", "female", "male"]

NPC_AGES: List[str] = ["child", "teen", "adult", "senior"]

NPC_PROFESSIONS: List[str] = [
    "random", "lawyer", "accountant", "banker", "business", "chef",
    "doctor", "nurse", "construction", "teacher", "student", "police",
    "firefighter", "farmer", "fisherman", "retail", "delivery", "mechanic",
    "cyclist",
]

NPC_CLIPS: List[str] = ["idle", "walk", "wave"]

VEHICLE_CLASSES: List[str] = [
    "sedan", "hatchback", "suv", "pickup", "van", "delivery_truck",
    "bus", "taxi", "sports_car",
]

ROAD_CLASSES: List[str] = [
    "highway", "single_lane", "two_lane", "four_lane", "one_way",
]

MEDIAN_STYLES: List[str] = ["painted", "raised", "planted"]

PARK_TYPES_LIST: List[str] = [
    "neighbourhood_park", "community_park", "city_park", "urban_plaza",
    "botanical_garden", "waterfront_park", "dog_park", "playground_park",
    "sports_park", "formal_garden", "forest_park",
]

ROOF_TYPES: List[str] = [
    "flat", "flat_parapet", "sloped", "gable", "hip", "terrace",
]

WINDOW_TYPES: List[str] = [
    "rectangular", "tall", "wide", "ribbon", "curtain_wall", "arched",
    "strip", "picture",
]

GROUND_FLOOR_TYPES: List[str] = [
    "retail", "lobby", "apartment_entrance", "office_lobby",
    "loading_bay", "garage", "none",
]

BALCONY_TYPES: List[str] = ["none", "metal", "concrete", "glass"]

WINDOW_LIGHT_STATES: List[str] = ["always_dark", "always_lit", "random"]

DET_LEVELS: List[str] = ["low", "medium", "high"]

TREE_TYPES: List[str] = ["deciduous", "evergreen", "poplar", "palm"]

TREE_SEASONS: List[str] = ["spring", "summer", "autumn", "winter"]

FENCE_TYPES: List[str] = ["chain_link", "metal_panels", "wooden", "concrete"]

ROAD_MARKING_STYLES: List[str] = ["simple", "dashed", "full", "none"]

# ---------------------------------------------------------------------------
# Numeric limits:       (min, max, default)
# ---------------------------------------------------------------------------

LIMITS: Dict[str, Tuple[float, float, float]] = {
    "width": (3.0, 120.0, 16.0),
    "depth": (3.0, 120.0, 14.0),
    "floors": (1, 60, 5),
    "floor_height": (2.2, 6.0, 3.1),
    "window_spacing": (1.0, 8.0, 2.4),
    "window_width": (0.5, 6.0, 1.6),
    "window_height": (0.5, 4.5, 1.7),
    "frame_thickness": (0.02, 0.25, 0.06),
    "balcony_depth": (0.5, 3.0, 1.4),
    "trim_width": (0.02, 0.6, 0.08),
    "footprint_margin": (0.0, 3.0, 0.15),
    "podium_floors": (0, 6, 0),
    "roof_extras": (0, 20, 6),
    "seed": (0, 2**31 - 1, 1),
    # roads
    "road_width": (3.0, 40.0, 9.0),
    "road_length": (5.0, 500.0, 60.0),
    "sidewalk_width": (0.5, 12.0, 2.5),
    "curb_height": (0.02, 0.4, 0.15),
    "road_curvature": (0.0, 90.0, 0.0),
    "lane_count": (1, 6, 2),
    # vegetation
    "tree_height": (1.5, 45.0, 9.0),
    "trunk_radius": (0.03, 2.0, 0.28),
    "canopy_radius": (0.3, 18.0, 3.0),
    "branch_count": (0, 12, 5),
    # props
    "prop_height": (0.3, 14.0, 4.0),
    # vehicle
    "vehicle_width": (1.2, 3.6, 1.9),
    "vehicle_length": (2.5, 18.0, 4.6),
    "vehicle_scale": (0.5, 2.0, 1.0),
    "window_tint": (0.0, 1.0, 0.6),
    # NPC
    "npc_height": (1.2, 2.1, 1.75),
    # road classification
    "lane_width": (2.5, 5.0, 3.5),
    "median_width": (0.4, 6.0, 1.6),
    # parks
    "park_width": (8.0, 400.0, 44.0),
    "park_length": (8.0, 400.0, 56.0),
    "park_entrances": (1, 8, 3),
    "park_path_density": (0.0, 1.0, 0.6),
    "park_path_width": (0.8, 8.0, 2.2),
    "park_tree_density": (0.0, 3.0, 1.0),
    "park_bush_density": (0.0, 3.0, 1.0),
    "park_seating_density": (0.0, 3.0, 1.0),
    "park_light_density": (0.0, 3.0, 1.0),
}

# number of polygons, hard safety ceiling for any single asset
POLYGON_CEILING = 400_000

DETAIL_BUDGETS: Dict[str, Tuple[float, float]] = {
    "low": (3_000, 25_000),
    "medium": (8_000, 120_000),
    "high": (15_000, 300_000),
}


@dataclass
class ParamSpec:
    """Declarative parameter descriptor used by validation and by the GLM
    JSON-schema generator."""

    key: str
    ptype: str                      # int | float | str | bool | list
    choices: Optional[List[str]] = None
    limits: Optional[Tuple[float, float]] = None
    required: bool = False
    description: str = ""


# Spec for the natural-language JSON payload (section 11 of the project spec)
NL_SCHEMA: List[ParamSpec] = [
    ParamSpec("asset_type", "str", choices=ASSET_TYPES, required=True,
              description="Which asset to build"),
    ParamSpec("style", "str", choices=ARCH_STYLES + ["auto"],
              description="Architectural style"),
    ParamSpec("floors", "int", limits=(LIMITS["floors"][0], LIMITS["floors"][1])),
    ParamSpec("width", "float", limits=LIMITS["width"][:2]),
    ParamSpec("depth", "float", limits=LIMITS["depth"][:2]),
    ParamSpec("floor_height", "float", limits=LIMITS["floor_height"][:2]),
    ParamSpec("roof_type", "str", choices=ROOF_TYPES),
    ParamSpec("balcony_style", "str", choices=BALCONY_TYPES),
    ParamSpec("window_type", "str", choices=WINDOW_TYPES),
    ParamSpec("ground_floor", "str", choices=GROUND_FLOOR_TYPES),
    ParamSpec("materials", "dict",
              description="Map with optional keys primary/secondary/windows/trim"),
    ParamSpec("detail_level", "str", choices=DET_LEVELS),
    ParamSpec("seed", "int", limits=LIMITS["seed"][:2]),
]

# ---------------------------------------------------------------------------


@dataclass
class GenerationParams:
    """Flat, validated, engine-facing description of one CityForge asset.

    The Blender-facing property groups (properties.py) mirror these fields.
    """

    asset_type: str = "RESIDENTIAL"
    style: str = "modern_residential"

    # building mass
    width: float = 16.0
    depth: float = 14.0
    floors: int = 5
    floor_height: float = 3.1

    # facade
    window_type: str = "rectangular"
    window_spacing: float = 2.4
    window_width: float = 1.6
    window_height: float = 1.7
    window_sill: float = 0.9
    frame_thickness: float = 0.06
    window_light: str = "random"
    mullions: bool = True

    # balconies
    balcony_style: str = "concrete"
    balcony_frequency: float = 0.5     # share of bays that get balconies
    balcony_depth: float = 1.4

    # roof
    roof_type: str = "flat_parapet"
    roof_extras: int = 6
    rooftop_terrace: bool = False

    # ground / structure
    ground_floor: str = "apartment_entrance"
    floor_collapse: float = 1.0        # ground floor height multiplier
    podium_floors: int = 0
    podium_width: float = 0.0          # extra footprint around the tower
    entrance: str = "center"
    columns: bool = True
    trim_width: float = 0.08

    # materials (keys into the material library)
    material_primary: str = "concrete"
    material_secondary: str = "dark_concrete"
    material_window: str = "glass"
    material_trim: str = "dark_metal"
    material_accent: str = "white_concrete"

    # generation control
    detail_level: str = "medium"
    poly_budget: int = POLYGON_CEILING
    seed: int = 1
    variation: int = 0

    # architectural levels (independent checkboxes)
    arch_level_1: bool = True     # structure: massing, windows, roof, doors
    arch_level_2: bool = True     # facade detail: trim, balconies, signage boards
    arch_level_3: bool = True     # premium: roof clutter, awnings, ornaments

    # construction animation (buildings, optional)
    construction_animation: bool = False
    construction_duration: float = 12.0   # seconds at scene fps

    # building diversity forms
    residential_form: str = "auto"      # detached/townhouse/lowrise/...
    commercial_form: str = "auto"       # small_retail/restaurant/cafe/...
    building_kind: str = "auto"         # BUILDING_KINDS key (category system)
    tower_form: str = "box"             # box/tapered/setback/tapered_setback/crown
    facade_grid: str = "auto"           # curtain-wall mullion rhythm
    crown_lighting: bool = False        # architectural crown lighting

    # business identity (commercial ground floors)
    business_category: str = "random"
    business_name: str = ""             # empty -> auto-generate per seed

    # colour customization (RGBA 0..1); None-able via use flags
    use_random_palette: bool = False    # coherent seeded palette
    use_custom_colors: bool = False     # use the explicit colour pickers
    color_primary: Tuple4 = (0.82, 0.81, 0.775, 1.0)
    color_secondary: Tuple4 = (0.34, 0.34, 0.35, 1.0)
    color_window: Tuple4 = (0.45, 0.62, 0.80, 1.0)
    color_trim: Tuple4 = (0.09, 0.10, 0.11, 1.0)

    # roads
    road_width: float = 9.0
    road_length: float = 60.0
    road_curvature: float = 0.0
    lane_count: int = 2
    sidewalk_width: float = 2.5
    sidewalk_enabled: bool = True
    curb_height: float = 0.15
    bike_lane: bool = False
    parking_lane: bool = False
    grass_strip: bool = True
    crosswalks: bool = True
    road_markings: str = "dashed"

    # vegetation
    tree_type: str = "deciduous"
    tree_height: float = 9.0
    trunk_radius: float = 0.28
    canopy_radius: float = 3.0
    branch_count: int = 5
    leaf_density: float = 0.7
    season: str = "summer"

    # props
    prop_style: str = "modern"
    prop_height: float = 4.0
    fence_type: str = "chain_link"
    fence_length: float = 10.0
    sign_variants: str = "stop"

    # vehicle
    vehicle_class: str = "sedan"
    vehicle_width: float = 1.9
    vehicle_length: float = 4.6
    vehicle_scale: float = 1.0
    vehicle_color_body: Tuple4 = (0.55, 0.06, 0.05, 1.0)
    vehicle_color_roof: Tuple4 = (0.10, 0.10, 0.11, 1.0)
    vehicle_color_wheel: Tuple4 = (0.03, 0.03, 0.035, 1.0)
    window_tint: float = 0.6          # 0 = clear, 1 = black
    vehicle_random_look: bool = False

    # NPC characters
    npc_style: str = "random"
    npc_gender: str = "random"
    npc_age: str = "adult"            # child/teen/adult/senior
    npc_profession: str = "random"    # PROFESSIONS key or random/none
    npc_height: float = 1.75          # metres
    npc_accessories: bool = True
    npc_rigged: bool = False
    npc_clip: str = "idle"            # idle/walk/wave

    # road classification
    road_class: str = "two_lane"
    road_direction: str = "two_way"   # two_way | one_way_positive | one_way_negative
    median_enabled: bool = False
    median_width: float = 1.6
    median_style: str = "raised"
    lane_width: float = 3.5

    # parks
    park_type: str = "community_park"
    park_width: float = 44.0
    park_length: float = 56.0
    park_shape: str = "auto"          # rectangular/square/circular/irregular/auto
    park_entrances: int = 3
    park_path_density: float = 0.6
    park_path_width: float = 2.2
    park_tree_density: float = 1.0
    park_bush_density: float = 1.0
    park_seating_density: float = 1.0
    park_light_density: float = 1.0
    park_water: bool = True
    park_sports: bool = True
    park_fenced: bool = False
    park_name: str = ""               # entrance signage text (auto if empty)

    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    @property
    def height(self) -> float:
        return self.floors * self.floor_height

    def to_dict(self) -> Dict[str, Any]:
        return {
            k: getattr(self, k)
            for k in self.__dataclass_fields__
            if k != "extra"
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationParams":
        params = cls()
        for key, value in data.items():
            if hasattr(params, key):
                setattr(params, key, value)
        return params

    def footprint(self) -> Tuple[float, float]:
        return (self.width, self.depth)


# ---------------------------------------------------------------------------
# Style catalog: how a named architectural style biases every parameter.
# ---------------------------------------------------------------------------

StyleProfile = Dict[str, Any]

STYLE_PROFILES: Dict[str, StyleProfile] = {
    "modern_residential": {
        "window_type": "rectangular",
        "window_spacing": 2.6,
        "window_sill": 0.95,
        "balcony_style": "glass",
        "balcony_frequency": 0.65,
        "roof_type": "flat_parapet",
        "ground_floor": "apartment_entrance",
        "material_primary": "white_concrete",
        "material_secondary": "dark_concrete",
        "material_window": "glass",
        "material_trim": "dark_metal",
        "floor_height": 3.0,
        "setbacks": False,
    },
    "contemporary_commercial": {
        "window_type": "ribbon",
        "window_sill": 1.0,
        "window_height": 1.9,
        "balcony_style": "none",
        "roof_type": "flat",
        "ground_floor": "retail",
        "material_primary": "dark_concrete",
        "material_secondary": "painted_metal",
        "material_window": "reflective_glass",
        "material_trim": "dark_metal",
        "floor_height": 3.4,
        "signage": True,
    },
    "glass_office_tower": {
        "window_type": "curtain_wall",
        "window_sill": 0.35,
        "window_height": 2.4,
        "window_spacing": 1.5,
        "balcony_style": "none",
        "roof_type": "flat",
        "ground_floor": "office_lobby",
        "material_primary": "dark_glass",
        "material_secondary": "dark_metal",
        "material_window": "blue_tinted_glass",
        "material_trim": "dark_metal",
        "floor_height": 3.6,
        "columns": True,
        "setbacks": True,
        "podium_floors": 2,
    },
    "concrete_apartment": {
        "window_type": "rectangular",
        "window_spacing": 2.2,
        "window_sill": 1.05,
        "balcony_style": "concrete",
        "balcony_frequency": 0.55,
        "roof_type": "flat_parapet",
        "ground_floor": "apartment_entrance",
        "material_primary": "concrete",
        "material_secondary": "dark_concrete",
        "material_window": "glass",
        "material_trim": "painted_metal",
        "floor_height": 2.8,
    },
    "brick_residential": {
        "window_type": "tall",
        "window_spacing": 2.4,
        "window_sill": 1.0,
        "balcony_style": "metal",
        "balcony_frequency": 0.35,
        "roof_type": "gable",
        "ground_floor": "apartment_entrance",
        "material_primary": "brick_red",
        "material_secondary": "concrete",
        "material_window": "glass",
        "material_trim": "painted_metal",
        "floor_height": 3.0,
        "corners_columns": False,
    },
    "industrial_warehouse": {
        "window_type": "strip",
        "window_sill": 2.2,
        "window_height": 1.1,
        "balcony_style": "none",
        "roof_type": "sloped",
        "roof_extras": 10,
        "ground_floor": "loading_bay",
        "material_primary": "dark_metal",
        "material_secondary": "concrete",
        "material_window": "glass",
        "material_trim": "painted_metal",
        "floor_height": 4.6,
        "columns": True,
    },
    "mixed_use_urban": {
        "window_type": "rectangular",
        "window_spacing": 2.5,
        "window_sill": 1.0,
        "balcony_style": "metal",
        "balcony_frequency": 0.4,
        "roof_type": "flat_parapet",
        "ground_floor": "retail",
        "material_primary": "brick_multicolor",
        "material_secondary": "concrete",
        "material_window": "glass",
        "material_trim": "painted_metal",
        "floor_height": 3.2,
        "signage": True,
    },
    "suburban_house": {
        "window_type": "picture",
        "window_spacing": 3.2,
        "window_sill": 0.95,
        "balcony_style": "none",
        "roof_type": "hip",
        "roof_pitch": 0.55,
        "ground_floor": "apartment_entrance",
        "material_primary": "wood",
        "material_secondary": "concrete",
        "material_window": "glass",
        "material_trim": "painted_metal",
        "floor_height": 2.8,
        "attached_structure": True,
    },
    "traditional_lowrise": {
        "window_type": "arched",
        "window_spacing": 2.8,
        "window_sill": 1.05,
        "balcony_style": "none",
        "roof_type": "gable",
        "roof_pitch": 0.5,
        "ground_floor": "retail",
        "material_primary": "brick_brown",
        "material_secondary": "concrete",
        "material_window": "glass",
        "material_trim": "painted_metal",
        "floor_height": 3.4,
        "signage": True,
    },
    "modern_highrise": {
        "window_type": "curtain_wall",
        "window_sill": 0.4,
        "window_height": 2.2,
        "window_spacing": 1.9,
        "balcony_style": "none",
        "roof_type": "flat",
        "ground_floor": "office_lobby",
        "material_primary": "white_concrete",
        "material_secondary": "dark_glass",
        "material_window": "reflective_glass",
        "material_trim": "dark_metal",
        "floor_height": 3.3,
        "columns": True,
        "setbacks": True,
    },
    # --- modern skyscraper styles -----------------------------------------
    "glass_curtain_tower": {
        "window_type": "curtain_wall",
        "window_sill": 0.30,
        "window_height": 2.6,
        "window_spacing": 1.4,
        "balcony_style": "none",
        "roof_type": "flat",
        "ground_floor": "office_lobby",
        "material_primary": "grey_glass",
        "material_secondary": "dark_metal",
        "material_window": "blue_tinted_glass",
        "material_trim": "steel_frame",
        "floor_height": 3.5,
        "columns": False,
        "tower_form": "box",
        "facade_grid": "vertical",
        "crown_lighting": True,
    },
    "modern_office_skyscraper": {
        "window_type": "curtain_wall",
        "window_sill": 0.35,
        "window_height": 2.4,
        "window_spacing": 1.7,
        "balcony_style": "none",
        "roof_type": "flat",
        "ground_floor": "office_lobby",
        "material_primary": "dark_metal",
        "material_secondary": "dark_glass",
        "material_window": "reflective_glass",
        "material_trim": "steel_frame",
        "floor_height": 3.6,
        "columns": True,
        "tower_form": "setback",
        "facade_grid": "ortho",
    },
    "contemporary_residential_tower": {
        "window_type": "curtain_wall",
        "window_sill": 0.45,
        "window_height": 2.1,
        "window_spacing": 2.1,
        "balcony_style": "glass",
        "balcony_frequency": 0.7,
        "roof_type": "flat_parapet",
        "ground_floor": "office_lobby",
        "material_primary": "white_concrete",
        "material_secondary": "grey_glass",
        "material_window": "blue_tinted_glass",
        "material_trim": "dark_metal",
        "floor_height": 3.1,
        "tower_form": "tapered",
        "facade_grid": "horizontal",
        "crown_lighting": True,
    },
    "mixed_use_tower": {
        "window_type": "curtain_wall",
        "window_sill": 0.40,
        "window_height": 2.2,
        "window_spacing": 1.8,
        "balcony_style": "glass",
        "balcony_frequency": 0.5,
        "roof_type": "flat",
        "ground_floor": "retail",
        "material_primary": "concrete",
        "material_secondary": "green_glass",
        "material_window": "green_glass",
        "material_trim": "dark_metal",
        "floor_height": 3.3,
        "tower_form": "setback",
        "podium_floors": 3,
        "facade_grid": "ortho",
    },
    "futuristic_tower": {
        "window_type": "curtain_wall",
        "window_sill": 0.30,
        "window_height": 2.8,
        "window_spacing": 1.2,
        "balcony_style": "none",
        "roof_type": "flat",
        "ground_floor": "office_lobby",
        "material_primary": "grey_glass",
        "material_secondary": "steel_frame",
        "material_window": "reflective_glass",
        "material_trim": "steel_frame",
        "floor_height": 3.8,
        "columns": False,
        "tower_form": "tapered_setback",
        "facade_grid": "horizontal",
        "crown_lighting": True,
    },
}

# residential / commercial sub-form presets: massing + entrance behaviour
RESIDENTIAL_FORM_PRESETS: Dict[str, StyleProfile] = {
    "detached_house": {
        "width": 10.0, "depth": 8.0, "floors": 2, "floor_height": 2.9,
        "roof_type": "hip", "ground_floor": "apartment_entrance",
        "window_type": "picture", "balcony_style": "none",
        "material_primary": "wood",
    },
    "townhouse": {
        "width": 6.0, "depth": 9.0, "floors": 3, "floor_height": 2.9,
        "roof_type": "flat_parapet", "ground_floor": "apartment_entrance",
        "window_type": "tall", "balcony_style": "metal",
        "balcony_frequency": 0.5, "material_primary": "brick_red",
    },
    "lowrise_apartments": {
        "floors": 4, "ground_floor": "apartment_entrance",
        "roof_type": "flat_parapet",
    },
    "midrise_apartments": {
        "floors": 8, "ground_floor": "apartment_entrance",
        "roof_type": "flat_parapet", "balcony_frequency": 0.6,
    },
    "highrise_tower": {
        "floors": 18, "ground_floor": "office_lobby",
        "roof_type": "flat", "balcony_style": "glass",
        "balcony_frequency": 0.65,
    },
}

COMMERCIAL_FORM_PRESETS: Dict[str, StyleProfile] = {
    "small_retail": {
        "floors": 1, "depth": 12.0, "ground_floor": "retail",
        "roof_type": "flat_parapet",
    },
    "restaurant": {
        "floors": 2, "ground_floor": "retail", "roof_type": "flat_parapet",
    },
    "cafe": {
        "floors": 1, "width": 8.0, "depth": 9.0, "ground_floor": "retail",
        "roof_type": "flat_parapet",
    },
    "pub": {
        "floors": 2, "width": 9.0, "depth": 10.0, "ground_floor": "retail",
        "roof_type": "flat_parapet",
    },
    "office_building": {
        "floors": 5, "ground_floor": "office_lobby", "roof_type": "flat",
        "window_type": "ribbon",
    },
    "shopping_building": {
        "floors": 2, "width": 26.0, "depth": 18.0, "ground_floor": "retail",
        "roof_type": "flat",
    },
    "mixed_use": {
        "floors": 6, "ground_floor": "retail", "roof_type": "flat_parapet",
    },
}

# house/warehouse etc. need asset type -> default style mapping
TYPE_DEFAULT_STYLE: Dict[str, str] = {
    "RESIDENTIAL": "modern_residential",
    "COMMERCIAL": "contemporary_commercial",
    "OFFICE": "glass_office_tower",
    "INDUSTRIAL": "industrial_warehouse",
    "MIXED": "mixed_use_urban",
    "SKYSCRAPER": "modern_highrise",
    "HOUSE": "suburban_house",
    "SHOP": "traditional_lowrise",
    "WAREHOUSE": "industrial_warehouse",
    "PARKING_STRUCTURE": "mixed_use_urban",
}

# ---------------------------------------------------------------------------
# Style application helper for non-UI paths (scripts, tests, future GLM)
# ---------------------------------------------------------------------------

# palette registry: material key -> base RGB, populated by the material
# library at import time (kept here so params stays bpy-free)
PALETTE_BY_KEY: Dict[str, tuple] = {}


def apply_style_defaults(params: GenerationParams) -> GenerationParams:
    """Copy style-typical values onto a GenerationParams instance.

    Mirrors the behaviour of the UI `style` update callback so scripts and AI
    payloads that only set `style` produce consistent buildings.  Non-UI
    profile hints (signage, setbacks, roof pitch) are ignored here.
    Also syncs the colour pickers to the style palette so the colours the
    user sees always match the colours the generator will use.
    """
    profile = STYLE_PROFILES.get(params.style)
    if not profile:
        return params
    for key, value in profile.items():
        if key in ("roof_pitch", "corners_columns", "attached_structure",
                   "signage", "setbacks"):
            continue
        if hasattr(params, key):
            setattr(params, key, value)
    for mat_key, color_attr in (
            ("material_primary", "color_primary"),
            ("material_secondary", "color_secondary"),
            ("material_window", "color_window"),
            ("material_trim", "color_trim")):
        base = PALETTE_BY_KEY.get(getattr(params, mat_key, ""))
        if base:
            setattr(params, color_attr, (base[0], base[1], base[2], 1.0))
    return params


def apply_form_defaults(params: GenerationParams) -> GenerationParams:
    """Apply the building-kind / residential / commercial form presets.

    Called after style defaults; form presets may override massing fields
    (width/depth/floors) but respect explicitly-set style fields.
    """
    kind = getattr(params, "building_kind", "auto")
    if kind and kind != "auto" and kind in BUILDING_KINDS:
        preset = BUILDING_KINDS[kind]
        for key, value in preset.items():
            if key == "label":
                continue
            if hasattr(params, key):
                setattr(params, key, value)
        return params
    if params.asset_type == "HOUSE":
        params.residential_form = "detached_house"
    if params.residential_form not in ("auto", ""):
        preset = RESIDENTIAL_FORM_PRESETS.get(params.residential_form, {})
        for key, value in preset.items():
            if hasattr(params, key):
                setattr(params, key, value)
    if params.commercial_form not in ("auto", ""):
        preset = COMMERCIAL_FORM_PRESETS.get(params.commercial_form, {})
        for key, value in preset.items():
            if hasattr(params, key):
                setattr(params, key, value)
    return params


def apply_arch_levels(params: GenerationParams) -> GenerationParams:
    """Validate the independent architectural level checkboxes.

    Levels 2 and 3 build on level 1: if level 1 is disabled but 2 or 3 are
    enabled, level 1 is force-enabled and the change is recorded so callers
    can surface it.
    """
    if not params.arch_level_1 and (params.arch_level_2
                                    or params.arch_level_3):
        params.arch_level_1 = True
        params.extra["levels_note"] = (
            "level 2/3 requires level 1; level 1 was enabled")
    if not any((params.arch_level_1, params.arch_level_2,
                params.arch_level_3)):
        params.arch_level_1 = True
        params.extra["levels_note"] = "all levels off: structure only"
    return params


INDUSTRIAL_TYPES = {"INDUSTRIAL", "WAREHOUSE"}


def sanitize_category(params: GenerationParams) -> List[str]:
    """Clamp cross-category contamination; returns notes.

    Industrial/warehouse generation can never produce residential forms,
    balconied homes, or retail ground floors; residential generation can
    never produce loading bays.
    """
    notes: List[str] = []
    if params.asset_type in INDUSTRIAL_TYPES:
        if params.style in ("modern_residential", "suburban_house",
                            "brick_residential", "concrete_apartment",
                            "traditional_lowrise"):
            params.style = "industrial_warehouse"
            notes.append("style forced to industrial_warehouse")
        if params.residential_form not in ("auto", ""):
            params.residential_form = "auto"
            notes.append("residential form cleared")
        if params.ground_floor not in ("loading_bay", "none", "office_lobby"):
            params.ground_floor = "loading_bay"
            notes.append("ground floor forced to loading_bay")
        if params.balcony_style != "none":
            params.balcony_style = "none"
            notes.append("balconies removed")
        if params.business_category != "random":
            params.business_category = "random"
            notes.append("business identity cleared")
    elif params.asset_type in ("RESIDENTIAL", "HOUSE"):
        if params.ground_floor in ("loading_bay", "garage"):
            params.ground_floor = "apartment_entrance"
            notes.append("residential ground floor restored")
        if params.commercial_form not in ("auto", ""):
            params.commercial_form = "auto"
            notes.append("commercial form cleared")
    return notes


# ---------------------------------------------------------------------------
# Building category system: categories -> kinds -> generation presets
# ---------------------------------------------------------------------------

# kind presets: label, asset_type, style, floors, floor_height, ground_floor,
# width, depth, form overrides, roof_type
BUILDING_KINDS: Dict[str, Dict[str, Any]] = {
    # --- Residential ---
    "detached_house": dict(label="Detached House", asset_type="HOUSE",
                           style="modern_residential", floors=2,
                           floor_height=2.9, ground_floor="apartment_entrance",
                           width=10.0, depth=8.0, roof_type="hip",
                           residential_form="detached_house"),
    "semi_detached": dict(label="Semi-Detached House", asset_type="HOUSE",
                          style="suburban_house", floors=2, floor_height=2.9,
                          ground_floor="apartment_entrance", width=8.0,
                          depth=9.0, roof_type="gable",
                          residential_form="detached_house"),
    "duplex": dict(label="Duplex", asset_type="RESIDENTIAL",
                   style="modern_residential", floors=2, floor_height=2.9,
                   ground_floor="apartment_entrance", width=12.0, depth=10.0,
                   roof_type="flat_parapet",
                   residential_form="lowrise_apartments"),
    "townhouse": dict(label="Townhouse", asset_type="RESIDENTIAL",
                      style="brick_residential", floors=3, floor_height=2.9,
                      ground_floor="apartment_entrance", width=6.0, depth=9.0,
                      roof_type="flat_parapet", residential_form="townhouse"),
    "row_houses": dict(label="Row Houses", asset_type="RESIDENTIAL",
                       style="brick_residential", floors=3, floor_height=3.0,
                       ground_floor="apartment_entrance", width=18.0,
                       depth=10.0, roof_type="gable",
                       residential_form="townhouse"),
    "apartments": dict(label="Apartments", asset_type="RESIDENTIAL",
                       style="modern_residential", floors=6,
                       floor_height=3.0, ground_floor="apartment_entrance",
                       width=18.0, depth=14.0, roof_type="flat_parapet",
                       residential_form="midrise_apartments"),
    "condominiums": dict(label="Condominiums", asset_type="RESIDENTIAL",
                         style="contemporary_commercial", floors=9,
                         floor_height=3.1, ground_floor="office_lobby",
                         width=20.0, depth=16.0, roof_type="flat_parapet",
                         residential_form="midrise_apartments"),
    "residential_tower": dict(label="Residential Tower",
                              asset_type="RESIDENTIAL",
                              style="contemporary_residential_tower",
                              floors=24, floor_height=3.1,
                              ground_floor="office_lobby", width=20.0,
                              depth=18.0, roof_type="flat",
                              residential_form="highrise_tower"),
    # --- Retail & Shops ---
    "small_shop": dict(label="Small Shop", asset_type="SHOP",
                       style="contemporary_commercial", floors=1,
                       floor_height=3.6, ground_floor="retail", width=10.0,
                       depth=9.0, roof_type="flat_parapet",
                       commercial_form="small_retail"),
    "corner_store": dict(label="Corner Store", asset_type="SHOP",
                         style="contemporary_commercial", floors=1,
                         floor_height=3.5, ground_floor="retail", width=8.0,
                         depth=8.0, roof_type="flat_parapet",
                         commercial_form="small_retail"),
    "restaurant": dict(label="Restaurant", asset_type="COMMERCIAL",
                       style="contemporary_commercial", floors=2,
                       floor_height=3.6, ground_floor="retail", width=14.0,
                       depth=11.0, roof_type="flat_parapet",
                       commercial_form="restaurant"),
    "cafe": dict(label="Cafe", asset_type="COMMERCIAL",
                 style="contemporary_commercial", floors=1, floor_height=3.5,
                 ground_floor="retail", width=8.0, depth=9.0,
                 roof_type="flat_parapet", commercial_form="cafe"),
    "shopping_centre": dict(label="Shopping Centre", asset_type="COMMERCIAL",
                            style="contemporary_commercial", floors=2,
                            floor_height=4.2, ground_floor="retail",
                            width=34.0, depth=22.0, roof_type="flat",
                            commercial_form="shopping_building"),
    "strip_mall": dict(label="Strip Mall", asset_type="COMMERCIAL",
                       style="contemporary_commercial", floors=1,
                       floor_height=4.0, ground_floor="retail", width=32.0,
                       depth=14.0, roof_type="flat_parapet",
                       commercial_form="small_retail"),
    "standalone_retail": dict(label="Standalone Retail",
                              asset_type="COMMERCIAL",
                              style="contemporary_commercial", floors=1,
                              floor_height=4.5, ground_floor="retail",
                              width=22.0, depth=16.0, roof_type="flat",
                              commercial_form="shopping_building"),
    # --- Office ---
    "office_small": dict(label="Small Office", asset_type="OFFICE",
                         style="contemporary_commercial", floors=4,
                         floor_height=3.4, ground_floor="office_lobby",
                         width=16.0, depth=13.0, roof_type="flat",
                         commercial_form="office_building"),
    "office_block": dict(label="Office Block", asset_type="OFFICE",
                         style="glass_office_tower", floors=10,
                         floor_height=3.5, ground_floor="office_lobby",
                         width=22.0, depth=18.0, roof_type="flat"),
    # --- Industrial ---
    "factory": dict(label="Factory", asset_type="INDUSTRIAL",
                    style="industrial_warehouse", floors=2, floor_height=4.6,
                    ground_floor="loading_bay", width=30.0, depth=20.0,
                    roof_type="sloped"),
    "warehouse": dict(label="Warehouse", asset_type="WAREHOUSE",
                      style="industrial_warehouse", floors=1,
                      floor_height=6.0, ground_floor="loading_bay",
                      width=32.0, depth=22.0, roof_type="sloped"),
    "distribution_centre": dict(label="Distribution Centre",
                                asset_type="WAREHOUSE",
                                style="industrial_warehouse", floors=1,
                                floor_height=7.0, ground_floor="loading_bay",
                                width=44.0, depth=26.0, roof_type="sloped"),
    "manufacturing": dict(label="Manufacturing Plant", asset_type="INDUSTRIAL",
                          style="industrial_warehouse", floors=1,
                          floor_height=6.5, ground_floor="loading_bay",
                          width=36.0, depth=24.0, roof_type="sloped"),
    "workshop": dict(label="Industrial Workshop", asset_type="INDUSTRIAL",
                     style="industrial_warehouse", floors=1, floor_height=4.0,
                     ground_floor="loading_bay", width=14.0, depth=10.0,
                     roof_type="flat_parapet"),
    "storage_building": dict(label="Storage Building", asset_type="WAREHOUSE",
                             style="industrial_warehouse", floors=1,
                             floor_height=4.5, ground_floor="loading_bay",
                             width=18.0, depth=12.0, roof_type="sloped"),
    "logistics_building": dict(label="Logistics Building",
                               asset_type="WAREHOUSE",
                               style="industrial_warehouse", floors=2,
                               floor_height=5.0, ground_floor="loading_bay",
                               width=38.0, depth=24.0, roof_type="sloped"),
    # --- Institutional / Public / Hospitality / Healthcare / Education ---
    "school": dict(label="School", asset_type="OFFICE",
                   style="concrete_apartment", floors=3, floor_height=3.4,
                   ground_floor="apartment_entrance", width=30.0, depth=14.0,
                   roof_type="flat_parapet"),
    "hospital": dict(label="Hospital", asset_type="OFFICE",
                     style="modern_highrise", floors=6, floor_height=3.6,
                     ground_floor="office_lobby", width=30.0, depth=20.0,
                     roof_type="flat"),
    "hotel": dict(label="Hotel", asset_type="MIXED",
                  style="modern_highrise", floors=10, floor_height=3.3,
                  ground_floor="office_lobby", width=24.0, depth=18.0,
                  roof_type="flat"),
    "bank": dict(label="Bank", asset_type="COMMERCIAL",
                 style="traditional_lowrise", floors=2, floor_height=4.0,
                 ground_floor="office_lobby", width=16.0, depth=12.0,
                 roof_type="flat_parapet"),
    "fire_station": dict(label="Fire Station", asset_type="INDUSTRIAL",
                         style="contemporary_commercial", floors=2,
                         floor_height=4.2, ground_floor="garage", width=18.0,
                         depth=14.0, roof_type="flat_parapet"),
    "barn": dict(label="Barn", asset_type="INDUSTRIAL",
                 style="industrial_warehouse", floors=1, floor_height=5.0,
                 ground_floor="loading_bay", width=12.0, depth=18.0,
                 roof_type="gable"),
    "mixed_use_building": dict(label="Mixed-Use", asset_type="MIXED",
                               style="mixed_use_urban", floors=6,
                               floor_height=3.2, ground_floor="retail",
                               width=16.0, depth=14.0,
                               roof_type="flat_parapet"),
}

# category -> list of kinds
BUILDING_CATEGORIES: Dict[str, List[str]] = {
    "Residential": ["detached_house", "semi_detached", "duplex", "townhouse",
                    "row_houses", "apartments", "condominiums",
                    "residential_tower"],
    "Retail & Shops": ["small_shop", "corner_store", "restaurant", "cafe",
                       "shopping_centre", "strip_mall", "standalone_retail"],
    "Office": ["office_small", "office_block"],
    "Industrial": ["factory", "warehouse", "distribution_centre",
                   "manufacturing", "workshop", "storage_building",
                   "logistics_building"],
    "Institutional": ["school", "bank", "fire_station"],
    "Hospitality & Healthcare": ["hotel", "hospital"],
    "Mixed-Use": ["mixed_use_building"],
    "Towers": ["residential_tower", "office_block"],
}


_KEY_CHOICES: Dict[str, List[str]] = {
    "asset_type": ASSET_TYPES,
    "style": ARCH_STYLES,
    "window_type": WINDOW_TYPES,
    "window_light": WINDOW_LIGHT_STATES,
    "balcony_style": BALCONY_TYPES,
    "roof_type": ROOF_TYPES,
    "ground_floor": GROUND_FLOOR_TYPES,
    "entrance": ["center", "corner", "side", "none"],
    "detail_level": DET_LEVELS,
    "road_markings": ROAD_MARKING_STYLES,
    "sign_variants": SIGN_TYPES,
    "tree_type": TREE_TYPES,
    "season": TREE_SEASONS,
    "fence_type": FENCE_TYPES,
    "vehicle_class": ["sedan", "van", "truck", "bus", "hatchback", "taxi"],
    "residential_form": RESIDENTIAL_FORMS,
    "commercial_form": COMMERCIAL_FORMS,
    "tower_form": TOWER_FORMS,
    "facade_grid": FACADE_GRIDS,
    "business_category": BUSINESS_CATEGORIES,
    "npc_style": NPC_STYLES,
    "npc_gender": NPC_GENDERS,
    "npc_age": NPC_AGES,
    "npc_profession": NPC_PROFESSIONS,
    "npc_clip": NPC_CLIPS,
    "road_class": ROAD_CLASSES,
    "road_direction": ["two_way", "one_way_positive", "one_way_negative"],
    "median_style": MEDIAN_STYLES,
    "park_type": PARK_TYPES_LIST,
    "park_shape": ["auto", "rectangular", "square", "circular", "irregular"],
    "material_primary": None,   # material names validated by generator
    "material_secondary": None,
    "material_window": None,
    "material_trim": None,
    "material_accent": None,
}

_KEY_LIMITS: Dict[str, Tuple[float, float]] = {
    key: (lo, hi) for key, (lo, hi, _default) in LIMITS.items()
}
_KEY_LIMITS["poly_budget"] = (100, POLYGON_CEILING)


class ParamDesc:
    _name: str
    ptype: str
    choices: Optional[List[str]]
    limits: Optional[Tuple[float, float]]
    default: Any

    def __init__(self, name, ptype, choices=None, limits=None, default=None):
        self._name = name
        self.ptype = ptype
        self.choices = choices
        self.limits = limits
        self.default = default

    @property
    def key(self) -> str:
        return self._name


# ---------------------------------------------------------------------------
# Auto-generated parameter registry used by validation and the GLM schema.
# ---------------------------------------------------------------------------

def _ptype_of(annot: str) -> str:
    """Map a (stringified) dataclass annotation to a validation ptype."""
    if annot in ("int", "Optional[int]"):
        return "int"
    if annot in ("float", "Optional[float]"):
        return "float"
    if annot in ("str", "Optional[str]"):
        return "str"
    if annot in ("bool", "Optional[bool]"):
        return "bool"
    if "Tuple" in annot or annot == "tuple":
        return "color"
    if annot in ("Dict[str, Any]", "dict", "Optional[dict]"):
        return "dict"
    return "str" if annot.startswith("str") else "float"


PARAM_SPECS: Dict[str, ParamDesc] = {}
PARAM_KEYS: List[str] = []

for _name, _field_info in GenerationParams.__dataclass_fields__.items():
    if _name == "extra":
        continue
    _ptype = _ptype_of(str(_field_info.type))
    _spec = ParamDesc(
        _name,
        _ptype,
        choices=_KEY_CHOICES.get(_name),
        limits=_KEY_LIMITS.get(_name),
        default=getattr(GenerationParams(), _name),
    )
    PARAM_SPECS[_name] = _spec
    PARAM_KEYS.append(_name)

# nested "materials" payload from the NL schema (section 11):
# {primary, secondary, windows, trim} - mapped onto material_* by nl bridge
PARAM_SPECS["materials"] = ParamDesc("materials", "dict", default={})
PARAM_KEYS.append("materials")
