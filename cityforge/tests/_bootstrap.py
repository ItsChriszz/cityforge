# SPDX-License-Identifier: GPL-3.0-or-later
"""Import bootstrap so tests can run both standalone and inside Blender."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))     # repo root
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
