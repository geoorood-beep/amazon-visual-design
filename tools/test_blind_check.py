"""Tests for tools/blind_check.py and its use in the review form (UTA_STYLE.md 4.7).

    python -m unittest discover -s tools -p "test_blind_check.py" -v
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

import blind_check as bc

ROOT = bc.ROOT
HEADER = ",".join(bc.COLUMNS) + "\n"
FAKE = r'''
import json, os, sys
out, images = sys.argv[1], sys.argv[2:]
for img in images:
    assert os.path.isabs(img) and os.path.isfile(img), img
name = os.path.basename(images[0])
answers = {"G1": "没有", "G2": "画面里没有人手", "G3": "1", "G4": "没有", "K1": "相对的两侧", "K2": "2"}
if name.startswith("bad"):
    answers["K1"] = "相邻的两侧"
if name.startswith("blank"):
    answers = {k: "看不到" if k.startswith("K") else v for k, v in answers.items()}
    answers.update(G3="0", G1="画面里没有宠物")
json.dump(answers, open(out, "w"), ensure_ascii=False)
'''
PRODUCT = HEADER + (
    'K1,水位窗和控制头在哪两侧？,相对的两侧;相邻的两侧;看不到,相对的两侧,yes,,已确认,外形识别点 2,'
    '"the window is opposite the head",\n'
    'K2,顶面几个键？,1;2;看不到,2,yes,assembled,已确认,外形识别点 5,two keys,\n'
    'K3,拆开时拿出来的是什么？,整个组件;一个水泵,整个组件,no,disassembled,待确认,AI 推定,one unit,\n'
    'G4,产品上有没有 logo？,没有;有,没有,no,,不用,本品印着型号,,\n')


class Repo:
    def __init__(self, case, product_csv=PRODUCT):
        self.root = tempfile.mkdtemp()
        case.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "references"))
        shutil.copy(os.path.join(ROOT, bc.COMMON), os.path.join(self.root, bc.COMMON))
        os.makedirs(os.path.join(self.root, "products", "x"))
        with open(os.path.join(self.root, "products", "x", "checks.csv"), "w", encoding="utf-8") as fh:
            fh.write(product_csv)
        self.fake = os.path.join(self.root, "fake_reviewer.py")
        with open(self.fake, "w", encoding="utf-8") as fh:
            fh.write(FAKE)
        os.makedirs(os.path.join(self.root, "img"))

    def image(self, name):
        path = os.path.join(self.root, "img", name)
        with open(path, "wb") as fh:
            fh.write(b"x")
        return path

    def run(self, *argv):
        out = io.StringIO()
        code = bc.main(list(argv), root=self.root, out=out)
        return code, out.getvalue()

    @property
    def reviewer(self):
        return "%s %s {out} {images}" % (sys.executable, self.fake)


class QuestionsTest(unittest.TestCase):
    def test_repo_question_lists_are_valid(self):
        self.assertEqual(bc.validate(), [])

    def test_product_rows_replace_and_drop_common_ones(self):
        repo = Repo(self)
        ids = [c["id"] for c in bc.load_checks(repo.root, "x")]
        self.assertIn("G1", ids)
        self.assertNotIn("G4", ids)
        self.assertIn("K1", ids)

    def test_questions_follow_the_product_state(self):
        repo = Repo(self)
        checks = bc.load_checks(repo.root, "x")
        assembled = [c["id"] for c in bc.for_state(checks, "assembled")]
        apart = [c["id"] for c in bc.for_state(checks, "disassembled")]
        self.assertIn("K2", assembled)
        self.assertNotIn("K3", assembled)
        self.assertIn("K3", apart)
        self.assertNotIn("K2", apart)

    def test_bad_rows_are_reported(self):
        repo = Repo(self, HEADER + "K1,问题,甲;乙,丙,yes,,已确认,,,\n")
        errors = "\n".join(bc.validate(repo.root))
        self.assertIn("expected answer '丙' is not an option", errors)
        self.assertIn("may_hide is yes", errors)
        self.assertIn("no fix_en", errors)
        self.assertIn("no source", errors)

    def test_the_prompt_carries_only_questions_and_options(self):
        repo = Repo(self)
        checks = bc.for_state(bc.load_checks(repo.root, "x"), "assembled")
        prompt = bc.build_prompt(checks)
        self.assertIn("[K1] 水位窗和控制头在哪两侧？", prompt)
        self.assertIn("相对的两侧；相邻的两侧；看不到", prompt)
        for leak in ("外形识别点", "the window is opposite", "fix", "已确认"):
            self.assertNotIn(leak, prompt)
        schema = bc.build_schema(checks)
        self.assertEqual(schema["properties"]["K1"]["enum"], ["相对的两侧", "相邻的两侧", "看不到"])
        self.assertEqual(sorted(schema["required"]), sorted(c["id"] for c in checks))


class ScoreTest(unittest.TestCase):
    def setUp(self):
        repo = Repo(self)
        self.checks = bc.load_checks(repo.root, "x")

    def test_verdicts(self):
        k1 = [c for c in self.checks if c["id"] == "K1"][0]
        self.assertEqual(bc.verdict(k1, "相对的两侧"), "对")
        self.assertEqual(bc.verdict(k1, "相邻的两侧"), "错")
        self.assertEqual(bc.verdict(k1, "看不到"), "看不到")
        self.assertEqual(bc.verdict(k1, "侧面"), "无效")
        self.assertEqual(bc.verdict(k1, None), "没答")

    def test_only_confirmed_questions_decide(self):
        checks = bc.for_state(self.checks, "disassembled")
        entry = bc.score(checks, {"G1": "没有", "G2": "画面里没有人手", "G3": "1", "K1": "相对的两侧", "K3": "一个水泵"})
        self.assertTrue(entry["passed"])
        self.assertEqual(entry["summary"]["参考"], 1)
        entry = bc.score(checks, {"G1": "没有", "G2": "画面里没有人手", "G3": "1", "K1": "相邻的两侧", "K3": "整个组件"})
        self.assertFalse(entry["passed"])
        self.assertEqual(entry["fix"], "the window is opposite the head")

    def test_answers_are_found_in_chatty_output(self):
        self.assertEqual(bc.parse_answers('好的。\n{"K1": "对"}\n'), {"K1": "对"})
        self.assertEqual(bc.parse_answers('{"answers": {"K1": "对"}}'), {"K1": "对"})
        with self.assertRaises(bc.CheckError):
            bc.parse_answers("no json here")


class RunTest(unittest.TestCase):
    def test_wrong_answers_fail_v1_and_print_the_fix(self):
        repo = Repo(self)
        good, bad = repo.image("good.png"), repo.image("bad.png")
        code, out = repo.run("run", "--product", "x", "--image", good, "--image", bad, "--reviewer", repo.reviewer)
        self.assertEqual(code, 0, out)
        self.assertIn("BLIND - good.png", out)
        self.assertIn("V1 FAIL", out)
        self.assertIn("✗ K1", out)
        self.assertIn("FIX: the window is opposite the head", out)
        self.assertIn("V1 fail 1 (bad.png)", out)
        with open(os.path.join(repo.root, "outputs", "x", "blind_check.json"), encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertTrue(saved["good.png"]["passed"])
        self.assertFalse(saved["bad.png"]["passed"])

    def test_relative_image_paths_still_reach_the_reviewer(self):
        repo = Repo(self)
        repo.image("good.png")
        here = os.getcwd()
        os.chdir(repo.root)
        self.addCleanup(os.chdir, here)
        code, out = repo.run("run", "--product", "x", "--image", "img/good.png", "--reviewer", repo.reviewer)
        self.assertEqual(code, 0, out)
        self.assertIn("V1 fail 0", out)

    def test_a_reviewer_that_saw_nothing_is_not_a_verdict(self):
        repo = Repo(self)
        blank = repo.image("blank.png")
        code, out = repo.run("run", "--product", "x", "--image", blank, "--reviewer", repo.reviewer)
        self.assertIn("UNSEEN", out)
        self.assertIn("V1 fail 0", out)
        self.assertIn("unseen 1", out)
        self.assertNotIn("FIX:", out)

    def test_missing_image_is_an_error(self):
        repo = Repo(self)
        code, out = repo.run("run", "--product", "x", "--image", os.path.join(repo.root, "nope.png"), "--reviewer", repo.reviewer)
        self.assertEqual(code, 1)
        self.assertIn("image not found", out)

    def test_manual_answers_can_be_scored(self):
        repo = Repo(self)
        img = repo.image("bad.png")
        answers = os.path.join(repo.root, "a.json")
        with open(answers, "w", encoding="utf-8") as fh:
            json.dump({"G1": "没有", "G2": "没有", "G3": "1", "K1": "相邻的两侧", "K2": "2"}, fh, ensure_ascii=False)
        code, out = repo.run("score", "--product", "x", "--image", img, "--answers", answers, "--slot", "S2")
        self.assertIn("BLIND S2 bad.png", out)
        self.assertIn("V1 FAIL", out)


class ReviewFormTest(unittest.TestCase):
    def test_form_lists_flagged_images_first(self):
        import review_form
        task = os.path.join(ROOT, "tools", "fixtures", "round10l_v2_task.md")
        with tempfile.TemporaryDirectory() as root:
            os.symlink(os.path.join(ROOT, "products"), os.path.join(root, "products"))
            folder = os.path.join(root, "outputs", "round10l")
            os.makedirs(folder)
            with open(os.path.join(folder, "S5_clean_v01.png"), "wb") as fh:
                fh.write(b"x")
            with open(os.path.join(folder, "blind_check.json"), "w", encoding="utf-8") as fh:
                json.dump({"S5_clean_v01.png": {"image": "outputs/round10l/S5_clean_v01.png", "seen": True, "passed": False,
                           "results": [{"id": "K1", "question": "水位窗在哪？", "answer": "侧面", "expect": ["正面"],
                                        "verdict": "错", "counts": True},
                                       {"id": "K2", "question": "几个键？", "answer": "2", "expect": ["2"],
                                        "verdict": "对", "counts": True}]}}, fh, ensure_ascii=False)
            out, _data = review_form.build(task, None, None, True, root=root)
            with open(out, encoding="utf-8") as fh:
                page = fh.read()
            sheet = json.loads(re.search(r'id="sheet" type="application/json">(.*?)</script>', page, re.S).group(1))
        self.assertEqual(sheet["blind_flagged"], ["S5"])
        s5 = next(it for it in sheet["items"] if it["slot"] == "S5")
        self.assertEqual(s5["blind"]["right"], 1)
        self.assertEqual(s5["blind"]["fail"][0]["answer"], "侧面")
        other = next(it for it in sheet["items"] if it["slot"] != "S5")
        self.assertEqual(other["blind"], {})
        self.assertIn("独立核对没过的图，先看这些", page)


class WiringTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_and_agents(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("### 4.7 独立核对", "tools/blind_check.py run", "products/<产品>/checks.csv",
                       "references/checks_common.csv", "以独立核对为准"):
            self.assertIn(marker, guide)
        self.assertIn("blind_check.py", self.read("AGENTS.md"))


if __name__ == "__main__":
    unittest.main()
