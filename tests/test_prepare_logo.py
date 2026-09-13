"""Black-box tests for prepare_logo.py: brand logos delivered on black or white become trimmed transparent PNGs.

Fixture on black (400x200): white square x50-149 y50-149, yellow (254,208,0) x200-299 y50-149, and a
half-intensity yellow edge (127,104,0) at x300-309 y50-149. The logo's extent is x50-309, y50-149, so the
trimmed output is 260x100 and source (x, y) maps to output (x-50, y-50).

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_prepare_logo.py' -v
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

SCRIPT = os.environ.get("PREPARE_LOGO_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-overlay-builder/scripts/prepare_logo.py")


class PrepareLogo(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="logo-test-")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_script(self, src, *extra):
        out = os.path.join(self.d, "logo_out.png")
        proc = subprocess.run([sys.executable, SCRIPT, src, "--out", out, *extra], capture_output=True, text=True)
        img = Image.open(out).convert("RGBA") if os.path.exists(out) else None
        return proc, img

    def on_black(self, noise=False):
        img = Image.new("RGB", (400, 200), (0, 0, 0))
        if noise:
            rnd = random.Random(7)
            px = img.load()
            for y in range(200):
                for x in range(400):
                    v = rnd.randint(0, 12)
                    px[x, y] = (v, v, v)
        d = ImageDraw.Draw(img)
        d.rectangle([50, 50, 149, 149], fill=(255, 255, 255))
        d.rectangle([200, 50, 299, 149], fill=(254, 208, 0))
        d.rectangle([300, 50, 309, 149], fill=(127, 104, 0))
        p = os.path.join(self.d, "on_black.png")
        img.save(p)
        return p

    def assertMade(self, proc, img):
        self.assertEqual(proc.returncode, 0, proc.stderr[-1000:])
        self.assertIsNotNone(img)

    def assertRGB(self, px, want, tol):
        self.assertTrue(all(abs(a - b) <= tol for a, b in zip(px[:3], want)), f"{px[:3]} != {want} (tol {tol})")

    def test_black_background_becomes_fully_transparent(self):
        proc, img = self.run_script(self.on_black())
        self.assertMade(proc, img)
        self.assertEqual(img.getpixel((125, 50))[3], 0)

    def test_output_is_trimmed_to_the_logo(self):
        proc, img = self.run_script(self.on_black())
        self.assertMade(proc, img)
        self.assertEqual(img.size, (260, 100))

    def test_white_ink_stays_opaque_white(self):
        proc, img = self.run_script(self.on_black())
        self.assertMade(proc, img)
        px = img.getpixel((50, 50))
        self.assertEqual(px[3], 255)
        self.assertRGB(px, (255, 255, 255), 2)

    def test_colour_survives_on_half_transparent_edges(self):
        # Luminance-as-alpha without un-premultiplying would leave (127,104,0): a muddy dark fringe.
        proc, img = self.run_script(self.on_black())
        self.assertMade(proc, img)
        px = img.getpixel((255, 50))
        self.assertAlmostEqual(px[3], 127, delta=4)
        self.assertRGB(px, (254, 208, 0), 6)

    def test_dark_noise_in_a_jpeg_background_does_not_leave_a_haze(self):
        proc, img = self.run_script(self.on_black(noise=True))
        self.assertMade(proc, img)
        self.assertEqual(img.size, (260, 100), "noise was treated as part of the logo")
        self.assertEqual(max(img.getpixel((x, y))[3] for x in range(105, 145) for y in range(10, 90)), 0)

    def test_white_background_is_removed_and_dark_ink_kept(self):
        img = Image.new("RGB", (300, 100), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([20, 20, 119, 79], fill=(0, 0, 0))
        d.rectangle([150, 20, 249, 79], fill=(255, 0, 0))
        src = os.path.join(self.d, "on_white.png")
        img.save(src)
        proc, out = self.run_script(src)
        self.assertMade(proc, out)
        self.assertEqual(out.size, (230, 60))
        self.assertEqual(out.getpixel((10, 10))[3], 255)
        self.assertRGB(out.getpixel((10, 10)), (0, 0, 0), 2)
        self.assertEqual(out.getpixel((140, 10))[3], 255)
        self.assertRGB(out.getpixel((140, 10)), (255, 0, 0), 2)
        self.assertEqual(out.getpixel((115, 10))[3], 0)

    def test_background_that_is_neither_black_nor_white_is_refused(self):
        ok, out = self.run_script(self.on_black())
        self.assertMade(ok, out)
        os.remove(os.path.join(self.d, "logo_out.png"))
        img = Image.new("RGB", (300, 100), (128, 128, 128))
        ImageDraw.Draw(img).rectangle([100, 30, 199, 69], fill=(255, 255, 255))
        src = os.path.join(self.d, "on_grey.png")
        img.save(src)
        proc, out = self.run_script(src)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(out)

    def on_checker(self, ink=(0, 0, 0), name="checker.png"):
        # Photoshop-style preview: 16px cells of 255 and 204, as brand portals bake into "large" JPG previews.
        img = Image.new("RGB", (320, 160))
        px = img.load()
        for y in range(160):
            for x in range(320):
                v = 255 if ((x // 16) + (y // 16)) % 2 == 0 else 204
                px[x, y] = (v, v, v)
        d = ImageDraw.Draw(img)
        d.rectangle([40, 40, 119, 119], fill=ink)
        d.rectangle([160, 40, 239, 119], fill=(254, 208, 0))
        p = os.path.join(self.d, name)
        img.save(p)
        return p

    def test_light_checkerboard_preview_is_removed_behind_dark_and_coloured_ink(self):
        proc, img = self.run_script(self.on_checker())
        self.assertMade(proc, img)
        self.assertEqual(img.size, (200, 80))
        self.assertEqual(img.getpixel((85, 10))[3], 0, "white checker cell left behind")
        self.assertEqual(img.getpixel((101, 10))[3], 0, "grey checker cell left behind")
        self.assertEqual(img.getpixel((10, 10))[3], 255)
        self.assertRGB(img.getpixel((10, 10)), (0, 0, 0), 3)
        self.assertGreaterEqual(img.getpixel((130, 10))[3], 250)
        self.assertRGB(img.getpixel((130, 10)), (254, 208, 0), 6)

    def test_light_ink_on_a_checkerboard_is_refused(self):
        # White letters on white/grey squares cannot be separated from the background at all.
        ok, out = self.run_script(self.on_checker())
        self.assertMade(ok, out)
        os.remove(os.path.join(self.d, "logo_out.png"))
        proc, out = self.run_script(self.on_checker(ink=(255, 255, 255), name="neg_checker.png"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(out)

    def test_recolor_neutral_turns_dark_ink_white_but_keeps_brand_colour(self):
        proc, img = self.run_script(self.on_checker(), "--recolor-neutral", "#FFFFFF")
        self.assertMade(proc, img)
        self.assertEqual(img.getpixel((10, 10))[3], 255)
        self.assertRGB(img.getpixel((10, 10)), (255, 255, 255), 3)
        self.assertRGB(img.getpixel((130, 10)), (254, 208, 0), 6)

    def test_clean_run_writes_nothing_to_stderr(self):
        proc, img = self.run_script(self.on_black())
        self.assertMade(proc, img)
        self.assertEqual(proc.stderr, "")

    def test_already_transparent_png_keeps_its_alpha_and_is_trimmed(self):
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([40, 60, 139, 99], fill=(0, 128, 255, 255))
        d.rectangle([140, 60, 149, 99], fill=(0, 128, 255, 90))
        src = os.path.join(self.d, "transparent.png")
        img.save(src)
        proc, out = self.run_script(src)
        self.assertMade(proc, out)
        self.assertEqual(out.size, (110, 40))
        self.assertEqual(out.getpixel((105, 20)), (0, 128, 255, 90))


if __name__ == "__main__":
    unittest.main()
