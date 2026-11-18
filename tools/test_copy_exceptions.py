"""Positive and negative tests for the 2.7 copy exceptions.

Run from the repository root:
    python -m unittest discover -s tools -p "test_check_*.py"
"""
import os
import unittest

import check_card
import check_set
import copy_exceptions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = """
| F1 | 本品是无线 10L 饮水机 | 可写「无线」 | 画面须避开 wireless |
| F2 | 无线感应出水 | 感应出水 | 不要使用 wireless |
| F5 | 电池 4000 毫安，续航 15–21 天。多宠或密集触发感应可能缩短续航 | 可写 4000 mAh、续航 15–21 天，且必须保留「多宠或密集触发感应可能缩短续航」的限定 | 不得无条件承诺 15 天。避开 battery |
| F6 | 304 不锈钢 | 304 | 不写电池 |
| F7 | 不得写无线的普通杯子 | 普通杯子 | |
| F8 | 身边没有拖出的电源线 | 不必拖着电源线 | |
"""
OK = "15-21 days, and multiple pets or frequent sensing may shorten runtime"
OK_HF = "15–21 days, and multiple pets or high-frequency sensing may shorten runtime"


class Grants(unittest.TestCase):
    def setUp(self):
        self.grants = copy_exceptions.grants_from_text(CARD)

    def test_only_confirmed_claims_are_granted(self):
        self.assertIn("wireless", self.grants["F1"])
        self.assertIn("wireless", self.grants["F2"])
        self.assertNotIn("battery", self.grants["F1"])
        self.assertIn("battery", self.grants["F5"])
        self.assertIn("duration_15_21", self.grants["F5"])
        self.assertNotIn("wireless", self.grants["F6"])
        self.assertNotIn("battery", self.grants["F6"])
        self.assertNotIn("duration_15_21", self.grants["F6"])
        self.assertEqual(self.grants["F7"], set())
        self.assertEqual(self.grants["F8"], set())

    def test_banned_column_does_not_grant(self):
        text = "| F1 | 不锈钢盆 | 304 | 不得写无线，避开 battery，可写 15–21 天 |"
        self.assertEqual(copy_exceptions.grants_from_text(text)["F1"], set())

    def test_duration_without_caveat_in_the_card_is_not_granted(self):
        text = "| F1 | 续航 15–21 天 | 可写 15–21 天 | |"
        self.assertNotIn("duration_15_21", copy_exceptions.grants_from_text(text)["F1"])


class Duration(unittest.TestCase):
    def setUp(self):
        self.held = copy_exceptions.grants_from_text(CARD)["F5"]
        self.other = set()

    def test_full_sentence_passes(self):
        self.assertEqual(copy_exceptions.duration_hits(OK, self.held), [])
        self.assertEqual(copy_exceptions.duration_hits(OK_HF, self.held), [])

    def test_missing_caveat_fails(self):
        self.assertIn("days", copy_exceptions.duration_hits("15-21 days", self.held))

    def test_caveat_in_the_next_sentence_fails(self):
        text = "15-21 days. Multiple pets or frequent sensing may shorten runtime."
        self.assertIn("days", copy_exceptions.duration_hits(text, self.held))

    def test_keyword_stuffing_fails(self):
        text = "15-21 days with multiple pets nearby, and frequent sensing may shorten runtime later"
        self.assertIn("days", copy_exceptions.duration_hits(text, self.held))

    def test_wrong_number_or_unit_fails(self):
        for text in ("15 days, and " + OK.split(", and ", 1)[1],
                     "21 days, and " + OK.split(", and ", 1)[1],
                     "14-21 days, and " + OK.split(", and ", 1)[1],
                     "15-21 weeks, and " + OK.split(", and ", 1)[1],
                     "15-21 day, and " + OK.split(", and ", 1)[1]):
            self.assertTrue(copy_exceptions.duration_hits(text, self.held), text)

    def test_other_duration_words_still_fail_beside_a_good_phrase(self):
        text = OK + " for vacation"
        hits = copy_exceptions.duration_hits(text, self.held)
        self.assertIn("vacation", [hit.lower() for hit in hits])
        self.assertNotIn("days", [hit.lower() for hit in hits])

    def test_unauthorised_fact_fails_even_with_the_full_sentence(self):
        self.assertIn("days", copy_exceptions.duration_hits(OK, self.other))


