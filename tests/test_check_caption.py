"""Black-box tests for check_caption.py against the MW4 campaign rules (a real brief, see brief.txt).

The approved caption is copied from the caption that went out with approved clip 1.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_check_caption.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.environ.get("CHECK_CAPTION_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clipping-campaign-producer/scripts/check_caption.py")

CAMPAIGN = {
    "name": "Call of Duty Modern Warfare 4 Multiplayer Beta",
    "caption": {
        "required_phrases": ["Pre-order Modern Warfare 4 today and play day one, October 23rd"],
        "required_tags": ["@callofduty"],
        "disclosure": {"options": ["#Ad", "#Advertisement", "#Sponsored"]},
        "max_extra_hashtags": 3,
        "language": "en",
    },
}

PHRASE = "Pre-order Modern Warfare 4 today and play day one, October 23rd"
BODY = ("Pushed the hardpoint with zero hesitation and the whole room paid for it. Double kill and the Artillery "
        "Beacon was already in the air before they respawned. @callofduty " + PHRASE)
GOOD = f"{BODY}\n\n#Ad\n\n#ModernWarfare4 #MW4Beta #CallOfDuty"


class CheckCaption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="caption-test-")
        cls.campaign = os.path.join(cls.d, "campaign.json")
        with open(cls.campaign, "w") as f:
            json.dump(CAMPAIGN, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def check(self, caption, *extra):
        path = os.path.join(self.d, "caption.txt")
        with open(path, "w") as f:
            f.write(caption)
        out = os.path.join(self.d, "result.json")
        if os.path.exists(out):
            os.remove(out)
        proc = subprocess.run([sys.executable, SCRIPT, path, "--campaign", self.campaign, "--json", out, *extra],
                              capture_output=True, text=True)
        result = None
        if os.path.exists(out):
            with open(out) as f:
                result = json.load(f)
        return proc, result

    def failed(self, result):
        return {i["check"] for i in result["issues"] if i["level"] == "FAIL"}

    def assertVerdict(self, proc, result, verdict):
        self.assertIsNotNone(result, proc.stderr[-800:])
        self.assertEqual(result["verdict"], verdict, result["issues"])
        self.assertEqual(proc.returncode, 1 if verdict == "FAIL" else 0)

    def test_caption_that_went_out_with_an_approved_clip_passes(self):
        proc, result = self.check(GOOD)
        self.assertVerdict(proc, result, "PASS")

    def test_paraphrased_required_phrase_fails_and_points_at_the_near_miss(self):
        proc, result = self.check(GOOD.replace("Pre-order", "Preorder"))
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("required_phrase", self.failed(result))
        self.assertTrue(any("Preorder" in i["msg"] for i in result["issues"]), result["issues"])

    def test_required_phrase_must_match_capitalisation_exactly(self):
        # "This exact wording is required" - a lower-cased date is a substitution a reviewer can reject.
        proc, result = self.check(GOOD.replace("October 23rd", "october 23rd"))
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("required_phrase", self.failed(result))

    def test_missing_brand_tag_fails(self):
        proc, result = self.check(GOOD.replace("@callofduty ", ""))
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("required_tag", self.failed(result))

    def test_tag_is_matched_as_a_whole_handle_not_a_prefix(self):
        proc, result = self.check(GOOD.replace("@callofduty", "@callofdutyleague"))
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("required_tag", self.failed(result))

    def test_tag_case_does_not_matter(self):
        proc, result = self.check(GOOD.replace("@callofduty", "@CallOfDuty"))
        self.assertVerdict(proc, result, "PASS")

    def test_disclosure_inside_the_paragraph_fails(self):
        proc, result = self.check(f"{BODY} #Ad\n\n#ModernWarfare4 #MW4Beta #CallOfDuty")
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("disclosure_own_line", self.failed(result))

    def test_hashtag_before_the_disclosure_fails(self):
        proc, result = self.check(f"{BODY}\n\n#MW4\n#Ad\n\n#ModernWarfare4 #CallOfDuty")
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("disclosure_first", self.failed(result))

    def test_missing_disclosure_fails(self):
        proc, result = self.check(f"{BODY}\n\n#ModernWarfare4 #MW4Beta #CallOfDuty")
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("disclosure_present", self.failed(result))

    def test_disclosure_must_use_the_briefs_exact_spelling(self):
        proc, result = self.check(GOOD.replace("#Ad", "#ad"))
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("disclosure_present", self.failed(result))

    def test_alternative_disclosure_from_the_brief_is_accepted(self):
        proc, result = self.check(GOOD.replace("#Ad", "#Sponsored"))
        self.assertVerdict(proc, result, "PASS")

    def test_more_extra_hashtags_than_allowed_fails(self):
        proc, result = self.check(GOOD + " #COD")
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("extra_hashtags", self.failed(result))

    def test_like_for_like_style_promises_fail(self):
        # TikTok's For You feed standards name "like-for-like" promises as engagement manipulation.
        for bait in ("Like for like!", "follow4follow", "sub for sub?", "L4L"):
            proc, result = self.check(GOOD.replace("Pushed the hardpoint", f"{bait} Pushed the hardpoint"))
            self.assertIn("engagement_bait", self.failed(result), bait)

    def test_softer_engagement_bait_warns(self):
        proc, result = self.check(GOOD.replace("Pushed the hardpoint", "Tag a friend who needs this. Pushed the hardpoint"))
        levels = {i["check"]: i["level"] for i in result["issues"]}
        self.assertEqual(levels.get("engagement_bait"), "WARN", result["issues"])
        self.assertEqual(proc.returncode, 0)

    def test_ordinary_gameplay_words_are_not_bait(self):
        caption = GOOD.replace("Pushed the hardpoint", "Followed them into the hardpoint, liked the angle, pushed")
        proc, result = self.check(caption)
        self.assertNotIn("engagement_bait", {i["check"] for i in result["issues"]})

    def test_non_latin_script_is_flagged_for_english_only_campaigns(self):
        proc, result = self.check(GOOD.replace("Double kill", "더블 킬"))
        self.assertIsNotNone(result, proc.stderr[-800:])
        self.assertIn("language", {i["check"] for i in result["issues"]})
        self.assertNotEqual(result["verdict"], "PASS")

    def test_youtube_title_over_100_characters_fails(self):
        proc, result = self.check(GOOD, "--platform", "shorts", "--title", "Modern Warfare 4 Beta - " + "x" * 90)
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("title_length", self.failed(result))

    def uncapped(self, caption, *extra):
        # a brief with no hashtag cap of its own, so only the platform's limits apply
        path = os.path.join(self.d, "uncapped.json")
        with open(path, "w") as f:
            json.dump({"caption": {**CAMPAIGN["caption"], "max_extra_hashtags": None}}, f)
        cap_path = os.path.join(self.d, "caption_uncapped.txt")
        with open(cap_path, "w") as f:
            f.write(caption)
        out = os.path.join(self.d, "uncapped_result.json")
        proc = subprocess.run([sys.executable, SCRIPT, cap_path, "--campaign", path, "--json", out, *extra],
                              capture_output=True, text=True)
        with open(out) as f:
            return proc, json.load(f)

    def test_tiktok_accepts_captions_up_to_4000_characters(self):
        # TikTok raised the caption limit from 2,200 to 4,000 characters.
        long_body = BODY + " " + "Clean gunplay all match. " * 100
        caption = f"{long_body}\n\n#Ad\n\n#ModernWarfare4 #MW4Beta #CallOfDuty"
        self.assertTrue(2200 < len(caption) < 4000)
        proc, result = self.check(caption, "--platform", "tiktok")
        self.assertNotIn("caption_length", {i["check"] for i in result["issues"]})

    def test_reels_rejects_more_than_five_hashtags(self):
        # Instagram has enforced a 5-hashtag cap on posts and Reels since December 2025.
        proc, result = self.uncapped(f"{BODY}\n\n#Ad\n\n#MW4 #CallOfDuty #ModernWarfare4 #CODBeta #FPS", "--platform", "reels")
        self.assertIn("hashtag_limit", self.failed(result))
        proc, result = self.uncapped(f"{BODY}\n\n#Ad\n\n#MW4 #CallOfDuty #ModernWarfare4 #CODBeta", "--platform", "reels")
        self.assertNotIn("hashtag_limit", {i["check"] for i in result["issues"]})

    def test_shorts_ignores_hashtags_only_beyond_sixty(self):
        tags = " ".join(f"#tag{i}" for i in range(20))
        proc, result = self.uncapped(f"{BODY}\n\n#Ad\n\n{tags}", "--platform", "shorts")
        self.assertNotIn("hashtag_limit", {i["check"] for i in result["issues"]})
        tags = " ".join(f"#tag{i}" for i in range(60))
        proc, result = self.uncapped(f"{BODY}\n\n#Ad\n\n{tags}", "--platform", "shorts")
        self.assertIn("hashtag_limit", self.failed(result))

    def test_reels_caption_over_2200_characters_fails(self):
        long_body = BODY + " " + "Clean gunplay all match. " * 90
        proc, result = self.check(f"{long_body}\n\n#Ad\n\n#ModernWarfare4 #MW4Beta #CallOfDuty", "--platform", "reels")
        self.assertVerdict(proc, result, "FAIL")
        self.assertIn("caption_length", self.failed(result))


class CampaignVariants(unittest.TestCase):
    """Placement rules that differ between real-style briefs (fixtures: handoff/mimo2/test_briefs)."""

    NEON = "Race through the neon — Neon Drift launches September 14th"

    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="caption-variants-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def check(self, caption, **caption_rules):
        rules = {"required_phrases": [self.NEON], "required_tags": ["@neondriftgame", "@velocitydynamics"],
                 "disclosure": {"options": ["#Sponsored"]}, "max_extra_hashtags": 0, "language": "en"}
        for k, v in caption_rules.items():
            if k in ("position", "own_line", "after_phrase", "only_one", "options"):
                rules["disclosure"][k] = v
            else:
                rules[k] = v
        camp = os.path.join(self.d, "campaign.json")
        with open(camp, "w") as f:
            json.dump({"caption": rules}, f)
        cap, out = os.path.join(self.d, "caption.txt"), os.path.join(self.d, "result.json")
        with open(cap, "w") as f:
            f.write(caption)
        proc = subprocess.run([sys.executable, SCRIPT, cap, "--campaign", camp, "--json", out], capture_output=True, text=True)
        with open(out) as f:
            result = json.load(f)
        return {i["check"] for i in result["issues"] if i["level"] == "FAIL"}, result

    def test_disclosure_as_the_very_first_word_passes_when_the_brief_asks_for_it(self):
        failed, result = self.check(f"#Sponsored {self.NEON}. That last corner.\n\n@neondriftgame @velocitydynamics",
                                    position="start")
        self.assertEqual(failed, set(), result["issues"])

    def test_disclosure_not_at_the_start_fails_when_the_brief_asks_for_it(self):
        failed, _ = self.check(f"{self.NEON}. That last corner.\n\n#Sponsored\n\n@neondriftgame @velocitydynamics",
                               position="start")
        self.assertIn("disclosure_position", failed)

    def test_inline_disclosure_passes_when_the_brief_does_not_require_its_own_line(self):
        failed, result = self.check(f"{self.NEON} #Sponsored @neondriftgame @velocitydynamics", own_line=False)
        self.assertEqual(failed, set(), result["issues"])

    def test_second_disclosure_fails_when_only_one_is_allowed(self):
        failed, _ = self.check(f"{self.NEON}\n#Sponsored\n#Ad\n@neondriftgame @velocitydynamics",
                               options=["#Sponsored", "#Ad"], only_one=True, max_extra_hashtags=3)
        self.assertIn("disclosure_only_one", failed)

    def test_disclosure_must_follow_the_required_phrase_when_the_brief_says_so(self):
        ok, result = self.check(f"Clean drift. {self.NEON}\n#Sponsored\n@neondriftgame @velocitydynamics", after_phrase=True)
        self.assertEqual(ok, set(), result["issues"])
        failed, _ = self.check(f"{self.NEON}. Clean drift.\n#Sponsored\n@neondriftgame @velocitydynamics", after_phrase=True)
        self.assertIn("disclosure_after_phrase", failed)

    def test_tags_at_the_end_pass_and_tags_elsewhere_fail_when_required_at_the_end(self):
        ok, result = self.check(f"{self.NEON}\n\n#Sponsored\n\n@neondriftgame @velocitydynamics", tags_position="end")
        self.assertEqual(ok, set(), result["issues"])
        failed, _ = self.check(f"@neondriftgame @velocitydynamics {self.NEON}\n\n#Sponsored", tags_position="end")
        self.assertIn("tags_position", failed)

    def test_tags_first_pass_and_tags_later_fail_when_required_at_the_start(self):
        ok, result = self.check(f"@velocitydynamics @neondriftgame {self.NEON}\n\n#Sponsored", tags_position="start")
        self.assertEqual(ok, set(), result["issues"])
        failed, _ = self.check(f"{self.NEON} @neondriftgame @velocitydynamics\n\n#Sponsored", tags_position="start")
        self.assertIn("tags_position", failed)


if __name__ == "__main__":
    unittest.main()
