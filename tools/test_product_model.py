"""Product source (UTA_STYLE.md 1.18, 3.10): the 3D model gives the shape at any angle, Codex the rest.

    python -m unittest discover -s tools -p "test_product_model.py" -v
"""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_card
import check_set
import product_model as pm
import render_refs
import shape_check
from test_check_set import V2

ROOT = pm.ROOT
READY = {"product": "demo", "source": "demo.stp", "mesh": "demo.glb", "status": "ready", "unit": "mm",
         "axes": {"front": "-Y", "up": "+Z"}, "scale_check": {"dim": "L", "model_mm": 312, "measured_mm": 310},
         "approved": "user 2026-11-21"}


class RouteTest(unittest.TestCase):
    def test_every_card_takes_the_shape_reference_when_it_can(self):
        for slot in ("M1", "S2", "P2a"):
            self.assertEqual(pm.route(slot, ready=True), "render_ref")
        self.assertEqual(pm.route("M1", ready=False), "generate")
        self.assertEqual(pm.route("M1", ready=True, has_renderer=False), "generate")
        self.assertEqual(set(pm.STEPS), set(pm.ROUTES))

    def test_card_to_camera_table_covers_every_value(self):
        self.assertEqual(set(pm.VIEW_AZIMUTH), set(check_set.VIEW_TEXT))
        self.assertEqual(set(pm.CAMERA_ELEVATION), set(check_set.CAMERA_TEXT))
        self.assertEqual(set(pm.SHOT_FILL), set(check_set.SHOT_TEXT))
        self.assertEqual(set(pm.LENS_MM), set(check_set.LENSES))
        self.assertIn("1:1", pm.CANVAS_PX)

    def test_jobs(self):
        close = pm.job_for("S2", {"product_view": "front", "camera": "eye_level", "shot_size": "close",
                                  "lens": "standard", "product_state": "assembled", "focus": "control_panel",
                                  "canvas": "4:5"})
        self.assertEqual((close["focus"], close["fill"]), ("control_panel", 0.72))
        medium = pm.job_for("S3", dict(close, shot_size="medium"))
        self.assertEqual(medium["focus"], "whole")
        self.assertEqual(pm.job_for("M1", {})["canvas"], "1:1")
        a, b = pm.job_id(close, READY), pm.job_id(dict(close), READY)
        self.assertEqual(a, b)
        self.assertNotEqual(a, pm.job_id(close, dict(READY, revision=2)))


class CardGapTest(unittest.TestCase):
    MODEL = dict(READY, parts={"control_panel": ["08_*"]}, states={"loading": {"rotate": {}}})

    def test_close_shot_on_an_unmapped_part_is_caught(self):
        self.assertEqual(pm.card_gaps("close", "control_panel", "assembled", self.MODEL), [])
        gaps = pm.card_gaps("extreme_close", "lid_hinge", "assembled", self.MODEL)
        self.assertEqual(len(gaps), 1)
        self.assertIn("lid_hinge", gaps[0])
        # a medium or wide shot frames the whole product, so its focus part needs no mapping
        self.assertEqual(pm.card_gaps("wide", "lid_hinge", "assembled", self.MODEL), [])

    def test_unmapped_state_is_caught(self):
        self.assertEqual(pm.card_gaps("medium", "whole", "loading", self.MODEL), [])
        self.assertIn("disassembled", pm.card_gaps("medium", "whole", "disassembled", self.MODEL)[0])

    def test_check_set_runs_it(self):
        with open(os.path.join(ROOT, "tools", "check_set.py"), encoding="utf-8") as fh:
            self.assertIn("product_model.card_gaps(shot, focus, card_state(card)", fh.read())


class ModelJsonTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "products", "demo", "model"))

    def write(self, data):
        with open(os.path.join(self.root, "products", "demo", "model", "model.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def test_no_model_means_generate(self):
        self.assertIsNone(pm.load_model(self.root, "demo"))
        self.assertFalse(pm.is_ready(self.root, "demo"))

    def test_ready_needs_axes_mesh_scale_and_approval(self):
        self.write(READY)
        self.assertTrue(pm.is_ready(self.root, "demo"))
        for broken in (dict(READY, approved=""), dict(READY, axes={}), dict(READY, mesh=""),
                       dict(READY, scale_check={"model_mm": 330, "measured_mm": 310}), dict(READY, status="draft")):
            self.write(broken)
            self.assertFalse(pm.is_ready(self.root, "demo"), broken)
        self.write(dict(READY, axes={"front": "north", "up": "+Z"}))
        self.assertIn("axes.front", " ".join(pm.model_problems(self.root, "demo", pm.load_model(self.root, "demo"))))
        out = io.StringIO()
        self.write(dict(READY, status="maybe"))
        self.assertEqual(pm.main(["check"], root=self.root, out=out), 1)
        self.assertIn("status must be draft or ready", out.getvalue())

    def test_repo_models_are_valid(self):
        out = io.StringIO()
        self.assertEqual(pm.main(["check"], out=out), 0, out.getvalue())


class CompileTest(unittest.TestCase):
    def cards(self):
        with open(V2, encoding="utf-8") as fh:
            _, _, cards = check_set.parse_task(fh.read())
        return {c.slot: c for c in cards}

    def pools(self, renderer="/usr/bin/blender"):
        return {"model_ready": True, "renderer": renderer, "model": READY, "product": "round10l",
                "expressions": {}, "people": {}, "moods": {}}

    def test_no_model_leaves_the_card_alone(self):
        self.assertNotIn("product_source", "\n".join(check_set.compile_card(self.cards()["M1"], {})))

    def test_ready_model_adds_a_shape_reference_and_a_job(self):
        pools = self.pools()
        lines = check_set.compile_card(self.cards()["P2a"], pools)
        self.assertIn("product_source: render_ref", lines)
        ref = [l for l in lines if l.startswith("render_ref: outputs/round10l/renders/")]
        self.assertEqual(len(ref), 1)
        self.assertEqual(len(pools["render_jobs"]), 1)
        job = list(pools["render_jobs"].values())[0]
        self.assertEqual((job["view"], job["camera"], job["shot"], job["canvas"]), ("side_right", "eye_level", "full", "3:2"))
        main = check_set.compile_card(self.cards()["M1"], pools)
        self.assertIn("product_source: render_ref", main)
        self.assertEqual(len(pools["render_jobs"]), 2)

    def test_no_blender_falls_back(self):
        lines = check_set.compile_card(self.cards()["M1"], self.pools(renderer=None))
        self.assertIn("product_source: generate", lines)
        self.assertFalse([l for l in lines if l.startswith("render_ref:")])


class CheckCardTest(unittest.TestCase):
    def test_shape_reference_reaches_the_prompt(self):
        index = check_card.load_index()
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        card = sorted((Path(ROOT) / "cards" / "round10l").glob("S*_*.md"))[0]
        text = card.read_text(encoding="utf-8").replace("canvas: 4:5\n", "canvas: 4:5\nproduct_source: render_ref\n"
                                                         "render_ref: outputs/round10l/renders/abc.png | shape only\n", 1)
        (folder / card.name).write_text(text, encoding="utf-8")
        errors, _w, context = check_card.validate(folder / card.name, index)
        self.assertEqual(errors, [])
        self.assertEqual(context["render_ref"], "outputs/round10l/renders/abc.png")
        prompt = check_card.build_prompt(context, check_card.load_prompt_blocks())
        self.assertIn("SHAPE: The first attached picture is a plain 3D render", prompt)
        bad = text.replace("render_ref: outputs/round10l/renders/abc.png | shape only\n", "")
        (folder / card.name).write_text(bad, encoding="utf-8")
        errors, _w, _c = check_card.validate(folder / card.name, index)
        self.assertTrue(any("needs a render_ref line" in e for e in errors), errors)


class RenderRefsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        d = os.path.join(self.root, "products", "demo", "model")
        os.makedirs(d)
        with open(os.path.join(d, "model.json"), "w", encoding="utf-8") as fh:
            json.dump(READY, fh)
        open(os.path.join(d, "demo.glb"), "wb").close()

    def test_only_missing_jobs_go_to_blender_once(self):
        job = pm.job_for("M1", {})
        jobs = {pm.job_id(job, READY): job, "old": dict(job, view="rear")}
        pm.save_jobs(self.root, "demo", jobs)
        folder = pm.render_dir(self.root, "demo")
        open(os.path.join(folder, "old.png"), "wb").close()
        calls = []

        def fake(model, todo, folder_, blender=None, timeout=3600):
            calls.append(sorted(todo))
            return ["ALL"]

        real = render_refs.blender_run
        render_refs.blender_run = fake
        try:
            out = io.StringIO()
            self.assertEqual(render_refs.main(["run", "--product", "demo"], root=self.root, out=out), 0)
        finally:
            render_refs.blender_run = real
        self.assertEqual(calls, [[pm.job_id(job, READY)]])
        self.assertIn("RENDERED 1 new, 1 reused", out.getvalue())

    def test_check_set_renders_the_round_itself(self):
        job = pm.job_for("M1", {})
        jobs = {pm.job_id(job, READY): job}
        real = render_refs.blender_run
        render_refs.blender_run = lambda *a, **k: ["ALL"]
        lines = []
        try:
            self.assertTrue(check_set.render_now(self.root, "demo", jobs, lines.append))
        finally:
            render_refs.blender_run = real
        self.assertTrue(any("RENDERED 1 new" in l for l in lines), lines)
        os.remove(os.path.join(self.root, "products", "demo", "model", "demo.glb"))
        lines = []
        self.assertFalse(check_set.render_now(self.root, "demo", jobs, lines.append))
        self.assertIn("WARN [1.18]", lines[0])
        self.assertIn("照常生成", lines[1])

    def test_missing_mesh_is_an_error(self):
        os.remove(os.path.join(self.root, "products", "demo", "model", "demo.glb"))
        out = io.StringIO()
        self.assertEqual(render_refs.main(["run", "--product", "demo"], root=self.root, out=out), 2)
        self.assertIn("run `convert` first", out.getvalue())


class ShapeCheckTest(unittest.TestCase):
    ANSWER = {"same_product": "yes", "proportion": "same", "fix_en": "",
              "differences": [{"part": "lid", "problem": "slightly thicker", "severity": "minor"}]}

    def test_verdicts(self):
        self.assertEqual(shape_check.verdict(self.ANSWER), "PASS")
        major = dict(self.ANSWER, differences=[{"part": "bowl", "problem": "missing", "severity": "major"}])
        self.assertEqual(shape_check.verdict(major), "FAIL")
        self.assertEqual(shape_check.verdict(dict(self.ANSWER, proportion="taller")), "FAIL")
        self.assertEqual(shape_check.verdict(dict(self.ANSWER, same_product="unsure")), "UNSURE")
        self.assertIn("bowl: missing", shape_check.fix_line(major))

    def test_whole_answer_is_parsed_not_a_nested_object(self):
        text = "noise " + json.dumps(self.ANSWER) + " trailing"
        self.assertEqual(shape_check.parse_object(text)["same_product"], "yes")

    def test_run_with_a_reviewer_command(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        img = os.path.join(root, "a.png")
        open(img, "wb").close()
        answer = os.path.join(root, "answer.json")
        with open(answer, "w", encoding="utf-8") as fh:
            json.dump(dict(self.ANSWER, same_product="no", fix_en="Make the hopper taller."), fh)
        out = io.StringIO()
        code = shape_check.main(["run", "--product", "demo", "--image", img, "--render", img, "--slot", "S2",
                                 "--reviewer", "cp %s {out}" % answer], root=root, out=out)
        self.assertEqual(code, 1)
        self.assertIn("SHAPE FAIL S2", out.getvalue())
        self.assertIn("FIX: Make the hopper taller.", out.getvalue())
        self.assertTrue(os.path.exists(os.path.join(root, "outputs", "demo", "shape_check.json")))


class ShapeBatchTest(unittest.TestCase):
    def test_a_whole_round_in_parallel(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        out_dir = os.path.join(root, "outputs", "demo")
        renders = os.path.join(out_dir, "renders")
        os.makedirs(renders)
        for name in ("aaa.png", "bbb.png", "ccc.png"):
            open(os.path.join(renders, name), "wb").close()
        for name in ("S2_bowl_base_v01.png", "S2_bowl_base_v02.png", "S2_bowl_v03.png", "M1_main_v01.png",
                     "P2a_tray_v01.png", "P2_x_desktop_1464x600_v01.png"):
            open(os.path.join(out_dir, name), "wb").close()
        task = os.path.join(root, "task.md")
        with open(task, "w", encoding="utf-8") as fh:
            fh.write("UTA-TASK v1\nproduct: demo\ncards: 4\n\n"
                     "=== cards/demo/M1_main.md ===\nslot: M1\nrender_ref: outputs/demo/renders/aaa.png | shape\n"
                     "=== cards/demo/S2_bowl.md ===\nslot: S2\nrender_ref: outputs/demo/renders/bbb.png | shape\n"
                     "=== cards/demo/S3_lid.md ===\nslot: S3\nrender_ref: outputs/demo/renders/ccc.png | shape\n"
                     "=== cards/demo/S4_text.md ===\nslot: S4\nproduct_source: generate\n")
        answer = os.path.join(root, "answer.json")
        with open(answer, "w", encoding="utf-8") as fh:
            json.dump(dict(ShapeCheckTest.ANSWER, same_product="no", fix_en="Make the lid flatter."), fh)
        self.assertEqual(shape_check.newest_picture(out_dir, "S2"), os.path.join(out_dir, "S2_bowl_base_v02.png"))
        self.assertIsNone(shape_check.newest_picture(out_dir, "P2"))
        out = io.StringIO()
        code = shape_check.main(["batch", "--product", "demo", "--task", task, "--jobs", "3",
                                 "--reviewer", "cp %s {out}" % answer], root=root, out=out)
        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("SHAPE FAIL M1", text)
        self.assertIn("SHAPE FAIL S2", text)
        self.assertIn("SHAPE SKIP S3: no picture yet", text)
        self.assertNotIn("S4", text)
        self.assertIn("SHAPE BATCH 2 checked: PASS 0, FAIL 2", text)
        self.assertIn("regenerate with the FIX lines: M1 S2", text)
        with open(os.path.join(out_dir, "shape_check.json"), encoding="utf-8") as fh:
            self.assertEqual(len(json.load(fh)), 2)


class RepoTest(unittest.TestCase):
    def test_cad_files_never_reach_the_repo(self):
        if not os.path.exists(os.path.join(ROOT, ".git")):
            self.skipTest("not a git checkout")
        for name in ("source.stp", "part.step", "demo.glb", "scene.blend", "render.png"):
            code = subprocess.run(["git", "check-ignore", "-q", "products/pw002_s/model/%s" % name], cwd=ROOT).returncode
            self.assertEqual(code, 0, name)
        self.assertEqual(subprocess.run(["git", "check-ignore", "-q", "products/pw002_s/model/model.json"], cwd=ROOT).returncode, 1)
        self.assertEqual(subprocess.run(["git", "check-ignore", "-q", "outputs/demo/renders/x.png"], cwd=ROOT).returncode, 0)

    def test_wiring(self):
        with open(os.path.join(ROOT, "UTA_STYLE.md"), encoding="utf-8") as fh:
            guide = fh.read()
        for marker in ("### 1.18 产品来源", "### 3.10 3D 渲染路线", "tools/render_refs.py", "tools/shape_check.py",
                       "模型文件不进仓库", "颜色只到"):
            self.assertIn(marker, guide)
        with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as fh:
            self.assertIn("shape_check.py batch", fh.read())


class CameraNumbersTest(unittest.TestCase):
    """Optional camera numbers on a card (UTA_STYLE.md 1.18, 2.4, v3.54)."""

    CARD = {"product_view": "three_quarter_right", "camera": "low_angle", "shot_size": "full", "lens": "hero_low",
            "product_state": "assembled", "focus": "whole", "canvas": "4:5"}

    def test_numbers_replace_the_table_but_not_the_distance(self):
        plain = pm.job_for("S2", self.CARD)
        self.assertNotIn("azimuth", plain)
        job = pm.job_for("S2", dict(self.CARD, cam_az="55", cam_el="-12", cam_focal="24"))
        self.assertEqual((job["azimuth"], job["elevation"], job["focal_mm"], job["res_scale"]),
                         (55, -12, 24, pm.RES_SCALE))
        self.assertEqual((job["fill"], job["focus"], job["view"]), (plain["fill"], plain["focus"], plain["view"]))
        self.assertNotEqual(pm.job_id(plain, READY), pm.job_id(job, READY))
        main = pm.job_for("M1", {"cam_az": "-30", "cam_el": "20", "cam_focal": "70"})
        self.assertEqual((main["azimuth"], main["elevation"], main["focal_mm"]), (-30, 20, 70))
        self.assertEqual(main["fill"], pm.MAIN_JOB["fill"])
        self.assertEqual(pm.job_for("M1", {}), pm.MAIN_JOB)

    def test_close_shot_still_aims_at_the_focus_part(self):
        job = pm.job_for("S3", dict(self.CARD, shot_size="close", focus="control_panel",
                                    cam_az="40", cam_el="-8", cam_focal="85"))
        self.assertEqual((job["focus"], job["focal_mm"]), ("control_panel", 85))

    def test_numbers_are_checked(self):
        self.assertEqual(pm.cam_errors({}), [])
        self.assertEqual(pm.cam_errors({"cam_az": "none", "cam_el": "", "cam_focal": "none"}), [])
        self.assertIn("三个一起写", pm.cam_errors({"cam_az": "30"})[0])
        self.assertIn("要写数字", pm.cam_errors({"cam_az": "left", "cam_el": "8", "cam_focal": "50"})[0])
        self.assertIn("要在 14 到 135 之间", pm.cam_errors({"cam_az": "30", "cam_el": "8", "cam_focal": "300"})[0])
        self.assertIsNone(pm.cam_numbers({"cam_az": "30"}))
        # a rear three-quarter sits halfway between the side (90) and the rear (180): both rows are nearest
        rear34 = {"cam_az": "135", "cam_el": "8", "cam_focal": "35"}
        self.assertEqual(pm.cam_errors(rear34, "side_right", "eye_level"), [])
        self.assertEqual(pm.cam_errors(rear34, "rear", "eye_level"), [])
        far = pm.cam_errors(rear34, "three_quarter_right", "eye_level")
        self.assertEqual(len(far), 1)
        self.assertIn("rear 或 side_right", far[0])
        self.assertEqual(pm.cam_errors(dict(rear34, cam_az="-180"), "rear", "eye_level"), [])
        low = pm.cam_errors(dict(rear34, cam_el="-12"), "side_right", "eye_level")
        self.assertEqual(len(low), 1)
        self.assertIn("camera 要写离它最近的一档 low_angle", low[0])

    def test_check_set_keeps_the_numbers_out_of_task_v1(self):
        self.assertEqual(check_set.CAM_FIELDS, pm.CAM_FIELDS)
        self.assertTrue(set(pm.CAM_FIELDS) <= check_set.V2_ONLY_FIELDS)
        self.assertEqual(set(pm.CAM_RANGE), set(pm.CAM_FIELDS))

    def test_renderer_puts_left_where_the_prompt_says(self):
        """A negative azimuth moves the camera to the left of a person facing the product, as VIEW_TEXT says."""
        self.assertIn("to the left of centre", check_set.VIEW_TEXT["front_left"])
        self.assertLess(pm.VIEW_AZIMUTH["front_left"], 0)
        with open(os.path.join(ROOT, "tools", "blender_refs.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("mathutils.Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))", src)
        self.assertIn('mathutils.Matrix.Rotation(a, 3, "Z")', src)
        self.assertNotIn("-math.sin(a)", src)


if __name__ == "__main__":
    unittest.main()
