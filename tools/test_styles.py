"""The style pool (UTA_STYLE.md 1.13): every style can be lit, has graded examples, and ST07 is there.

    python -m unittest discover -s tools -p "test_styles.py" -v
"""
import csv
import os
import unittest

import check_set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rows(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class StylePoolTest(unittest.TestCase):
    def test_every_style_uses_known_lights_and_real_examples(self):
        for s in rows("pools", "styles.csv"):
            lights = [x for x in s["lights"].split(";") if x]
            self.assertTrue(lights, s["id"])
            self.assertLessEqual(set(lights), set(check_set.LIGHT_SETUPS), s["id"])
            for path in s["examples"].split(";"):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), (s["id"], path))

    def test_warm_sun_style(self):
        style = {s["id"]: s for s in rows("pools", "styles.csv")}["ST07"]
        self.assertEqual(style["name"], "暖阳生活风")
        self.assertIn("stays neutral silver", style["look_en"])
        for word in ("水位窗", "信息卡", "铜色"):
            self.assertIn(word, style["avoid"])
        cases = [r for r in rows("references", "INDEX.csv") if r["style_id"] == "ST07"]
        self.assertEqual(len(cases), 2)
        self.assertIn("暖阳生活风", open(os.path.join(ROOT, "UTA_STYLE.md"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
