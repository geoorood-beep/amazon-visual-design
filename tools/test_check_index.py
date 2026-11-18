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


class ConfirmAndTechniquesTest(unittest.TestCase):
    """Visual confirmation sheet and brand technique library (v3.21)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_techniques_are_valid(self):
        self.assertEqual(check_index.validate_techniques(), [])

    def test_bad_technique_is_reported(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "t.csv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(",".join(check_index.TECH_COLUMNS) + "\n")
            fh.write("T01,poster,Apple,x,how,transfer,all,avoid,\n")
            fh.write("T01,story,,x,how,transfer,all,avoid,www.apple.com no note\n")
        errors = check_index.validate_techniques(path=path)
        self.assertTrue(any("dimension" in e for e in errors), errors)
        self.assertTrue(any("id 重复" in e for e in errors), errors)
        self.assertTrue(any("brand 不能空" in e for e in errors), errors)
        self.assertTrue(any("examples 每一条" in e for e in errors), errors)

    def test_examples_cover_every_brand(self):
        import csv
        with open(os.path.join(ROOT, "references", "techniques.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        with_examples = [r for r in rows if r["examples"].strip()]
        self.assertGreaterEqual(len(with_examples), len(rows) // 2)
        for domain in ("apple.com", "anker.com", "mi.com", "coca-colacompany.com"):
            self.assertTrue(any(domain in r["examples"] for r in with_examples), domain)

    def test_brand_studies_point_at_real_techniques(self):
        import csv, re
        with open(os.path.join(ROOT, "references", "techniques.csv"), encoding="utf-8") as fh:
            ids = {r["id"] for r in csv.DictReader(fh)}
        guide = self.read("UTA_STYLE.md")
        start = guide.index("### 2.1 读什么")
        read_list = guide[start:guide.index("### 2.2", start)]
        studies = sorted(f for f in os.listdir(os.path.join(ROOT, "references", "brands")) if f.endswith(".md"))
        self.assertEqual(studies, ["anker.md", "apple.md", "coca-cola.md", "xiaomi.md"])
        for name in studies:
            study = self.read("references", "brands", name)
            cited = set(re.findall(r"\bT\d{2}\b", study))
            self.assertTrue(cited, name + " cites no technique")
            self.assertEqual(cited - ids, set(), name)
            self.assertIn("## 8. 不学什么", study, name)
            self.assertIn("references/brands/" + name, read_list, name)

    def test_every_dimension_and_brand_is_covered(self):
        import csv
        with open(os.path.join(ROOT, "references", "techniques.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual({r["dimension"] for r in rows}, check_index.TECH_DIMENSIONS)
        self.assertTrue({"Apple", "Anker", "Xiaomi", "Coca-Cola"} <= {r["brand"] for r in rows})

    def test_template_has_a_parseable_sheet(self):
        import json, re
        html = self.read("grok", "confirm_template.html")
        m = re.search(r'<script id="sheet" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(m)
        data = json.loads(m.group(1))
        image = data["images"][0]
        for key in ("slot", "story", "route", "case", "product_ref", "scene", "pet", "shot", "headline"):
            self.assertIn(key, image)

    def test_wiring(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        start = guide.index("### 2.1 读什么")
        self.assertIn("references/techniques.csv", guide[start:guide.index("### 2.2", start)])
        self.assertIn("**品牌手法库。**", guide)
        self.assertIn("**给人看的确认表。**", guide)
        self.assertIn("grok/confirm_template.html", guide)
        self.assertIn("grok/confirm_template.html", skill)
        self.assertIn("不发 Markdown 文件", skill)


class UsageWiringTest(unittest.TestCase):
    """Product usage model is named where the writer and Codex read (v3.25)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_fact_visuals_table_is_sane(self):
        import csv
        import usage_model
        with open(os.path.join(ROOT, "references", "fact_visuals.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for r in rows:
            self.assertIn(r["state"], usage_model.GENERIC_STATES, r["id"])
            self.assertTrue(r["keywords"].strip() and r["must_show_en"].strip(), r["id"])

    def test_spec_skill_and_agents_name_it(self):
        guide = self.read("UTA_STYLE.md")
        start = guide.index("### 2.1 读什么")
        self.assertIn("references/fact_visuals.csv", guide[start:guide.index("### 2.2", start)])
        start = guide.index("### 2.4")
        self.assertIn("`product_state`", guide[start:guide.index("### 2.5", start)])
        for marker in ("### 1.15 产品怎么用", "### 3.7 入库产品视频", "| V5 |", "- S-8 ", "- A-13 ",
                       "### 1.16 多角度", "- S-9 ", "- S-10 ", "- A-14 ", "- A-15 ", "- U-1 ", "`effect`",
                       "**不确定就问用户。**"):
            self.assertIn(marker, guide)
        self.assertIn("product_state", self.read("grok", "grok-UTAstyle-skill.md"))
        self.assertIn("入库产品视频", self.read("AGENTS.md"))
        self.assertIn("## 事实的画面要求", self.read("products", "_template", "PRODUCT.md"))
        self.assertIn("## 内部结构", self.read("products", "_template", "PRODUCT.md"))
        self.assertIn("不确定就问", self.read("grok", "grok-UTAstyle-skill.md"))


class UnderstandingTest(unittest.TestCase):
    """Every product is understood first; unsure points go to the user (v3.27)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_understand_template_has_a_parseable_sheet(self):
        import json, re
        html = self.read("grok", "understand_template.html")
        m = re.search(r'<script id="sheet" type="application/json">(.*?)</script>', html, re.S)
        data = json.loads(m.group(1))
        for key in ("summary", "parts", "flow", "functions", "states", "internal", "questions"):
            self.assertIn(key, data)
        self.assertIn("confidence", data["functions"][0])
        self.assertIn("recommend", data["questions"][0])

    def test_wiring(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("**先理解产品（所有产品通用，每个产品一次）。**", "**第零轮：先理解产品", "### 3.8 更新产品理解",
                       "`disassembled`", "`loading`", "grok/understand_template.html"):
            self.assertIn(marker, guide)
        self.assertNotIn("top_removed", guide)
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("## 先理解产品（每个产品一次）", skill)
        self.assertIn("grok/understand_template.html", skill)
        self.assertIn("更新产品理解", self.read("AGENTS.md"))
        self.assertIn("## 产品理解", self.read("products", "_template", "PRODUCT.md"))

    def test_generic_rules_are_not_fountain_only(self):
        import csv
        with open(os.path.join(ROOT, "references", "fact_visuals.csv"), encoding="utf-8") as fh:
            text = " ".join(r["must_show_en"] for r in csv.DictReader(fh))
        self.assertNotIn("top unit", text)
        self.assertIn("air", text)


class FastPathTest(unittest.TestCase):
    """Normal path is three clicks; no batching by image; light reading (v3.28)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_fast_path_is_the_default(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("**快速通道：正常情况下用户只点三次。**", guide)
        self.assertNotIn("按图分批", guide + skill)
        self.assertIn("「★ 全部按推荐」", skill)
        self.assertIn("卡片以外的文字最多三行", skill)
        self.assertIn("正常情况下用户只点三次", skill)

    def test_read_check_is_one_line(self):
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("已读取：规范 <版本句原文>", skill)
        self.assertNotIn("每个再加一行", skill)

    def test_codex_does_not_stop_midway(self):
        guide = self.read("UTA_STYLE.md")
        self.assertIn("不在出图中途停下等用户", guide)

    def test_story_emotion_and_items_are_selectable(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        for text in (guide, skill):
            self.assertIn("情绪卡", text)
            self.assertIn("逐项选", text)
        self.assertIn("**改某一张。**", guide)
        self.assertIn("★ 剩下的全部按推荐", skill)

    def test_vivid_expressions_and_lenses_are_wired(self):
        import csv
        guide = self.read("UTA_STYLE.md")
        for marker in ("### 1.17 夸张表情和特殊镜头", "- S-11 ", "- A-16 ", "- K-6 ", "| `lens` |", "`impact:`"):
            self.assertIn(marker, guide)
        with open(os.path.join(ROOT, "pools", "expressions.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual({r["level"] for r in rows}, {"自然", "夸张"})
        self.assertGreaterEqual(sum(r["level"] == "夸张" for r in rows), 8)
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("人物情绪 · 宠物表情 · 镜头", skill)
        self.assertIn("冲击力", skill)

    def test_default_eight_sub_images(self):
        self.assertIn("副图默认 8 张", self.read("UTA_STYLE.md"))
        self.assertIn("副图默认 8 张", self.read("grok", "grok-UTAstyle-skill.md"))


if __name__ == "__main__":
    unittest.main()
