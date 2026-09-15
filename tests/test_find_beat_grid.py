"""Tests for find_beat_grid.py against a fully-controlled synthetic click track (exact 120 BPM,
not an ffmpeg filter approximation - a filter-generated "click track" turned out not to be clean
enough to trust as ground truth, see the mutation/verification history in this file's PR).

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_find_beat_grid.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np

SCRIPT = os.environ.get("FIND_BEAT_GRID_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-beat-sync/scripts/find_beat_grid.py")

TMP = None
CLICK_120 = None  # exact 120 BPM (0.5s period), 16s
CLICK_90 = None    # exact 90 BPM (0.667s period), 12s
SILENT = None


def setUpModule():
    global TMP, CLICK_120, CLICK_90, SILENT
    TMP = tempfile.mkdtemp(prefix="beatgrid-test-")
    CLICK_120 = os.path.join(TMP, "click120.wav")
    CLICK_90 = os.path.join(TMP, "click90.wav")
    SILENT = os.path.join(TMP, "silent.wav")
    write_click_track(CLICK_120, bpm=120, duration=16.0)
    write_click_track(CLICK_90, bpm=90, duration=12.0)
    write_click_track(SILENT, bpm=120, duration=4.0, silent=True)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def write_click_track(path, bpm, duration, sr=22050, silent=False):
    period = 60.0 / bpm
    n = int(sr * duration)
    audio = np.zeros(n, dtype=np.float32)
    if not silent:
        click_len = int(sr * 0.02)
        t_click = np.arange(click_len) / sr
        click = (np.sin(2 * np.pi * 440 * t_click) * np.hanning(click_len)).astype(np.float32)
        t = 0.0
        while t < duration:
            start = int(t * sr)
            end = min(n, start + click_len)
            audio[start:end] += click[:end - start]
            t += period
    pcm = (audio * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def run(args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class FindBeatGrid(unittest.TestCase):
    def test_recovers_exact_120_bpm_with_high_confidence(self):
        out = os.path.join(TMP, "g120.json")
        r = run(["--audio", CLICK_120, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        g = json.load(open(out))
        self.assertAlmostEqual(g["bpm"], 120.0, delta=1.0)
        self.assertGreater(g["confidence"], 0.8)

    def test_recovers_exact_90_bpm(self):
        out = os.path.join(TMP, "g90.json")
        r = run(["--audio", CLICK_90, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        g = json.load(open(out))
        self.assertAlmostEqual(g["bpm"], 90.0, delta=1.5)
        self.assertGreater(g["confidence"], 0.8)

    def test_grid_points_are_spaced_by_the_recovered_period(self):
        out = os.path.join(TMP, "g120b.json")
        run(["--audio", CLICK_120, "--out", out])
        g = json.load(open(out))
        gaps = [b - a for a, b in zip(g["grid"], g["grid"][1:])]
        for gap in gaps:
            self.assertAlmostEqual(gap, g["period_s"], delta=0.01)

    def test_window_start_end_is_recorded_and_respected(self):
        out = os.path.join(TMP, "g120c.json")
        r = run(["--audio", CLICK_120, "--start", "2", "--end", "10", "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        g = json.load(open(out))
        self.assertEqual(g["window"], [2.0, 10.0])
        self.assertAlmostEqual(g["bpm"], 120.0, delta=1.5)

    def test_silent_audio_fails_cleanly(self):
        out = os.path.join(TMP, "gsilent.json")
        r = run(["--audio", SILENT, "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("silent", r.stderr)

    def test_missing_source_fails(self):
        r = run(["--audio", os.path.join(TMP, "nope.wav"), "--out", os.path.join(TMP, "x.json")])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_bad_bpm_range_fails(self):
        out = os.path.join(TMP, "gbad.json")
        r = run(["--audio", CLICK_120, "--min-bpm", "150", "--max-bpm", "100", "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--max-bpm", r.stderr)

    def test_end_before_start_fails(self):
        out = os.path.join(TMP, "gbad2.json")
        r = run(["--audio", CLICK_120, "--start", "5", "--end", "2", "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--end must be after --start", r.stderr)

    def test_extracts_from_a_video_clip_not_just_bare_audio(self):
        clip = os.path.join(TMP, "clip.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi",
                        "-i", "testsrc2=s=320x568:r=15:d=16", "-i", CLICK_120,
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", clip], check=True)
        out = os.path.join(TMP, "gclip.json")
        r = run(["--clip", clip, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        g = json.load(open(out))
        self.assertAlmostEqual(g["bpm"], 120.0, delta=1.5)


if __name__ == "__main__":
    unittest.main()
