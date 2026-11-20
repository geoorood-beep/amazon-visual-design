"""A+ module library and page recipes (UTA_STYLE.md 1.9, 2.4, 2.6 A-17 to A-19).

    python -m unittest discover -s tools -p "test_aplus_recipes.py" -v
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import check_card
import check_set
from test_check_set import Base, V2, read

ROOT = Path(check_card.ROOT)
PREMIUM = ROOT / "cards" / "examples_premium"


def card(slot, **fields):
    return check_set.Card("cards/x/%s_x.md" % slot, ["slot: %s" % slot] + ["%s: %s" % kv for kv in fields.items()])


def screen(slot, module, tone="light", beat="life", **more):
    base = dict(module=module, edition="premium", tone=tone, beat=beat, selling_point="none", hero_number="none")
    base.update(more)
    return card(slot, **base)


def rules(cards, recipe="free"):
    recipes = check_set.load_recipes(str(ROOT))
    _fails, warns = check_set.set_rules(check_set.TaskSet(cards), {}, strict=False, pools={"recipe": recipes[recipe]})
    return [(rule, msg) for rule, msg in warns if rule.startswith("A-")]


def page(*mods, **extra):
    """A premium page: one screen per module, panels filled in with different facts."""
    cards, n = [], 0
    for i, mod in enumerate(mods, 1):
        slot = "P%d" % i
        more = dict(extra.get(slot, {}))
        if mod == "scene":
            more.setdefault("pet", "cat")
            more.setdefault("text_area", "left" if i % 2 else "right")
            more.setdefault("selling_point", "F%d" % i)
        else:
            count = {"overview": 4, "bento": 4, "cards3": 3, "contrast": 2, "fit": 2, "steps": 2}.get(mod, 1)
            names = [slot + "abcdefgh"[k] for k in range(count)]
            more.setdefault("panels", ", ".join(names))
            for name in names:
                n += 1
                cards.append(card(name, selling_point="F%d" % (10 + n), canvas="1:1"))
        cards.insert(0, screen(slot, mod, **more))
    return cards


class LibraryTest(unittest.TestCase):
    def test_recipes_use_real_modules(self):
        recipes = check_set.load_recipes(str(ROOT))
        self.assertEqual(set(recipes), {"A", "B", "C", "D", "free"})
        for rid, row in recipes.items():
            steps = check_set.recipe_steps(row)
            if rid == "free":
                self.assertEqual(steps, [])
                continue
            for step in steps:
                self.assertTrue(step <= set(check_set.MODULES), (rid, step))
            self.assertEqual(steps[0], {"scene"}, rid)
            self.assertTrue(steps[-1] <= check_set.CLOSING, rid)
            for key in ("name", "learn_from", "fits", "how", "example"):
                self.assertTrue(row[key].strip(), (rid, key))

    def test_the_two_checkers_agree_on_modules(self):
        self.assertEqual(set(check_card.MODULES), set(check_set.MODULES))
        self.assertEqual(set(check_set.MODULES) - check_set.STANDARD_MODULES, check_card.PREMIUM_MODULES)

    def test_recipe_problems(self):
        steps = check_set.recipe_steps({"skeleton": "scene > bento|grid > contrast > specs|fit"})
        self.assertEqual(check_set.recipe_problems(["scene", "grid", "number", "contrast", "specs"], steps), [])
        self.assertIn("中间缺 contrast", check_set.recipe_problems(["scene", "contrast", "grid", "specs"], steps)[0])
        self.assertIn("第一屏要是 scene", check_set.recipe_problems(["grid", "grid", "contrast", "fit"], steps)[0])
        self.assertIn("最后一屏要是 fit 或 specs", check_set.recipe_problems(["scene", "grid", "contrast", "number"], steps)[0])

    def test_panel_frames(self):
        self.assertEqual(check_card.panel_canvas("split", "premium", 1, 0), "3:2")
        self.assertEqual([check_card.panel_canvas("bento", "premium", 4, i) for i in range(4)], ["3:2", "3:2", "1:1", "1:1"])
        self.assertEqual(check_card.panel_canvas("overview", "premium", 8, 7), "1:1")
        self.assertEqual(check_card.panel_canvas("cards3", "premium", 3, 0), "1:1")


class SetRulesTest(unittest.TestCase):
    def test_recipe_b_page_passes(self):
        cards = page("scene", "overview", "number", "split", "bento", "split", "specs",
                     P1={"seam": "next"}, P3={"tone": "dark", "hero_number": "10 L"})
        self.assertEqual(rules(cards, "B"), [])

    def test_recipe_skeleton_is_enforced(self):
        cards = page("scene", "bento", "number", "split", "specs", P3={"tone": "dark", "hero_number": "10 L"})
        found = rules(cards, "A")
        self.assertIn(("A-17", "套路 A「痛点解决」：中间缺 contrast（骨架要按顺序出现）"), found)
        self.assertNotIn("A-17", [r for r, _m in rules(cards, "free")])

    def test_closing_may_be_trust_or_fit(self):
        for close in ("trust", "fit"):
            cards = page("scene", "bento", "number", "contrast", close, P3={"tone": "dark", "hero_number": "10 L"})
            self.assertNotIn("A-2", [r for r, _m in rules(cards)], close)
        cards = page("scene", "bento", "number", "contrast", "split", P3={"tone": "dark", "hero_number": "10 L"})
        self.assertIn(("A-2", "最后一屏要是 specs、trust 或 fit，现在是 split"), rules(cards))

    def test_overview_only_on_screen_two(self):
        cards = page("scene", "bento", "overview", "number", "specs", P4={"tone": "dark", "hero_number": "10 L"})
        self.assertIn(("A-19", "P3 是卖点总览，只能放第 2 屏"), rules(cards))

    def test_seam_rules(self):
        cards = page("scene", "split", "bento", "number", "specs",
                     P1={"seam": "next"}, P4={"tone": "dark", "hero_number": "10 L"})
        self.assertIn(("A-18", "P1 接 P2：下面一屏要是组合模块，现在是 split"), rules(cards))
        cards = page("scene", "bento", "number", "contrast", "specs",
                     P2={"seam": "next"}, P3={"tone": "dark", "hero_number": "10 L"})
        found = rules(cards)
        self.assertIn(("A-18", "P2 写了 seam：上面一屏要是 scene 或 number，现在是 bento"), found)
        self.assertIn(("A-18", "P2 和 P3 拼接，深浅要一样"), found)

    def test_a_dark_seam_pair_counts_as_one_dark_screen(self):
        cards = page("scene", "number", "overview", "contrast", "specs",
                     P2={"seam": "next", "tone": "dark", "hero_number": "10 L"}, P3={"tone": "dark"})
        found = rules(cards)
        self.assertFalse([m for r, m in found if r == "A-8"], found)

    def test_standard_edition_keeps_its_four_modules(self):
        cards = [card("P1", module="scene", edition="standard", beat="hook", pet="cat", text_area="left",
                      selling_point="F1", hero_number="none"),
                 card("P2", module="bento", edition="standard", beat="detail", selling_point="none",
                      panels="P2a, P2b, P2c, P2d", hero_number="none"),
                 card("P3", module="specs", edition="standard", beat="close", selling_point="none", panels="P3a",
                      hero_number="none")]
        self.assertIn(("A-4", "标准版不能用 bento"), rules(cards))


class TaskTest(Base):
    def header(self, value):
        return read(V2).replace("scope: full\n", "scope: full\naplus_recipe: %s\n" % value, 1)

    def test_unknown_recipe_is_a_task_error(self):
        code, out, _ = self.run_task(self.write("t.md", self.header("Z")))
        self.assertEqual(code, 2)
        self.assertIn("aplus_recipe", out)

    def test_recipe_in_header_is_checked(self):
        code, out, _ = self.run_task(self.write("t.md", self.header("C")))
        self.assertNotEqual(code, 0)
        self.assertIn("aplus_recipe=C 质感叙事", out)
        self.assertIn("[A-17] 套路 C「质感叙事」", out)

    def test_old_tasks_are_free(self):
        code, out, _ = self.run_task(V2)
        self.assertNotIn("A-17", out)
        self.assertNotIn("aplus_recipe=", out)


class ModuleCardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = check_card.load_index()

    def validate(self, name, edits=(), extra=None):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for source in PREMIUM.glob("*.md"):
                shutil.copy(source, folder / source.name)
            if extra:
                src, dst, changes = extra
                text = (folder / src).read_text(encoding="utf-8")
                for old, new in changes:
                    self.assertIn(old, text)
                    text = text.replace(old, new)
                (folder / dst).write_text(text, encoding="utf-8")
            for file, old, new in edits:
                text = (folder / file).read_text(encoding="utf-8")
                self.assertIn(old, text, file)
                (folder / file).write_text(text.replace(old, new), encoding="utf-8")
            errors, _w, context = check_card.validate(folder / name, self.index)
        return errors, context

    P3D = ("P3c_window.md", "P3d_extra.md", [("slot: P3c", "slot: P3d"), ("selling_point: F6", "selling_point: F1"),
                                              ("label: Water Window", "label: Wide Basin")])

    def test_split_with_lines_from_its_fact(self):
        errors, context = self.validate("P2_capacity.md", [("P2_capacity.md", "module: number", "module: split"),
                                                            ("P2_capacity.md", "lines: none", "lines: F1 | 10 L")])
        self.assertEqual(errors, [])
        self.assertEqual(context["lines"], [("F1", "10 L")])
        errors, _ = self.validate("P2_capacity.md", [("P2_capacity.md", "module: number", "module: split"),
                                                      ("P2_capacity.md", "lines: none", "lines: F2 | 304 Steel")])
        self.assertIn("every line of a split module must use its fact F1", errors)

    def test_bento_takes_four_panels_two_wide(self):
        edits = [("P3_built.md", "module: grid", "module: bento"),
                 ("P3_built.md", "panels: P3a, P3b, P3c", "panels: P3a, P3b, P3c, P3d")]
        errors, _ = self.validate("P3_built.md", edits, self.P3D)
        self.assertIn("panel P3b: canvas must be 3:2 (the lead panel of this premium module is wide)", errors)
        errors, _ = self.validate("P3_built.md", edits + [("P3b_quiet.md", "canvas: 1:1", "canvas: 3:2")], self.P3D)
        self.assertEqual(errors, [])
        errors, _ = self.validate("P3_built.md", edits[:1])
        self.assertIn("a bento module needs 4 panel(s), got 3", errors)

    def test_overview_and_cards3(self):
        square = [("P3a_steel.md", "canvas: 3:2", "canvas: 1:1")]
        errors, _ = self.validate("P3_built.md", square + [
            ("P3_built.md", "module: grid", "module: overview"),
            ("P3_built.md", "panels: P3a, P3b, P3c", "panels: P3a, P3b, P3c, P3d")], self.P3D)
        self.assertEqual(errors, [])
        errors, _ = self.validate("P3_built.md", square + [("P3_built.md", "module: grid", "module: cards3")])
        self.assertEqual(errors, [])

    def test_fit_shares_one_fact(self):
        errors, _ = self.validate("P4_rinse.md", [("P4_rinse.md", "module: contrast", "module: fit")])
        self.assertEqual(errors, [])

    def test_new_modules_are_premium_only(self):
        errors, _ = self.validate("P4_rinse.md", [("P4_rinse.md", "module: contrast", "module: fit"),
                                                   ("P4_rinse.md", "edition: premium", "edition: standard")])
        self.assertIn("module: fit is only for the premium edition", errors)

    def test_seam(self):
        errors, context = self.validate("P1_together.md", [("P1_together.md", "tone: light\n", "tone: light\nseam: next\n")])
        self.assertEqual(errors, [])
        self.assertEqual(context["seam"], "next")
        errors, _ = self.validate("P3_built.md", [("P3_built.md", "tone: dark\n", "tone: dark\nseam: next\n")])
        self.assertIn("seam: only a scene or number screen joins the screen below it", errors)
        errors, _ = self.validate("P1_together.md", [("P1_together.md", "tone: light\n", "tone: light\nseam: prev\n")])
        self.assertIn("seam must be 'next' (this screen joins the next one), or left out", errors)


class WiringTest(unittest.TestCase):
    def test_guide_skill_and_docs(self):
        guide = (ROOT / "UTA_STYLE.md").read_text(encoding="utf-8")
        for marker in ("**卖点选版式。**", "**页面套路。**", "**无缝拼接（`seam`）。**", "references/aplus_recipes.csv",
                       "- A-17 ", "- A-18 ", "- A-19 ", "`aplus_recipe:`", "| `overview` 卖点总览 |", "| `trust` 信任收尾 |"):
            self.assertIn(marker, guide)
        self.assertNotIn("`contrast` 只拍自家产品的两个状态", guide)
        skill = (ROOT / "grok" / "grok-UTAstyle-skill.md").read_text(encoding="utf-8")
        self.assertIn("aplus_recipe", skill)
        self.assertIn("references/aplus_recipes.csv", skill)


if __name__ == "__main__":
    unittest.main()
