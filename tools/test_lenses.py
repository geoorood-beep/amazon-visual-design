"""Special lenses (UTA_STYLE.md 1.17): the three wide lenses added in 3.50.

    python -m unittest discover -s tools -p "test_lenses.py" -v
"""
import csv
import os
import re
import unittest

import check_set
from test_check_set import Base, V2, read

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = ("surface_wide", "reach_in", "hero_wide")


def set_lens(text, slot, lens, **fields):
    """Give one card a lens (and override some of its fields)."""
    head = "slot: %s\n" % slot
    start = text.index(head)
    end = text.index("\n---", start)
    block = text[start:end]
    block = re.sub(r"^lens: .*\n", "", block, flags=re.M)
    block = block.replace(head, head + "lens: %s\n" % lens, 1)
    for k, v in fields.items():
        block = re.sub(r"^%s: .*$" % k, "%s: %s" % (k, v), block, count=1, flags=re.M)
    return text[:start] + block + text[end:]


class LibraryTest(unittest.TestCase):
    def test_new_lenses_have_prompts_and_rules(self):
        for lens in NEW:
            self.assertIn(lens, check_set.LENSES)
            self.assertIn("Not a fisheye", check_set.LENS_TEXT[lens].replace("not a fisheye", "Not a fisheye"))
            self.assertIn(check_set.PRODUCT_SAFE, check_set.LENS_TEXT[lens])
            self.assertIn(lens, check_set.LENS_RULES)

    def test_fact_visuals_recommend_them(self):
        with open(os.path.join(ROOT, "references", "fact_visuals.csv"), encoding="utf-8") as fh:
            lenses = {r["id"]: r["lenses"].split(";") for r in csv.DictReader(fh)}
        for lens_list in lenses.values():
            for lens in lens_list:
                self.assertIn(lens, check_set.LENSES)
        self.assertIn("surface_wide", lenses["FV05"])
        self.assertIn("reach_in", lenses["FV01"])
        self.assertIn("hero_wide", lenses["FV08"])


class TaskTest(Base):
    def test_lens_reaches_the_prompt(self):
        text = set_lens(read(V2), "S2", "hero_wide", shot_size="medium", camera="eye_level")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("OK   cards/round10l/S2_capacity.md", out)
        self.assertNotIn("lens=hero_wide", out)
        _, _, cards = check_set.parse_task(text)
        s2 = [c for c in cards if c.slot == "S2"][0]
        self.assertIn("one leading line", "\n".join(check_set.compile_card(s2, None)))

    def test_shot_and_camera_must_fit_the_lens(self):
        text = set_lens(read(V2), "S2", "surface_wide", shot_size="full", camera="top_down")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertNotEqual(code, 0)
        self.assertIn("lens=surface_wide 要配景别 close 或 extreme_close，现在是 full", out)
        self.assertIn("lens=surface_wide 要配机位 eye_level 或 low_angle，现在是 top_down", out)

    def test_hero_wide_once_per_group(self):
        text = set_lens(read(V2), "S2", "hero_wide", shot_size="medium", camera="low_angle")
        text = set_lens(text, "S3", "hero_wide", shot_size="medium", camera="low_angle")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("[S-12] 主图和副图里产品英雄广角 hero_wide 用了 2 张：S2, S3", out)


class LensAnchorTest(Base):
    def test_every_lens_case_exists(self):
        cases = check_set.load_lens_cases(ROOT)
        for lens in NEW:
            self.assertTrue(cases.get(lens), lens)
        for lens, paths in cases.items():
            self.assertIn(lens, check_set.LENSES)
            for p in paths:
                self.assertTrue(os.path.isfile(os.path.join(ROOT, p)), p)

    def test_anchor_that_does_not_show_the_lens(self):
        code, out, emit = self.run_task(V2)
        self.assertIn("P1 用了镜头 wide_close，锚图不是这种镜头的示范图", out)
        self.assertIn("EXP_013.jpg", out)
        p1 = self.card_block(read(emit), "P1_together.md")
        self.assertIn(check_set.CASE_LIGHT_TEXT, p1)
        self.assertNotIn(check_set.CASE_CAMERA_TEXT, p1)

    def test_anchor_that_shows_the_lens(self):
        text = read(V2).replace(
            "  anchor: docs/uta_style_v3/assets/key/D_multipet_C5X2G933.jpg | two pets sharing one product only; not the product, the spacing marks, numbers or any text",
            "  anchor: docs/uta_style_v3/assets/key/EXP_013.jpg | the wide lens close to the face only; not the product, the dog or any text", 1)
        code, out, emit = self.run_task(self.write("t.md", text))
        self.assertNotIn("P1 用了镜头 wide_close", out)
        p1 = self.card_block(read(emit), "P1_together.md")
        self.assertIn(check_set.CASE_CAMERA_TEXT, p1)


class WiringTest(unittest.TestCase):
    def test_guide(self):
        guide = open(os.path.join(ROOT, "UTA_STYLE.md"), encoding="utf-8").read()
        for lens in NEW:
            self.assertIn("| `%s` |" % lens, guide)
        for marker in ("- S-12 ", "- A-20 ", "不用鱼眼", "**锚图按镜头挑。**", "LENS_hero_wide_cable.webp"):
            self.assertIn(marker, guide)


if __name__ == "__main__":
    unittest.main()
