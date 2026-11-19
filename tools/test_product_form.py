"""Tests for tools/product_form.py and references/categories/ (optional product form).

    python -m unittest discover -s tools -p "test_product_form.py" -v
"""
import base64
import io
import json
import os
import shutil
import tempfile
import unittest

import product_form as pf

ROOT = pf.ROOT
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


class Repo:
    """A throwaway repo root with the real category library and form template."""

    def __init__(self, case):
        self.root = tempfile.mkdtemp()
        case.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(os.path.join(ROOT, pf.CATEGORY_REL), os.path.join(self.root, pf.CATEGORY_REL))
        os.makedirs(os.path.join(self.root, "grok"))
        shutil.copy(os.path.join(ROOT, pf.TEMPLATE_REL), os.path.join(self.root, pf.TEMPLATE_REL))

    def product(self, pid, card="", photos=(), ref_views=None):
        folder = os.path.join(self.root, "products", pid)
        os.makedirs(os.path.join(folder, "photos"), exist_ok=True)
        if card:
            with open(os.path.join(folder, "PRODUCT.md"), "w", encoding="utf-8") as fh:
                fh.write(card)
        for name in photos:
            with open(os.path.join(folder, "photos", name), "wb") as fh:
                fh.write(PNG)
        if ref_views:
            with open(os.path.join(folder, "ref_views.csv"), "w", encoding="utf-8") as fh:
                fh.write("path,product_view,cameras,parts,checked\n" + "\n".join(ref_views) + "\n")
        return folder

    def run(self, *argv):
        out = io.StringIO()
        code = pf.main(list(argv), root=self.root, out=out)
        return code, out.getvalue()


def card(summary, facts=()):
    rows = "\n".join("| %s | %s | %s | 不可写 |" % (fid, text, text) for fid, text in facts)
    return ("# 产品卡：x\n\n%s\n\n## 已确认事实\n\n| 编号 | 事实 | 画面可写 | 不可写成 |\n|---|---|---|---|\n%s\n\n"
            "## Parts (prompt)\n\n## 外形识别点\n" % (summary, rows))


class CategoryLibraryTest(unittest.TestCase):
    def test_repo_categories_are_valid(self):
        self.assertEqual(pf.validate(), [])

    def test_every_category_has_the_safe_rules(self):
        for cid in pf.list_categories(ROOT):
            cat = pf.load_category(ROOT, cid)
            self.assertIn("assembled", [s["id"] for s in cat["states"]], cid)
            for q in cat["questions"]:
                self.assertGreaterEqual(q["rec"], -1, cid)

    def test_bad_category_is_reported(self):
        repo = Repo(self)
        path = os.path.join(repo.root, pf.CATEGORY_REL, "smart_feeder.json")
        with open(path, encoding="utf-8") as fh:
            cat = json.load(fh)
        cat["parts"][1]["type"] = "零件"
        cat["parts"][2]["parent"] = "nowhere"
        cat["size"]["dims"]["L"]["unit"] = "L"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cat, fh, ensure_ascii=False)
        errors = "\n".join(pf.validate(repo.root))
        self.assertIn("type '零件'", errors)
        self.assertIn("parent 'nowhere'", errors)
        self.assertIn("size.dims.L unit must be a length unit", errors)
        code, out = repo.run("check")
        self.assertEqual(code, 1)
        self.assertIn("CATEGORY ERROR", out)


