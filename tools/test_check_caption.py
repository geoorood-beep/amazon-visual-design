"""Caption is visible typeset copy. The S6 comparison is one card only.

Run from the repository root:
    python3 -m unittest discover -s tools -p "test_check_*.py"
"""
import unittest

import check_card
import check_set
import copy_exceptions

OK = "15-21 days, multiple pets or frequent sensing may shorten runtime"
SPLIT_HEAD = "15-21 days"
SPLIT_TAIL = "multiple pets or frequent sensing may shorten runtime"
S6_CAPTION = "generic unbranded cord risk, not a test"
S6_EVIDENCE = (
    "On the left an unbranded corded basin, two dogs trip on the cord. "
    "On the right the main basin has no cord and a border collie drinks."
)


class Fake:
    def __init__(self, **fields):
        self.fields = fields
        self.parse_errors = []
        self.slot_value = fields.get("slot", "S1")

    def f(self, key, default=""):
        return self.fields.get(key, default)

    def is_none(self, key):
        return str(self.fields.get(key, "none")).strip().lower() in ("", "none")

    @property
    def slot(self):
        return self.slot_value


class CaptionVisible(unittest.TestCase):
    def test_caption_is_typeset_and_story_is_not(self):
        fields = {
            "eyebrow": "none",
            "headline": "Battery As Stated",
            "subtitle": "none",
            "hero_number": "none",
            "label": "4000 mAh",
            "caption": OK,
            "story": "A cat rests beside the basin.",
        }
        visible = dict(check_card.visible_typeset_lines(fields))
        self.assertEqual(visible["caption"], OK)
        self.assertNotIn("story", visible)
        self.assertNotIn("A cat rests", " ".join(visible.values()))

    def test_generation_prompt_does_not_carry_the_caption(self):
        blocks = check_card.load_prompt_blocks()
        context = {
            "fields": {
                "product": "pw002_s",
                "slot": "P3c",
                "selling_point": "F5",
                "comparison": "none",
                "evidence": "The cat rests beside the basin.",
                "human_action": "none",
                "pet": "a British shorthair",
                "pet_action": "rests",
                "camera": "eye_level",
                "scene": "a kitchen floor",
                "light": "side light from the left",
                "text_area": "left",
                "caption": OK,
            },
            "kind": "S",
            "panel": False,
            "identity": ["one steel basin"],
            "geometry": [],
            "attach": [],
            "edition": "standard",
            "tone": "light",
        }
        prompt = check_card.build_prompt(context, blocks)
        typeset = " ".join(value for _key, value in check_card.visible_typeset_lines(context["fields"]))
        self.assertIn(OK, typeset)
        self.assertNotIn(OK, prompt)
        self.assertIn("Do not render any text", prompt)

    def test_duration_stays_inside_the_caption_sentence(self):
        grants = {"F5": {"duration_15_21"}, "F1": set()}
        claims = {"wireless", "battery"}
        good = Fake(selling_point="F5", caption=OK, headline="Battery As Stated",
                    subtitle="none", eyebrow="none", hero_number="none", label="none", lines="none")
        errs = []
        check_set.check_copy(good, errs, grants, claims)
        self.assertEqual(errs, [])

        split = Fake(selling_point="F5", headline=SPLIT_HEAD, caption=SPLIT_TAIL,
                     subtitle="none", eyebrow="none", hero_number="none", label="none", lines="none")
        errs = []
        check_set.check_copy(split, errs, grants, claims)
        self.assertTrue(any(err.startswith("headline") and "days" in err for err in errs), errs)
        bare = Fake(selling_point="F5", caption="15-21 days", headline="none", subtitle="none",
                    eyebrow="none", hero_number="none", label="none", lines="none")
        errs = []
        check_set.check_copy(bare, errs, grants, claims)
        self.assertTrue(any(err.startswith("caption") and "days" in err for err in errs), errs)

        wrong = Fake(selling_point="F1", caption=OK, headline="none", subtitle="none",
                     eyebrow="none", hero_number="none", label="none", lines="none")
        errs = []
        check_set.check_copy(wrong, errs, grants, claims)
        self.assertTrue(any("caption" in err and "days" in err for err in errs), errs)

        other = Fake(selling_point="F5", caption="15-21 weeks, multiple pets or frequent sensing may shorten runtime",
                     headline="none", subtitle="none", eyebrow="none", hero_number="none",
                     label="none", lines="none")
        errs = []
        check_set.check_copy(other, errs, grants, claims)
        self.assertTrue(any("caption" in err for err in errs), errs)

    def test_caption_word_cap(self):
        errs = []
        check_card.check_words(
            {"caption": "one two three four five six seven eight nine ten eleven twelve thirteen"},
            "caption", check_card.MAX_CAPTION_WORDS, errs,
        )
        self.assertTrue(errs)
        errs = []
        check_card.check_words({"caption": OK}, "caption", check_card.MAX_CAPTION_WORDS, errs)
        self.assertEqual(errs, [])


class ComparisonScope(unittest.TestCase):
    def card(self, **fields):
        base = {
            "card_version": "2",
            "product": "pw002_s",
            "slot": "S6",
            "selling_point": "F8",
            "comparison": "risk_scenario",
            "caption": S6_CAPTION,
            "evidence": S6_EVIDENCE,
            "headline": "No Cord On Ours",
            "subtitle": "none",
            "story": "Two dogs trip on a generic cord while ours has none.",
        }
        base.update(fields)
        return Fake(**base)

    def test_only_pw002_s6_f8_passes(self):
        errs = []
        check_set.check_comparison(self.card(), errs)
        self.assertEqual(errs, [])
        errs = []
        check_set.check_comparison(self.card(product="round10l"), errs)
        self.assertTrue(errs)
        errs = []
        check_set.check_comparison(self.card(slot="S5"), errs)
        self.assertTrue(errs)
        errs = []
        check_set.check_comparison(self.card(selling_point="F1"), errs)
        self.assertTrue(errs)

    def test_missing_disclaimer_tip_and_brand_fail(self):
        errs = []
        check_set.check_comparison(self.card(caption="Two dogs, one cord"), errs)
        self.assertTrue(any("generic unbranded" in err for err in errs), errs)
        errs = []
        check_set.check_comparison(self.card(
            evidence="The basin tips over in a measured test by Petlibro.",
            story="A certified guarantee.",
        ), errs)
        self.assertTrue(any("不允许" in err for err in errs), errs)

    def test_prompt_note_is_limited_to_that_card(self):
        note = copy_exceptions.comparison_prompt_note("pw002_s", "S6", "F8", "risk_scenario")
        self.assertIn("unbranded", note)
        self.assertIn("Do not tip", note)
        self.assertEqual(copy_exceptions.comparison_prompt_note("pw002_s", "S1", "F8", "risk_scenario"), "")
        self.assertEqual(copy_exceptions.comparison_prompt_note("pw002_s", "S6", "F8", "none"), "")
