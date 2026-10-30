# SPDX-License-Identifier: GPL-3.0-or-later
"""Natural-language integration architecture.

Two paths into generation parameters:

1. **Local parser** – a deterministic keyword/number extractor.  It has no
   AI and limited vocabulary; it is a working convenience, not a substitute
   for a language model.

2. **GLM bridge** – a clearly marked integration point.  It is *inactive*
   until the user configures an endpoint via environment variables
   (``CFGLM_ENDPOINT``, optionally ``CFGLM_API_KEY``, ``CFGLM_MODEL``).
   It POSTs the user's description and expects JSON *parameters only* —
   any payload is strictly validated by :mod:`cityforge.core.validation`
   before it reaches geometry code.  AI output is never executed.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from ..core.params import (
    ARCH_STYLES,
    ROOF_TYPES,
    GROUND_FLOOR_TYPES,
    BALCONY_TYPES,
    WINDOW_TYPES,
    DET_LEVELS,
    TYPE_DEFAULT_STYLE,
)
from ..utils import get_logger

_log = get_logger()

STYLE_KEYWORDS = {
    "modern residential": "modern_residential",
    "modern": "modern_residential",
    "brick": "brick_residential",
    "glass tower": "glass_office_tower",
    "office tower": "glass_office_tower",
    "warehouse": "industrial_warehouse",
    "industrial": "industrial_warehouse",
    "suburban": "suburban_house",
    "apartment": "concrete_apartment",
    "block": "concrete_apartment",
    "high rise": "modern_highrise",
    "highrise": "modern_highrise",
}

ROOF_KEYWORDS = {
    "flat roof": "flat",
    "flat": "flat_parapet",
    "gable": "gable",
    "pitched": "gable",
    "hip": "hip",
    "sloped": "sloped",
}

GROUND_KEYWORDS = {
    "retail": "retail",
    "shop": "retail",
    "storefront": "retail",
    "store fronts": "retail",
    "lobby": "office_lobby",
    "loading bay": "loading_bay",
    "loading": "loading_bay",
    "garage": "garage",
    "parking": "garage",
}

BALCONY_KEYWORDS = {
    "glass balcony": "glass",
    "balcony": "concrete",
    "no balcony": "none",
}


def local_parse(prompt: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Best-effort keyword extraction.  Returns (params, notes).

    Notes explain which fields were successfully interpreted; anything the
    parser could not interpret is left at defaults.  No network access, no
    AI, fully deterministic.
    """
    text = prompt.lower().replace("balconies", "balcony")
    out: Dict[str, Any] = {}
    notes: Dict[str, str] = {}

    def note(key: str, value: Any, how: str) -> None:
        out[key] = value
        notes[key] = f"{value} ({how})"

    # asset type
    type_hints = [
        ("apartment", "RESIDENTIAL"), ("residential", "RESIDENTIAL"),
        ("house", "HOUSE"), ("office", "OFFICE"), ("skyscraper", "SKYSCRAPER"),
        ("tower", "SKYSCRAPER"), ("shop", "SHOP"), ("store", "COMMERCIAL"),
        ("commercial", "COMMERCIAL"), ("warehouse", "WAREHOUSE"),
        ("factory", "INDUSTRIAL"), ("industrial", "INDUSTRIAL"),
        ("mixed", "MIXED"), ("road", "ROAD"), ("sidewalk", "SIDEWALK"),
        ("tree", "TREE"), ("bush", "BUSH"), ("bench", "BENCH"),
        ("streetlight", "STREETLIGHT"), ("sign", "TRAFFIC_SIGN"),
        ("vehicle", "VEHICLE"), ("car", "VEHICLE"),
    ]
    for word, atype in type_hints:
        if re.search(r"\b" + word + r"\b", text):
            note("asset_type", atype, "keyword")
            break

    # floors: "12-storey", "12 storeys", "12 floors"
    m = re.search(r"(\d+)[- ]?(?:storey|story|floor|floors)", text)
    if m:
        note("floors", int(m.group(1)), "number+keyword")

    # dimensions: "24 m wide", "24 metre depth", "width 24", "depth 18"
    for axis, key in (("wide", "width"), ("width", "width"),
                      ("long", "depth"), ("depth", "depth"),
                      ("deep", "depth")):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:m|metre|meter|)\s*" + axis, text)
        if not m:
            m = re.search(axis + r" (\d+(?:\.\d+)?)", text)
        if m:
            note(key, float(m.group(1)), "number+axis")

    # height expressed in floors only, floor height in metres
    m = re.search(r"(\d+(?:\.\d+)?)\s*m (?:tall|high|height)", text)
    if m:
        total = float(m.group(1))
        if out.get("floors"):
            out["floor_height"] = round(total / max(1, out["floors"]), 2)
            notes["floor_height"] = f"{out['floor_height']} (height / floors)"

    # styles
    for kw, style in STYLE_KEYWORDS.items():
        if kw in text:
            note("style", style, "keyword")
            break
    if "style" not in out and out.get("asset_type") in TYPE_DEFAULT_STYLE:
        out["style"] = TYPE_DEFAULT_STYLE[out["asset_type"]]

    for kw, roof in ROOF_KEYWORDS.items():
        if re.search(r"\b" + kw + r"\b", text):
            note("roof_type", roof, "keyword")
            break
    for kw, ground in GROUND_KEYWORDS.items():
        if re.search(r"\b" + kw + r"\b", text):
            note("ground_floor", ground, "keyword")
            break
    for kw, balc in BALCONY_KEYWORDS.items():
        if kw in text:
            note("balcony_style", balc, "keyword")
            break

    # detail level
    for lvl in DET_LEVELS:
        if lvl in text:
            note("detail_level", lvl, "keyword")
            break

    # seed: "seed 1234"
    m = re.search(r"seed[: ]+(\d+)", text)
    if m:
        note("seed", int(m.group(1)), "number")

    if not out:
        notes["_summary"] = "no recognizable keywords; defaults used"
    return out, notes


