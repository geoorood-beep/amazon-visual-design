"""Tests for tools/check_set.py (UTA_STYLE.md v3.2).

Run from the repository root:
    python -m unittest discover -s tools -p "test_check_*.py"
"""
import io
import os
import re
import shutil
import tempfile
import unittest

import check_set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tools", "fixtures")
V1 = os.path.join(FIX, "round10l_v1_task.md")
V2 = os.path.join(FIX, "round10l_v2_task.md")
VIEWS = os.path.join(ROOT, "products", "round10l", "ref_views.csv")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def run_task(self, path, emit=True, views=VIEWS, state=None):
        out = io.StringIO()
        emit_path = os.path.join(self.tmp, "task_v1.md") if emit else None
        code = check_set.run(path, emit=emit_path, views_path=views, root=ROOT,
                             state=state or os.path.join(self.tmp, "task_full_v2.md"), out=out)
        return code, out.getvalue(), emit_path

    def mutate(self, old, new, count=1, text=None):
        text = text if text is not None else read(V2)
        self.assertEqual(text.count(old), count, "fixture changed: %r" % old)
        return text.replace(old, new)

    def card_block(self, text, name):
        m = re.search(r"=== cards/round10l/%s ===\n---\n(.*?)\n---\n" % re.escape(name), text, re.S)
        self.assertIsNotNone(m, name)
        return m.group(0)


class LegacyV1(Base):
    def test_user_task_passes_with_warnings_and_passthrough(self):
        code, out, emit = self.run_task(V1)
        self.assertEqual(code, 0, out)
        self.assertIn("LEGACY v1", out)
        for expect in ("[S-6] 文字位置 top_left 用了 6 张",
                       "[A-3] 单图屏（scene、number）连续超过两屏",
                       "[A-4] 高级版组合模块只有 1 屏",
                       "[G-1] 同一种互动和宠物组合出现 4 次：S1, S2, P1, P2a",
                       "[A-1] 开场屏 P1 是远景 wide",
                       "WARN S2: headline 里重复了强调数字 10",
                       "WARN S6: human_action 写了指着产品的动作"):
            self.assertIn(expect, out)
        self.assertNotIn("没有产品参考图支撑", out)  # v3.19: camera is not limited by ref_views
        self.assertNotIn("FAIL", out)
        body = read(V1)
        expected = "\n".join(l for l in body[body.index("UTA-TASK v1"):].splitlines()
                             if not l.strip().startswith("```")) + "\n"
        self.assertEqual(read(emit), expected)


class SampleV2(Base):
    def test_sample_passes(self):
        code, out, emit = self.run_task(V2)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("\nOK   "), 23, out)
        self.assertIn("SET FAIL 0", out)

    def test_emit_is_card_version_1(self):
        code, out, emit = self.run_task(V2)
        text = read(emit)
        self.assertTrue(text.startswith("UTA-TASK v1\nproduct: round10l\ncards: 23\n"))
        self.assertEqual(text.count("card_version: 1"), 23)
        self.assertNotIn("card_version: 2", text)
        self.assertIsNone(re.search(r"^(shot_size|product_view|focus|interaction|light_setup|foreground|beat|scope):",
                                    text, re.M))
        s3 = self.card_block(text, "S3_steel.md")
        self.assertIn("for scale. Extreme close-up with a macro-lens look: the rim fills", s3)
        self.assertIn("do not copy its camera angle or framing.", s3)
        self.assertIn("Foreground: the cat's whiskers along the top edge, soft and out of focus", s3)
        self.assertIn("Light setup: hard side light", s3)
        m1 = self.card_block(text, "M1_white.md")
        self.assertIn("evidence: none\n", m1)
        self.assertIn("camera: wide\n", m1)
        p2 = self.card_block(text, "P2_quiet.md")
        self.assertIn("module: number\n", p2)
        self.assertNotIn("Light setup", p2)

    def test_saves_full_set_for_patch(self):
        state = os.path.join(self.tmp, "full.md")
        self.run_task(V2, state=state)
        self.assertTrue(read(state).startswith("UTA-TASK v2"))


