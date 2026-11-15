#!/usr/bin/env python3
"""尺寸、白边、dark/outdoor、JSON 退出码，以及排版原型正负例。

底图都是测试纯色或测试渐变，不是产品参考图，也不替代 product_reference.png。
不修改 docs/uta_style_v3/tests/v05_gpt 里的样本。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADE = os.path.join(ROOT, "tools", "grade_check.py")
RENDER = os.path.join(ROOT, "tools", "layout_render.py")
FACTS = os.path.join(ROOT, "tools", "facts.json")
FONTS = os.path.join(ROOT, "fonts", "poppins")


def run_grade(args):
    proc = subprocess.run(
        [sys.executable, GRADE, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def save_rgb(path, array):
    Image.fromarray(array.astype(np.uint8), "RGB").save(path)


def flat(width, height, color):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = color
    return image


class GradeCheckTests(unittest.TestCase):
    def test_slot_size_and_white_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = os.path.join(tmp, "g1.png")
            bad_size = os.path.join(tmp, "small.png")
            bad_edge = os.path.join(tmp, "edge.png")
            save_rgb(good, flat(2000, 2000, (255, 255, 255)))
            save_rgb(bad_size, flat(100, 100, (255, 255, 255)))
            edge = flat(2000, 2000, (255, 255, 255))
            edge[0, :, :] = (254, 255, 255)
            save_rgb(bad_edge, edge)
            code, out, err = run_grade(["--slot", "G1", "--json", good])
            self.assertEqual(err, "")
            self.assertEqual(code, 0, out)
            payload = json.loads(out)
            self.assertTrue(payload["results"][0]["white_edge_ok"])
            self.assertTrue(payload["results"][0]["size_ok"])
            code, out, _err = run_grade(["--slot", "S", "--json", bad_size])
            self.assertEqual(code, 1)
            self.assertIn("size", json.loads(out)["results"][0]["flags"])
            code, out, _err = run_grade(["--slot", "G1", "--json", bad_edge])
            self.assertEqual(code, 1)
            self.assertIn("white_edge", json.loads(out)["results"][0]["flags"])
            ap = os.path.join(tmp, "ap.png")
            mobile = os.path.join(tmp, "m.png")
            master = os.path.join(tmp, "master.png")
            save_rgb(ap, flat(1464, 600, (240, 236, 230)))
            save_rgb(mobile, flat(1200, 900, (240, 236, 230)))
            save_rgb(master, flat(2928, 1200, (240, 236, 230)))
            for slot, path in (("AP-PC", ap), ("AP-M", mobile), ("AP-PC", master)):
                code, out, err = run_grade(["--slot", slot, "--json", path])
                self.assertEqual(code, 1, out + err)
                flags = json.loads(out)["results"][0]["flags"]
                self.assertNotIn("size", flags)
                self.assertTrue(json.loads(out)["results"][0]["size_ok"])

    def test_dark_and_outdoor_still_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            dark = os.path.join(tmp, "dark.png")
            outdoor = os.path.join(tmp, "outdoor.png")
            save_rgb(dark, self.make_dark())
            save_rgb(outdoor, self.make_outdoor())
            code, out, err = run_grade(["--dark", "--json", dark])
            self.assertEqual(code, 0, out + err)
            self.assertEqual(json.loads(out)["mode"], "dark")
            code, out, err = run_grade(["--outdoor", "--json", outdoor])
            self.assertEqual(code, 0, out + err)
            self.assertEqual(json.loads(out)["mode"], "outdoor")
            code, _out, _err = run_grade(["--dark", "--json", outdoor])
            self.assertNotEqual(code, 0)

    def test_contrast_exit_code_and_mutual_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = os.path.join(tmp, "flat.png")
            save_rgb(image, flat(32, 32, (180, 170, 160)))
            code, out, err = run_grade(["--contrast", "--json", image])
            self.assertEqual(err, "")
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(out)["pass"])
            code, _out, err = run_grade(["--contrast", "--dark", image])
            self.assertEqual(code, 2)
            self.assertIn("只能选一个", err)

    def test_missing_file_exit_2(self):
        code, _out, err = run_grade(["--json", "docs/no-such-image.png"])
        self.assertEqual(code, 2)
        self.assertTrue(err)

    def paint_blocks(self, blocks):
        """按面积比例铺纯色块。颜色来自文档区间的可复现构造，不是产品图。"""
        side = 200
        image = np.zeros((side * side, 3), dtype=np.uint8)
        start = 0
        total = side * side
        for fraction, color in blocks:
            count = int(round(fraction * total))
            image[start : start + count] = color
            start += count
        image[start:] = blocks[-1][1]
        return image.reshape(side, side, 3)

    def make_dark(self):
        # 8% / 70% / 22%，使 p5、p95、均值、标准差、饱和度和 R−B 落进 §9.1 B 档。
        return self.paint_blocks([
            (0.08, (33, 9, 0)),
            (0.70, (84, 60, 43)),
            (0.22, (199, 175, 158)),
        ])

    def make_outdoor(self):
        # 15% / 60% / 25%，落进 §12A.2。
        return self.paint_blocks([
            (0.15, (29, 42, 29)),
            (0.60, (107, 153, 107)),
            (0.25, (180, 255, 180)),
        ])


class LayoutPrototypeTests(unittest.TestCase):
    def write_layout(self, directory, name, payload):
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return path

    def base(self, bg):
        return {
            "slot": "S",
            "bg": bg,
            "title": "1 m sensing",
            "subtitle": "一米感应",
            "hero": {"number": "1", "unit": "m"},
            "cards": [],
            "anchor": "top-left",
            "mode": "light",
            "hero_scale": 2.0,
            "avoid": [],
        }

    def run_layout(self, layout, out_dir, font_dir=FONTS):
        return subprocess.run(
            [sys.executable, RENDER, "--layout", layout, "--out-dir", out_dir, "--facts", FACTS, "--font-dir", font_dir],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_positive_poppins_and_negative_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            bg = os.path.join(tmp, "test-solid-not-a-product.png")
            save_rgb(bg, flat(1600, 2000, (232, 224, 210)))
            out = os.path.join(tmp, "ok")
            layout = self.write_layout(tmp, "ok.json", self.base(bg))
            proc = self.run_layout(layout, out)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report_path = os.path.join(out, "ok_report.json")
            with open(report_path, encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertEqual(report["fonts"]["title"]["family"], "Poppins")
            self.assertEqual(report["fonts"]["title"]["style"], "Bold")
            self.assertFalse(report["fonts"]["title"]["silent_substitution"])
            self.assertEqual(report["sizes"]["title_px_at_upload"], 92)
            self.assertEqual(report["occlusion_check"], "NOT_CHECKED_NO_MARKED_REGION")
            self.assertTrue(os.path.isfile(os.path.join(out, "ok_master.png")))
            master = Image.open(os.path.join(out, "ok_master.png"))
            self.assertEqual(master.size, (1600, 2000))

            blocked = self.base(bg)
            blocked["title"] = "5L Capacity"
            proc = self.run_layout(self.write_layout(tmp, "capacity.json", blocked), os.path.join(tmp, "bad1"))
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertFalse(os.path.exists(os.path.join(tmp, "bad1", "capacity_master.png")))
            self.assertIn("白名单", proc.stdout)

            wifi = self.base(bg)
            wifi["subtitle"] = "Wi-Fi"
            proc = self.run_layout(self.write_layout(tmp, "wifi.json", wifi), os.path.join(tmp, "bad2"))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("禁用词", proc.stdout)

            layers = self.base(bg)
            layers["cards"] = ["304 不锈钢"]
            proc = self.run_layout(self.write_layout(tmp, "layers.json", layers), os.path.join(tmp, "bad3"))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("3 层", proc.stdout)

            words = self.base(bg)
            words["hero"] = None
            words["title"] = "1 m sensing 1 m sensing"
            proc = self.run_layout(self.write_layout(tmp, "words.json", words), os.path.join(tmp, "bad4"))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("5 个英文单词", proc.stdout)

            avoid = self.base(bg)
            avoid["avoid"] = [{"x": 0, "y": 0, "w": 900, "h": 500}]
            proc = self.run_layout(self.write_layout(tmp, "avoid.json", avoid), os.path.join(tmp, "bad5"))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("标记区域", proc.stdout)

            tall = self.base(bg)
            tall["hero"] = None
            tall["hero_scale"] = 2.0
            tall["cards"] = ["304 不锈钢"] * 14
            proc = self.run_layout(self.write_layout(tmp, "tall.json", tall), os.path.join(tmp, "bad6"))
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("安全区", proc.stdout)

            empty_fonts = os.path.join(tmp, "nofonts")
            os.makedirs(empty_fonts)
            proc = self.run_layout(layout, os.path.join(tmp, "bad7"), font_dir=empty_fonts)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("拒绝改用其他字体", proc.stdout)

            g1 = os.path.join(tmp, "g1.png")
            save_rgb(g1, flat(2000, 2000, (255, 255, 255)))
            banned = self.base(g1)
            banned["slot"] = "G1"
            proc = self.run_layout(self.write_layout(tmp, "g1.json", banned), os.path.join(tmp, "bad8"))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("不排文字", proc.stdout)


if __name__ == "__main__":
    unittest.main()
