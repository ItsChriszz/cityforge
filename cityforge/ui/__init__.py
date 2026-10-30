# SPDX-License-Identifier: GPL-3.0-or-later
"""UI module: panels and operators for the CityForge sidebar."""

from . import operators
from . import panel

CLASSES = operators.CLASSES + panel.CLASSES


def register():
    operators.register()
    panel.register()


def unregister():
    panel.unregister()
    operators.unregister()
