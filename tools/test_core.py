"""Core selling points (UTA_STYLE.md 2.2): the user picks their lens and story; the task records them as core:.

    python -m unittest discover -s tools -p "test_core.py" -v
"""
import os
import unittest

import check_set
from test_check_set import Base, V2, read

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def card(slot, **fields):
    return check_set.Card("cards/x/%s_x.md" % slot, ["slot: %s" % slot] + ["%s: %s" % kv for kv in fields.items()])


def with_core(value):
    return read(V2).replace("scope: full\n", "scope: full\ncore: %s\n" % value, 1)


class TaskTest(Base):
    def test_core_is_read_and_passes(self):
        code, out, _ = self.run_task(self.write("t.md", with_core("F3;F1")))
        self.assertEqual(code, 0, out)
        self.assertIn("core=F3;F1", out)
        self.assertNotIn("[C-2]", out)

    def test_core_must_be_one_or_two_real_facts(self):
        for value in ("F9", "F1;F2;F3", "F3;F3"):
            code, out, _ = self.run_task(self.write("t.md", with_core(value)))
            self.assertEqual(code, 2, value)
            self.assertIn("TASK ERROR [C-1]", out)

    def test_old_tasks_have_no_core(self):
        code, out, _ = self.run_task(V2)
        self.assertNotIn("core=", out)


class RuleTest(unittest.TestCase):
    def test_core_fact_must_appear_in_subs_and_aplus(self):
        cards = [card("S1", selling_point="F1"), card("S2", selling_point="F2"),
                 card("P1", module="scene", selling_point="F1"),
                 card("P2", module="grid", selling_point="none", panels="P2a, P2b"),
                 card("P2a", selling_point="F3"), card("P2b", selling_point="F4")]
        ts = check_set.TaskSet(cards)
        self.assertEqual(check_set.core_rules(ts, {"core": ["F1", "F3"]}),
                         [("C-2", "主推卖点 F3 在副图里一张图都没讲（2.2）")])
        self.assertEqual(check_set.core_rules(ts, {"core": ["F2"]}),
                         [("C-2", "主推卖点 F2 在A+里一张图都没讲（2.2）")])
        self.assertEqual(check_set.core_rules(ts, {}), [])


class WiringTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_guide_skill_and_confirm_page(self):
        guide = self.read("UTA_STYLE.md")
        for marker in ("**主推卖点由用户选表达。**", "- `core:` 主推卖点", "- C-1 ", "- C-2 ", "主推卖点的表达卡"):
            self.assertIn(marker, guide)
        skill = self.read("grok", "grok-UTAstyle-skill.md")
        self.assertIn("**主推卖点的镜头和故事让用户选。**", skill)
        self.assertIn("`core:`", skill)
        page = self.read("grok", "confirm_template.html")
        self.assertIn("data.core", page)
        self.assertIn("m.core", page)


if __name__ == "__main__":
    unittest.main()
