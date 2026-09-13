"""Black-box tests for qa_clip.py, the last check on a rendered clip before it is posted.

Synthetic 1080x1920 clips stand in for each failure seen in the MW4 campaign:
  full       sharp moving noise, full frame                          -> clean
  skytop     smooth sky gradient over the top 30%, sharp below        -> clean (plain skies are not letterboxing)
  letterbox  608 px content band on black                              -> full_frame FAIL
  blurfill   the v1 layout: sharp band over a blurred, darkened copy   -> full_frame FAIL (all 5 v1 clips were flagged)
  silent     silent audio track;  noaudio: no audio stream at all
  short      6 s, under the brief's 10 s minimum
  deadair    tone 0-3 s, silence 3-11 s, tone 11-14 s                  -> dead_air FAIL
  overlap    a_2to8 re-uses 4 of its 6 s from b_0to6; c_other is unrelated footage

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_qa_clip.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

STAGE = os.path.expanduser("~/Downloads/clip-skills/scripts-staging")
SCRIPT = os.environ.get("QA_CLIP_SCRIPT") or os.path.join(STAGE, "clipping-campaign-producer/scripts/qa_clip.py")
CUTTER = os.environ.get("CLIP_CUTTER_SCRIPTS") or os.path.join(STAGE, "gameplay-clip-cutter/scripts")
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "gameplay_3s.mp4")
TMP = None

NOISE = "noise=alls=100:allf=t+u"
TONE = "sine=frequency=440:sample_rate=48000:duration={d},volume=0.5"
CAMPAIGN = {"duration": {"min": 10, "max": 60},
            "onscreen": {"required_text_any": [["MW4 Open Beta", "This Weekend"], ["MW4 Beta Weekend"]],
                         "logo_required": True}}


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


def make(name, video_graph, audio_graph=None, duration=12):
    out = os.path.join(TMP, name)
    cmd = ["-filter_complex", video_graph + "[v]"]
    maps = ["-map", "[v]"]
    if audio_graph:
        cmd[1] += ";" + audio_graph + "[a]"
        maps += ["-map", "[a]"]
    ff(*cmd, *maps, "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
       *(["-c:a", "aac"] if audio_graph else ["-an"]), out)
    return out


def setUpModule():
    global TMP
    TMP = tempfile.mkdtemp(prefix="qa-test-")
    tone = TONE.format(d=12)
    make("full.mp4", f"color=c=gray:s=1080x1920:r=30:d=12,{NOISE}", tone)
    make("skytop.mp4", f"color=c=gray:s=1080x1344:r=30:d=12,{NOISE}[n];"
         "gradients=s=1080x576:c0=0x5080c0:c1=0xc0d8f0:x0=0:y0=0:x1=0:y1=576:r=30:d=12[s];[s][n]vstack", tone)
    make("letterbox.mp4", f"color=c=gray:s=1080x608:r=30:d=12,{NOISE},pad=1080:1920:0:656:black", tone)
    make("blurfill.mp4", f"color=c=gray:s=1920x1080:r=30:d=12,{NOISE},split[a][b];"
         "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30,eq=brightness=-0.18[bg];"
         "[b]scale=1080:608[fg];[bg][fg]overlay=0:656,drawbox=x=240:y=200:w=600:h=70:color=white:t=fill", tone)
    # flagged v1 clip 2's pattern: the blurred fill is near-black in some frames and bright in others, so neither
    # "bars" nor "blur" alone covers 60% of frames - but every frame is letterboxed
    make("mixedfill.mp4", f"color=c=gray:s=1920x1080:r=30:d=12,{NOISE},split[a][b];"
         "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30,"
         "eq=brightness='if(lt(t,5.5),-0.7,0)':eval=frame[bg];"
         "[b]scale=1080:608[fg];[bg][fg]overlay=0:656", tone)
    make("silent.mp4", f"color=c=gray:s=1080x1920:r=30:d=12,{NOISE}", "anullsrc=r=48000:cl=stereo")
    make("noaudio.mp4", f"color=c=gray:s=1080x1920:r=30:d=12,{NOISE}")
    make("short.mp4", f"color=c=gray:s=1080x1920:r=30:d=6,{NOISE}", TONE.format(d=6), duration=6)
    make("deadair.mp4", f"color=c=gray:s=1080x1920:r=30:d=14,{NOISE}",
         f"{TONE.format(d=3)}[t1];anullsrc=r=48000:cl=mono,atrim=duration=8[q];{TONE.format(d=3)}[t2];"
         "[t1][q][t2]concat=n=3:v=0:a=1", duration=14)
    ff("-filter_complex", "mandelbrot=s=270x480:r=30:maxiter=120,scale=1080:1920[v]", "-map", "[v]", "-t", "10",
       "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", os.path.join(TMP, "fractal.mp4"))
    for name, start in (("b_0to6.mp4", 0), ("a_2to8.mp4", 2)):
        ff("-ss", str(start), "-t", "6", "-i", os.path.join(TMP, "fractal.mp4"), "-f", "lavfi", "-i", TONE.format(d=6),
           "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
           os.path.join(TMP, name))
    make("c_other.mp4", "life=s=270x480:r=30:mold=10:ratio=0.2:death_color=#101010:life_color=#f0f0f0,scale=1080:1920",
         TONE.format(d=6), duration=6)
    # the same footage as b_0to6, re-encoded: what re-uploading an already-posted clip looks like
    ff("-i", os.path.join(TMP, "b_0to6.mp4"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p",
       "-c:a", "aac", os.path.join(TMP, "b_reupload.mp4"))
    # 3 s cut from a delivered, platform-approved-style MW4 clip (sharpness 0.20); synthetic textures do not
    # blur like real gameplay, so blur fixtures are derived from it
    shutil.copy(FIXTURE, os.path.join(TMP, "detail.mp4"))
    for name, sigma in (("blurry.mp4", 8), ("extreme_blur.mp4", 30)):
        ff("-i", FIXTURE, "-vf", f"gblur=sigma={sigma}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "copy", os.path.join(TMP, name))
    with open(os.path.join(TMP, "campaign.json"), "w") as f:
        json.dump(CAMPAIGN, f)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def qa(*clips, extra=(), campaign="campaign.json"):
    out = os.path.join(TMP, f"qa_{abs(hash((clips, extra, campaign)))}.json")
    proc = subprocess.run([sys.executable, SCRIPT, *[os.path.join(TMP, c) for c in clips],
                           "--campaign", os.path.join(TMP, campaign), "--json", out, *extra],
                          capture_output=True, text=True, env={**os.environ, "CLIP_CUTTER_SCRIPTS": CUTTER})
    if not os.path.exists(out):
        return proc, None
    with open(out) as f:
        return proc, json.load(f)


def spec(texts, logo=True):
    elements = [{"id": f"t{i}", "type": "text", "text": t, "size": 80, "y": 150 + 130 * i} for i, t in enumerate(texts)]
    if logo:
        elements.append({"id": "logo", "type": "image", "src": "logo.png", "width": 320, "y": 1340})
    path = os.path.join(TMP, f"spec_{abs(hash((tuple(texts), logo)))}.json")
    with open(path, "w") as f:
        json.dump({"elements": elements}, f)
    return path


class Asserts(unittest.TestCase):
    def clip(self, proc, result, name):
        self.assertIsNotNone(result, proc.stderr[-1500:])
        return next(c for c in result["clips"] if os.path.basename(c["clip"]) == name)

    def levels(self, c):
        return {i["check"]: i["level"] for i in c["issues"]}


class FullFrame(Asserts):
    def test_full_frame_clip_has_no_framing_issue(self):
        proc, result = qa("full.mp4")
        self.assertNotIn("full_frame", self.levels(self.clip(proc, result, "full.mp4")))

    def test_plain_sky_across_the_top_is_not_mistaken_for_letterboxing(self):
        proc, result = qa("skytop.mp4")
        self.assertNotIn("full_frame", self.levels(self.clip(proc, result, "skytop.mp4")))

    def test_black_letterbox_bars_fail(self):
        proc, result = qa("letterbox.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "letterbox.mp4")).get("full_frame"), "FAIL")

    def test_blurred_background_fill_fails_even_with_text_over_it(self):
        proc, result = qa("blurfill.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "blurfill.mp4")).get("full_frame"), "FAIL")


    def test_letterbox_alternating_between_dark_and_blurred_fill_fails(self):
        proc, result = qa("mixedfill.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "mixedfill.mp4")).get("full_frame"), "FAIL")


class Sharpness(Asserts):
    def test_sharp_gameplay_has_no_sharpness_issue(self):
        proc, result = qa("detail.mp4")
        self.assertNotIn("sharpness", self.levels(self.clip(proc, result, "detail.mp4")))

    def test_heavily_blurred_gameplay_fails(self):
        # Instagram and TikTok both name blurry / low-resolution video as not recommended.
        proc, result = qa("blurry.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "blurry.mp4")).get("sharpness"), "FAIL")

    def test_extremely_blurred_gameplay_still_fails_instead_of_being_skipped(self):
        # Blur so strong that no detail survives must not be mistaken for a flat frame and pass unchecked.
        proc, result = qa("extreme_blur.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "extreme_blur.mp4")).get("sharpness"), "FAIL")


class AudioAndLength(Asserts):
    def test_clean_clip_passes_overall_and_exits_zero(self):
        proc, result = qa("full.mp4", extra=("--overlay-spec", spec(["MW4 OPEN BETA", "THIS WEEKEND"])))
        c = self.clip(proc, result, "full.mp4")
        self.assertEqual(c["verdict"], "PASS", c["issues"])
        self.assertEqual(proc.returncode, 0)

    def test_silent_audio_track_fails(self):
        proc, result = qa("silent.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "silent.mp4")).get("audio"), "FAIL")
        self.assertEqual(proc.returncode, 1)

    def test_missing_audio_stream_fails(self):
        proc, result = qa("noaudio.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "noaudio.mp4")).get("audio"), "FAIL")

    def test_frame_rate_other_than_the_briefs_fails(self):
        with open(os.path.join(TMP, "campaign_60fps.json"), "w") as f:
            json.dump({**CAMPAIGN, "render": {"fps": 60}}, f)
        proc, result = qa("full.mp4", campaign="campaign_60fps.json")
        self.assertEqual(self.levels(self.clip(proc, result, "full.mp4")).get("fps"), "FAIL")
        proc, result = qa("full.mp4")
        self.assertNotIn("fps", self.levels(self.clip(proc, result, "full.mp4")))

    def test_clip_under_the_brief_minimum_fails(self):
        proc, result = qa("short.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "short.mp4")).get("duration"), "FAIL")


class DeadAir(Asserts):
    def test_eight_seconds_of_silence_mid_clip_fails_dead_air(self):
        proc, result = qa("deadair.mp4")
        self.assertEqual(self.levels(self.clip(proc, result, "deadair.mp4")).get("dead_air"), "FAIL")

    def test_continuous_action_audio_has_no_dead_air_issue(self):
        proc, result = qa("full.mp4")
        self.assertNotIn("dead_air", self.levels(self.clip(proc, result, "full.mp4")))


class Overlap(Asserts):
    def test_clip_reusing_most_of_another_clips_footage_is_flagged_with_the_share(self):
        proc, result = qa("a_2to8.mp4", extra=("--against", os.path.join(TMP, "b_0to6.mp4")))
        c = self.clip(proc, result, "a_2to8.mp4")
        issue = next((i for i in c["issues"] if i["check"] == "overlap"), None)
        self.assertIsNotNone(issue, c["issues"])
        self.assertEqual(issue["level"], "WARN")
        self.assertIn("b_0to6.mp4", issue["msg"])

    def test_reuploading_an_already_made_clip_fails(self):
        # Instagram hides Reels "already posted"; TikTok and YouTube demote reused material without new edits.
        proc, result = qa("b_reupload.mp4", extra=("--against", os.path.join(TMP, "b_0to6.mp4")))
        self.assertEqual(self.levels(self.clip(proc, result, "b_reupload.mp4")).get("overlap"), "FAIL")
        self.assertEqual(proc.returncode, 1)

    def test_a_clip_is_not_its_own_duplicate_when_listed_again_by_another_path(self):
        # Checking new clips against "delivered/*.mp4" after copying them in must not compare a clip with itself.
        proc, result = qa("b_0to6.mp4", extra=("--against", os.path.join(TMP, ".", "b_0to6.mp4")))
        self.assertNotIn("overlap", self.levels(self.clip(proc, result, "b_0to6.mp4")))

    def test_unrelated_footage_is_not_flagged_as_overlap(self):
        proc, result = qa("c_other.mp4", extra=("--against", os.path.join(TMP, "b_0to6.mp4")))
        self.assertNotIn("overlap", self.levels(self.clip(proc, result, "c_other.mp4")))


class OnScreenRequirements(Asserts):
    def test_overlay_missing_a_required_phrase_fails(self):
        proc, result = qa("full.mp4", extra=("--overlay-spec", spec(["MW4 OPEN BETA", "SNIPER DOESN'T MISS"])))
        self.assertEqual(self.levels(self.clip(proc, result, "full.mp4")).get("onscreen_text"), "FAIL")

    def test_an_alternative_wording_listed_in_the_brief_passes(self):
        proc, result = qa("full.mp4", extra=("--overlay-spec", spec(["MW4 Beta   Weekend"])))
        self.assertNotIn("onscreen_text", self.levels(self.clip(proc, result, "full.mp4")))

    def test_overlay_without_a_logo_fails_when_the_brief_requires_one(self):
        proc, result = qa("full.mp4", extra=("--overlay-spec", spec(["MW4 OPEN BETA", "THIS WEEKEND"], logo=False)))
        self.assertEqual(self.levels(self.clip(proc, result, "full.mp4")).get("logo"), "FAIL")


if __name__ == "__main__":
    unittest.main()
