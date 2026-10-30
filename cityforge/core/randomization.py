# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic randomisation helpers.

Every stochastic decision in CityForge routes through :func:`make_rng`:
identical seeds always produce identical assets.
"""

from __future__ import annotations

import random
from typing import Any, List, Optional, Sequence, Tuple

from ..utils import make_rng

__all__ = ["make_rng", "jitter", "pick", "pick_weighted", "chance"]


def jitter(rng: random.Random, base: float, amount: float,
           lo: Optional[float] = None, hi: Optional[float] = None) -> float:
    """`base +/- amount`, optionally clamped. Deterministic for a given rng."""
    value = base + rng.uniform(-amount, amount)
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def pick(rng: random.Random, choices: Sequence[Any]) -> Any:
    return rng.choice(choices)


def pick_weighted(rng: random.Random, choices: Sequence[Tuple[Any, float]]) -> Any:
    vals = [c for c, _w in choices]
    weights = [max(0.0, w) for _c, w in choices]
    return rng.choices(vals, weights=weights, k=1)[0]


def chance(rng: random.Random, probability: float) -> bool:
    return rng.random() < probability


def variation_seed(base_seed: int, variation: int) -> int:
    """Correlated but distinct seeds for variations of one asset."""
    return (base_seed * 1_000_003 + variation * 7_717) % (2 ** 31)
