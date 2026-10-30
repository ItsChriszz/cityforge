# SPDX-License-Identifier: GPL-3.0-or-later
"""CityForge generic utilities: deterministic RNG, hashing, logging."""

import hashlib
import logging
import random
import sys

_log = logging.getLogger("CityForge")


def get_logger() -> logging.Logger:
    """Return the shared CityForge logger."""
    if not _log.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("[CityForge] %(levelname)s: %(message)s")
        )
        _log.addHandler(handler)
        _log.setLevel(logging.INFO)
    return _log


def seed_from_string(text: str, base_seed: int = 0) -> int:
    """Convert arbitrary text into a 32-bit seed, mixed with a base seed.

    Used to decorrelate sub-systems (windows vs balconies vs roof) that all
    start from the same user-provided seed so tailoring each one with a
    different salt still behaves deterministically.
    """
    digest = hashlib.sha256(f"{base_seed}:{text}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def make_rng(seed: int, salt: str = "") -> random.Random:
    """Deterministic random.Random instance for a seed/salt pair."""
    return random.Random(seed_from_string(salt, seed) if salt else seed & 0xFFFFFFFF)


class Hash32(int):
    """Small helper making it obvious where hash(-1) pitfalls were avoided."""


def stable_hash_string(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")
