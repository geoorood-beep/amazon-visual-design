"""Tests for tools/check_index.py (UTA_STYLE.md 2.5, 3.6)."""
import io
import os
import shutil
import tempfile
import unittest

import check_index

ROOT = check_index.ROOT
INDEX = os.path.join(ROOT, "references", "INDEX.csv")


class IndexTest(unittest.TestCase):
    def write_index(self, text):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "INDEX.csv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_repo_index_is_valid(self):
        self.assertEqual(check_index.validate(), [])

    def test_bad_values_are_reported(self):
        with open(INDEX, encoding="utf-8") as fh:
            text = fh.read()
        old = '"docs/uta_style_v3/assets/key/XHS_011.jpg"'
        self.assertIn(old, text)
        lines = text.splitlines()
        row = next(l for l in lines if l.startswith(old))
        bad = row.replace('"A"', '"S"').replace('"low_sun"', '"noon"')
        errors = check_index.validate(index_path=self.write_index(text.replace(row, bad)))
        self.assertTrue(any("grade 要写 A、B 或 C" in e for e in errors), errors)
        self.assertTrue(any("light 不认识：noon" in e for e in errors), errors)

    def test_inbox_lists_new_images(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, "references", "inbox"))
        os.makedirs(os.path.join(root, *check_index.CASE_DIR.split("/")))
        open(os.path.join(root, "references", "inbox", "my case (1).JPG"), "wb").close()
        out = io.StringIO()
        check_index.inbox(root, out)
        text = out.getvalue()
        self.assertIn("待入库 1 张", text)
        self.assertIn("NEW_my_case_1.jpg", text)


class WiringTest(unittest.TestCase):
    """Everything the scripts and the card writer depend on is named where they read it."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_digest_is_in_sync(self):
        self.assertEqual(self.read("references", "CASES.md"), check_index.digest_text())

    def test_read_list_names_every_pool(self):
        import check_set
        guide = self.read("UTA_STYLE.md")
        start = guide.index("### 2.1 读什么")
        section = guide[start:guide.index("### 2.2", start)]
        for fname in check_set.POOL_FILES.values():
            self.assertIn("pools/" + fname, section)
        self.assertIn("references/CASES.md", section)

    def test_guide_ends_with_the_marker_section(self):
        guide = self.read("UTA_STYLE.md")
        headings = [l for l in guide.splitlines() if l.startswith("## ")]
        self.assertEqual(headings[-1], "## 禁用词")
        self.assertIn("最后一节是「禁用词」", guide)

    def test_choice_numbers_match_the_example(self):
        guide = self.read("UTA_STYLE.md")
        for row in ("| 0 | 故事 |", "| 1 | 证据方案 |", "| 2 | 场景 |", "| 3 | 宠物 |",
                    "| 4 | 表情 |", "| 5 | 人物 |", "| 6 | 标题 |"):
            self.assertIn(row, guide)
        self.assertIn("S5：0B 1A 2B 3A 4C 5A 6B", guide)

    def test_card_fields_checked_by_script_are_documented(self):
        import check_set
        guide = self.read("UTA_STYLE.md")
        start = guide.index("### 2.4")
        section = guide[start:guide.index("### 2.5", start)]
        for field in check_set.POOL_FIELDS + ["story"] + check_set.V2_IMAGE_FIELDS:
            self.assertIn("`%s`" % field, section, field)


class AgentsIntakeTest(unittest.TestCase):
    def test_agents_and_guide_name_the_intake(self):
        with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as fh:
            agents = fh.read()
        with open(os.path.join(ROOT, "UTA_STYLE.md"), encoding="utf-8") as fh:
            guide = fh.read()
        self.assertIn("入库新案例", agents)
        self.assertIn("### 3.6 新案例入库", guide)
        self.assertIn("**案例的三种用法。**", guide)


if __name__ == "__main__":
    unittest.main()
