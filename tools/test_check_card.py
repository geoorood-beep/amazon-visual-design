"""Tests for tools/check_card.py.

Run from the repo root:
    python -m unittest discover -s tools -p "test_check_card.py" -v
"""
import contextlib
import io
import re
import shutil
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
            "ref layout must be none for this card",
        )

    def test_m1_with_text_is_rejected(self):
        text = GOOD.replace("slot: S5", "slot: M1").replace("canvas: 4:5", "canvas: 1:1")
        errors = self.errors_for(text)
        self.assertTrue(any("M1 is product only" in error for error in errors), errors)

    def test_missing_field_is_rejected(self):
        self.assert_rejected("camera: down_45\n", "", "missing field 'camera'")


class APlusTest(unittest.TestCase):
    """A+ cards: scene, panels and the grid / steps / specs module cards."""

    @classmethod
    def setUpClass(cls):
        cls.index = check_card.load_index()

    def errors_after(self, card_name, edits=(), remove=()):
        """Copy the sample cards to a temp folder, edit some, validate one."""
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for source in (ROOT / "cards" / "round10l").glob("*.md"):
                if source.name not in remove:
                    shutil.copy(source, folder / source.name)
            for name, old, new in edits:
                text = (folder / name).read_text(encoding="utf-8")
                self.assertIn(old, text, f"test fixture out of date: {name}")
                (folder / name).write_text(text.replace(old, new), encoding="utf-8")
            errors, _warnings, _context = check_card.validate(folder / card_name, self.index)
        return errors

    def assert_error(self, expected, card_name, edits=(), remove=()):
        errors = self.errors_after(card_name, edits, remove)
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected an error containing {expected!r}, got {errors}",
        )

    def context_for(self, name):
        errors, _warnings, context = check_card.validate(ROOT / "cards" / "round10l" / name, self.index)
        self.assertEqual(errors, [])
        return context

    def test_module_card_collects_its_panels(self):
        context = self.context_for("P6_daily_use.md")
        self.assertEqual(context["type"], "module")
        self.assertEqual([p["fields"]["slot"] for p in context["panels"]], ["P6a", "P6b", "P6c"])

    def test_specs_lines_are_parsed(self):
        context = self.context_for("P8_essentials.md")
        self.assertEqual([fact for fact, _text in context["lines"]], ["F1", "F2", "F3", "F4"])

    def test_scene_and_panel_prompts_ask_for_croppable_frames(self):
        blocks = check_card.load_prompt_blocks()
        scene = check_card.build_prompt(self.context_for("P1_cats_and_dogs.md"), blocks)
        panel = check_card.build_prompt(self.context_for("P6b_quiet.md"), blocks)
        self.assertIn("horizontal 3:2", scene)
        self.assertIn("the left third", scene)
        self.assertIn("central 60%", panel)
        self.assertNotIn("Under 20 dB", panel, "labels must not reach the image model")

    def test_p_slot_without_module_is_rejected(self):
        self.assert_error("needs 'module:'", "P1_cats_and_dogs.md", [("P1_cats_and_dogs.md", "module: scene\n", "")])

    def test_scene_text_area_must_be_a_side(self):
        self.assert_error(
            "text_area must be one of", "P1_cats_and_dogs.md",
            [("P1_cats_and_dogs.md", "text_area: left", "text_area: top_left")],
        )

    def test_panel_with_its_own_headline_is_rejected(self):
        self.assert_error(
            "a panel carries no text of its own", "P6a_steel.md",
            [("P6a_steel.md", "headline: none", "headline: Built to Last")],
        )

    def test_missing_panel_card_is_rejected(self):
        self.assert_error("panel P6c: expected exactly one card", "P6_daily_use.md", remove=("P6c_window.md",))

    def test_panel_error_fails_the_module(self):
        self.assert_error(
            "panel P6a: number '25'", "P6_daily_use.md",
            [("P6a_steel.md", "label: 304 Stainless Steel", "label: 25 Year Steel")],
        )

    def test_grid_panels_need_different_facts(self):
        self.assert_error(
            "different fact", "P6_daily_use.md",
            [("P6b_quiet.md", "selling_point: F3", "selling_point: F2"),
             ("P6b_quiet.md", "label: Under 20 dB", "label: Brushed Finish")],
        )

    def test_grid_panel_without_label_is_rejected(self):
        self.assert_error(
            "'label' is required", "P6_daily_use.md",
            [("P6c_window.md", "label: Water Window", "label: none")],
        )

    def test_steps_panels_must_share_the_fact(self):
        self.assert_error(
            "every panel of a steps module must use F5", "P7_clean_steps.md",
            [("P7b_wipe.md", "selling_point: F5", "selling_point: F2")],
        )

    def test_panel_list_must_be_in_order(self):
        self.assert_error(
            "panels must be listed as", "P7_clean_steps.md",
            [("P7_clean_steps.md", "panels: P7a, P7b", "panels: P7b, P7a")],
        )

    def test_too_many_panels_is_rejected(self):
        self.assert_error(
            "needs 1 panel(s)", "P8_essentials.md",
            [("P8_essentials.md", "panels: P8a", "panels: P8a, P8b")],
        )

    def test_spec_line_number_must_match_its_fact(self):
        self.assert_error(
            "number '12'", "P8_essentials.md",
            [("P8_essentials.md", "F1 | 10 L", "F1 | 12 L")],
        )

    def test_spec_line_needs_a_real_fact(self):
        self.assert_error(
            "'F9' is not a fact id", "P8_essentials.md",
            [("P8_essentials.md", "F4 | Cats and Dogs", "F9 | Lasts for Weeks")],
        )

    def test_module_headline_number_must_come_from_its_facts(self):
        self.assert_error(
            "number '7'", "P6_daily_use.md",
            [("P6_daily_use.md", "headline: Made for Daily Use", "headline: Made for 7 Days")],
        )

    def test_module_card_cannot_carry_scene_fields(self):
        self.assert_error(
            "belongs on the panel cards", "P6_daily_use.md",
            [("P6_daily_use.md", "panels: P6a, P6b, P6c", "panels: P6a, P6b, P6c\ncamera: wide")],
        )