class DetectTest(unittest.TestCase):
    def test_keyword_matching(self):
        self.assertFalse(pf.keyword_in("L", "wireless 10L"))
        self.assertFalse(pf.keyword_in("lid", "slide"))
        self.assertTrue(pf.keyword_in("feeder", "Cat Feeder 4L"))
        self.assertTrue(pf.keyword_in("dog leash", "6ft dog leash, reflective"))
        self.assertTrue(pf.keyword_in("喂食器", "智能宠物喂食器 4L"))

    def test_product_card_picks_the_category(self):
        repo = Repo(self)
        repo.product("feeder_x", card("智能宠物喂食器，4L 粮桶，带摄像头。"))
        ranked = pf.detect(repo.root, "feeder_x")
        self.assertEqual(ranked[0][1]["id"], "smart_feeder")
        code, out = repo.run("detect", "--product", "feeder_x")
        self.assertEqual(code, 0)
        self.assertIn("CATEGORY smart_feeder", out)
        self.assertIn("VARIANTS", out)
        self.assertIn("camera", out)

    def test_request_text_alone_is_enough(self):
        repo = Repo(self)
        for text, want in (("6ft reflective dog leash with padded handle", "dog_leash"),
                           ("全自动猫砂盆 滚筒款", "smart_litter_box"),
                           ("7-in-1 pet grooming vacuum kit", "pet_grooming_vacuum"),
                           ("不锈钢无线宠物饮水机", "pet_fountain")):
            self.assertEqual(pf.detect(repo.root, None, text)[0][1]["id"], want, text)

    def test_nothing_matches_falls_back_to_generic(self):
        repo = Repo(self)
        code, out = repo.run("detect", "--text", "陶瓷花瓶")
        self.assertEqual(code, 0)
        self.assertIn("CATEGORY generic", out)
        self.assertIn("LOOK at the photos for", out)

    def test_combined_product_is_flagged(self):
        repo = Repo(self)
        code, out = repo.run("detect", "--text", "宠物喂食器 + 宠物饮水机 二合一 automatic pet feeder and pet water fountain")
        self.assertIn("COMBO?", out)


class SkeletonTest(unittest.TestCase):
    def test_variant_parts_only_when_asked(self):
        repo = Repo(self)
        plain = pf.skeleton(repo.root, "leash_x", ["dog_leash"])
        keys = [p["key"] for p in plain["parts"]]
        self.assertIn("snap_hook", keys)
        self.assertNotIn("housing", keys)
        self.assertEqual(plain["photos"][0]["slot"], "top")
        retract = pf.skeleton(repo.root, "leash_x", ["dog_leash"], ["retractable"])
        keys = [p["key"] for p in retract["parts"]]
        self.assertIn("housing", keys)
        self.assertEqual(retract["photos"][0]["slot"], "front")
        housing = [p for p in retract["parts"] if p["key"] == "housing"][0]
        button = [p for p in retract["parts"] if p["key"] == "brake_button"][0]
        self.assertEqual(button["parent"], housing["id"])

    def test_questions_already_answered_by_the_variant_are_dropped(self):
        repo = Repo(self)
        asked = [q["key"] for q in pf.skeleton(repo.root, "feeder_x", ["smart_feeder"])["questions"]]
        self.assertEqual(asked[:2], ["q_camera", "q_bowl"])
        sheet = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"], ["camera", "dual_bowl"])
        asked = [q["key"] for q in sheet["questions"] + sheet["questions_more"]]
        self.assertNotIn("q_camera", asked)
        self.assertNotIn("q_bowl", asked)
        self.assertEqual(sheet["variant_names"], ["带摄像头", "双盆（带分流出粮）"])
        self.assertEqual([q["id"] for q in sheet["questions"]], ["Q1", "Q2", "Q3"])

    def test_unknown_variant_is_refused(self):
        repo = Repo(self)
        with self.assertRaises(pf.FormError):
            pf.skeleton(repo.root, "leash_x", ["dog_leash"], ["camera"])

    def test_every_part_starts_as_a_guess(self):
        repo = Repo(self)
        sheet = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"], ["camera"])
        self.assertTrue(all(p["conf"] == "推定" for p in sheet["parts"]))
        self.assertTrue(all(p["type"] in pf.TYPES for p in sheet["parts"]))
        self.assertEqual(len(sheet["questions"]), pf.SHOWN_QUESTIONS)
        self.assertTrue(sheet["questions_more"])
        self.assertTrue(sheet["ai_todo"])

    def test_facts_map_to_states(self):
        repo = Repo(self)
        repo.product("feeder_x", card("智能宠物喂食器", [("F1", "定时出粮，每天最多 6 餐"), ("F2", "粮桶可拆，可水洗"),
                                                       ("F3", "wireless design")]))
        sheet = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"])
        states = {s["id"]: s["for"] for s in sheet["states"]}
        self.assertIn("F1", states["dispensing"])
        self.assertIn("F2", states["disassembled"])
        self.assertNotIn("F3", states["refill"])

    def test_photos_and_refs_are_matched(self):
        repo = Repo(self)
        repo.product("feeder_x", card("智能宠物喂食器"), photos=("01_front.png", "02_side_left.png", "07_accessory_back.png"),
                     ref_views=["products/feeder_x/ref/r45.png,three_quarter_left,eye_level,whole;hopper,yes",
                                "products/feeder_x/ref/bowl.png,front,eye_level,bowl,yes"])
        sheet = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"])
        slots = {p["slot"]: p for p in sheet["photos"]}
        self.assertTrue(slots["front"]["img"].endswith("01_front.png"))
        self.assertEqual(slots["front"]["src"], "实拍")
        self.assertTrue(slots["three_quarter_left"]["img"].endswith("r45.png"))
        self.assertEqual(slots["rear"]["img"], "")
        bowl = [p for p in sheet["parts"] if p["key"] == "bowl"][0]
        self.assertEqual(bowl["imgs"], ["products/feeder_x/ref/bowl.png"])
        self.assertIn("spec_ruler_top", slots)
        self.assertIn("hopper_open", slots)

    def test_old_card_gets_update_items(self):
        repo = Repo(self)
        repo.product("feeder_x", card("智能宠物喂食器"))
        ups = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"])["updates"]
        self.assertEqual(len(ups), 2)
        self.assertIn("产品理解", ups[0]["text"])


