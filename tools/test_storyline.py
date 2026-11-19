"""Tests for the set-level storyline (UTA_STYLE.md 1.14, 2.6 L rules).

    python -m unittest discover -s tools -p "test_storyline.py" -v
"""
import csv
import os
import re
import unittest

import check_set
from test_check_set import Base, ROOT, V2, read

CAST = "PT01;PT07;PT02;PT03;PT05;PT06;HP05;HP02;HP01;HP08;HP03"


def with_chapters(text, chapters=None):
    """Give every card that has a story one chapter line, numbered in order."""
    n = [0]

    def add(m):
        n[0] += 1
        label = chapters[n[0] - 1] if chapters else "第%d章" % n[0]
        return m.group(0) + "\nchapter: " + label
    return re.sub(r"^story: (?!none).*$", add, text, flags=re.M)


def header(text, storyline=None, cast=None):
    extra = ""
    if storyline:
        extra += "storyline: %s\n" % storyline
    if cast:
        extra += "cast: %s\n" % cast
    return text.replace("scope: full\n", "scope: full\n" + extra, 1)


def techniques(text, slot, ids):
    return re.sub(r"(^slot: %s\n)" % re.escape(slot), r"\1techniques: %s\n" % ids, text, count=1, flags=re.M)


class LibraryTest(unittest.TestCase):
    def test_storylines_point_at_real_techniques(self):
        with open(os.path.join(ROOT, "references", "techniques.csv"), encoding="utf-8") as fh:
            dims = {r["id"]: r["dimension"] for r in csv.DictReader(fh)}
        with open(os.path.join(ROOT, "references", "storylines.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(check_set.DEFAULT_STORYLINE, ids)
        for r in rows:
            self.assertIn(r["cast"], ("yes", "no"), r["id"])
            self.assertIn(r["chapters"], check_set.STORY_CHAPTERS, r["id"])
            for t in r["learn_from"].split(";"):
                self.assertIn(t, dims, (r["id"], t))
            for t in r["headline_voice"].split(";"):
                self.assertEqual(dims.get(t), "headline", (r["id"], t))
        default = [r for r in rows if r["id"] == check_set.DEFAULT_STORYLINE][0]
        self.assertEqual((default["cast"], default["chapters"]), ("no", "none"))


class RulesTest(Base):
    def test_old_tasks_without_a_storyline_are_unchanged(self):
        code, out, _ = self.run_task(V2)
        self.assertEqual(code, 0, out)
        self.assertNotIn("[L-", out)
        self.assertNotIn("storyline=", out)

    def test_unknown_storyline_is_a_task_error(self):
        code, out, _ = self.run_task(self.write("t.md", header(read(V2), "SL9")))
        self.assertEqual(code, 2)
        self.assertIn("storyline", out)

    def test_a_storyline_needs_chapters_and_a_cast(self):
        code, out, _ = self.run_task(self.write("t.md", header(read(V2), "SL1")))
        self.assertNotEqual(code, 0)
        self.assertIn("[L-1]", out)
        self.assertIn("[L-3]", out)

    def test_full_storyline_passes_and_cast_pets_may_recur(self):
        text = with_chapters(header(read(V2), "SL1", CAST))
        for slot, ids in (("S1", "T01;T47"), ("S4", "T33;T04"), ("P1", "T42")):
            text = techniques(text, slot, ids)
        code, out, emit = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 0, out)
        self.assertIn("storyline=SL1 一天里的几个瞬间", out)
        self.assertNotIn("[L-", out)
        self.assertNotIn("[K-1]", out)
        emitted = read(emit)
        self.assertNotIn("chapter:", emitted)
        self.assertNotIn("techniques:", emitted)

    def test_too_few_techniques_is_a_warning(self):
        code, out, _ = self.run_task(self.write("t.md", with_chapters(header(read(V2), "SL1", CAST))))
        self.assertEqual(code, 0, out)
        self.assertIn("[L-4] 整套只借用了 0 条品牌手法", out)

    def test_one_chapter_one_image(self):
        text = with_chapters(header(read(V2), "SL1", CAST), ["清晨"] * 2 + ["第%d章" % i for i in range(3, 30)])
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertNotEqual(code, 0)
        self.assertIn("[L-2] chapter「清晨」", out)

    def test_pet_outside_the_cast_is_a_warning(self):
        text = with_chapters(header(read(V2), "SL1", CAST.replace("PT05;", "")))
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("[L-3]", out)
        self.assertIn("PT05 不在 cast 里", out)

    def test_unknown_technique_fails_and_off_voice_headline_warns(self):
        text = with_chapters(header(read(V2), "SL1", CAST))
        text = techniques(text, "S1", "T99")
        text = techniques(text, "S2", "T16;T01;T33")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertNotEqual(code, 0)
        self.assertIn("[L-4] S1 写的手法 T99", out)
        self.assertIn("[L-5] S2 的标题手法 T16", out)


class WiringTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_and_skill(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("**整套主线。**", "references/storylines.csv", "`storyline:`", "`cast:`", "| `chapter` |",
                       "| `techniques` |", "- L-1 ", "- L-5 "):
            self.assertIn(marker, guide)
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("references/storylines.csv", skill)
        self.assertIn("cast", skill)


if __name__ == "__main__":
    unittest.main()
