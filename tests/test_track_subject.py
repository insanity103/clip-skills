"""Tests for track_subject.py.

Covers everything except the actual SAM 2 video predictor call: frame extraction, per-frame bbox
math, the smoothing/keyframe-downsampling that builds crop_track.json, and mask writing - all against
synthetic mask/center data standing in for real SAM 2 propagation output. Running SAM 2 needs torch
and a downloaded checkpoint, neither of which belong in this test suite - see SKILL.md.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_track_subject.py' -v
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

SCRIPT = os.environ.get("TRACK_SUBJECT_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-subject-tracker/scripts/track_subject.py")

spec = importlib.util.spec_from_file_location("track_subject", SCRIPT)
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

TMP = None
CLIP = None


def setUpModule():
    global TMP, CLIP
    TMP = tempfile.mkdtemp(prefix="track-test-")
    CLIP = os.path.join(TMP, "clip.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi",
                    "-i", "testsrc2=s=640x1136:r=30:d=1", CLIP], check=True)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class ProbeAndExtract(unittest.TestCase):
    def test_probe_fps_reads_the_real_rate(self):
        self.assertAlmostEqual(ts.probe_fps(CLIP), 30.0, delta=0.5)

    def test_extract_frames_writes_zero_indexed_jpegs(self):
        out_dir = os.path.join(TMP, "frames1")
        n = ts.extract_frames(CLIP, 0.0, 1.0, out_dir)
        self.assertGreaterEqual(n, 25)
        self.assertTrue(os.path.exists(os.path.join(out_dir, "00000.jpg")))

    def test_extract_frames_of_a_missing_clip_fails(self):
        with self.assertRaises(SystemExit):
            ts.extract_frames(os.path.join(TMP, "nope.mp4"), 0, 1, os.path.join(TMP, "frames2"))


class BboxCenter(unittest.TestCase):
    def test_center_of_a_known_box(self):
        mask = np.zeros((100, 200), dtype=bool)
        mask[40:60, 80:120] = True  # x in [80,119], y in [40,59]
        cx, cy = ts.bbox_center(mask)
        self.assertAlmostEqual(cx, 99.5, delta=1)
        self.assertAlmostEqual(cy, 49.5, delta=1)

    def test_empty_mask_returns_none(self):
        self.assertIsNone(ts.bbox_center(np.zeros((10, 10), dtype=bool)))


class SmoothAndKeyframe(unittest.TestCase):
    def test_linear_motion_produces_an_increasing_offset_track(self):
        centers = [100 + (500 - 100) * i / 29 for i in range(30)]
        track = ts.smooth_and_keyframe(centers, fps=30, interval=0.4, source_w=1000, window=1)
        self.assertEqual(track[0]["t"], 0.0)
        self.assertAlmostEqual(track[0]["x"], 100 - 500, delta=2)   # offset = center - source_w/2
        self.assertAlmostEqual(track[-1]["x"], 500 - 500, delta=2)
        self.assertEqual([p["t"] for p in track], sorted(p["t"] for p in track))

    def test_keyframes_are_spaced_by_roughly_the_requested_interval(self):
        centers = [300.0] * 60  # static subject, 2s at 30fps
        track = ts.smooth_and_keyframe(centers, fps=30, interval=0.5, source_w=1000, window=1)
        gaps = [b["t"] - a["t"] for a, b in zip(track, track[1:])]
        for g in gaps[:-1]:  # the final gap can be short (snapped to the last frame)
            self.assertAlmostEqual(g, 0.5, delta=0.05)

    def test_a_lost_frame_holds_the_last_known_position(self):
        centers = [100.0, 100.0, None, None, 300.0]
        track = ts.smooth_and_keyframe(centers, fps=1, interval=1, source_w=1000, window=1)
        self.assertEqual(track[2]["x"], round(100 - 500))

    def test_track_output_shape_matches_what_render_vertical_expects(self):
        track = ts.smooth_and_keyframe([500.0, 500.0], fps=30, interval=0.4, source_w=1000, window=1)
        for p in track:
            self.assertEqual(set(p.keys()), {"t", "x"})
            self.assertIsInstance(p["t"], float)
            self.assertIsInstance(p["x"], int)

    def test_empty_input_fails(self):
        with self.assertRaises(SystemExit):
            ts.smooth_and_keyframe([], fps=30, interval=0.4, source_w=1000)


class WriteMasks(unittest.TestCase):
    def test_writes_one_binary_png_per_mask_in_order(self):
        masks = [np.zeros((10, 10), dtype=bool) for _ in range(3)]
        masks[1][2:5, 2:5] = True
        out_dir = os.path.join(TMP, "masks1")
        ts.write_masks(masks, out_dir)
        files = sorted(os.listdir(out_dir))
        self.assertEqual(files, ["frame_00000.png", "frame_00001.png", "frame_00002.png"])
        m1 = np.array(Image.open(os.path.join(out_dir, "frame_00001.png")))
        self.assertEqual(m1[3, 3], 255)
        self.assertEqual(m1[0, 0], 0)


class CliValidation(unittest.TestCase):
    def test_missing_clip_fails(self):
        out = run(["--clip", os.path.join(TMP, "nope.mp4"), "--start", "0", "--dur", "2",
                   "--checkpoint", "x.pt", "--model-cfg", "x.yaml", "--point", "1,2",
                   "--out-dir", os.path.join(TMP, "o1")])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("not found", out.stderr)

    def test_needs_a_point_or_a_box(self):
        out = run(["--clip", CLIP, "--start", "0", "--dur", "1", "--checkpoint", "x.pt",
                   "--model-cfg", "x.yaml", "--out-dir", os.path.join(TMP, "o2")])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--point or a --box", out.stderr)

    def test_non_positive_duration_fails(self):
        out = run(["--clip", CLIP, "--start", "0", "--dur", "0", "--checkpoint", "x.pt",
                   "--model-cfg", "x.yaml", "--point", "1,2", "--out-dir", os.path.join(TMP, "o3")])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--dur must be positive", out.stderr)

    def test_more_labels_than_points_fails(self):
        out = run(["--clip", CLIP, "--start", "0", "--dur", "1", "--checkpoint", "x.pt",
                   "--model-cfg", "x.yaml", "--point", "1,2", "--label", "1", "--label", "0",
                   "--out-dir", os.path.join(TMP, "o4")])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("more --label than --point", out.stderr)


if __name__ == "__main__":
    unittest.main()
