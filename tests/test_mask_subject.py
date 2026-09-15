"""Tests for mask_subject.py.

Covers everything except the actual SAM model call: CLI validation, frame extraction, and the mask/
preview PNG compositing (against a synthetic circular mask standing in for real SAM output - the
compositing math doesn't care where the mask came from). Actually running SAM needs torch and a
downloaded checkpoint, neither of which belong in this test suite - see SKILL.md.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_mask_subject.py' -v
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

SCRIPT = os.environ.get("MASK_SUBJECT_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-subject-mask/scripts/mask_subject.py")

spec = importlib.util.spec_from_file_location("mask_subject", SCRIPT)
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)

TMP = None
CLIP = None
FRAME = None


def setUpModule():
    global TMP, CLIP, FRAME
    TMP = tempfile.mkdtemp(prefix="mask-test-")
    CLIP = os.path.join(TMP, "clip.mp4")
    FRAME = os.path.join(TMP, "frame.png")
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi",
                    "-i", "testsrc2=s=640x1136:r=30:d=2", CLIP], check=True)
    ms.extract_frame(CLIP, 1.0, FRAME)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


def circular_mask(image, frac=0.25):
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, r = w // 2, h // 2, int(min(w, h) * frac)
    return ((xx - cx) ** 2 + (yy - cy) ** 2) < r ** 2


class ParseHelpers(unittest.TestCase):
    def test_parse_point(self):
        self.assertEqual(ms.parse_point("12.5,30"), (12.5, 30.0))

    def test_parse_box(self):
        self.assertEqual(ms.parse_box("1,2,3,4"), (1.0, 2.0, 3.0, 4.0))

    def test_parse_box_rejects_inverted_coordinates(self):
        out = run(["--frame", FRAME, "--checkpoint", "x.pth", "--box", "100,100,50,200", "--out", "m.png"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("must be greater than", out.stderr)


class ExtractFrame(unittest.TestCase):
    def test_extracts_a_real_frame(self):
        out_png = os.path.join(TMP, "extracted.png")
        ms.extract_frame(CLIP, 0.5, out_png)
        self.assertTrue(os.path.exists(out_png))
        img = Image.open(out_png)
        self.assertEqual(img.size, (640, 1136))


class MaskAndPreviewCompositing(unittest.TestCase):
    """The mask/preview writers don't care that this mask is synthetic, not real SAM output."""

    @classmethod
    def setUpClass(cls):
        cls.image = np.array(Image.open(FRAME).convert("RGB"))
        cls.mask = circular_mask(cls.image)

    def test_save_mask_is_binary_and_matches_the_source_shape(self):
        out = os.path.join(TMP, "mask.png")
        ms.save_mask(self.mask, out)
        m = np.array(Image.open(out))
        self.assertEqual(m.shape, self.mask.shape)
        self.assertEqual(m.dtype, np.uint8)
        self.assertTrue(set(np.unique(m).tolist()) <= {0, 255})

    def test_save_mask_center_is_masked_corner_is_not(self):
        out = os.path.join(TMP, "mask2.png")
        ms.save_mask(self.mask, out)
        m = np.array(Image.open(out))
        h, w = m.shape
        self.assertEqual(m[h // 2, w // 2], 255)
        self.assertEqual(m[0, 0], 0)

    def test_save_preview_is_same_size_as_source_and_is_rgb(self):
        out = os.path.join(TMP, "preview.png")
        h, w = self.image.shape[:2]
        ms.save_preview(self.image, self.mask, [(w // 2, h // 2)], [1], (5, 5, w - 5, h - 5), out)
        p = Image.open(out)
        self.assertEqual(p.size, (w, h))
        self.assertEqual(p.mode, "RGB")

    def test_save_preview_works_with_no_box(self):
        out = os.path.join(TMP, "preview_nobox.png")
        h, w = self.image.shape[:2]
        ms.save_preview(self.image, self.mask, [(w // 2, h // 2)], [1], None, out)
        self.assertTrue(os.path.exists(out))


class CliValidation(unittest.TestCase):
    def test_needs_a_point_or_a_box(self):
        out = run(["--frame", FRAME, "--checkpoint", "x.pth", "--out", "m.png"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--point or a --box", out.stderr)

    def test_missing_frame_fails(self):
        out = run(["--frame", os.path.join(TMP, "nope.png"), "--checkpoint", "x.pth",
                   "--point", "10,20", "--out", "m.png"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("not found", out.stderr)

    def test_clip_without_at_fails(self):
        out = run(["--clip", CLIP, "--checkpoint", "x.pth", "--point", "10,20", "--out", "m.png"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--clip needs --at", out.stderr)

    def test_more_labels_than_points_fails(self):
        out = run(["--frame", FRAME, "--checkpoint", "x.pth", "--point", "10,20",
                   "--label", "1", "--label", "0", "--out", "m.png"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("more --label than --point", out.stderr)

    def test_bad_point_format_fails(self):
        out = run(["--frame", FRAME, "--checkpoint", "x.pth", "--point", "abc", "--out", "m.png"])
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("bad --point", out.stderr)


if __name__ == "__main__":
    unittest.main()