class PremiumEditionTest(APlusTest):
    """The premium A+ edition: tone, the wide lead panel, number and contrast modules."""

    FOLDER = "examples_premium"

    def errors_after(self, card_name, edits=(), remove=()):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for source in (ROOT / "cards" / self.FOLDER).glob("*.md"):
                if source.name not in remove:
                    shutil.copy(source, folder / source.name)
            for name, old, new in edits:
                text = (folder / name).read_text(encoding="utf-8")
                self.assertIn(old, text, f"test fixture out of date: {name}")
                (folder / name).write_text(text.replace(old, new), encoding="utf-8")
            errors, _warnings, _context = check_card.validate(folder / card_name, self.index)
        return errors

    def context_for(self, name):
        errors, _warnings, context = check_card.validate(ROOT / "cards" / self.FOLDER / name, self.index)
        self.assertEqual(errors, [])
        return context

    # The inherited standard-edition tests point at cards/round10l; they are run by APlusTest.
    test_module_card_collects_its_panels = None
    test_specs_lines_are_parsed = None
    test_scene_and_panel_prompts_ask_for_croppable_frames = None
    test_p_slot_without_module_is_rejected = None
    test_scene_text_area_must_be_a_side = None
    test_panel_with_its_own_headline_is_rejected = None
    test_missing_panel_card_is_rejected = None
    test_panel_error_fails_the_module = None
    test_grid_panels_need_different_facts = None
    test_grid_panel_without_label_is_rejected = None
    test_steps_panels_must_share_the_fact = None
    test_panel_list_must_be_in_order = None
    test_too_many_panels_is_rejected = None
    test_spec_line_number_must_match_its_fact = None
    test_spec_line_needs_a_real_fact = None
    test_module_headline_number_must_come_from_its_facts = None
    test_module_card_cannot_carry_scene_fields = None

    def test_edition_and_tone_reach_the_context(self):
        context = self.context_for("P3_built.md")
        self.assertEqual((context["edition"], context["tone"]), ("premium", "dark"))
        self.assertEqual(self.context_for("P1_together.md")["edition"], "premium")

    def test_lead_panel_prompt_is_wide(self):
        blocks = check_card.load_prompt_blocks()
        lead = check_card.build_prompt(self.context_for("P3a_steel.md"), blocks)
        small = check_card.build_prompt(self.context_for("P3b_quiet.md"), blocks)
        self.assertIn("horizontal 3:2", lead)
        self.assertIn("square 1:1", small)
        self.assertIn("lower-left corner calm", small)

    def test_standard_edition_cannot_be_dark(self):
        self.assert_error(
            "tone: dark is only for the premium edition", "P3_built.md",
            [("P3_built.md", "edition: premium", "edition: standard")],
        )

    def test_standard_edition_has_no_number_module(self):
        self.assert_error(
            "module: number is only for the premium edition", "P2_capacity.md",
            [("P2_capacity.md", "edition: premium\n", "")],
        )

    def test_unknown_edition_is_rejected(self):
        self.assert_error(
            "edition must be standard or premium", "P2_capacity.md",
            [("P2_capacity.md", "edition: premium", "edition: deluxe")],
        )

    def test_panel_cannot_set_edition(self):
        self.assert_error(
            "only for P1-P8 cards", "P3b_quiet.md",
            [("P3b_quiet.md", "canvas: 1:1", "canvas: 1:1\nedition: premium")],
        )

    def test_premium_grid_lead_panel_must_be_wide(self):
        self.assert_error(
            "panel P3a: canvas must be 3:2", "P3_built.md",
            [("P3a_steel.md", "canvas: 3:2", "canvas: 1:1")],
        )

    def test_premium_grid_small_panel_must_be_square(self):
        self.assert_error(
            "panel P3b: canvas must be 1:1", "P3_built.md",
            [("P3b_quiet.md", "canvas: 1:1", "canvas: 3:2")],
        )

    def test_premium_grid_takes_at_most_three_panels(self):
        self.assert_error(
            "needs 2 to 3 panel(s)", "P3_built.md",
            [("P3_built.md", "panels: P3a, P3b, P3c", "panels: P3a, P3b, P3c, P3d")],
        )

    def test_number_module_needs_a_hero_number(self):
        self.assert_error(
            "a number module needs hero_number", "P2_capacity.md",
            [("P2_capacity.md", "hero_number: 10 L", "hero_number: none")],
        )

    def test_number_module_checks_the_number_against_its_fact(self):
        self.assert_error(
            "number '12'", "P2_capacity.md",
            [("P2_capacity.md", "hero_number: 10 L", "hero_number: 12 L")],
        )

    def test_number_panel_takes_no_label(self):
        self.assert_error(
            "'label' must be none in a number module", "P2_capacity.md",
            [("P2a_capacity_scene.md", "label: none", "label: Big Basin")],
        )

    def test_contrast_panels_must_share_the_fact(self):
        self.assert_error(
            "every panel of a contrast module must use F5", "P4_rinse.md",
            [("P4a_before.md", "selling_point: F5", "selling_point: F2")],
        )

    def test_contrast_takes_exactly_two_panels(self):
        self.assert_error(
            "needs 2 panel(s)", "P4_rinse.md",
            [("P4_rinse.md", "panels: P4a, P4b", "panels: P4a")],
        )

    def test_set_notes_flag_mixed_editions_and_adjacent_dark_screens(self):
        dark = self.context_for("P3_built.md")
        standard = dict(self.context_for("P2_capacity.md"), edition="standard")
        also_dark = dict(self.context_for("P4_rinse.md"), tone="dark")
        cards = [(Path("P2.md"), standard), (Path("P3.md"), dark), (Path("P4.md"), also_dark)]
        notes = " | ".join(check_card.set_notes(cards))
        self.assertIn("mix the standard and the premium edition", notes)
        self.assertIn("P3 and P4 are both dark", notes)


