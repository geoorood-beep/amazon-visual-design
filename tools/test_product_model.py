"""Product source (UTA_STYLE.md 1.18, 3.10): the 3D route, its switch, and that CAD never reaches the repo.

    python -m unittest discover -s tools -p "test_product_model.py" -v
"""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import check_set
import product_model as pm
from test_check_set import V2

ROOT = pm.ROOT
READY = {"product": "demo", "source": "demo.stp", "status": "ready", "unit": "mm",
         "scale_check": {"dim": "L", "model_mm": 312, "measured_mm": 310}, "approved": "user 2026-11-21"}


class RouteTest(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(pm.route("M1", ready=True), "render")
        self.assertEqual(pm.route("S2", "product_only", ready=True), "render_composite")
        self.assertEqual(pm.route("S3", "drink", "hero_wide", ready=True), "render_composite")
        self.assertEqual(pm.route("S4", "drink", "surface_wide", ready=True), "render_ref")
        self.assertEqual(pm.route("P2a", "rest", ready=True), "render_ref")
        self.assertEqual(pm.route("M1", ready=False), "generate")
        self.assertEqual(pm.route("M1", ready=True, has_renderer=False), "generate")
        self.assertEqual(set(pm.STEPS), set(pm.ROUTES))


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

    def test_ready_needs_scale_check_and_approval(self):
        self.write(READY)
        self.assertTrue(pm.is_ready(self.root, "demo"))
        self.write(dict(READY, approved=""))
        self.assertFalse(pm.is_ready(self.root, "demo"))
        self.write(dict(READY, scale_check={"model_mm": 330, "measured_mm": 310}))
        self.assertIn("differ by more than 2%", " ".join(pm.model_problems(self.root, "demo", pm.load_model(self.root, "demo"))))
        self.write(dict(READY, status="draft"))
        self.assertFalse(pm.is_ready(self.root, "demo"))
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

    def test_route_is_written_only_when_the_model_is_ready(self):
        cards = self.cards()
        off = "\n".join(check_set.compile_card(cards["M1"], {}))
        self.assertNotIn("product_source:", off)
        on = {"model_ready": True, "renderer": "/usr/bin/blender", "expressions": {}, "people": {}, "moods": {}}
        self.assertIn("product_source: render", check_set.compile_card(cards["M1"], on))
        lines = "\n".join(check_set.compile_card(cards["P2a"], on))
        self.assertIn("product_source: render_ref", lines)
        no_blender = {"model_ready": True, "renderer": None}
        self.assertIn("product_source: generate", check_set.compile_card(cards["M1"], no_blender))


class RepoTest(unittest.TestCase):
    def test_cad_files_never_reach_the_repo(self):
        if not os.path.exists(os.path.join(ROOT, ".git")):
            self.skipTest("not a git checkout")
        for name in ("source.stp", "part.step", "demo.glb", "scene.blend", "render.png"):
            path = "products/pw002_s/model/%s" % name
            code = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode
            self.assertEqual(code, 0, path)
        code = subprocess.run(["git", "check-ignore", "-q", "products/pw002_s/model/model.json"], cwd=ROOT).returncode
        self.assertEqual(code, 1)

    def test_wiring(self):
        with open(os.path.join(ROOT, "UTA_STYLE.md"), encoding="utf-8") as fh:
            guide = fh.read()
        for marker in ("### 1.18 产品来源", "### 3.10 3D 渲染路线", "`render_composite`", "模型文件不进仓库"):
            self.assertIn(marker, guide)
        with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as fh:
            self.assertIn("PRODUCT SOURCE", fh.read())


if __name__ == "__main__":
    unittest.main()
