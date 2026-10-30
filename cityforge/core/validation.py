# SPDX-License-Identifier: GPL-3.0-or-later
"""Strict parameter validation.

Every path into the generator (UI, presets, natural-language parser, future
GLM bridge) funnels parameters through :func:`validate_params` before any
geometry is created.  Unknown keys, out-of-range values and illegal choices
never reach the mesh code.

This module has no `bpy` dependency so it can be tested with plain Python.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

from .params import (
    PARAM_KEYS,
    PARAM_SPECS,
    POLYGON_CEILING,
    DETAIL_BUDGETS,
)

# keys that only the generator itself may set (never accepted from outside)
_FORBIDDEN_KEYS = {"extra", "variation"}


class ValidationError(Exception):
    """Raised when a parameter set is malformed or out of range."""

    def __init__(self, issues: List[str]):
        self.issues = issues
        super().__init__("; ".join(issues[:8]))


def coerce_value(ptype: str, raw: Any) -> Any:
    """Best-effort type coercion (AI/JSON payloads often send '12' vs 12)."""
    if ptype == "int":
        return int(math.floor(float(raw)))
    if ptype == "float":
        return float(raw)
    if ptype == "color":
        if isinstance(raw, (list, tuple)):
            vals = [max(0.0, min(1.0, float(c))) for c in raw]
            if len(vals) < 3:
                raise ValueError("colour needs 3-4 components")
            return tuple(vals + [1.0] * (4 - len(vals)))
        raise ValueError("expected [r, g, b, a]")
    if ptype == "bool":
        if isinstance(raw, str):
            return raw.lower() in ("true", "1", "yes", "on")
        return bool(raw)
    if ptype == "list":
        if isinstance(raw, (list, tuple)):
            return list(raw)
        return [raw]
    if ptype == "dict":
        if isinstance(raw, dict):
            return raw
        raise ValueError("expected an object/map")
    if ptype == "str":
        return str(raw)
    return raw


def _check_one(spec, value: Any, issues: List[str]) -> Any:
    """Validate a single value against its ParamSpec. Returns coerced value or
    appends an issue and returns the spec default."""
    ptype = spec.ptype
    try:
        value = coerce_value(ptype, value)
    except (TypeError, ValueError, OverflowError):
        issues.append(f"{spec.key}: expected {ptype}, got {value!r}")
        return spec.default
    if ptype == "dict":
        if not isinstance(value, dict):
            issues.append(f"{spec.key}: expected an object/map")
            return spec.default
        # material sub-keys must map to known material groups
        allowed = {"primary", "secondary", "windows", "trim", "accent"}
        if any(k not in allowed for k in value):
            issues.append(
                f"{spec.key}: unknown keys {sorted(set(value) - allowed)}")
    if ptype in ("float", "int"):
        if not math.isfinite(float(value)):
            issues.append(f"{spec.key}: value is not finite")
            return spec.default
        if spec.limits:
            lo, hi = spec.limits
            if float(value) < lo or float(value) > hi:
                issues.append(
                    f"{spec.key}: {value} outside allowed range [{lo}, {hi}]"
                )
                return spec.default
    if ptype == "str" and spec.choices and value not in spec.choices:
        issues.append(
            f"{spec.key}: unknown choice {value!r} "
            f"(expected one of {spec.choices})"
        )
        return spec.default
    return value


def normalize_params(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Validate and normalise a parameter dictionary.

    Returns (clean_params, issues).  Minor problems (clipped ranges, unknown
    types) are fixed with defaults and reported as *issues*; a strict caller
    may treat a non-empty issue list as fatal.
    """
    if not isinstance(data, dict):
        raise ValidationError([f"parameters must be a JSON object, got {type(data).__name__}"])

    clean: Dict[str, Any] = {}
    issues: List[str] = []

    for key, value in data.items():
        if key in _FORBIDDEN_KEYS:
            issues.append(f"{key}: this key can not be set from outside")
            continue
        spec = PARAM_SPECS.get(key)
        if spec is None:
            issues.append(f"{key}: unknown parameter")
            continue
        clean[key] = _check_one(spec, value, issues)

    if clean.get("poly_budget"):
        if clean["poly_budget"] > POLYGON_CEILING:
            issues.append(
                f"poly_budget: {clean['poly_budget']} exceeds the safety "
                f"ceiling of {POLYGON_CEILING}"
            )
            clean["poly_budget"] = POLYGON_CEILING

    # cross-field sanity: floors x floor_height x budget is realistic
    floors = clean.get("floors", 5)
    floor_height = clean.get("floor_height", 3.1)
    budget = clean.get("poly_budget", POLYGON_CEILING)

    return clean, issues


def validate_params(data: Dict[str, Any]) -> Dict[str, Any]:
    """Strictly validate; raise ValidationError if anything is wrong."""
    clean, issues = normalize_params(data)
    if issues:
        raise ValidationError(issues)
    return clean


def validate_nl_payload(payload: str) -> Tuple[Dict[str, Any], List[str]]:
    """Validate a raw JSON string coming from a natural-language bridge.

    Returns (clean_dict, issues). Raises ValidationError on malformed JSON.
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # malformed JSON
        raise ValidationError([f"malformed JSON: {exc}"]) from exc
    return normalize_params(data)


def default_params() -> Dict[str, Any]:
    return {key: spec.default for key, spec in PARAM_SPECS.items()}
