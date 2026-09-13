"""Black-box tests for render_vertical.py against synthetic sources with hand-computed geometry.

Banded source, 1920x1080 @ 30 fps, 6 s, mono 44.1 kHz tone:
  x    0-655   blue
  x  656-1263  centre band: lime 0-2 s, magenta 2-4 s, yellow 4-6 s; black stripe at x 950-969
  x 1264-1919  red
The centred 9:16 crop of a 1080-high frame is 608 px wide starting at x=656, i.e. exactly the centre
band. Scaled to 1080 wide (x1.7763) the stripe lands at output x ~522-558 when there is no zoom.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -v
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from PIL import Image, ImageDraw

SCRIPT = os.environ.get("RENDER_VERTICAL_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/vertical-clip-renderer/scripts/render_vertical.py")

PALETTE = {"lime": (0, 255, 0), "magenta": (255, 0, 255), "yellow": (255, 255, 0), "blue": (0, 0, 255),
           "red": (255, 0, 0), "white": (255, 255, 255), "black": (0, 0, 0)}

TMP = None


def setUpModule():
    global TMP
    TMP = tempfile.mkdtemp(prefix="rv-test-")
    make_banded_source(os.path.join(TMP, "banded.mp4"))
    make_tall_portrait_source(os.path.join(TMP, "tall.mp4"))
    make_silent_source(os.path.join(TMP, "silent.mp4"))
    make_overlay(os.path.join(TMP, "overlay.png"))


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


def make_banded_source(path):
    ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=656x1080:r=30:d=6",
           "-f", "lavfi", "-i", "color=c=red:s=656x1080:r=30:d=6",
           "-f", "lavfi", "-i", "color=c=lime:s=608x1080:r=30:d=2",
           "-f", "lavfi", "-i", "color=c=magenta:s=608x1080:r=30:d=2",
           "-f", "lavfi", "-i", "color=c=yellow:s=608x1080:r=30:d=2",
           "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=6",
           "-filter_complex",
           "[2:v][3:v][4:v]concat=n=3:v=1:a=0,drawbox=x=294:y=0:w=20:h=1080:color=black:t=fill[c];"
           "[0:v][c][1:v]hstack=inputs=3,format=yuv420p[v]",
           "-map", "[v]", "-map", "5:a", "-c:v", "libx264", "-preset", "ultrafast", "-g", "15",
           "-c:a", "aac", "-ac", "1", path)


def make_tall_portrait_source(path):
    # 540x1200: black 0-99, red 100-599, blue 600-1099, black 1100-1199.
    # A centred 9:16 crop is 540x960 from y=120, so the black bars must not appear.
    ffmpeg("-f", "lavfi", "-i", "color=c=black:s=540x100:r=30:d=2",
           "-f", "lavfi", "-i", "color=c=red:s=540x500:r=30:d=2",
           "-f", "lavfi", "-i", "color=c=blue:s=540x500:r=30:d=2",
           "-f", "lavfi", "-i", "color=c=black:s=540x100:r=30:d=2",
           "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:duration=2",
           "-filter_complex", "[0:v][1:v][2:v][3:v]vstack=inputs=4,format=yuv420p[v]",
           "-map", "[v]", "-map", "4:a", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", path)


def make_silent_source(path):
    ffmpeg("-f", "lavfi", "-i", "color=c=lime:s=1920x1080:r=30:d=2",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", path)


def make_overlay(path):
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle([60, 1400, 259, 1599], fill=(255, 255, 255, 255))
    img.save(path)


def render(*args, cwd=None):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, cwd=cwd)


def streams(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def frame_at(video, t):
    out = os.path.join(TMP, f"frame-{os.getpid()}-{abs(hash((video, t)))}.png")
    ffmpeg("-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", out)
    img = Image.open(out).convert("RGB")
    img.load()
    os.remove(out)
    return img


def stripe_width(img, y=960):
    """Width of the dark run through the horizontal centre."""
    lum = [sum(img.getpixel((x, y))) / 3 for x in range(img.width)]
    x = img.width // 2
    if lum[x] >= 80:
        return 0
    lo, hi = x, x
    while lo > 0 and lum[lo - 1] < 80:
        lo -= 1
    while hi < img.width - 1 and lum[hi + 1] < 80:
        hi += 1
    return hi - lo + 1


class Asserts(unittest.TestCase):
    def assertRendered(self, proc, path):
        self.assertEqual(proc.returncode, 0, f"render failed:\n{proc.stderr[-1500:]}")
        self.assertTrue(os.path.exists(path), f"no output at {path}")

    def assertColor(self, img, xy, name):
        px = img.getpixel(xy)[:3]
        nearest = min(PALETTE, key=lambda k: sum((a - b) ** 2 for a, b in zip(PALETTE[k], px)))
        dist = sum((a - b) ** 2 for a, b in zip(PALETTE[name], px)) ** 0.5
        self.assertTrue(nearest == name and dist < 90, f"pixel {xy} is {px} (nearest {nearest}), expected {name}")


class RenderBandedTwoBeats(Asserts):
    """Beats out of chronological order: source 4-5 s (yellow) then 0-1 s (lime), no zoom, with overlay."""

    @classmethod
    def setUpClass(cls):
        cls.out = os.path.join(TMP, "two_beats.mp4")
        cls.proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "4:1,0:1",
                          "--overlay", os.path.join(TMP, "overlay.png"), "--zoom", "0",
                          "--quality", "draft", "--out", cls.out)

    def setUp(self):
        self.assertRendered(self.proc, self.out)

    def test_output_is_portrait_1080x1920(self):
        v = next(s for s in streams(self.out)["streams"] if s["codec_type"] == "video")
        self.assertEqual((v["width"], v["height"]), (1080, 1920))

    def test_keeps_source_frame_rate_with_exact_frame_count(self):
        v = next(s for s in streams(self.out)["streams"] if s["codec_type"] == "video")
        self.assertEqual(v["avg_frame_rate"], "30/1")
        self.assertEqual(int(v["nb_frames"]), 60)

    def test_audio_is_48k_stereo_aac_spanning_the_clip(self):
        a = next((s for s in streams(self.out)["streams"] if s["codec_type"] == "audio"), None)
        self.assertIsNotNone(a, "no audio stream")
        self.assertEqual((a["codec_name"], int(a["sample_rate"]), a["channels"]), ("aac", 48000, 2))
        self.assertAlmostEqual(float(a["duration"]), 2.0, delta=0.1)

    def test_footage_fills_the_frame_top_to_bottom(self):
        img = frame_at(self.out, 0.5)
        for xy in [(200, 15), (200, 960), (200, 1905), (880, 960)]:
            self.assertColor(img, xy, "yellow")

    def test_crop_is_centred_on_the_source(self):
        img = frame_at(self.out, 0.5)
        self.assertColor(img, (540, 960), "black")
        self.assertTrue(30 <= stripe_width(img) <= 42, f"stripe width {stripe_width(img)}")

    def test_beats_play_in_edl_order_from_their_own_source_times(self):
        self.assertColor(frame_at(self.out, 0.5), (200, 960), "yellow")
        self.assertColor(frame_at(self.out, 1.5), (200, 960), "lime")

    def test_overlay_is_drawn_over_every_beat(self):
        for t, under in [(0.5, "yellow"), (1.5, "lime")]:
            img = frame_at(self.out, t)
            self.assertColor(img, (160, 1500), "white")
            self.assertColor(img, (880, 1500), under)


class CropOffsets(Asserts):
    def test_x_offset_moves_the_crop_into_the_right_band(self):
        out = os.path.join(TMP, "offset_right.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1", "--x", "656",
                      "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        self.assertColor(frame_at(out, 0.5), (540, 960), "red")

    def test_offset_past_the_frame_edge_is_clamped_not_an_error(self):
        out = os.path.join(TMP, "offset_clamped.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1", "--x", "5000",
                      "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        img = frame_at(out, 0.5)
        self.assertColor(img, (40, 960), "red")
        self.assertColor(img, (1040, 960), "red")

    def test_per_beat_offset_in_the_edl_applies_to_that_beat_only(self):
        out = os.path.join(TMP, "offset_per_beat.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1:-656,0:1:656",
                      "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        self.assertColor(frame_at(out, 0.5), (540, 960), "blue")
        self.assertColor(frame_at(out, 1.5), (540, 960), "red")


class PushIn(Asserts):
    def test_push_in_magnifies_the_centre_over_the_clip(self):
        out = os.path.join(TMP, "zoom_single.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:2", "--zoom", "0.5",
                      "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        first, last = stripe_width(frame_at(out, 0.05)), stripe_width(frame_at(out, 1.95))
        self.assertTrue(first > 0 and last >= 1.3 * first, f"stripe {first}px -> {last}px")

    def test_push_in_continues_across_a_cut_instead_of_resetting(self):
        out = os.path.join(TMP, "zoom_across_cut.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1,0:1", "--zoom", "0.5",
                      "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        before, after = stripe_width(frame_at(out, 0.95)), stripe_width(frame_at(out, 1.05))
        self.assertGreaterEqual(after, before - 2, f"zoom snapped back at the cut: {before}px -> {after}px")


class OtherSourceShapes(Asserts):
    def test_source_without_audio_still_gets_an_audio_track(self):
        out = os.path.join(TMP, "from_silent.mp4")
        proc = render("--src", os.path.join(TMP, "silent.mp4"), "--edl", "0:1.5", "--zoom", "0",
                      "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        a = [s for s in streams(out)["streams"] if s["codec_type"] == "audio"]
        self.assertEqual(len(a), 1)
        self.assertAlmostEqual(float(a[0]["duration"]), 1.5, delta=0.1)

    def test_low_resolution_source_warns_that_the_clip_will_be_soft(self):
        # 640x360: the 9:16 crop is 202 px wide, a 5.3x upscale. Platforms demote blurry, low-resolution video.
        src = os.path.join(TMP, "lowres.mp4")
        ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=2", "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", src)
        out = os.path.join(TMP, "from_lowres.mp4")
        proc = render("--src", src, "--edl", "0:1", "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        self.assertIn("upscales 5.3x", proc.stderr)

    def test_fps_override_conforms_a_60fps_source_to_30(self):
        # Some briefs require 30 fps output regardless of the source rate.
        src = os.path.join(TMP, "sixty.mp4")
        ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=60:d=2", "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", src)
        out = os.path.join(TMP, "sixty_to_30.mp4")
        proc = render("--src", src, "--edl", "0:1", "--zoom", "0.05", "--fps", "30", "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        v = next(s for s in streams(out)["streams"] if s["codec_type"] == "video")
        self.assertEqual((v["avg_frame_rate"], int(v["nb_frames"])), ("30/1", 30))

    def test_1080p_source_renders_without_an_upscale_warning(self):
        out = os.path.join(TMP, "from_1080p.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1", "--zoom", "0",
                      "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        self.assertNotIn("upscales", proc.stderr)

    def test_too_tall_portrait_source_is_cropped_vertically_not_squashed(self):
        out = os.path.join(TMP, "from_tall.mp4")
        proc = render("--src", os.path.join(TMP, "tall.mp4"), "--edl", "0:1", "--zoom", "0",
                      "--quality", "draft", "--out", out)
        self.assertRendered(proc, out)
        img = frame_at(out, 0.5)
        self.assertColor(img, (540, 12), "red")
        self.assertColor(img, (540, 900), "red")
        self.assertColor(img, (540, 1020), "blue")
        self.assertColor(img, (540, 1908), "blue")


class EditFilesAndJobs(Asserts):
    def test_edit_json_resolves_paths_relative_to_itself(self):
        d = tempfile.mkdtemp(dir=TMP)
        shutil.copy(os.path.join(TMP, "banded.mp4"), os.path.join(d, "src.mp4"))
        shutil.copy(os.path.join(TMP, "overlay.png"), os.path.join(d, "ov.png"))
        with open(os.path.join(d, "edit.json"), "w") as f:
            json.dump({"out": "clip.mp4", "overlay": "ov.png", "zoom": 0,
                       "beats": [{"src": "src.mp4", "start": 4, "dur": 1}]}, f)
        proc = render("--edit", os.path.join(d, "edit.json"), "--quality", "draft", cwd=TMP)
        self.assertRendered(proc, os.path.join(d, "clip.mp4"))
        img = frame_at(os.path.join(d, "clip.mp4"), 0.5)
        self.assertColor(img, (200, 960), "yellow")
        self.assertColor(img, (160, 1500), "white")

    def test_jobs_file_renders_every_clip(self):
        d = tempfile.mkdtemp(dir=TMP)
        src = os.path.join(TMP, "banded.mp4")
        jobs = [{"out": os.path.join(d, "a.mp4"), "zoom": 0, "beats": [{"src": src, "start": 2, "dur": 1}]},
                {"out": os.path.join(d, "b.mp4"), "zoom": 0, "beats": [{"src": src, "start": 4, "dur": 1}]}]
        with open(os.path.join(d, "jobs.json"), "w") as f:
            json.dump({"jobs": jobs}, f)
        proc = render("--jobs", os.path.join(d, "jobs.json"), "--quality", "draft")
        self.assertRendered(proc, os.path.join(d, "a.mp4"))
        self.assertRendered(proc, os.path.join(d, "b.mp4"))
        self.assertColor(frame_at(os.path.join(d, "a.mp4"), 0.5), (200, 960), "magenta")
        self.assertColor(frame_at(os.path.join(d, "b.mp4"), 0.5), (200, 960), "yellow")


class Failures(Asserts):
    def test_beat_past_the_end_of_the_source_is_rejected_without_output(self):
        # ffmpeg alone would silently render a 0.5 s beat here; only validation can refuse it.
        src = os.path.join(TMP, "banded.mp4")
        ok = os.path.join(TMP, "near_end.mp4")
        self.assertRendered(render("--src", src, "--edl", "4.5:1", "--zoom", "0", "--quality", "draft", "--out", ok), ok)
        out = os.path.join(TMP, "past_end.mp4")
        proc = render("--src", src, "--edl", "5.5:1", "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("5.5", proc.stderr, "error should point at the offending beat")
        self.assertFalse(os.path.exists(out))

    def test_failed_render_leaves_no_file_behind(self):
        d = tempfile.mkdtemp(dir=TMP)
        src = os.path.join(TMP, "banded.mp4")
        out = os.path.join(d, "clip.mp4")
        good = os.path.join(TMP, "overlay.png")
        self.assertRendered(render("--src", src, "--edl", "0:1", "--overlay", good, "--zoom", "0",
                                   "--quality", "draft", "--out", out), out)
        os.remove(out)
        bad = os.path.join(d, "not_an_image.png")
        with open(bad, "w") as f:
            f.write("this is not a png")
        proc = render("--src", src, "--edl", "0:1", "--overlay", bad, "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(sorted(os.listdir(d)), ["not_an_image.png"])


class Cancellation(Asserts):
    def test_cancelled_render_leaves_no_file_behind(self):
        # A half-written clip.mp4 next to finished ones is easy to mistake for a finished clip and upload.
        d = tempfile.mkdtemp(dir=TMP)
        out = os.path.join(d, "clip.mp4")
        proc = subprocess.Popen([sys.executable, SCRIPT, "--src", os.path.join(TMP, "banded.mp4"),
                                 "--edl", "0:5.5,0:5.5", "--zoom", "0.3", "--quality", "final", "--out", out],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + 60
            while time.time() < deadline and not any(f.endswith(".mp4") for f in os.listdir(d)):
                time.sleep(0.05)
            self.assertTrue(any(f.endswith(".mp4") for f in os.listdir(d)), "render never started writing")
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=30)
            time.sleep(1.5)
            self.assertEqual(os.listdir(d), [])
        finally:
            if proc.poll() is None:
                proc.kill()
            subprocess.run(["pkill", "-f", d])


class FinalQuality(Asserts):
    def test_final_upload_copy_is_h264_high_4_2_0(self):
        # A pipeline that ends in RGB makes x264 emit High 4:4:4, which phones and upload pipelines reject.
        out = os.path.join(TMP, "final.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1",
                      "--overlay", os.path.join(TMP, "overlay.png"), "--zoom", "0", "--quality", "final", "--out", out)
        self.assertRendered(proc, out)
        v = next(s for s in streams(out)["streams"] if s["codec_type"] == "video")
        self.assertEqual((v["codec_name"], v["profile"], v["pix_fmt"]), ("h264", "High", "yuv420p"))


class OverlayValidation(Asserts):
    def test_overlay_that_is_not_a_full_frame_portrait_png_is_rejected(self):
        # Passing the bare logo instead of a built overlay would stretch it across the whole frame.
        logo = os.path.join(TMP, "bare_logo.png")
        Image.new("RGBA", (400, 200), (255, 255, 255, 255)).save(logo)
        out = os.path.join(TMP, "stretched_logo.mp4")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "0:1", "--overlay", logo,
                      "--zoom", "0", "--quality", "draft", "--out", out)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(os.path.exists(out))


class Preview(Asserts):
    def test_preview_geometry_matches_the_rendered_frame_under_push_in(self):
        vid, png = os.path.join(TMP, "parity.mp4"), os.path.join(TMP, "parity.png")
        src = os.path.join(TMP, "banded.mp4")
        self.assertRendered(render("--src", src, "--edl", "0:2", "--zoom", "0.5", "--quality", "draft", "--out", vid), vid)
        self.assertRendered(render("--src", src, "--edl", "0:2", "--zoom", "0.5", "--preview-at", "1.9", "--out", png), png)
        rendered, previewed = stripe_width(frame_at(vid, 1.9)), stripe_width(Image.open(png).convert("RGB"))
        self.assertTrue(rendered > 45 and abs(rendered - previewed) <= 3,
                        f"render stripe {rendered}px vs preview stripe {previewed}px at t=1.9")

    def test_preview_is_one_still_of_the_mapped_moment_with_overlay(self):
        out = os.path.join(TMP, "preview.png")
        proc = render("--src", os.path.join(TMP, "banded.mp4"), "--edl", "4:1,0:1",
                      "--overlay", os.path.join(TMP, "overlay.png"), "--zoom", "0",
                      "--preview-at", "0.5", "--out", out)
        self.assertRendered(proc, out)
        img = Image.open(out).convert("RGB")
        self.assertEqual(img.size, (1080, 1920))
        self.assertColor(img, (200, 960), "yellow")
        self.assertColor(img, (160, 1500), "white")


if __name__ == "__main__":
    unittest.main()
