"""Black-box tests for pick_cover.py: a clip with a sharp half and a heavily blurred half should
only ever yield candidates from the sharp half.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_pick_cover.py' -v
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.environ.get("PICK_COVER_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-cover-picker/scripts/pick_cover.py")

TMP = None
CLIP = None  # 0-5s sharp testsrc2, 5-10s the same source heavily boxblurred


def setUpModule():
    global TMP, CLIP
    TMP = tempfile.mkdtemp(prefix="cover-test-")
    sharp, blurry, listfile = (os.path.join(TMP, n) for n in ("sharp.mp4", "blurry.mp4", "list.txt"))
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x1136:r=30:d=5", "-c:v", "libx264", "-preset", "ultrafast",
           "-pix_fmt", "yuv420p", sharp)
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x1136:r=30:d=5", "-vf", "boxblur=20:1", "-c:v", "libx264",
           "-preset", "ultrafast", "-pix_fmt", "yuv420p", blurry)
    with open(listfile, "w") as f:
        f.write(f"file '{sharp}'\nfile '{blurry}'\n")
    CLIP = os.path.join(TMP, "clip.mp4")
    ffmpeg("-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", CLIP)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


def run(args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class PickCover(unittest.TestCase):
    def test_all_candidates_come_from_the_sharp_half(self):
        out = os.path.join(TMP, "covers1")
        r = run([CLIP, "--out-dir", out, "--top", "5", "--fps", "4", "--min-gap", "0.5"])
        self.assertEqual(r.returncode, 0, r.stderr)
        files = sorted(glob.glob(os.path.join(out, "cover_*.png")))
        self.assertEqual(len(files), 5)
        for f in files:
            t = float(os.path.basename(f)[len("cover_"):-len("s.png")])
            self.assertLess(t, 5.0, f"{f} should come from the sharp (0-5s) half")

    def test_min_gap_is_respected(self):
        out = os.path.join(TMP, "covers2")
        r = run([CLIP, "--out-dir", out, "--top", "5", "--fps", "8", "--min-gap", "2.0"])
        self.assertEqual(r.returncode, 0, r.stderr)
        times = sorted(float(os.path.basename(f)[len("cover_"):-len("s.png")])
                       for f in glob.glob(os.path.join(out, "cover_*.png")))
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual(b - a, 2.0 - 1e-6)

    def test_window_restricted_to_blurry_half_still_returns_best_effort(self):
        out = os.path.join(TMP, "covers3")
        r = run([CLIP, "--out-dir", out, "--start", "5", "--end", "10", "--top", "2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        files = glob.glob(os.path.join(out, "cover_*.png"))
        self.assertEqual(len(files), 2)
        for f in files:
            t = float(os.path.basename(f)[len("cover_"):-len("s.png")])
            self.assertGreaterEqual(t, 5.0)

    def test_missing_clip_fails(self):
        r = run([os.path.join(TMP, "nope.mp4"), "--out-dir", os.path.join(TMP, "covers4")])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_start_after_end_fails(self):
        r = run([CLIP, "--out-dir", os.path.join(TMP, "covers5"), "--start", "8", "--end", "3"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("outside the clip", r.stderr)

    def test_start_beyond_duration_fails(self):
        r = run([CLIP, "--out-dir", os.path.join(TMP, "covers6"), "--start", "50"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("outside the clip", r.stderr)


if __name__ == "__main__":
    unittest.main()
