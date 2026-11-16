"""Tests for tools/check_card.py.

Run from the repo root:
    python -m unittest discover -s tools -p "test_check_card.py" -v
"""
import tempfile
import unittest
from pathlib import Path

import check_card

ROOT = Path(__file__).resolve().parent.parent
GOOD = (ROOT / "cards" / "round10l" / "S5_clean.md").read_text(encoding="utf-8")


class CheckCardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = check_card.load_index()

    def errors_for(self, text):
        with tempfile.TemporaryDirectory() as folder:
            card = Path(folder) / "card.md"
            card.write_text(text, encoding="utf-8")
            errors, _warnings, _context = check_card.validate(card, self.index)
        return errors

    def assert_rejected(self, old, new, expected):
        self.assertIn(old, GOOD, "test fixture out of date")
        errors = self.errors_for(GOOD.replace(old, new))
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected an error containing {expected!r}, got {errors}",
        )

    def test_sample_cards_pass(self):
        for card in sorted((ROOT / "cards").glob("*/*.md")):
            errors, _warnings, context = check_card.validate(card, self.index)
            self.assertEqual(errors, [], card.name)
            self.assertIsNotNone(context)

    def test_prompt_is_built_from_the_card(self):
        card = ROOT / "cards" / "round10l" / "S5_clean.md"
        _errors, _warnings, context = check_card.validate(card, self.index)
        prompt = check_card.build_prompt(context, check_card.load_prompt_blocks())
        self.assertIn("pill-shaped transparent water window", prompt)
        self.assertIn("45 degrees looking down", prompt)
        self.assertIn("Attached image 1 is the product reference", prompt)
        self.assertNotIn("Easy to Clean", prompt, "copy must not reach the image model")

    def test_number_outside_the_fact_is_rejected(self):
        self.assert_rejected("hero_number: none", "hero_number: 25 dB", "number '25'")

    def test_number_from_another_fact_is_rejected(self):
        self.assert_rejected("hero_number: none", "hero_number: 10 L", "number '10'")

    def test_process_wording_is_rejected(self):
        self.assert_rejected(
            "subtitle: Rinse the basin you can see.",
            "subtitle: Six confirmed facts.",
            "'confirmed'",
        )

    def test_product_forbidden_word_is_rejected(self):
        self.assert_rejected(
            "subtitle: Rinse the basin you can see.",
            "subtitle: Dishwasher safe.",
            "'dishwasher'",
        )

    def test_unknown_fact_id_is_rejected(self):
        self.assert_rejected("selling_point: F5", "selling_point: F9", "not a fact id")

    def test_path_not_in_index_is_rejected(self):
        self.assert_rejected(
            "references/anchors/v06_S6_clean_sink.png",
            "references/anchors/made_up.png",
            "not listed in references/INDEX.csv",
        )

    def test_wrong_reference_type_is_rejected(self):
        self.assert_rejected(
            "references/anchors/v06_S6_clean_sink.png",
            "docs/uta_style_v3/assets/key/EXP_011.jpg",
            "is type 'expression'",
        )

    def test_other_products_reference_is_rejected(self):
        self.assert_rejected(
            "products/round10l/ref/front_high.png",
            "products/clover_square/ref/three_quarter_high.png",
            "not to round10l",
        )

    def test_missing_product_reference_is_rejected(self):
        self.assert_rejected(
            "product: products/round10l/ref/front_high.png | product structure, proportions and steel finish only",
            "product: none",
            "ref product is required",
        )

    def test_chinese_in_prompt_field_is_rejected(self):
        self.assert_rejected(
            "camera: down_45\nscene: Bright kitchen",
            "camera: down_45\nscene: 明亮的厨房 Bright kitchen",
            "'scene' must be written in English",
        )

    def test_wrong_canvas_is_rejected(self):
        self.assert_rejected("canvas: 4:5", "canvas: 1:1", "canvas for S5 must be 4:5")

    def test_unknown_camera_is_rejected(self):
        self.assert_rejected("camera: down_45", "camera: fisheye", "camera must be one of")

    def test_long_headline_is_rejected(self):
        self.assert_rejected(
            "headline: Easy to Clean",
            "headline: So Very Easy to Rinse and Clean",
            "headline has more than",
        )

    def test_layout_reference_on_s_slot_is_rejected(self):
        self.assert_rejected(
            "layout: none",
            "layout: docs/uta_style_v3/assets/key/AP_005.jpg | module structure only",
            "layout references are for P slots only",
        )

    def test_m1_with_text_is_rejected(self):
        text = GOOD.replace("slot: S5", "slot: M1").replace("canvas: 4:5", "canvas: 1:1")
        errors = self.errors_for(text)
        self.assertTrue(any("M1 is product only" in error for error in errors), errors)

    def test_missing_field_is_rejected(self):
        self.assert_rejected("camera: down_45\n", "", "missing field 'camera'")


if __name__ == "__main__":
    unittest.main()