class MainImageTest(unittest.TestCase):
    def test_m1_prompt_is_product_only(self):
        index = check_card.load_index()
        errors, _warnings, context = check_card.validate(ROOT / "cards" / "round10l" / "M1_white.md", index)
        self.assertEqual(errors, [])
        prompt = check_card.build_prompt(context, check_card.load_prompt_blocks())
        self.assertIn("pure white background", prompt)
        self.assertIn("same front view", prompt)
        self.assertNotIn("whole room", prompt)
        self.assertEqual([slot for slot, _path, _purpose in context["attach"]], ["product"])


class GrokSkillTest(unittest.TestCase):
    """The grok-UTAstyle skill must stay in step with UTA_STYLE.md and the repo."""

    SKILL = (ROOT / "grok" / "grok-UTAstyle-skill.md").read_text(encoding="utf-8")
    GUIDE = (ROOT / "UTA_STYLE.md").read_text(encoding="utf-8")

    def test_skill_reads_the_guide_instead_of_pinning_a_version(self):
        """The skill follows the UTA_STYLE.md it just read and does not embed a version."""
        self.assertRegex(self.GUIDE, r"版本 \d+\.\d+")
        pinned = re.findall(r"\b\d+\.\d+\b", self.SKILL)
        self.assertEqual(pinned, [], pinned)
        self.assertIn("UTA_STYLE.md", self.SKILL)
        self.assertIn("读不到", self.SKILL)
        self.assertIn("凭记忆", self.SKILL)
        self.assertIn("以刚读到的规范为准", self.SKILL)

    def test_files_the_skill_reads_exist(self):
        for path in re.findall(r"`((?:cards|products|references)/[^`<>]+\.(?:md|csv))`", self.SKILL):
            if "<" not in path:
                self.assertTrue((ROOT / path).is_file(), path)

    def test_read_check_line_is_on_line_three(self):
        third = self.GUIDE.splitlines()[2]
        self.assertTrue(third.startswith("版本 "), third)
        self.assertIn("。", third)

    def test_sections_the_skill_cites_exist(self):
        headings = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)", self.GUIDE, re.M))
        for section in set(re.findall(r"`UTA_STYLE\.md` (\d+\.\d+)", self.SKILL)):
            self.assertIn(section, headings, section)


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
        self.assertTrue(any("no 'UTA-TASK v1' line found" in error for error in errors), errors)

    def test_instruction_line_before_the_header_is_ignored(self):
        text = "```\n按 UTA style 执行下面这份任务单。\n" + task_sheet([self.CARD]) + "\n```\n"
        product, cards, errors = check_card.parse_task(text)
        self.assertEqual(errors, [])
        self.assertEqual((product, len(cards)), ("round10l", 1))

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
        self.assertIn("THEN COMPOSE", output.getvalue())
        self.assertNotIn("check_card.py cards/round10l/P6_daily_use.md\n  python tools/check_card.py cards/round10l/P6a", output.getvalue())
        self.assertNotIn("(updated)", output.getvalue())
        for path, content in before.items():
            self.assertEqual(path.read_bytes().replace(b"\r\n", b"\n"), content, path.name)


if __name__ == "__main__":
    unittest.main()