class Terms(unittest.TestCase):
    def setUp(self):
        self.grants = copy_exceptions.grants_from_text(CARD)

    def test_bound_words_pass_and_the_other_word_does_not(self):
        self.assertEqual(copy_exceptions.term_hits("Wireless flow", self.grants["F2"]), [])
        self.assertEqual(copy_exceptions.term_hits("4000 mAh battery", self.grants["F5"]), [])
        self.assertEqual(copy_exceptions.term_hits("Wireless battery", self.grants["F2"]), ["battery"])
        self.assertEqual(copy_exceptions.term_hits("Wireless", self.grants["F6"]), ["wireless"])
        self.assertEqual(copy_exceptions.term_hits("battery", self.grants["F8"]), ["battery"])

    def test_round10l_has_no_grant(self):
        grants = copy_exceptions.load_grants(ROOT, "round10l")
        self.assertTrue(all("wireless" not in held and "battery" not in held for held in grants.values()))
        self.assertEqual(copy_exceptions.term_hits("Wireless", grants.get("F1", set())), ["wireless"])
        self.assertIn("days", copy_exceptions.duration_hits("Lasts for days", grants.get("F1", set())))


class CheckerWiring(unittest.TestCase):
    def card(self, **fields):
        class Fake:
            def f(self, key, default=""):
                return fields.get(key, default)

            def is_none(self, key):
                return str(fields.get(key, "none")).strip().lower() in ("", "none")
        return Fake()

    def test_story_and_headline_use_the_same_duration_rule(self):
        grants = copy_exceptions.grants_from_text(CARD)
        ok = self.card(selling_point="F5", headline=OK, story=OK, eyebrow="none",
                       subtitle="none", hero_number="none", label="none", lines="none")
        errs = []
        check_set.check_copy(ok, errs, grants)
        check_set.check_story(ok, errs, grants)
        self.assertEqual(errs, [])
        split = self.card(
            selling_point="F5",
            headline="15-21 days",
            subtitle="multiple pets or frequent sensing may shorten runtime",
            story="15-21 days",
            eyebrow="none", hero_number="none", label="none", lines="none",
        )
        errs = []
        check_set.check_copy(split, errs, grants)
        check_set.check_story(split, errs, grants)
        self.assertTrue(any("headline" in err and "days" in err for err in errs), errs)
        self.assertTrue(any(err.startswith("story") and "days" in err for err in errs), errs)

    def test_wrong_fact_on_a_line_fails(self):
        grants = copy_exceptions.grants_from_text(CARD)
        card = self.card(
            selling_point="none",
            eyebrow="none", headline="The bowl", subtitle="none", hero_number="none",
            label="none", lines="F6 | " + OK,
        )
        errs = []
        check_set.check_copy(card, errs, grants)
        self.assertTrue(any("lines" in err and "days" in err for err in errs), errs)
        good = self.card(
            selling_point="none",
            eyebrow="none", headline="Wireless", subtitle="none", hero_number="none",
            label="none", lines="F5 | " + OK,
        )
        errs = []
        check_set.check_copy(good, errs, grants)
        self.assertTrue(any("headline" in err and "wireless" in err for err in errs), errs)
        self.assertFalse(any(err.startswith("lines") for err in errs), errs)

    def test_check_card_keeps_round10l_blocked_and_allows_a_bound_fact(self):
        errs = []
        check_card.check_copy("Wireless flow", ["10 L"], "round10l", [], errs, fact_id="F1")
        self.assertTrue(any("wireless" in err for err in errs), errs)
        errs = []
        check_card.check_copy("Fresh water for days", ["10 L"], "round10l", [], errs, fact_id="F1")
        self.assertTrue(any("days" in err for err in errs), errs)

        def fake_load(_root, _product):
            return copy_exceptions.grants_from_text(CARD)

        original = copy_exceptions.load_grants
        copy_exceptions.load_grants = fake_load
        try:
            errs = []
            check_card.check_copy("Wireless flow", ["感应出水"], "fixture", [], errs, fact_id="F2")
            self.assertEqual(errs, [])
            errs = []
            check_card.check_copy(OK, ["15-21 days"], "fixture", [], errs, fact_id="F5")
            self.assertEqual(errs, [])
            errs = []
            check_card.check_copy("Wireless flow", ["304"], "fixture", [], errs, fact_id="F6")
            self.assertTrue(any("wireless" in err for err in errs), errs)
            errs = []
            check_card.check_copy(OK, ["304"], "fixture", [], errs, fact_id="F6")
            self.assertTrue(any("days" in err for err in errs), errs)
        finally:
            copy_exceptions.load_grants = original