class CardRules(Base):
    def test_camera_not_in_ref_views_is_allowed(self):
        # v3.19: camera comes from the case reference, not from ref_views.csv
        text = self.mutate("camera: low_angle\nscene: Bedroom floor at night",
                           "camera: top_down\nscene: Bedroom floor at night")
        code, out, emit = self.run_task(self.write("t.md", text))
        self.assertIn("OK   cards/round10l/S4_quiet.md", out)
        self.assertNotIn("参考视角覆盖", out)
        self.assertIn("Take the camera height, framing and composition from the style reference", read(emit))

    def test_cutaway_still_needs_structure_reference(self):
        text = self.mutate("camera: low_angle\nscene: Bedroom floor at night",
                           "camera: low_angle\nscene: Bedroom floor at night")
        text = text.replace("product_view: front\n", "product_view: cutaway\n", 1)
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 1, out)
        self.assertIn("cutaway 只有 ref_views.csv 登记了 cutaway 那一行", out)

    def test_focus_must_be_in_parts(self):
        text = self.mutate("focus: spout", "focus: base_plate")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 1, out)
        self.assertIn("focus=base_plate 不在任何产品参考图的 parts 里", out)

    def test_close_shot_cannot_focus_whole(self):
        text = self.mutate("focus: spout", "focus: whole")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("close 的 focus 不能是 whole", out)

    def test_pointing_hand_fails(self):
        text = self.mutate(
            "human_action: One hand of an adult wiping the brushed front panel with a folded white cloth",
            "human_action: One hand of an adult pointing at the brushed front panel")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL cards/round10l/P6b_wipe.md", out)
        self.assertIn("指着产品", out)

    def test_module_fails_with_its_panels(self):
        text = self.mutate(
            "human_action: One hand of an adult wiping the brushed front panel with a folded white cloth",
            "human_action: One hand of an adult pointing at the brushed front panel")
        code, out, emit = self.run_task(self.write("t.md", text))
        for name in ("P6_clean_steps.md", "P6a_rinse.md", "P6b_wipe.md"):
            self.assertIn("FAIL cards/round10l/" + name, out)
        self.assertNotIn("P6a_rinse.md", read(emit))
        self.assertIn("cards: 20", read(emit))

    def test_hero_number_repeated_in_headline_fails(self):
        text = self.mutate("headline: Brushed Stainless Steel", "headline: 304 Brushed Steel")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("headline 里重复了强调数字 304", out)

    def test_structure_words_fail_unless_negated(self):
        text = self.mutate("simple Nordic kitchen\nlight: Hard daylight from a window on the left, a clear reflection",
                           "simple Nordic kitchen, a filter visible inside\nlight: Hard daylight from a window on the left, a clear reflection")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("写了参考图看不到的结构或特效（filter）", out)
        text = self.mutate("simple Nordic kitchen\nlight: Hard daylight from a window on the left, a clear reflection",
                           "simple Nordic kitchen, no filter in view\nlight: Hard daylight from a window on the left, a clear reflection")
        code, out, _ = self.run_task(self.write("t2.md", text))
        self.assertEqual(code, 0, out)

    def test_duration_copy_fails(self):
        text = self.mutate("subtitle: A wide basin for cats and dogs.", "subtitle: Fresh water for days.")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("写了时长说法（days）", out)

    def test_m1_v2_fields_must_be_none(self):
        text = self.mutate("light: none\nshot_size: none", "light: none\nshot_size: medium")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("M1 的 shot_size 要写 none", out)

    def test_module_card_must_not_carry_image_fields(self):
        text = self.mutate("panels: P7a\n", "panels: P7a\nshot_size: medium\n")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("模块卡不写 shot_size", out)

    def test_v1_card_in_v2_task_fails(self):
        text = self.mutate("card_version: 2\nproduct: round10l\nslot: S5", "card_version: 1\nproduct: round10l\nslot: S5")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("卡要写 card_version: 2", out)

    def test_interaction_needs_matching_actor(self):
        text = self.mutate("interaction: human_rinse", "interaction: rest")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("interaction=rest 是宠物的动作，pet 不能是 none", out)


