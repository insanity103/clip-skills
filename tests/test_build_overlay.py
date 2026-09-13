"""Black-box tests for build_overlay.py. Pure image work, no video.

Placement is checked against the PNG's own opaque pixels (alpha > 200), not only the sidecar the script
writes, so a wrong box and a wrong drawing cannot agree with each other by accident.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_build_overlay.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPT = os.environ.get("BUILD_OVERLAY_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-overlay-builder/scripts/build_overlay.py")
# macOS ships DIN Condensed; Linux desktops ship DejaVu Sans Condensed (older Debian/Ubuntu, Fedora, Arch paths)
# or, where that package was dropped (Ubuntu 24.04+), Liberation Sans Narrow Bold - build_overlay.py's own
# DEFAULT_FONTS falls back to it, so the test must recognize it too or the whole class silently skips.
FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
                   "/usr/share/fonts/dejavu-sans-fonts/DejaVuSansCondensed-Bold.ttf",
                   "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"]
DIN = next((f for f in FONT_CANDIDATES if os.path.exists(f)), FONT_CANDIDATES[0])


def opaque_bbox(img, lo=200):
    """(x0, y0, x1, y1) inclusive of fully drawn pixels; soft shadow is excluded by the threshold."""
    a = img.getchannel("A").point(lambda v: 255 if v > lo else 0)
    b = a.getbbox()
    return None if b is None else (b[0], b[1], b[2] - 1, b[3] - 1)


@unittest.skipUnless(os.path.exists(DIN), "no condensed bold test font installed (DIN Condensed or DejaVu Sans Condensed)")
class BuildOverlay(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ov-test-")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def build(self, elements, *extra, **top):
        spec = {"defaults": {"font": DIN}, "elements": elements, **top}
        sp = os.path.join(self.d, "spec.json")
        with open(sp, "w") as f:
            json.dump(spec, f)
        out = os.path.join(self.d, "overlay.png")
        proc = subprocess.run([sys.executable, SCRIPT, sp, "--out", out, *extra], capture_output=True, text=True)
        side = os.path.join(self.d, "overlay.boxes.json")
        boxes = json.load(open(side)) if os.path.exists(side) else None
        img = Image.open(out) if os.path.exists(out) else None
        return proc, img, boxes

    def assertBuilt(self, proc, img):
        self.assertEqual(proc.returncode, 0, proc.stderr[-1200:])
        self.assertIsNotNone(img, "no PNG written")

    def element(self, boxes, eid):
        return next(e for e in boxes["elements"] if e["id"] == eid)

    def logo(self, w, h, color=(255, 0, 0, 255)):
        p = os.path.join(self.d, f"logo_{w}x{h}.png")
        Image.new("RGBA", (w, h), color).save(p)
        return p

    def test_canvas_is_a_transparent_portrait_png(self):
        proc, img, _ = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400}])
        self.assertBuilt(proc, img)
        self.assertEqual((img.size, img.mode), ((1080, 1920), "RGBA"))
        self.assertEqual(img.getpixel((5, 5))[3], 0)
        self.assertEqual(img.getpixel((1074, 1914))[3], 0)

    def test_text_top_lands_on_the_requested_y_centred_horizontally(self):
        proc, img, _ = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400}])
        self.assertBuilt(proc, img)
        x0, y0, x1, _ = opaque_bbox(img)
        self.assertAlmostEqual(y0, 400, delta=2)
        self.assertAlmostEqual((x0 + x1) / 2, 539.5, delta=2)

    def test_long_line_shrinks_to_stay_inside_the_side_margins(self):
        text = "MODERN WARFARE BETA WEEKEND"
        proc, img, boxes = self.build([{"id": "t", "type": "text", "text": text, "size": 140, "y": 300, "max_lines": 1}],
                                      margin=60)
        self.assertBuilt(proc, img)
        x0, _, x1, _ = opaque_bbox(img)
        self.assertGreaterEqual(x0, 59)
        self.assertLessEqual(x1, 1020)
        self.assertLess(self.element(boxes, "t")["size"], 140)

    def test_text_too_long_for_one_line_wraps_instead_of_shrinking_past_the_floor(self):
        text = "INSIDE THE MODERN WARFARE 4 MULTIPLAYER BETA"
        proc, img, boxes = self.build([{"id": "t", "type": "text", "text": text, "size": 108, "y": 300}], margin=60)
        self.assertBuilt(proc, img)
        el = self.element(boxes, "t")
        self.assertEqual(len(el["lines"]), 2)
        # Floor is 70% of size (76px here). build_overlay.py itself only drops below it, with a stderr
        # warning, when even the wrapped text can't fit at the floor - a narrower font (e.g. Liberation
        # Sans Narrow Bold) can still need a couple px past that for this exact string. Small tolerance
        # instead of an exact floor keeps this a real regression check without pinning one font's kerning.
        self.assertGreaterEqual(el["size"], 76 - 3)
        x0, _, x1, _ = opaque_bbox(img)
        self.assertGreaterEqual(x0, 59)
        self.assertLessEqual(x1, 1020)

    def test_below_stacks_an_element_under_another_with_the_gap(self):
        proc, img, _ = self.build([{"id": "a", "type": "text", "text": "TOP", "size": 80, "y": 300},
                                   {"id": "b", "type": "text", "text": "BOTTOM", "size": 80, "below": "a", "gap": 20}])
        self.assertBuilt(proc, img)
        alpha = img.getchannel("A")
        rows = [y for y in range(250, 700) if any(alpha.getpixel((x, y)) > 200 for x in range(0, 1080, 2))]
        runs, start = [], rows[0]
        for prev, cur in zip(rows, rows[1:]):
            if cur != prev + 1:
                runs.append((start, prev))
                start = cur
        runs.append((start, rows[-1]))
        self.assertEqual(len(runs), 2, f"expected two separate text blocks, got rows {runs}")
        self.assertAlmostEqual(runs[1][0] - runs[0][1] - 1, 20, delta=3)

    def test_overlapping_elements_are_refused_and_no_png_is_written(self):
        ok, img, _ = self.build([{"id": "a", "type": "text", "text": "ONE", "size": 100, "y": 500},
                                 {"id": "b", "type": "text", "text": "TWO", "size": 100, "y": 700}])
        self.assertBuilt(ok, img)
        os.remove(os.path.join(self.d, "overlay.png"))
        proc, img, _ = self.build([{"id": "a", "type": "text", "text": "ONE", "size": 100, "y": 500},
                                   {"id": "b", "type": "text", "text": "TWO", "size": 100, "y": 520}])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(img)

    def test_image_is_scaled_to_width_keeping_its_aspect_ratio(self):
        proc, img, _ = self.build([{"id": "logo", "type": "image", "src": self.logo(400, 100), "width": 320, "y": 1300}])
        self.assertBuilt(proc, img)
        x0, y0, x1, y1 = opaque_bbox(img)
        self.assertEqual((x1 - x0 + 1, y1 - y0 + 1), (320, 80))
        self.assertEqual((x0, y0), (380, 1300))

    def test_right_aligned_element_sits_against_the_margin(self):
        proc, img, _ = self.build([{"id": "logo", "type": "image", "src": self.logo(200, 100), "width": 200, "y": 200,
                                    "align": "right"}], margin=60)
        self.assertBuilt(proc, img)
        self.assertEqual(opaque_bbox(img)[2], 1019)

    def test_white_text_with_default_styling_is_readable_on_a_white_background(self):
        proc, img, _ = self.build([{"id": "t", "type": "text", "text": "THIS WEEKEND", "size": 90, "color": "#FFFFFF",
                                    "y": 600}])
        self.assertBuilt(proc, img)
        x0, y0, x1, y1 = opaque_bbox(img, lo=20)
        flat = Image.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, 255)), img).convert("L")
        dark = sum(1 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if flat.getpixel((x, y)) < 100)
        self.assertGreater(dark / ((x1 - x0 + 1) * (y1 - y0 + 1)), 0.05, "white text vanishes on white footage")

    def test_element_under_a_platform_ui_zone_is_reported(self):
        zones = os.path.join(self.d, "zones.json")
        with open(zones, "w") as f:
            json.dump({"testapp": {"bottom bar": [0, 1700, 1080, 1920]}}, f)
        proc, img, boxes = self.build([{"id": "logo", "type": "image", "src": self.logo(300, 100), "width": 300, "y": 1750},
                                       {"id": "safe", "type": "text", "text": "OK", "size": 80, "y": 800}],
                                      "--zones", zones, "--check-safe", "testapp")
        self.assertBuilt(proc, img)
        hits = {(h["element"], h["platform"]) for h in boxes["safe_zone_hits"]}
        self.assertEqual(hits, {("logo", "testapp")})

    def test_builtin_platforms_all_cover_the_bottom_caption_area_and_not_mid_screen(self):
        proc, img, boxes = self.build([{"id": "low", "type": "text", "text": "TOO LOW", "size": 50, "y": 1845},
                                       {"id": "mid", "type": "text", "text": "FINE", "size": 80, "y": 800}],
                                      "--check-safe", "tiktok,shorts,reels")
        self.assertBuilt(proc, img)
        hits = {(h["element"], h["platform"]) for h in boxes["safe_zone_hits"]}
        self.assertEqual(hits, {("low", "tiktok"), ("low", "shorts"), ("low", "reels")})

    def test_unknown_font_is_an_error_not_a_silent_fallback(self):
        ok, img, _ = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400,
                                  "font": os.path.splitext(os.path.basename(DIN))[0]}])
        self.assertBuilt(ok, img)
        os.remove(os.path.join(self.d, "overlay.png"))
        proc, img, _ = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400,
                                    "font": "No Such Font Family 123"}])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(img)

    def test_first_installed_font_in_a_list_is_used_and_recorded(self):
        # One layout for a Mac and a Linux machine: fonts listed in order of preference.
        proc, img, boxes = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400,
                                        "font": ["No Such Font Family 123", DIN]}])
        self.assertBuilt(proc, img)
        self.assertEqual(self.element(boxes, "t")["font"], DIN)

    def test_a_font_list_with_nothing_installed_names_every_font_tried(self):
        proc, img, _ = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400,
                                    "font": ["No Such Font Family 123", "Another Missing Font 456"]}])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(img)
        self.assertIn("Another Missing Font 456", proc.stderr)

    def test_spec_without_any_font_uses_the_built_in_cross_platform_chain(self):
        proc, img, boxes = self.build([{"id": "t", "type": "text", "text": "HELLO", "size": 80, "y": 400}], defaults={})
        self.assertBuilt(proc, img)
        self.assertTrue(os.path.isfile(self.element(boxes, "t")["font"]))

    def test_element_running_off_the_bottom_of_the_canvas_is_refused(self):
        # A clipped logo breaks "the logo must be visible on screen".
        ok, img, _ = self.build([{"id": "logo", "type": "image", "src": self.logo(300, 100), "width": 300, "y": 1800}])
        self.assertBuilt(ok, img)
        os.remove(os.path.join(self.d, "overlay.png"))
        proc, img, _ = self.build([{"id": "logo", "type": "image", "src": self.logo(300, 100), "width": 300, "y": 1880}])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(img)


if __name__ == "__main__":
    unittest.main()
