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


class BootstrapTest(unittest.TestCase):
    def test_bootstrap_points_at_the_live_skill(self):
        with open(os.path.join(ROOT, "grok", "BOOTSTRAP.md"), encoding="utf-8") as fh:
            text = fh.read()
        url = "https://raw.githubusercontent.com/geoorood-beep/amazon-visual-design/main/grok/grok-UTAstyle-skill.md"
        self.assertIn(url, text)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "grok", "grok-UTAstyle-skill.md")))
        self.assertIn("每次都重新读取", text)


class AgentsIntakeTest(unittest.TestCase):
    def test_agents_and_guide_name_the_intake(self):
        with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as fh:
            agents = fh.read()
        with open(os.path.join(ROOT, "UTA_STYLE.md"), encoding="utf-8") as fh:
            guide = fh.read()
        self.assertIn("入库新案例", agents)
        self.assertIn("### 3.6 新案例入库", guide)
        self.assertIn("**案例的三种用法。**", guide)


class NewProductFlowTest(unittest.TestCase):
    """A new product must not stop at the product card (v3.18)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_skill_keeps_going_after_the_card(self):
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("## 新产品：建卡之后接着往下", skill)
        self.assertNotIn("确认后再来。不进入第 1 步", skill)
        self.assertIn("新建产品 <产品> 并做造型基准", skill)
        self.assertIn("同一条消息里接着进入第 1 步", skill)

    def test_guide_and_agents_accept_the_handoff(self):
        guide = self.read("UTA_STYLE.md")
        agents = self.read("AGENTS.md")
        start = guide.index("### 2.1 读什么")
        section = guide[start:guide.index("### 2.2", start)]
        self.assertNotIn("不进入 2.2", section)
        self.assertIn("同时照常进入 2.2", section)
        self.assertIn("新产品先建卡", guide)
        self.assertIn("新建产品 <产品> 并做造型基准", agents)


class FlowV319Test(unittest.TestCase):
    """No mid-flow stops, baseline as a reference set, deeper story options (v3.20)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_skill_keeps_going(self):
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("## 一直往下走", skill)
        self.assertIn("每条消息只能停在三种地方", skill)
        self.assertIn("进度：", skill)
        self.assertNotIn("每一格一张提问卡", skill)

    def test_baseline_is_a_reference_set(self):
        guide = self.read("UTA_STYLE.md")
        self.assertIn("**造型基准是参考集，不是机位清单。**", guide)
        self.assertIn("**确认：整体看一次。**", guide)
        self.assertNotIn("用户逐格回", guide)
        self.assertIn("**产品参考和机位参考分开。**", guide)

    def test_story_options_cover_routes(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        for route in ("R1 证据直给", "R2 家庭生活时刻", "R3 汇聚共享", "R4 没有它会怎样",
                      "R5 没人注意", "R6 尺度参照", "R7 情绪落点"):
            self.assertIn(route, guide)
        self.assertIn("| 一家人在地上 |", guide)
        self.assertIn("4 个故事选项", guide)
        self.assertIn("**卖点梳理。**", guide)
        self.assertNotIn("2–3 个故事", guide)
        self.assertNotIn("2–3 个故事", skill)


if __name__ == "__main__":
    unittest.main()