class SetRules(Base):
    def test_duplicate_composition_is_set_fail(self):
        p1 = self.card_block(read(V2), "P1_together.md")
        new = p1.replace("camera: eye_level", "camera: low_angle").replace("shot_size: close", "shot_size: full")
        text = read(V2).replace(p1, new)
        code, out, emit = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [G-1] S1 和 P1", out)
        self.assertIn("SET FAIL [A-1] 开场屏景别要是 close 或 medium", out)
        self.assertFalse(os.path.exists(emit))

    def test_adjacent_screens_same_shot_size(self):
        p2a = self.card_block(read(V2), "P2a_quiet_scene.md")
        text = read(V2).replace(p2a, p2a.replace("shot_size: full", "shot_size: close"))
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [A-5] 相邻两屏主图景别相同：P1 和 P2", out)
        self.assertIn("SET FAIL [G-2] P2a 和副图 S4", out)

    def test_adjacent_sub_images_same_shot_size(self):
        s3 = self.card_block(read(V2), "S3_steel.md")
        text = read(V2).replace(s3, s3.replace("shot_size: extreme_close", "shot_size: close"))
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("SET FAIL [S-3] 相邻两张副图景别相同：S3 和 S4 都是 close", out)

    def test_text_area_concentration(self):
        text = read(V2)
        for a in ("text_area: top_right", "text_area: bottom_left", "text_area: bottom_right"):
            text = text.replace(a, "text_area: top_left")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("SET FAIL [S-6] 文字位置 top_left 用了 6 张，最多 3 张", out)

    def test_light_monotony(self):
        text = read(V2)
        subs = [self.card_block(text, n) for n in
                ("S1_together.md", "S4_quiet.md", "S5_clean.md", "S6_window.md")]
        for b in subs:
            text = text.replace(b, re.sub(r"light_setup: \w+", "light_setup: side", b))
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("SET FAIL [S-4]", out)

    def test_premium_needs_composites(self):
        text = self.mutate("module: contrast", "module: grid")
        text = text.replace("module: grid\nedition: premium\ntone: light\nbeat: detail",
                            "module: steps\nedition: premium\ntone: light\nbeat: detail")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("[A-3] steps 用了 2 屏，最多 1 屏", out)
        self.assertIn("[A-4] 高级版至少要有一屏三格拼盘或前后对照", out)

    def test_dark_screens(self):
        text = self.mutate("module: grid\nedition: premium\ntone: light",
                           "module: grid\nedition: premium\ntone: dark")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertIn("SET FAIL [A-8] 深色屏相邻：P2 和 P3", out)


class TaskFormat(Base):
    def test_card_count_mismatch(self):
        text = self.mutate("cards: 23", "cards: 22")
        code, out, _ = self.run_task(self.write("t.md", text))
        self.assertEqual(code, 2)
        self.assertIn("TASK ERROR: cards: 写的是 22，实际有 23 张卡", out)

    def test_missing_views_is_task_error(self):
        code, out, _ = self.run_task(V2, views=os.path.join(self.tmp, "nope.csv"))
        self.assertEqual(code, 2)
        self.assertIn("TASK ERROR: 缺少产品参考视角表", out)

    def test_missing_header(self):
        code, out, _ = self.run_task(self.write("t.md", "hello\n"))
        self.assertEqual(code, 2)
        self.assertIn("TASK ERROR", out)


