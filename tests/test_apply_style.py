"""Black-box tests for apply_style.py against a synthetic clip with distinct diagonal features
(so an echo offset is visible as a duplicate line, not lost in solid color).

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_apply_style.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPT = os.environ.get("APPLY_STYLE_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-stylizer/scripts/apply_style.py")

TMP = None
CLIP = None  # 1080x1920, 3s, a white diagonal line on black, plus a sine tone
SILENT_CLIP = None


def setUpModule():
    global TMP, CLIP, SILENT_CLIP
    TMP = tempfile.mkdtemp(prefix="style-test-")
    CLIP = os.path.join(TMP, "clip.mp4")
    SILENT_CLIP = os.path.join(TMP, "silent.mp4")
    ffmpeg("-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=3",
           "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
           "-filter_complex", "[0:v]drawgrid=w=2:h=1920:t=6:c=white@1.0[v]",
           "-map", "[v]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", CLIP)
    ffmpeg("-f", "lavfi", "-i", "color=c=gray:s=1080x1920:r=30:d=2",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", SILENT_CLIP)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def run(args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


def frame_at(path, t, out_png):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", path, "-frames:v", "1", out_png], check=True)


class ApplyStyle(unittest.TestCase):
    def test_default_run_produces_valid_output(self):
        out = os.path.join(TMP, "default.mp4")
        r = run(["--clip", CLIP, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        info = ffprobe(out)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        a = next(s for s in info["streams"] if s["codec_type"] == "audio")
        self.assertEqual((v["width"], v["height"]), (1080, 1920))
        self.assertEqual(a["codec_name"], "aac")

    def test_echo_shifts_bright_pixels_downward(self):
        # a horizontal bright band near the top should also show a dimmer echo further down,
        # roughly at top_band_y + echo_offset_fraction * height.
        band_clip = os.path.join(TMP, "band.mp4")
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=200x400:r=10:d=1",
               "-vf", "drawbox=x=0:y=20:w=200:h=10:color=white:t=fill", band_clip)
        out = os.path.join(TMP, "band_styled.mp4")
        r = run(["--clip", band_clip, "--echo-opacity", "0.5", "--posterize", "0",
                 "--saturation", "1.0", "--contrast", "1.0", "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        png = os.path.join(TMP, "band_frame.png")
        frame_at(out, 0, png)
        img = Image.open(png).convert("L")
        col = [img.getpixel((100, y)) for y in range(img.height)]
        bright_rows = [y for y, v in enumerate(col) if v > 60]
        # original band around y=20-30, echo band around y=20+0.27*400=128 to ~138
        self.assertTrue(any(15 <= y <= 35 for y in bright_rows), "original band missing")
        self.assertTrue(any(115 <= y <= 150 for y in bright_rows), "echoed band missing")

    def test_echo_disabled_removes_the_duplicate(self):
        band_clip = os.path.join(TMP, "band2.mp4")
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=200x400:r=10:d=1",
               "-vf", "drawbox=x=0:y=20:w=200:h=10:color=white:t=fill", band_clip)
        out = os.path.join(TMP, "band2_styled.mp4")
        r = run(["--clip", band_clip, "--echo-opacity", "0", "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        png = os.path.join(TMP, "band2_frame.png")
        frame_at(out, 0, png)
        img = Image.open(png).convert("L")
        col = [img.getpixel((100, y)) for y in range(img.height)]
        bright_rows = [y for y, v in enumerate(col) if v > 60]
        self.assertTrue(any(15 <= y <= 35 for y in bright_rows), "original band missing")
        self.assertFalse(any(115 <= y <= 150 for y in bright_rows), "echo should be off")

    def test_audio_passthrough_when_present(self):
        out = os.path.join(TMP, "audio_check.mp4")
        r = run(["--clip", CLIP, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any(s["codec_type"] == "audio" for s in ffprobe(out)["streams"]))

    def test_silent_clip_has_no_audio_stream_in_output(self):
        out = os.path.join(TMP, "silent_out.mp4")
        r = run(["--clip", SILENT_CLIP, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(any(s["codec_type"] == "audio" for s in ffprobe(out)["streams"]))

    def test_all_neutral_options_fails(self):
        out = os.path.join(TMP, "bad1.mp4")
        r = run(["--clip", CLIP, "--echo-opacity", "0", "--posterize", "0",
                 "--saturation", "1.0", "--contrast", "1.0", "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing to apply", r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_bad_echo_opacity_fails(self):
        out = os.path.join(TMP, "bad2.mp4")
        r = run(["--clip", CLIP, "--echo-opacity", "1.5", "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--echo-opacity", r.stderr)

    def test_bad_posterize_fails(self):
        out = os.path.join(TMP, "bad3.mp4")
        r = run(["--clip", CLIP, "--posterize", "500", "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--posterize", r.stderr)

    def test_missing_clip_fails(self):
        out = os.path.join(TMP, "bad4.mp4")
        r = run(["--clip", os.path.join(TMP, "nope.mp4"), "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_leaves_no_partial_file_on_failure(self):
        out = os.path.join(TMP, "partial_check.mp4")
        run(["--clip", os.path.join(TMP, "nope.mp4"), "--out", out])
        self.assertFalse(os.path.exists(out))
        self.assertFalse(os.path.exists(out.replace(".mp4", ".partial.mp4")))


if __name__ == "__main__":
    unittest.main()
