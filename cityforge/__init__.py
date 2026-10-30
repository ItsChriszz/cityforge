# SPDX-License-Identifier: GPL-3.0-or-later
"""CityForge - procedural city asset generator for Blender.

Procedural, parameter-driven generation of game-ready city assets
(buildings, roads, vegetation, props, vehicles) with a Unity export pipeline.
"""

bl_info = {
    "name": "CityForge",
    "author": "CityForge Team",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > CityForge",
    "description": "Procedural city asset generator for city-building games",
    "support": "COMMUNITY",
    "doc_url": "https://github.com/cityforge/cityforge",
    "category": "Add Mesh",
}


def register():
    import bpy
    from . import properties
    from . import ui
    properties.register()
    ui.register()


def unregister():
    from . import properties
    from . import ui
    ui.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