# ---------------------------------------------------------------------------
# GLM bridge (inactive unless environment configured)
# ---------------------------------------------------------------------------

def bridge_configured() -> bool:
    return bool(os.environ.get("CFGLM_ENDPOINT"))


def request_glm(description: str,
                timeout: float = 30.0) -> Tuple[Dict[str, Any], str]:
    """Ask a GLM endpoint for structured parameters.

    Returns (params_dict, raw_request_json).  Raises RuntimeError with a
    helpful message when the bridge is not configured or misbehaves.
    """
    endpoint = os.environ.get("CFGLM_ENDPOINT")
    if not endpoint:
        raise RuntimeError(
            "The GLM bridge is not configured.\n"
            "To enable it, set these environment variables before starting "
            "Blender:\n"
            "  CFGLM_ENDPOINT   e.g. https://api.example.com/v1/chat/completions\n"
            "  CFGLM_API_KEY    your key (optional for local servers)\n"
            "  CFGLM_MODEL      model name (default 'glm-4')\n"
            "Without a bridge the local keyword parser is used instead.")

    system_prompt = (
        "You translate city-asset descriptions into JSON generation "
        "parameters for the CityForge Blender add-on. Respond ONLY with a "
        "single JSON object using keys from this schema: asset_type, style, "
        "floors, width, depth, floor_height, roof_type, balcony_style, "
        "window_type, ground_floor, materials {primary, secondary, windows, "
        "trim}, detail_level, seed. Valid values: asset_type in "
        f"{sorted(set(TYPE_DEFAULT_STYLE))}; style in {ARCH_STYLES}; "
        f"roof_type in {ROOF_TYPES}; ground_floor in {GROUND_FLOOR_TYPES}; "
        f"balcony_style in {BALCONY_TYPES}."
    )

    model = os.environ.get("CFGLM_MODEL", "glm-4")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": description},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("CFGLM_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(endpoint, data=payload, headers=headers,
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GLM endpoint unreachable: {exc}") from exc

    raw = body
    # chat-completions style; tolerate direct JSON payloads too
    content = raw
    if isinstance(raw, dict) and "choices" in raw:
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("unexpected GLM response structure")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"GLM returned non-JSON content: {exc}")
    if not isinstance(content, dict):
        raise RuntimeError("GLM response is not a JSON object")
    return content, json.dumps(raw, default=str)[:2000]