class BuildTest(unittest.TestCase):
    def test_build_never_overwrites_and_keeps_the_json(self):
        repo = Repo(self)
        repo.product("feeder_x", card("智能宠物喂食器"), photos=("01_front.png",))
        code, out = repo.run("skeleton", "--product", "feeder_x", "--category", "smart_feeder")
        self.assertEqual(code, 0, out)
        draft = os.path.join(repo.root, "outputs", "feeder_x", "product_form_draft.json")
        code, out = repo.run("build", "--sheet", draft)
        self.assertEqual(code, 0, out)
        self.assertIn("outputs/feeder_x/product_form_v01.html", out)
        code, out = repo.run("build", "--sheet", draft)
        self.assertIn("product_form_v02.html", out)
        folder = os.path.join(repo.root, "outputs", "feeder_x")
        self.assertTrue(os.path.isfile(os.path.join(folder, "product_form_v01.json")))
        with open(os.path.join(folder, "product_form_v02.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('"form": "outputs/feeder_x/product_form_v02.html"', html)
        self.assertIn("data:image/", html)

    def test_text_cannot_break_out_of_the_sheet(self):
        repo = Repo(self)
        sheet = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"])
        sheet["parts"][0]["where"] = "</script><b>x</b>"
        path = os.path.join(repo.root, "draft.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(sheet, fh, ensure_ascii=False)
        out_path, _, missing = pf.build(repo.root, path)
        with open(out_path, encoding="utf-8") as fh:
            html = fh.read()
        self.assertEqual(html.count("</script>"), 2)
        self.assertEqual(missing, [])

    def test_missing_images_are_reported_not_fatal(self):
        repo = Repo(self)
        sheet = pf.skeleton(repo.root, "feeder_x", ["smart_feeder"])
        sheet["photos"][0]["img"] = "products/feeder_x/photos/gone.png"
        path = os.path.join(repo.root, "draft.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(sheet, fh, ensure_ascii=False)
        _, _, missing = pf.build(repo.root, path)
        self.assertEqual(missing, ["products/feeder_x/photos/gone.png"])


class WiringTest(unittest.TestCase):
    """The guide, the Grok skill and AGENTS.md all route through the optional form (v3.40)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("### 3.9 写入产品资料", "**品类库。**", "**部件的关系类型。**", "**产品资料表（选填）。**",
                       "grok/product_template.html", "references/categories/", "收到「UTA-PRODUCT」", "它不是闸门"):
            self.assertIn(marker, guide)
        for t in pf.TYPES:
            self.assertIn("| %s |" % t, guide)

    def test_skill_and_agents(self):
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        for marker in ("grok/product_template.html", "references/categories/README.md", "UTA-PRODUCT",
                       "写入产品资料 <产品>", "不挡流程"):
            self.assertIn(marker, skill)
        agents = self.read("AGENTS.md")
        self.assertIn("写入产品资料", agents)
        self.assertIn("tools/product_form.py", agents)

    def test_template_sample_is_a_valid_sheet(self):
        html = self.read("grok", "product_template.html")
        start = html.index(pf.OPEN) + len(pf.OPEN)
        sheet = json.loads(html[start:html.index(pf.CLOSE, start)])
        for key in ("product", "summary", "questions", "parts", "states", "functions", "flow", "size", "photos"):
            self.assertIn(key, sheet)
        self.assertTrue(all(p["type"] in pf.TYPES for p in sheet["parts"]))
        self.assertIn("UTA-PRODUCT v1", html)


if __name__ == "__main__":
    unittest.main()