class PoolRules(Base):
    """1.13 option pools and the E-1, E-3, K-1, K-2 set rules (2.6)."""

    def run_text(self, text):
        return self.run_task(self.write("t.md", text))

    def test_missing_pool_field_fails_card(self):
        code, out, _ = self.run_text(self.mutate("scene_id: SC09\npet_id: PT02", "pet_id: PT02"))
        self.assertIn("缺少选项池字段：scene_id", out)

    def test_scene_must_fit_light_and_be_named(self):
        code, out, _ = self.run_text(self.mutate("scene_id: SC07", "scene_id: SC04"))
        self.assertIn("场景 SC04（卧室床边）只配光型", out)
        self.assertIn("scene 要写出场景 SC04", out)

    def test_pet_text_must_match_pool(self):
        code, out, _ = self.run_text(self.mutate("pet_id: PT03", "pet_id: PT04"))
        self.assertIn("pet 要写出宠物池 PT04 的样子", out)

    def test_expression_must_fit_interaction(self):
        code, out, _ = self.run_text(self.mutate("expression_id: EX03", "expression_id: EX06"))
        self.assertIn("表情 EX06（伸爪试探）不配互动 rest", out)

    def test_operating_hands_only(self):
        code, out, _ = self.run_text(self.mutate("person_id: HP02", "person_id: HP05"))
        self.assertIn("演示操作只出手和小臂", out)

    def test_evidence_used_twice_fails_set(self):
        code, out, _ = self.run_text(self.mutate("evidence_id: F6-D", "evidence_id: F6-A"))
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [E-1] 证据方案 F6-A 用了不止一次", out)

    def test_evidence_must_match_fact(self):
        code, out, _ = self.run_text(self.mutate("evidence_id: F2-A", "evidence_id: F3-A"))
        self.assertIn("evidence_id F3-A 属于 F3", out)

    def test_scene_repeats_fail_set(self):
        code, out, _ = self.run_text(self.mutate("scene_id: SC01\npet_id: PT03", "scene_id: SC03\npet_id: PT03"))
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [E-3] 场景 SC03 在副图里用了 3 次", out)
        self.assertIn("SET FAIL [E-3] 相邻两张副图 S5 和 S6", out)

    def test_one_pet_everywhere_fails_set(self):
        text = self.mutate("pet_id: PT02", "pet_id: PT01", count=2)
        text = self.mutate("pet_id: PT03", "pet_id: PT01", text=text)
        code, out, _ = self.run_text(text)
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [K-1] 宠物 PT01 出现在 8 张图里", out)

    def test_expression_repeats_fail_set(self):
        code, out, _ = self.run_text(self.mutate("expression_id: EX09", "expression_id: EX01"))
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [K-2] 表情 EX01 用了 3 次", out)
        self.assertIn("SET FAIL [K-2] 相邻两张副图 S1 和 S2", out)

    def test_style_header_required(self):
        code, out, _ = self.run_text(self.mutate("style: ST02\n", ""))
        self.assertEqual(code, 2, out)
        self.assertIn("头部要写 style:", out)

    def test_style_must_fit_light(self):
        code, out, _ = self.run_text(self.mutate("style: ST02", "style: ST04"))
        self.assertIn("风格 ST04（萌宠海报风）只配光型", out)

    def test_operation_hands_have_no_mood(self):
        code, out, _ = self.run_text(self.mutate("person_id: HP02\nperson_mood_id: none", "person_id: HP02\nperson_mood_id: MD01"))
        self.assertIn("只出手的人物看不到脸", out)

    def test_scene_person_needs_mood(self):
        code, out, _ = self.run_text(self.mutate("person_id: HP05\nperson_mood_id: MD01", "person_id: HP05\nperson_mood_id: none"))
        self.assertIn("情景里出镜的人物 HP05 要写 person_mood_id", out)

    def test_scenes_need_people(self):
        text = self.mutate("person_id: HP05\nperson_mood_id: MD01", "person_id: HP01\nperson_mood_id: none")
        code, out, _ = self.run_text(text)
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [K-3] 副图有 6 张，没有一张是有人物出镜的情景", out)
        text = self.mutate("person_id: HP08\nperson_mood_id: MD03", "person_id: HP02\nperson_mood_id: none")
        code, out, _ = self.run_text(text)
        self.assertIn("SET FAIL [K-3] A+ 有 7 屏", out)

    def test_mood_reaches_the_prompt(self):
        code, out, emit = self.run_task(V2)
        s1 = self.card_block(read(emit), "S1_together.md")
        self.assertIn("Mood: a soft genuine smile, eyes on the pet; not looking at the camera.", s1)

    def test_story_required_with_pet_or_person(self):
        text = re.sub(r"(?m)^story: Same spot after a refill.*\n", "", read(V2))
        code, out, _ = self.run_text(text)
        self.assertIn("有宠物或人物的图要写 story", out)

    def test_story_guards(self):
        old = "story: A curious orange cat taps the rim"
        code, out, _ = self.run_text(self.mutate(old, "story: 一只橘猫 taps the rim"))
        self.assertIn("story 要用英文写", out)
        code, out, _ = self.run_text(self.mutate(old, "story: After a weekend away, a curious orange cat taps the rim"))
        self.assertIn("story 写了时长说法（weekend）", out)
        code, out, _ = self.run_text(self.mutate(old, "story: The pump hums as a curious orange cat taps the rim"))
        self.assertIn("story 写了参考图看不到的结构或特效（pump）", out)

    def test_story_leads_the_evidence(self):
        code, out, emit = self.run_task(V2)
        s1 = self.card_block(read(emit), "S1_together.md")
        self.assertIn("evidence: Story: Late afternoon at home: the cat and the dog who never share anything", s1)
        self.assertNotIn("\nstory:", read(emit))

    def test_similar_stories_warn(self):
        text = self.mutate("story: In the sunroom the cat and the dog lean in from opposite sides and drink together, faces almost touching, a small peace between rivals.",
                           "story: Late afternoon at home: the cat and the dog who never share anything drink side by side from one basin, and the woman smiles at the truce.")
        code, out, _ = self.run_text(text)
        self.assertIn("WARN [K-4] S1 和 P1 的故事相似度", out)

    def test_case_used_three_times_fails_set(self):
        old = "  anchor: docs/uta_style_v3/assets/key/D_floor_labels_G4DX3QR8.jpg | two pets side by side at the same product only; not the product, the floor labels, numbers or any text"
        new = "  anchor: docs/uta_style_v3/assets/key/D_multipet_C5X2G933.jpg | two pets sharing one product only; not the product, the spacing marks, numbers or any text"
        code, out, _ = self.run_text(self.mutate(old, new))
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [K-5] 案例 D_multipet_C5X2G933.jpg 用了 3 次", out)

    def test_index_is_fully_annotated(self):
        import csv as _csv
        with open(os.path.join(ROOT, "references", "INDEX.csv"), encoding="utf-8") as fh:
            rows = list(_csv.DictReader(fh))
        for col in ("learn", "story", "structure", "light", "style_id", "fits", "avoid", "grade"):
            self.assertIn(col, rows[0])
        for r in rows:
            if r["type"] != "product":
                self.assertIn(r["grade"], ("A", "B", "C"), r["path"])
        with open(os.path.join(ROOT, "pools", "styles.csv"), encoding="utf-8") as fh:
            styles = list(_csv.DictReader(fh))
        grade = {r["path"]: r["grade"] for r in rows}
        for s in styles:
            for p in s["examples"].split(";"):
                self.assertIn(grade.get(p), ("A", "B"), (s["id"], p))

    def test_pools_reach_the_compiled_card(self):
        code, out, emit = self.run_task(V2)
        s2 = self.card_block(read(emit), "S2_capacity.md")
        self.assertIn("Person: a man's hands with a medium skin tone", s2)
        self.assertIn("Expression: mouth softly open", s2)
        self.assertIn("Style: Scandinavian home", s2)
        self.assertIsNone(re.search(r"^(evidence_id|scene_id|pet_id|person_id|expression_id):", read(emit), re.M))


