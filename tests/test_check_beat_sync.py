"""Tests for check_beat_sync.py against a hand-built grid (no need to regenerate one via
find_beat_grid.py - this script only reads the grid's "grid" list and "bpm"/"confidence" fields).

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_check_beat_sync.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.environ.get("CHECK_BEAT_SYNC_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-beat-sync/scripts/check_beat_sync.py")

TMP = None
GRID_PATH = None
GRID = {"bpm": 120.0, "period_s": 0.5, "confidence": 0.95, "anchor_s": 0.5,
       "grid": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]}


def setUpModule():
    global TMP, GRID_PATH
    TMP = tempfile.mkdtemp(prefix="beatsync-test-")
    GRID_PATH = os.path.join(TMP, "grid.json")
    with open(GRID_PATH, "w") as f:
        json.dump(GRID, f)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class CheckBeatSync(unittest.TestCase):
    def test_exact_hit_has_zero_offset_and_is_on_beat(self):
        r = run(["--grid", GRID_PATH, "--times", "1.0", "--out", os.path.join(TMP, "r1.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.load(open(os.path.join(TMP, "r1.json")))
        self.assertEqual(report["rows"][0]["offset_ms"], 0.0)
        self.assertTrue(report["rows"][0]["on_beat"])

    def test_offset_direction_is_signed_early_vs_late(self):
        r = run(["--grid", GRID_PATH, "--times", "0.95,1.05", "--out", os.path.join(TMP, "r2.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.load(open(os.path.join(TMP, "r2.json")))["rows"]
        self.assertLess(rows[0]["offset_ms"], 0)   # 0.95 is BEFORE the 1.0 beat -> early -> negative
        self.assertGreater(rows[1]["offset_ms"], 0)  # 1.05 is AFTER it -> late -> positive

    def test_tolerance_boundary(self):
        r = run(["--grid", GRID_PATH, "--times", "1.05,1.07", "--tolerance-ms", "60",
                "--out", os.path.join(TMP, "r3.json")])
        rows = json.load(open(os.path.join(TMP, "r3.json")))["rows"]
        self.assertTrue(rows[0]["on_beat"])    # 50ms offset, within 60ms
        self.assertFalse(rows[1]["on_beat"])   # 70ms offset, outside 60ms

    def test_times_file_with_labels_are_echoed_back(self):
        times_file = os.path.join(TMP, "times.json")
        with open(times_file, "w") as f:
            json.dump([{"t": 1.0, "label": "cut1"}, {"t": 2.0, "label": "gunshot1"}], f)
        r = run(["--grid", GRID_PATH, "--times-file", times_file, "--out", os.path.join(TMP, "r4.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.load(open(os.path.join(TMP, "r4.json")))["rows"]
        self.assertEqual([row["label"] for row in rows], ["cut1", "gunshot1"])

    def test_times_file_with_bare_numbers_works_too(self):
        times_file = os.path.join(TMP, "times2.json")
        with open(times_file, "w") as f:
            json.dump([1.0, 2.5], f)
        r = run(["--grid", GRID_PATH, "--times-file", times_file, "--out", os.path.join(TMP, "r5.json")])
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.load(open(os.path.join(TMP, "r5.json")))["rows"]
        self.assertEqual([row["t"] for row in rows], [1.0, 2.5])

    def test_summary_counts_on_beat_correctly(self):
        r = run(["--grid", GRID_PATH, "--times", "1.0,1.5,1.8", "--tolerance-ms", "60"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("2/3 within 60ms", r.stdout)

    def test_off_beat_never_causes_a_nonzero_exit(self):
        # landing off the beat is a creative fact to report, not an error to gate on
        r = run(["--grid", GRID_PATH, "--times", "1.25,1.75,2.25"])  # all exactly mid-beat
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_grid_fails(self):
        r = run(["--grid", os.path.join(TMP, "nope.json"), "--times", "1.0"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_missing_times_file_fails(self):
        r = run(["--grid", GRID_PATH, "--times-file", os.path.join(TMP, "nope.json")])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_bad_times_format_fails(self):
        r = run(["--grid", GRID_PATH, "--times", "not,numbers"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("bad --times", r.stderr)

    def test_non_positive_tolerance_fails(self):
        r = run(["--grid", GRID_PATH, "--times", "1.0", "--tolerance-ms", "0"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--tolerance-ms", r.stderr)

    def test_grid_with_no_grid_points_fails(self):
        bad_grid = os.path.join(TMP, "bad_grid.json")
        with open(bad_grid, "w") as f:
            json.dump({"bpm": 120}, f)
        r = run(["--grid", bad_grid, "--times", "1.0"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no \"grid\" points", r.stderr)


if __name__ == "__main__":
    unittest.main()
