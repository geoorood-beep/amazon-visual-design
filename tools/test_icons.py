"""Icon library (UTA_STYLE.md 1.5): the files, the token, and both checkers.

    python -m unittest discover -s tools -p "test_icons.py" -v
"""
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import check_card
import icons
from test_check_set import Base, V2, read

ROOT = Path(check_card.ROOT)
PREMIUM = ROOT / "cards" / "examples_premium"


class LibraryTest(unittest.TestCase):
    def test_every_icon_has_a_line_svg(self):
        rows = icons.load_icons(ROOT)
        self.assertGreaterEqual(len(rows), 30)
        self.assertTrue((ROOT / "references" / "icons" / "LICENSE").is_file())
        self.assertTrue((ROOT / "references" / "icons" / "board.png").is_file())
        for icon_id, row in rows.items():
            self.assertRegex(icon_id, r"^[a-z]+(-[a-z]+)*$")
            svg = (ROOT / icons.icon_path(icon_id)).read_text(encoding="utf-8")
            self.assertIn("<svg", svg, icon_id)
            self.assertIn('stroke="currentColor"', svg, icon_id)
            self.assertTrue(row["source"].startswith("lucide:"), icon_id)
            self.assertTrue(row["name"] and row["means"], icon_id)
        self.assertNotIn("wifi", " ".join(rows))
        for need in ("cord-free", "travel", "charging", "battery", "capacity", "quiet", "warranty"):
            self.assertIn(need, rows)

    def test_split_icon(self):
        self.assertEqual(icons.split_icon("{icon:capacity} 10 L"), ("capacity", "10 L", None))
        self.assertEqual(icons.split_icon("10 L"), (None, "10 L", None))
        self.assertEqual(icons.split_icon("10 L {icon:capacity}")[2], "the icon must come first, before the number or words")
        self.assertEqual(icons.split_icon("{icon:a} {icon:b} x")[2], "only one icon per line")
        self.assertEqual(icons.strip_icons("{icon:quiet} Under 20 dB"), "Under 20 dB")

    def test_icon_must_be_backed_by_the_fact(self):
        self.assertIsNone(icons.icon_problem(ROOT, "capacity", "容量 10 升 10 L", "hero_number"))
        self.assertIn("needs a fact that mentions", icons.icon_problem(ROOT, "battery", "容量 10 升 10 L", "hero_number"))
        self.assertIn("unknown icon", icons.icon_problem(ROOT, "rocket", "", "label"))
        self.assertIn("only goes on the lines of a trust screen", icons.icon_problem(ROOT, "warranty", "2 年质保", "label"))
        self.assertIsNone(icons.icon_problem(ROOT, "warranty", "2 年质保", "lines", "trust"))
        self.assertIsNone(icons.icon_problem(ROOT, "home", "anything", "label"))


class CheckCardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = check_card.load_index()

    def validate(self, name, edits):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for source in PREMIUM.glob("*.md"):
                shutil.copy(source, folder / source.name)
            for file, old, new in edits:
                text = (folder / file).read_text(encoding="utf-8")
                self.assertIn(old, text, file)
                (folder / file).write_text(text.replace(old, new), encoding="utf-8")
            return check_card.validate(folder / name, self.index)

    def test_hero_number_and_label_icons(self):
        errors, _w, context = self.validate("P2_capacity.md", [("P2_capacity.md", "hero_number: 10 L", "hero_number: {icon:capacity} 10 L")])
        self.assertEqual(errors, [])
        self.assertEqual(context["icons"], {"hero_number": "capacity"})
        self.assertEqual(context["fields"]["hero_number"], "10 L")
        errors, _w, context = self.validate("P3_built.md", [("P3b_quiet.md", "label: Under 20 dB", "label: {icon:quiet} Under 20 dB")])
        self.assertEqual(errors, [])
        quiet = [p for p in context["panels"] if p["fields"]["slot"] == "P3b"][0]
        self.assertEqual(quiet["icons"], {"label": "quiet"})

    def test_wrong_or_misplaced_icons_are_rejected(self):
        errors, _w, _c = self.validate("P2_capacity.md", [("P2_capacity.md", "hero_number: 10 L", "hero_number: {icon:battery} 10 L")])
        self.assertTrue(any("hero_number: icon 'battery'" in e for e in errors), errors)
        errors, _w, _c = self.validate("P2_capacity.md", [("P2_capacity.md", "headline: ", "headline: {icon:capacity} ")])
        self.assertTrue(any("headline: an icon only goes before" in e for e in errors), errors)

    def test_spec_line_icon(self):
        edits = [("P2_capacity.md", "module: number", "module: split"),
                 ("P2_capacity.md", "lines: none", "lines: F1 | {icon:capacity} 10 L")]
        errors, _w, context = self.validate("P2_capacity.md", edits)
        self.assertEqual(errors, [])
        self.assertEqual((context["lines"], context["line_icons"]), ([("F1", "10 L")], ["capacity"]))


class CheckSetTest(Base):
    def test_icons_in_a_task(self):
        ok = read(V2).replace("hero_number: Under 20 dB", "hero_number: {icon:quiet} Under 20 dB", 1)
        code, out, emit = self.run_task(self.write("t.md", ok))
        self.assertEqual(code, 0, out)
        self.assertIn("hero_number: {icon:quiet} Under 20 dB", read(emit))
        bad = read(V2).replace("hero_number: Under 20 dB", "hero_number: {icon:battery} Under 20 dB", 1)
        code, out, _ = self.run_task(self.write("t.md", bad))
        self.assertNotEqual(code, 0)
        self.assertIn("hero_number 的图标不对：icon 'battery'", out)
        bad = read(V2).replace("headline: Quiet at Bedtime", "headline: {icon:quiet} Quiet at Bedtime", 1)
        code, out, _ = self.run_task(self.write("t.md", bad))
        self.assertIn("headline 不能放图标", out)


class WiringTest(unittest.TestCase):
    def test_guide_and_skill(self):
        guide = (ROOT / "UTA_STYLE.md").read_text(encoding="utf-8")
        self.assertIn("**图标（选填）。**", guide)
        self.assertIn("references/icons/", guide)
        skill = (ROOT / "grok" / "grok-UTAstyle-skill.md").read_text(encoding="utf-8")
        self.assertIn("references/icons/icons.csv", skill)


if __name__ == "__main__":
    unittest.main()
