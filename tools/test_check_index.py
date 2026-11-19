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
        self.assertIn("只读 main", text)
        with open(os.path.join(ROOT, "grok", "grok-UTAstyle-skill.md"), encoding="utf-8") as fh:
            skill = fh.read()
        self.assertIn("**只读主干 main。**", skill)
        import re
        for url in re.findall(r"raw\.githubusercontent\.com/\S+", skill + text):
            self.assertIn("/amazon-visual-design/main/", url, url)


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
        self.assertIn("## 新产品：素材一到先做造型基准", skill)
        self.assertNotIn("确认后再来。不进入第 1 步", skill)
        self.assertIn("新建产品 <产品> 并做造型基准", skill)
        self.assertIn("同一条消息里接着发第 1 步的卡", skill)

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
        for marker in ("**先理解产品（所有产品通用，每个产品一次）。**", "**产品理解（每个产品一次）。**", "### 3.8 更新产品理解",
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
    """Normal path is two clicks; one card per kind of choice; light reading (v3.28, v3.37)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_fast_path_is_the_default(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("**快速通道：正常情况下用户只点两次。**", guide)
        self.assertNotIn("按图分批", guide + skill)
        self.assertNotIn("只点三次", guide + skill)
        self.assertIn("「★ 全部按推荐」", skill)
        self.assertIn("卡片以外的文字最多三行", skill)
        self.assertIn("正常情况下用户只点两次", skill)

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
            self.assertIn("情绪基调", text)
            self.assertIn("逐项选", text)
            self.assertIn("一类一张卡", text)
        self.assertIn("**改某一张。**", guide)
        self.assertNotIn("情绪卡", guide + skill)
        self.assertNotIn("故事卡", guide + skill)

    def test_vivid_expressions_and_lenses_are_wired(self):
        import csv
        guide = self.read("UTA_STYLE.md")
        for marker in ("### 1.17 夸张表情和特殊镜头", "- S-11 ", "- A-16 ", "- K-6 ", "| `lens` |", "`impact:`"):
            self.assertIn(marker, guide)
        with open(os.path.join(ROOT, "pools", "expressions.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual({r["level"] for r in rows}, {"自然", "夸张", "拟人"})
        self.assertGreaterEqual(sum(r["level"] == "夸张" for r in rows), 8)
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("人物情绪 · 宠物表情 · 镜头", skill)
        self.assertIn("冲击力", skill)

    def test_tech_effects_are_wired(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("`signal_wave`", "`glow_xray`", "`motion_run`", "`energy_flow`", "`accent:`", "**科技特效**"):
            self.assertIn(marker, guide)
        self.assertIn("科技特效", self.read("grok", "grok-UTAstyle-skill.md"))
        self.assertIn("**功能特效：", self.read("references", "brands", "anker.md"))

    def test_speed_and_status_rules(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("**快速造型基准（默认）。**", guide)
        self.assertIn("## 连接 Codex 的固定路线", skill)
        self.assertIn("## 状态标记、收图和进度", skill)
        for marker in ("🟠 需要你确认", "⏳ 进行中", "✅ 完成", "⚠️ 卡住了", "一次最多 5 张图"):
            self.assertIn(marker, skill)

    def test_baseline_prints_the_fast_route(self):
        import subprocess, sys
        out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_card.py"), "--baseline", "pw002_s"],
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout
        self.assertIn("== FAST", out)
        self.assertIn("front: 01_front.png", out)
        self.assertIn("ONE image", out)
        self.assertLess(out.index("== FAST"), out.index("== SLOW"))

    def test_default_eight_sub_images(self):
        self.assertIn("副图默认 8 张", self.read("UTA_STYLE.md"))
        self.assertIn("副图默认 8 张", self.read("grok", "grok-UTAstyle-skill.md"))


class ImageBaselineDisambiguationTest(unittest.TestCase):
    """3D means multi-angle images. Mesh delivery is not a route (v3.36)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_keeps_the_image_route_and_bars_mesh_files(self):
        guide = self.read("UTA_STYLE.md")
        self.assertIn("**3D 指的是立体效果图片。**", guide)
        self.assertIn("**快速造型基准（默认）。**", guide)
        self.assertIn("**确认：整体看一次。**", guide)
        self.assertIn("**配件参考以该产品卡为准。**", guide)
        self.assertNotIn("用户逐格回", guide)
        self.assertNotIn("Meshy", guide)
        self.assertNotIn("Tripo", guide)
        self.assertNotIn("Hunyuan3D", guide)
        self.assertNotIn("手上有 3D 建模工具时可以用", guide)
        self.assertNotIn("建一次模", guide)
        for marker in ("Blender mesh", "CAD", "OBJ", "GLB", "STEP", "方盒草模"):
            self.assertIn(marker, guide)
        self.assertNotIn("IMG_0638", guide)
        self.assertNotIn("12 张实拍", guide)

    def test_schedulers_say_images_and_real_photo_input(self):
        import re
        agents = self.read("AGENTS.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        for text in (agents, skill):
            self.assertIn("Blender mesh", text)
            self.assertIn("实际传", text)
        self.assertIn("逐角度确认", agents)
        self.assertIn("逐角度确认", skill)
        self.assertEqual(re.findall(r"\b\d+\.\d+\b", skill), [])

    def test_version_strings_follow_the_guide(self):
        import check_set
        import re
        third = self.read("UTA_STYLE.md").splitlines()[2]
        version = re.search(r"版本 (\d+\.\d+)", third).group(1)
        self.assertIn("**%s**" % version, self.read("README.md"))
        self.assertIn("## v%s" % version, self.read("CHANGELOG.md"))
        self.assertEqual(check_set.VERSION, version)

    def test_readme_and_agents_links_resolve(self):
        import re
        for name in ("README.md", "AGENTS.md"):
            text = self.read(name)
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("http://", "https://", "#")):
                    continue
                path = target.split("#", 1)[0]
                self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), name + " -> " + target)

    def test_pw002_s_accessory_scope_does_not_rewrite_confirmed_rows(self):
        import csv
        card = self.read("products", "pw002_s", "PRODUCT.md")
        self.assertIn("状态：已确认（2026-11-18）", card)
        self.assertIn("### 配件参考（未确认）", card)
        self.assertIn("2026-11-18 22:43", card)
        self.assertIn("IMG_0638.jpg", card)
        self.assertIn("IMG_0653.jpeg", card)
        self.assertIn("不是连续的 12 个编号", card)
        self.assertIn("旧第 13 张", card)
        self.assertIn("白底", card)
        for view in ("正面", "背面", "俯视", "斜角"):
            self.assertIn(view, card)
        self.assertIn("不继续 A+ 重做", card)
        self.assertIn("主横幅重做", card)
        with open(os.path.join(ROOT, "products", "pw002_s", "ref_views.csv"), encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        confirmed = [
            "products/pw002_s/ref/baseline_front.png",
            "products/pw002_s/ref/baseline_side.png",
            "products/pw002_s/ref/baseline_top_down.png",
            "products/pw002_s/ref/baseline_three_quarter.png",
            "products/pw002_s/ref/baseline_detail_1.png",
            "products/pw002_s/ref/baseline_detail_2.png",
            "products/pw002_s/ref/baseline_detail_3.png",
            "products/pw002_s/ref/baseline_detail_4.png",
            "products/pw002_s/ref/baseline_detail_5.png",
            "products/pw002_s/ref/baseline_detail_6.png",
            "products/pw002_s/ref/baseline_detail_7.png",
            "products/pw002_s/ref/baseline_detail_8.png",
        ]
        uploaded = [
            "products/pw002_s/ref/user_20261118_01_whole_top.jpg",
            "products/pw002_s/ref/user_20261118_02_front_down.png",
            "products/pw002_s/ref/user_20261118_03_side_left.png",
            "products/pw002_s/ref/user_20261118_04_side_right.png",
            "products/pw002_s/ref/user_20261118_05_connection.jpg",
            "products/pw002_s/ref/user_20261118_06_pump_exploded.jpg",
            "products/pw002_s/ref/user_20261118_07_button_panel.jpg",
            "products/pw002_s/ref/user_20261118_08_accessory_back.jpg",
            "products/pw002_s/ref/user_20261118_09_accessory_side.jpg",
        ]
        self.assertEqual([row["path"] for row in rows[:len(confirmed)]], confirmed)
        self.assertEqual([row["path"] for row in rows[len(confirmed):]], uploaded)
        self.assertTrue(all(row["checked"] == "yes" for row in rows[:len(confirmed)]))
        self.assertEqual(
            [(row["product_view"], row["cameras"], row["parts"]) for row in rows[:len(confirmed)]],
            [
                ("front", "eye_level", "whole;rim;water_window;control_head;front_opening"),
                ("side_left", "eye_level", "whole;rim;control_head"),
                ("front", "top_down", "whole;rim;control_head;tray;front_slot"),
                ("three_quarter_left", "eye_level;down_45", "whole;rim;water_window;control_head"),
                ("front", "eye_level", "rim"),
                ("front", "eye_level", "water_window"),
                ("front", "down_45", "tray;rim;control_head"),
                ("front", "eye_level", "control_head"),
                ("front", "top_down", "control_head;keys"),
                ("front", "eye_level", "front_opening"),
                ("front", "down_45", "tray"),
                ("front", "top_down", "front_slot"),
            ],
        )
        self.assertNotIn("part_", " ".join(row["path"] for row in rows))
        by_path = {row["path"]: row for row in rows}
        pump = by_path["products/pw002_s/ref/user_20261118_06_pump_exploded.jpg"]
        back = by_path["products/pw002_s/ref/user_20261118_08_accessory_back.jpg"]
        self.assertEqual(pump["product_view"], "front")
        self.assertNotEqual(pump["product_view"], "cutaway")
        self.assertEqual(pump["state"], "disassembled")
        self.assertNotEqual(back["product_view"], "rear")
        self.assertEqual(back["product_view"], "front")
        self.assertIn("本轮用户上传的造型参考", card)
        self.assertIn("不是早先12张", card)
        self.assertNotIn("它是真实拆解照片", card)
        self.assertIn("不写 `cutaway`", card)
        self.assertIn("不写 `rear`", card)
        plan = self.read("products", "pw002_s", "planning_round1.md")
        self.assertIn("主图 1 张、副图 6 张、高级版 A+ 7 屏", plan)
        sample = self.read("tools", "fixtures", "round10l_v2_task.md")
        self.assertIn("cards: 23", sample)



class AutoAdvanceTest(unittest.TestCase):
    """Grok decides layout-type items itself, asks one card per kind, and never stalls (v3.37)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_lists_what_is_not_asked(self):
        guide = self.read("UTA_STYLE.md")
        self.assertIn("**只问五类，其余你定。**", guide)
        decided = guide.split("**只问五类，其余你定。**")[1].split("**一类一张卡，管整套。**")[0]
        for item in ("`text_area`", "字体", "A+ 版本", "冲击力", "视角定位"):
            self.assertIn(item, decided)
        self.assertIn("**一类一张卡，管整套。**", guide)

    def test_auto_advance_rules(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("**自动推进：不卡住。**", guide)
        for text in (guide, skill):
            for marker in ("没回答的按★", "两次不成就跳过", "推定"):
                self.assertIn(marker, text)
        self.assertIn("## 自动推进", skill)

    def test_baseline_is_stage_one(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("第一段：造型基准", guide)
        self.assertIn("**视角定位。**", guide)
        self.assertNotIn("用一张提问卡请用户确认草稿", guide)
        self.assertIn("视角定位", skill)
        self.assertIn("视角定位", self.read("AGENTS.md"))
        self.assertNotIn("★ 对，按这份建卡并做造型基准", skill)
        confirm = self.read("grok", "confirm_template.html")
        self.assertIn('"decided"', confirm)



class ReviewFormTest(unittest.TestCase):
    """After a round, Codex turns the images into a form; blank means pass; Grok reworks (v3.38)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_wires_the_form_and_the_rework(self):
        guide = self.read("UTA_STYLE.md")
        self.assertIn("### 4.5 验收表单", guide)
        self.assertIn("### 4.6 自动返工", guide)
        self.assertIn("UTA-REVIEW v1", guide)
        self.assertIn("tools/review_form.py --task outputs/task.md --report outputs/report.md", guide)
        self.assertIn("空着的就是通过", guide)
        self.assertIn("FIX: …", guide)
        self.assertIn("| `fix` | 返工说明 |", guide)
        start = guide.index("### 3.2 固定步骤")
        step10 = guide.index("10. **验收表单。**", start)
        self.assertLess(guide.index("9. **回报。**", start), step10)
        self.assertLess(step10, guide.index("### 3.3", start))
        self.assertIn("收到「UTA-REVIEW」", guide)

    def test_skill_and_agents_carry_it(self):
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        agents = self.read("AGENTS.md")
        self.assertIn("UTA-REVIEW", skill)
        self.assertIn("返工 第 N 轮", skill)
        self.assertIn("review_form.py", agents)
        self.assertIn("验收表单", self.read("README.md"))
        template = self.read("grok", "review_template.html")
        self.assertIn('"items"', template)
        self.assertIn("UTA-REVIEW v1", template)

    def test_form_builder_fills_the_template(self):
        import json
        import re
        import tempfile
        import review_form
        task = os.path.join(ROOT, "tools", "fixtures", "round10l_v2_task.md")
        with tempfile.TemporaryDirectory() as root:
            os.symlink(os.path.join(ROOT, "products"), os.path.join(root, "products"))
            os.makedirs(os.path.join(root, "outputs", "round10l"))
            for name in ("S5_clean_v01.png", "S5_clean_v02.png", "S5_clean_base_v03.png"):
                with open(os.path.join(root, "outputs", "round10l", name), "wb") as fh:
                    fh.write(b"x")
            out, data = review_form.build(task, None, None, True, root=root)
            self.assertTrue(out.endswith("review_v01.html"))
            page = open(out, encoding="utf-8").read()
            sheet = json.loads(re.search(r'id="sheet" type="application/json">(.*?)</script>', page, re.S).group(1))
        self.assertEqual(sheet["product"], "round10l")
        slots = [it["slot"] for it in sheet["items"]]
        self.assertEqual(len(slots), len(set(slots)))
        s5 = next(it for it in sheet["items"] if it["slot"] == "S5")
        self.assertEqual([m["name"] for m in s5["images"]], ["S5_clean_v02.png"])
        self.assertTrue(all(not it["images"] for it in sheet["items"] if it["slot"] != "S5"))

    def test_report_marks_a_failed_check_as_candidate(self):
        import review_form
        blocks = review_form.parse_report(
            "图位：S5　卡：cards/round10l/S5_clean.md\nV1 产品对：通过\nV2 卖点看得懂：不合格\n"
            "画面说明：手在水槽里冲洗钢盆\n\n汇总：无\n")
        self.assertEqual(blocks["S5"]["result"], "候选（V2 没过）")
        self.assertEqual(blocks["S5"]["seen"], "手在水槽里冲洗钢盆")


if __name__ == "__main__":
    unittest.main()


class ReviewFormTest(unittest.TestCase):
    """After a round, Codex turns the images into a form; blank means pass; Grok reworks (v3.38)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_wires_the_form_and_the_rework(self):
        guide = self.read("UTA_STYLE.md")
        self.assertIn("### 4.5 验收表单", guide)
        self.assertIn("### 4.6 自动返工", guide)
        self.assertIn("UTA-REVIEW v1", guide)
        self.assertIn("tools/review_form.py --task outputs/task.md --report outputs/report.md", guide)
        self.assertIn("空着的就是通过", guide)
        self.assertIn("FIX: …", guide)
        self.assertIn("| `fix` | 返工说明 |", guide)
        start = guide.index("### 3.2 固定步骤")
        step10 = guide.index("10. **验收表单。**", start)
        self.assertLess(guide.index("9. **回报。**", start), step10)
        self.assertLess(step10, guide.index("### 3.3", start))
        self.assertIn("收到「UTA-REVIEW」", guide)

    def test_skill_and_agents_carry_it(self):
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        agents = self.read("AGENTS.md")
        self.assertIn("UTA-REVIEW", skill)
        self.assertIn("返工 第 N 轮", skill)
        self.assertIn("review_form.py", agents)
        self.assertIn("验收表单", self.read("README.md"))
        template = self.read("grok", "review_template.html")
        self.assertIn('"items"', template)
        self.assertIn("UTA-REVIEW v1", template)

    def test_form_builder_fills_the_template(self):
        import json
        import re
        import tempfile
        import review_form
        task = os.path.join(ROOT, "tools", "fixtures", "round10l_v2_task.md")
        with tempfile.TemporaryDirectory() as root:
            os.symlink(os.path.join(ROOT, "products"), os.path.join(root, "products"))
            os.makedirs(os.path.join(root, "outputs", "round10l"))
            for name in ("S5_clean_v01.png", "S5_clean_v02.png", "S5_clean_base_v03.png"):
                with open(os.path.join(root, "outputs", "round10l", name), "wb") as fh:
                    fh.write(b"x")
            out, data = review_form.build(task, None, None, True, root=root)
            self.assertTrue(out.endswith("review_v01.html"))
            page = open(out, encoding="utf-8").read()
            sheet = json.loads(re.search(r'id="sheet" type="application/json">(.*?)</script>', page, re.S).group(1))
        self.assertEqual(sheet["product"], "round10l")
        slots = [it["slot"] for it in sheet["items"]]
        self.assertEqual(len(slots), len(set(slots)))
        s5 = next(it for it in sheet["items"] if it["slot"] == "S5")
        self.assertEqual([m["name"] for m in s5["images"]], ["S5_clean_v02.png"])
        self.assertTrue(all(not it["images"] for it in sheet["items"] if it["slot"] != "S5"))

    def test_report_marks_a_failed_check_as_candidate(self):
        import review_form
        blocks = review_form.parse_report(
            "图位：S5　卡：cards/round10l/S5_clean.md\nV1 产品对：通过\nV2 卖点看得懂：不合格\n"
            "画面说明：手在水槽里冲洗钢盆\n\n汇总：无\n")
        self.assertEqual(blocks["S5"]["result"], "候选（V2 没过）")
        self.assertEqual(blocks["S5"]["seen"], "手在水槽里冲洗钢盆")


    def test_form_embeds_small_previews_and_links_the_original(self):
        import json
        import re
        import shutil
        import tempfile
        import review_form
        task = os.path.join(ROOT, "tools", "fixtures", "round10l_v2_task.md")
        source = os.path.join(ROOT, "products", "round10l", "ref", "front_high.png")
        with tempfile.TemporaryDirectory() as root:
            os.symlink(os.path.join(ROOT, "products"), os.path.join(root, "products"))
            os.makedirs(os.path.join(root, "outputs", "round10l"))
            shutil.copy(source, os.path.join(root, "outputs", "round10l", "S5_clean_v01.png"))
            del review_form.WARNINGS[:]
            out, _data = review_form.build(task, None, None, root=root)
            if review_form.WARNINGS:
                self.skipTest("no Pillow or sips here: " + review_form.WARNINGS[0])
            with open(out, encoding="utf-8") as fh:
                page = fh.read()
            sheet = json.loads(re.search(r'id="sheet" type="application/json">(.*?)</script>', page, re.S).group(1))
        s5 = next(it for it in sheet["items"] if it["slot"] == "S5")
        image = s5["images"][0]
        self.assertTrue(image["src"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(image["full"], "S5_clean_v01.png")
        self.assertLess(len(image["src"]) * 3 // 4, os.path.getsize(source) // 4)
