# SPDX-License-Identifier: GPL-3.0-or-later
"""Local, seeded business-name generation (no API required).

Names are built from category-specific word lists.  The same rng state and
category always produce the same name.
"""

from __future__ import annotations
from typing import List

import random

_PREFIXES = [
    "Golden", "Central", "Maple", "Union", "Riverside", "Old Town",
    "Metro", "Silver", "Crown", "Harbour", "Bluebird", "Copper",
    "Summit", "Garden", "Iron", "Pearl", "Oak", "Stone", "Amber", "Nova",
]

CATEGORY_WORDS = {
    "restaurant": ["Grill", "Kitchen", "Bistro", "Table", "Oven",
                   "Canteen", "Trattoria", "Brasserie"],
    "cafe": ["Espresso", "Beans", "Roast", "Coffee Lab", "Pour",
             "Barista", "Mocha", "Crema"],
    "pub": ["Arms", "Tavern", "Alehouse", "Tap", "Inn", "Keg"],
    "bar": ["Lounge", "Cocktail Room", "Speakeasy", "Bar", "Tasting Room"],
    "retail_shop": ["Goods", "Store", "Boutique", "Emporium", "Market",
                    "Trading Co."],
    "grocery_store": ["Grocers", "Fresh Market", "Food Hall", "Provisions",
                      "Grocery"],
    "convenience_store": ["Corner Store", "Mini Market", "Daily Mart",
                          "Quick Stop"],
    "office": ["Consulting", "Partners", "Group", "Associates", "Offices",
               "Solutions"],
    "other": ["Studio", "Workshop", "Depot", "Works", "Hub", "Hall"],
}

NAME_PATTERNS = [
    "{prefix} {word}",
    "{prefix} {word}",
    "The {word}",
    "{prefix} & Co. {word}",
    "{word} No. {n}",
]


def generate_business_name(rng: random.Random, category: str) -> str:
    words: List[str] = CATEGORY_WORDS.get(
        category, CATEGORY_WORDS["other"])
    pattern = rng.choice(NAME_PATTERNS)
    name = pattern.format(
        prefix=rng.choice(_PREFIXES),
        word=rng.choice(words),
        n=rng.randint(2, 49),
    )
    return name
