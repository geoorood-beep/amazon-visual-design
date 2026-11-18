"""PW002-S running water window: blue light and a readable level, nowhere else.

Run from the repository root:
    python3 -m unittest discover -s tools -p "test_check_*.py"
"""
import os
import unittest

import check_card
import check_set
import usage_model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fields(**extra):
    base = {
        "product": "pw002_s",
        "product_view": "front",
        "focus": "rim",
        "evidence": "the water starts to move",
        "story": "",
        "pet_action": "",
        "human_action": "",
    }
    base.update(extra)
    return base


class WindowLight(unittest.TestCase):
    def setUp(self):
        self.usage = usage_model.load_usage(ROOT, "pw002_s")
        self.other = usage_model.load_usage(ROOT, "round10l")

    def test_only_the_confirmed_product_has_the_sentence(self):
        self.assertIn("blue light", self.usage["window_light"])
        self.assertIn("readable", self.usage["window_light"])
        self.assertNotIn("do not", self.usage["window_light"].lower())
        self.assertNotIn("never", self.usage["window_light"].lower())
        self.assertEqual(self.other["window_light"], "")

    def test_running_front_view_only(self):
        self.assertTrue(usage_model.window_light_applies(self.usage, fields()))
        self.assertFalse(usage_model.window_light_applies(
            self.usage, fields(evidence="the basin stands full of water")))
        self.assertFalse(usage_model.window_light_applies(
            self.usage, fields(product_view="side_left")))
        self.assertFalse(usage_model.window_light_applies(
            self.usage, fields(evidence="hands rinse only the steel body")))
        self.assertFalse(usage_model.window_light_applies(
            self.usage, fields(evidence="This frame is not an operating shot. When water is running, do not paint a working glow.")))
        self.assertTrue(usage_model.window_light_applies(
            self.usage, fields(evidence="The fountain is running and the water window stays in frame.")))

    def test_running_light_does_not_replace_fact_inference(self):
        self.assertIn("FV03", usage_model.requirement(self.usage, "F2")["source"])
        self.assertNotIn("事实的画面要求", usage_model.requirement(self.usage, "F2")["source"])
        self.assertIn("water flowing", usage_model.requirement(self.usage, "F12")["must_show"])
        self.assertFalse(usage_model.window_light_applies(self.other, fields(product="round10l")))

    def test_prompt_states_the_light_without_the_old_ban(self):
        blocks = check_card.load_prompt_blocks()
        context = {
            "fields": dict(fields(), camera="eye_level", scene="a room", light="side light from the left",
                           pet="none", pet_action="none", human_action="none", text_area="left",
                           canvas="4:5"),
            "kind": "S",
            "panel": False,
            "identity": ["one steel basin", "no glowing window"],
            "geometry": [],
            "attach": [],
            "edition": "standard",
        }
        prompt = check_card.build_prompt(context, blocks)
        self.assertIn("blue light is visible inside that window", prompt)
        self.assertNotIn("glowing water window", prompt)
        self.assertNotIn("glowing window", prompt.lower())
        self.assertNotIn("product never glows", prompt)
        self.assertIn("steel body does not glow", prompt)

    def test_other_product_keeps_the_ban(self):
        blocks = check_card.load_prompt_blocks()
        context = {
            "fields": dict(fields(product="round10l", evidence="the water starts to move"),
                           camera="eye_level", scene="a room", light="side light",
                           pet="none", pet_action="none", human_action="none", text_area="left",
                           canvas="4:5"),
            "kind": "S", "panel": False, "identity": ["one basin"], "geometry": [], "attach": [],
            "edition": "standard",
        }
        prompt = check_card.build_prompt(context, blocks)
        self.assertIn("glowing water window", prompt)
        self.assertNotIn("blue light is visible inside that window", prompt)

    def test_compiled_night_lamp_does_not_forbid_the_confirmed_window(self):
        body = [
            "card_version: 2", "product: pw002_s", "slot: S4", "canvas: 4:5",
            "selling_point: F12",
            "evidence: A cat sleeps beside the basin while ripples remain on the water",
            "human_action: none", "pet: one ragdoll cat with blue eyes",
            "pet_action: sleeps", "camera: down_45", "scene: a room",
            "light: one warm lamp from the left", "shot_size: close",
            "product_view: front", "focus: rim", "interaction: rest",
            "light_setup: night_lamp", "foreground: none",
            "story: At night the cat sleeps while the water still ripples.",
            "text_area: left", "headline: Quiet", "subtitle: Under 25 dB", "hero_number: 25",
        ]
        card = check_set.Card("s.md", body)
        compiled = "\n".join(check_set.compile_card(card, {"usage": self.usage}))
        self.assertIn("blue light is visible inside that window", compiled)
        self.assertIn("That lamp lights the room", compiled)
        self.assertNotIn("water window glows", compiled)

        still = check_set.Card("s.md", [
            "card_version: 2", "product: pw002_s", "slot: P7a", "selling_point: F1",
            "evidence: The basin stands alone, full of water",
            "story: none", "pet_action: none", "human_action: none",
            "light: daylight from the left", "light_setup: side",
            "product_view: front", "focus: whole", "shot_size: medium",
            "camera: eye_level", "scene: a room", "foreground: none",
            "text_area: none", "headline: none", "subtitle: none", "hero_number: none",
        ])
        quiet = "\n".join(check_set.compile_card(still, {"usage": self.usage}))
        self.assertNotIn("blue light is visible inside that window", quiet)
