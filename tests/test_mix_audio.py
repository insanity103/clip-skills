"""Black-box tests for mix_audio.py against synthetic clips, music, and SFX.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_mix_audio.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.environ.get("MIX_AUDIO_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-audio-mixer/scripts/mix_audio.py")

TMP = None
CLIP = None
SILENT_CLIP = None
MUSIC = None
SFX = None


def setUpModule():
    global TMP, CLIP, SILENT_CLIP, MUSIC, SFX
    TMP = tempfile.mkdtemp(prefix="mix-test-")
    CLIP = os.path.join(TMP, "clip.mp4")
    SILENT_CLIP = os.path.join(TMP, "silent_clip.mp4")
    MUSIC = os.path.join(TMP, "music.wav")
    SFX = os.path.join(TMP, "sfx.wav")
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=6",
           "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", CLIP)
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=6",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", SILENT_CLIP)
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=20", MUSIC)
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=0.3", SFX)


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


class MixAudio(unittest.TestCase):
    def test_music_only_produces_valid_output(self):
        out = os.path.join(TMP, "music_only.mp4")
        r = run(["--clip", CLIP, "--music", MUSIC, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(out))
        info = ffprobe(out)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        a = next(s for s in info["streams"] if s["codec_type"] == "audio")
        self.assertEqual((v["width"], v["height"]), (1080, 1920))
        self.assertEqual(a["codec_name"], "aac")
        self.assertAlmostEqual(float(info["format"]["duration"]), 6.0, delta=0.15)

    def test_music_start_offset_is_accepted(self):
        out = os.path.join(TMP, "music_offset.mp4")
        r = run(["--clip", CLIP, "--music", MUSIC, "--music-start", "10", "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertAlmostEqual(float(ffprobe(out)["format"]["duration"]), 6.0, delta=0.15)

    def test_duck_runs_and_still_produces_full_length_audio(self):
        out = os.path.join(TMP, "ducked.mp4")
        r = run(["--clip", CLIP, "--music", MUSIC, "--duck", "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        info = ffprobe(out)
        self.assertAlmostEqual(float(info["format"]["duration"]), 6.0, delta=0.15)

    def test_sfx_only(self):
        sfx_json = os.path.join(TMP, "sfx.json")
        with open(sfx_json, "w") as f:
            json.dump([{"at": 1.0, "file": SFX}, {"at": 4.0, "file": SFX, "db": -3}], f)
        out = os.path.join(TMP, "sfx_only.mp4")
        r = run(["--clip", CLIP, "--sfx", sfx_json, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertAlmostEqual(float(ffprobe(out)["format"]["duration"]), 6.0, delta=0.15)

    def test_music_and_sfx_together(self):
        sfx_json = os.path.join(TMP, "sfx_both.json")
        with open(sfx_json, "w") as f:
            json.dump([{"at": 2.0, "file": SFX}], f)
        out = os.path.join(TMP, "both.mp4")
        r = run(["--clip", CLIP, "--music", MUSIC, "--duck", "--sfx", sfx_json, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertAlmostEqual(float(ffprobe(out)["format"]["duration"]), 6.0, delta=0.15)

    def test_clip_with_no_audio_stream_still_mixes(self):
        out = os.path.join(TMP, "from_silent.mp4")
        r = run(["--clip", SILENT_CLIP, "--music", MUSIC, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        info = ffprobe(out)
        self.assertTrue(any(s["codec_type"] == "audio" for s in info["streams"]))

    def test_video_is_not_reencoded(self):
        # framemd5 hashes decoded frames: with -c:v copy the output's frames must decode identically
        # to the source's, byte for byte, even though the audio track differs entirely.
        out = os.path.join(TMP, "copy_check.mp4")
        r = run(["--clip", CLIP, "--music", MUSIC, "--out", out])
        self.assertEqual(r.returncode, 0, r.stderr)

        def video_framemd5(path):
            p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v", "-f", "framemd5", "-"],
                               capture_output=True, text=True, check=True)
            return p.stdout

        self.assertEqual(video_framemd5(CLIP), video_framemd5(out))

    def test_no_music_and_no_sfx_fails(self):
        out = os.path.join(TMP, "bad1.mp4")
        r = run(["--clip", CLIP, "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing to mix", r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_sfx_timestamp_outside_clip_fails(self):
        sfx_json = os.path.join(TMP, "sfx_bad.json")
        with open(sfx_json, "w") as f:
            json.dump([{"at": 99, "file": SFX}], f)
        out = os.path.join(TMP, "bad2.mp4")
        r = run(["--clip", CLIP, "--sfx", sfx_json, "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("outside the clip", r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_missing_music_file_fails(self):
        out = os.path.join(TMP, "bad3.mp4")
        r = run(["--clip", CLIP, "--music", os.path.join(TMP, "nope.mp3"), "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_missing_clip_fails(self):
        out = os.path.join(TMP, "bad4.mp4")
        r = run(["--clip", os.path.join(TMP, "nope.mp4"), "--music", MUSIC, "--out", out])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_leaves_no_partial_file_on_failure(self):
        sfx_json = os.path.join(TMP, "sfx_bad2.json")
        with open(sfx_json, "w") as f:
            json.dump([{"at": 99, "file": SFX}], f)
        out = os.path.join(TMP, "partial_check.mp4")
        run(["--clip", CLIP, "--sfx", sfx_json, "--out", out])
        self.assertFalse(os.path.exists(out))
        self.assertFalse(os.path.exists(out.replace(".mp4", ".partial.mp4")))


if __name__ == "__main__":
    unittest.main()