class PatchScope(Base):
    def patch_with(self, block):
        return "UTA-TASK v2\nproduct: round10l\nstyle: ST02\nscope: patch\ncards: 1\n\n" + block + "\n"

    def test_patch_merges_with_saved_full_set(self):
        state = os.path.join(self.tmp, "full.md")
        self.run_task(V2, state=state)
        s3 = self.card_block(read(V2), "S3_steel.md")
        ok = self.patch_with(s3.replace("Fine grain you can see up close.", "Fine brushed grain, up close."))
        code, out, emit = self.run_task(self.write("p.md", ok), state=state)
        self.assertEqual(code, 0, out)
        self.assertIn("PATCH: 合进上一次的整套", out)
        self.assertIn("cards: 1", read(emit))
        bad = self.patch_with(s3.replace("shot_size: extreme_close", "shot_size: close"))
        code, out, _ = self.run_task(self.write("p2.md", bad), state=state)
        self.assertEqual(code, 2, out)
        self.assertIn("SET FAIL [S-3]", out)

    def test_patch_without_saved_set_skips_set_rules(self):
        s3 = self.card_block(read(V2), "S3_steel.md")
        code, out, _ = self.run_task(self.write("p.md", self.patch_with(s3)),
                                     state=os.path.join(self.tmp, "missing.md"))
        self.assertEqual(code, 0, out)
        self.assertIn("没有上一次的整套", out)


if __name__ == "__main__":
    unittest.main()
