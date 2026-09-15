"""Black-box tests for init_tracker.py and log_post.py against the MW4 campaign example.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_campaign_tracker.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from openpyxl import load_workbook

INIT_SCRIPT = os.environ.get("INIT_TRACKER_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/campaign-tracker/scripts/init_tracker.py")
LOG_SCRIPT = os.environ.get("LOG_POST_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/campaign-tracker/scripts/log_post.py")

CAMPAIGN = {
    "name": "Test Campaign",
    "platforms": ["tiktok"],
    "posting": {"min_days_live": 30, "likes_visible": True, "max_reposts": 2, "paid_boosting": False,
                "min_engagement_rate": 0.002},
}

TMP = None
CAMP_PATH = None


def setUpModule():
    global TMP, CAMP_PATH
    TMP = tempfile.mkdtemp(prefix="tracker-test-")
    CAMP_PATH = os.path.join(TMP, "campaign.json")
    with open(CAMP_PATH, "w") as f:
        json.dump(CAMPAIGN, f)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def init_tracker(*args):
    return subprocess.run([sys.executable, INIT_SCRIPT, *args], capture_output=True, text=True)


def log_post(*args):
    return subprocess.run([sys.executable, LOG_SCRIPT, *args], capture_output=True, text=True)


class InitTracker(unittest.TestCase):
    def test_creates_a_workbook_with_posts_and_campaign_sheets(self):
        out = os.path.join(TMP, "t1.xlsx")
        r = init_tracker("--campaign", CAMP_PATH, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        wb = load_workbook(out)
        self.assertEqual(wb.sheetnames, ["Posts", "Campaign"])
        self.assertEqual([c.value for c in wb["Posts"][1]],
                         ["Clip ID", "Platform", "URL", "Posted Date", "Live-Until Date", "Views",
                          "Likes", "Engagement Rate", "Min Required", "Status", "Notes"])

    def test_campaign_sheet_carries_the_posting_rules(self):
        out = os.path.join(TMP, "t2.xlsx")
        init_tracker("--campaign", CAMP_PATH, "--out", out)
        info = {row[0]: row[1] for row in load_workbook(out)["Campaign"].iter_rows(values_only=True)}
        self.assertEqual(info["Min days live"], 30)
        self.assertEqual(info["Max reposts of the same clip"], 2)
        self.assertEqual(info["Min engagement rate"], 0.002)

    def test_refuses_to_overwrite_without_force(self):
        out = os.path.join(TMP, "t3.xlsx")
        init_tracker("--campaign", CAMP_PATH, "--out", out)
        r = init_tracker("--campaign", CAMP_PATH, "--out", out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stderr)

    def test_force_overwrites(self):
        out = os.path.join(TMP, "t4.xlsx")
        init_tracker("--campaign", CAMP_PATH, "--out", out)
        r = init_tracker("--campaign", CAMP_PATH, "--out", out, "--force")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_campaign_file_fails(self):
        r = init_tracker("--campaign", os.path.join(TMP, "nope.json"), "--out", os.path.join(TMP, "t5.xlsx"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)


class LogPost(unittest.TestCase):
    def setUp(self):
        self.tracker = os.path.join(TMP, f"tracker_{self._testMethodName}.xlsx")
        init_tracker("--campaign", CAMP_PATH, "--out", self.tracker)

    def row(self, n=2):
        return list(load_workbook(self.tracker)["Posts"][n])

    def test_logs_a_row_with_correct_formulas(self):
        r = log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c1",
                     "--platform", "tiktok", "--url", "https://x.test/1", "--posted", "2026-01-01",
                     "--views", "1000", "--likes", "5")
        self.assertEqual(r.returncode, 0, r.stderr)
        vals = [c.value for c in self.row()]
        self.assertEqual(vals[0], "c1")
        self.assertEqual(vals[4], "=D2+30")
        self.assertEqual(vals[5], 1000)
        self.assertEqual(vals[6], 5)
        self.assertEqual(vals[7], '=IFERROR(G2/F2,"")')
        self.assertEqual(vals[8], 0.002)
        self.assertEqual(vals[9], '=IF(F2=0,"pending",IF(H2>=I2,"PASS","FAIL"))')

    def test_zero_views_still_logs_with_pending_status_formula(self):
        r = log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c1",
                     "--platform", "tiktok", "--url", "https://x.test/1", "--posted", "2026-01-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        vals = [c.value for c in self.row()]
        self.assertEqual(vals[5], 0)
        self.assertEqual(vals[9], '=IF(F2=0,"pending",IF(H2>=I2,"PASS","FAIL"))')

    def test_second_row_appends_not_overwrites(self):
        log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c1",
                 "--platform", "tiktok", "--url", "u1", "--posted", "2026-01-01")
        log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c2",
                 "--platform", "tiktok", "--url", "u2", "--posted", "2026-01-02")
        posts = load_workbook(self.tracker)["Posts"]
        self.assertEqual(posts.max_row, 3)
        self.assertEqual(posts.cell(2, 1).value, "c1")
        self.assertEqual(posts.cell(3, 1).value, "c2")

    def test_warns_but_does_not_block_past_max_reposts(self):
        # max_reposts is 2: posting c1 a 1st and 2nd time is within the limit and must NOT warn;
        # only the 3rd+ posting exceeds it. Checking every call's stderr individually (not just
        # the last) matters - a too-eager warning on the 2nd post is a real off-by-one to catch.
        results = []
        for i in range(3):
            results.append(log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c1",
                                    "--platform", "tiktok", "--url", "u", "--posted", f"2026-01-0{i + 1}"))
        for r in results:
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("warning", results[0].stderr)
        self.assertNotIn("warning", results[1].stderr)
        self.assertIn("logged 3 time(s)", results[2].stderr)
        self.assertEqual(load_workbook(self.tracker)["Posts"].max_row, 4)

    def test_missing_tracker_fails(self):
        r = log_post("--tracker", os.path.join(TMP, "nope.xlsx"), "--campaign", CAMP_PATH,
                     "--clip-id", "c1", "--platform", "tiktok", "--url", "u", "--posted", "2026-01-01")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_bad_date_fails(self):
        r = log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c1",
                     "--platform", "tiktok", "--url", "u", "--posted", "01/01/2026")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("bad --posted", r.stderr)

    def test_negative_views_fails(self):
        r = log_post("--tracker", self.tracker, "--campaign", CAMP_PATH, "--clip-id", "c1",
                     "--platform", "tiktok", "--url", "u", "--posted", "2026-01-01", "--views", "-1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("negative", r.stderr)

    def test_non_tracker_workbook_is_rejected(self):
        from openpyxl import Workbook
        bad = os.path.join(TMP, "bad.xlsx")
        Workbook().save(bad)
        r = log_post("--tracker", bad, "--campaign", CAMP_PATH, "--clip-id", "c1",
                     "--platform", "tiktok", "--url", "u", "--posted", "2026-01-01")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no \"Posts\" sheet", r.stderr)


if __name__ == "__main__":
    unittest.main()
