# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure-Python (no Blender) tests for validation, params and NL parsing.

Run:  python3 -m cityforge.tests.test_validation
"""

from __future__ import annotations

import _bootstrap  # noqa: F401  (adds project root to sys.path)
import unittest

from cityforge.core import nl_integration
from cityforge.core import params as P
from cityforge.core import validation


class TestValidation(unittest.TestCase):

    def test_defaults_are_valid(self):
        data = {k: v for k, v in P.GenerationParams().to_dict().items()
                if k not in validation._FORBIDDEN_KEYS}
        clean, issues = validation.normalize_params(data)
        self.assertEqual(issues, [])
        self.assertIn("floors", clean)

    def test_range_rejection(self):
        clean, issues = validation.normalize_params({"width": 5000.0})
        self.assertTrue(issues)
        self.assertEqual(clean["width"], 16.0)   # clipped to default

    def test_unknown_parameter(self):
        clean, issues = validation.normalize_params({"not_a_key": 1})
        self.assertTrue(any("unknown parameter" in i for i in issues))
        self.assertNotIn("not_a_key", clean)

    def test_choice_rejection(self):
        clean, issues = validation.normalize_params({"roof_type": "dome"})
        self.assertTrue(any("unknown choice" in i for i in issues))
        self.assertEqual(clean["roof_type"], "flat_parapet")

    def test_strict_validate_raises(self):
        with self.assertRaises(validation.ValidationError):
            validation.validate_params({"floors": -4})

    def test_malformed_json(self):
        with self.assertRaises(validation.ValidationError):
            validation.validate_nl_payload("{not json")
        with self.assertRaises(validation.ValidationError):
            validation.validate_nl_payload("[1, 2, 3]")

    def test_coercion(self):
        clean, issues = validation.normalize_params(
            {"floors": "12", "seed": "x"})
        self.assertEqual(clean["floors"], 12)
        self.assertEqual(clean["seed"], 1)   # 'x' invalid -> default
        self.assertTrue(issues)

    def test_polygon_ceiling(self):
        clean, issues = validation.normalize_params({"poly_budget": 10 ** 7})
        self.assertEqual(clean["poly_budget"], validation.POLYGON_CEILING)
        self.assertTrue(issues)

    def test_materials_dict(self):
        clean, issues = validation.normalize_params(
            {"materials": {"primary": "concrete", "bogus_key": 1}})
        self.assertTrue(any("unknown keys" in i for i in issues))

    def test_spec_registry_complete(self):
        # every GenerationParams field (minus extra) must be a known key
        fields = [k for k in P.GenerationParams.__dataclass_fields__
                  if k != "extra"]
        for f in fields:
            self.assertIn(f, P.PARAM_KEYS, f)


class TestNLIntegration(unittest.TestCase):

    def test_local_parse_floors(self):
        out, notes = nl_integration.local_parse(
            "Generate a modern 12-storey residential apartment building with a "
            "concrete podium and glass balconies, dark grey window frames, a "
            "flat roof, rooftop HVAC equipment, and a small ground-floor "
            "retail section.")
        self.assertEqual(out.get("asset_type"), "RESIDENTIAL")
        self.assertEqual(out.get("floors"), 12)
        self.assertEqual(out.get("style"), "modern_residential")
        self.assertEqual(out.get("balcony_style"), "glass")

    def test_local_parse_warehouse(self):
        out, _ = nl_integration.local_parse(
            "big industrial warehouse 30 metre wide loading bays seed 42")
        self.assertEqual(out.get("asset_type"), "WAREHOUSE")
        self.assertEqual(out.get("width"), 30.0)
        self.assertEqual(out.get("seed"), 42)

    def test_local_parse_deterministic(self):
        prompt = "12 storey modern high rise studio tower"
        a, _ = nl_integration.local_parse(prompt)
        b, _ = nl_integration.local_parse(prompt)
        self.assertEqual(a, b)

    def test_bridge_not_configured(self):
        import os
        endpoint = os.environ.pop("CFGLM_ENDPOINT", None)
        self.assertFalse(nl_integration.bridge_configured())
        if endpoint is not None:
            os.environ["CFGLM_ENDPOINT"] = endpoint


if __name__ == "__main__":
    unittest.main(verbosity=2)
