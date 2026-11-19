"""check_set's v2 -> v1 conversion must hand check_card something it accepts (3.2 step 2).

From v3.25 to v3.43 the conversion wrote refs.product without '| purpose', so check_card refused
every image card and the round stopped; it also swapped a reference the writer had named on purpose.

    python -m unittest discover -s tools -p "test_converter.py" -v
"""
import io
import pathlib
import os
import re
import shutil
import tempfile
import unittest

import check_card
import check_set

ROOT = check_set.ROOT if hasattr(check_set, "ROOT") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(ROOT, "tools", "fixtures", "round10l_v2_task.md")
VIEWS = os.path.join(ROOT, "products", "round10l", "ref_views.csv")


def view(path, side="front", state="assembled"):
    return {"path": path, "view": side, "cameras": ["eye_level"], "parts": ["whole"], "checked": True, "state": state}


def card(product_ref, side="side_left", state="assembled"):
    lines = ["slot: S1", "product_view: %s" % side, "camera: eye_level", "product_state: %s" % state, "refs:"]
    if product_ref is not None:
        lines.append("  product: %s" % product_ref)
    return check_set.Card("cards/x/S1_x.md", lines)


class EndToEndTest(unittest.TestCase):
    def test_every_converted_card_passes_the_check_card_parser(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        emit = os.path.join(tmp, "task_v1.md")
        code = check_set.run(V2, emit=emit, views_path=VIEWS, root=ROOT, state=os.path.join(tmp, "full.md"), out=io.StringIO())
        self.assertEqual(code, 0)
        with open(emit, encoding="utf-8") as fh:
            text = fh.read()
        blocks = re.findall(r"=== (cards/\S+) ===\n(---\n.*?\n---)\n", text, re.S)
        self.assertGreater(len(blocks), 10)
        for path, body in blocks:
            f = os.path.join(tmp, os.path.basename(path))
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(body + "\n")
            _fields, refs, errors = check_card.parse_card(pathlib.Path(f))
            self.assertEqual(errors, [], path)
            if refs.get("product"):
                self.assertTrue(refs["product"][1], "%s lost the product purpose" % path)


class ChosenRefTest(unittest.TestCase):
    VIEWS = [view("A.png", "front"), view("B.png", "side_left"), view("D.png", "front", "disassembled")]

    def test_a_named_registered_reference_is_kept(self):
        c = card("A.png | the accessory only")
        self.assertEqual(check_set.chosen_ref(c, self.VIEWS)["path"], "A.png")
        self.assertEqual(check_set.product_ref_line(c, check_set.chosen_ref(c, self.VIEWS)),
                         "  product: A.png | the accessory only")

    def test_an_unregistered_reference_is_replaced_and_its_purpose_kept(self):
        c = card("C.png | the accessory only")
        ref = check_set.chosen_ref(c, self.VIEWS)
        self.assertEqual(ref["path"], "B.png")
        self.assertEqual(check_set.product_ref_line(c, ref), "  product: B.png | the accessory only")

    def test_a_reference_in_the_wrong_state_is_replaced(self):
        c = card("A.png | whole product", side="front", state="disassembled")
        self.assertEqual(check_set.chosen_ref(c, self.VIEWS)["path"], "D.png")

    def test_a_missing_purpose_gets_the_default(self):
        c = card("A.png")
        self.assertEqual(check_set.product_ref_line(c, check_set.chosen_ref(c, self.VIEWS)),
                         "  product: A.png | " + check_set.DEFAULT_PRODUCT_PURPOSE)


class FlowTest(unittest.TestCase):
    """One confirmation carries the round; the package is sent once; a tool bug does not stop it (v3.44)."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_wiring(self):
        guide = self.read("UTA_STYLE.md")
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        for marker in ("**确认一次，做完一轮。**", "**交付包只发一次。**"):
            self.assertIn(marker, guide)
            self.assertIn(marker, skill)
        self.assertIn("**工具出错不停下。**", guide)
        self.assertIn("工具修复：无", guide)
        self.assertIn("不放宽、不删掉任何检查", guide)
        self.assertIn("工具出错不停下", self.read("AGENTS.md"))
        self.assertNotIn("给用户一张提问卡选下一步", skill)


if __name__ == "__main__":
    unittest.main()
