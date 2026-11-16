"""Tests for tools/check_card.py.

Run from the repo root:
    python -m unittest discover -s tools -p "test_check_card.py" -v
"""
import contextlib
import io
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


def task_sheet(cards, declared=None, product="round10l", fenced=False):
    parts = [check_card.TASK_HEADER, f"product: {product}", f"cards: {len(cards) if declared is None else declared}", ""]
    for path, body in cards:
        parts += [f"=== {path} ===", body.rstrip("\n"), ""]
    text = "\n".join(parts)
    return "```\n" + text + "\n```\n" if fenced else text


class TaskSheetTest(unittest.TestCase):
    CARD = ("cards/round10l/S5_clean.md", GOOD)

    def test_cards_are_split_out(self):
        other = ("cards/round10l/S4_quiet.md", GOOD.replace("slot: S5", "slot: S4"))
        product, cards, errors = check_card.parse_task(task_sheet([self.CARD, other]))
        self.assertEqual(errors, [])
        self.assertEqual(product, "round10l")
        self.assertEqual([path for path, _body in cards], [self.CARD[0], other[0]])
        self.assertEqual(cards[0][1], GOOD.rstrip("\n") + "\n")

    def test_code_fence_around_the_sheet_is_ignored(self):
        _product, cards, errors = check_card.parse_task(task_sheet([self.CARD], fenced=True))
        self.assertEqual(errors, [])
        self.assertEqual(len(cards), 1)

    def test_truncated_sheet_is_rejected(self):
        _product, _cards, errors = check_card.parse_task(task_sheet([self.CARD], declared=3))
        self.assertTrue(any("cut off" in error for error in errors), errors)

    def test_missing_header_is_rejected(self):
        text = task_sheet([self.CARD]).replace(check_card.TASK_HEADER, "Here is the task:")
        _product, _cards, errors = check_card.parse_task(text)
        self.assertTrue(any("first line must be" in error for error in errors), errors)

    def test_card_under_another_product_is_rejected(self):
        card = ("cards/clover_square/S5_clean.md", GOOD)
        _product, _cards, errors = check_card.parse_task(task_sheet([card]))
        self.assertTrue(any("is not under cards/round10l/" in error for error in errors), errors)

    def test_bad_marker_is_rejected(self):
        text = task_sheet([self.CARD]).replace("=== cards/round10l/S5_clean.md ===", "=== S5 clean ===")
        _product, _cards, errors = check_card.parse_task(text)
        self.assertTrue(any("bad card marker" in error for error in errors), errors)

    def test_run_task_on_the_sample_cards(self):
        """Feeding the repo's own cards back in must leave them unchanged and valid."""
        samples = sorted((ROOT / "cards" / "round10l").glob("*.md"))
        cards = [(p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8")) for p in samples]
        before = {p: p.read_bytes().replace(b"\r\n", b"\n") for p in samples}
        with tempfile.TemporaryDirectory() as folder:
            sheet = Path(folder) / "task.md"
            sheet.write_text(task_sheet(cards), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = check_card.run_task(sheet, check_card.load_index())
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("NEXT", output.getvalue())
        self.assertNotIn("(updated)", output.getvalue())
        for path, content in before.items():
            self.assertEqual(path.read_bytes().replace(b"\r\n", b"\n"), content, path.name)


if __name__ == "__main__":
    unittest.main()
