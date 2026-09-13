"""Black-box tests for hud_map.py on synthetic footage with known HUD and banner positions.

Backgrounds are blurred per-frame noise (always moving, like a first-person camera) or a frozen noise
texture (a player standing still). HUD pieces are drawn with drawbox at hand-picked coordinates:
  persistent HUD   hollow white box x80-379 y60-179, border 12 px, on screen the whole time
  banner           white bar x340-739 y400-459 with a black stripe, on screen from 2.0 to 3.5 s

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_hud_map.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.environ.get("HUD_MAP_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clip-overlay-builder/scripts/hud_map.py")

TMP = None
MOVING = "color=c=gray:s={s}:r=30:d={d},noise=alls=100:allf=t+u,boxblur=2:1"
STILL = "color=c=gray:s={s}:r=30:d={d},noise=alls=100:allf=u,boxblur=2:1"
HUD = "drawbox=x=80:y=60:w=300:h=120:color=white:t=12"
BANNER = ("drawbox=x=340:y=400:w=400:h=60:color=white:t=fill:enable='between(t,2,3.5)',"
          "drawbox=x=360:y=424:w=360:h=12:color=black:t=fill:enable='between(t,2,3.5)'")


def setUpModule():
    global TMP
    TMP = tempfile.mkdtemp(prefix="hud-test-")
    lavfi(os.path.join(TMP, "vertical.mp4"), f"{MOVING.format(s='1080x1920', d=6)},{HUD},{BANNER}")
    lavfi(os.path.join(TMP, "noise_only.mp4"), MOVING.format(s="1080x1920", d=4))
    lavfi(os.path.join(TMP, "still_then_moving.mp4"),
          f"{STILL.format(s='1080x1920', d=3)}[a];{MOVING.format(s='1080x1920', d=3)}[b];[a][b]concat=n=2:v=1:a=0")
    # two separate banners 160 px apart whose times overlap: 2.0-3.0 s and 2.8-3.8 s
    lavfi(os.path.join(TMP, "two_banners.mp4"),
          f"{MOVING.format(s='1080x1920', d=6)},"
          "drawbox=x=340:y=400:w=200:h=60:color=white:t=fill:enable='between(t,2,3)',"
          "drawbox=x=360:y=424:w=160:h=12:color=black:t=fill:enable='between(t,2,3)',"
          "drawbox=x=700:y=400:w=200:h=60:color=white:t=fill:enable='between(t,2.8,3.8)',"
          "drawbox=x=720:y=424:w=160:h=12:color=black:t=fill:enable='between(t,2.8,3.8)'")
    with open(os.path.join(TMP, "wide_sub.boxes.json"), "w") as f:
        json.dump({"canvas": [1080, 1920], "elements": [{"id": "sub", "type": "text", "box": [340, 380, 900, 440]}]}, f)
    lavfi(os.path.join(TMP, "landscape.mp4"),
          f"{MOVING.format(s='1920x1080', d=4)},drawbox=x=700:y=100:w=200:h=100:color=white:t=10,"
          f"drawbox=x=100:y=100:w=300:h=100:color=white:t=10")
    with open(os.path.join(TMP, "overlay.boxes.json"), "w") as f:
        json.dump({"canvas": [1080, 1920], "elements": [
            {"id": "hook", "type": "text", "box": [60, 100, 300, 150]},
            {"id": "sub", "type": "text", "box": [360, 380, 720, 440]},
            {"id": "logo", "type": "image", "box": [380, 1340, 700, 1470]}]}, f)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def lavfi(path, graph):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-filter_complex", graph, "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", path], check=True)


def hud_map(video, *extra):
    out = os.path.join(TMP, os.path.basename(video) + f".{abs(hash(extra))}.json")
    proc = subprocess.run([sys.executable, SCRIPT, video, "--json", out, "--no-png", *extra],
                          capture_output=True, text=True)
    if not os.path.exists(out):
        return proc, None
    with open(out) as f:
        return proc, json.load(f)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Asserts(unittest.TestCase):
    def assertMapped(self, proc, result):
        self.assertEqual(proc.returncode, 0, proc.stderr[-1200:])
        self.assertIsNotNone(result, "no JSON written")

    def assertNear(self, box, want, tol):
        self.assertTrue(all(abs(a - b) <= tol for a, b in zip(box, want)), f"box {box} is not within {tol}px of {want}")


class VerticalFootage(Asserts):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.map = hud_map(os.path.join(TMP, "vertical.mp4"))
        cls.boxed_proc, cls.boxed = hud_map(os.path.join(TMP, "vertical.mp4"), "--boxes",
                                            os.path.join(TMP, "overlay.boxes.json"))

    def test_persistent_hud_is_found_where_it_is_drawn(self):
        self.assertMapped(self.proc, self.map)
        near = [h["box"] for h in self.map["hud"] if overlaps(h["box"], [80, 60, 380, 180])]
        self.assertEqual(len(near), 1, f"hud boxes: {self.map['hud']}")
        self.assertNear(near[0], [80, 60, 380, 180], 40)

    def test_banner_is_an_event_only_while_it_is_on_screen(self):
        self.assertMapped(self.proc, self.map)
        hits = [e for e in self.map["events"] if overlaps(e["box"], [340, 400, 740, 460])]
        self.assertEqual(len(hits), 1, f"events: {self.map['events']}")
        self.assertTrue(1.8 <= hits[0]["t0"] <= 2.5 and 3.1 <= hits[0]["t1"] <= 3.8, hits[0])
        self.assertFalse(any(overlaps(h["box"], [340, 400, 740, 460]) for h in self.map["hud"]),
                         "a 1.5 s banner was classed as permanent HUD")

    def test_moving_background_alone_registers_nothing(self):
        self.assertMapped(self.proc, self.map)
        empty = [0, 700, 1080, 1920]
        self.assertEqual([h for h in self.map["hud"] if overlaps(h["box"], empty)], [])
        self.assertEqual([e for e in self.map["events"] if overlaps(e["box"], empty)], [])

    def test_overlay_element_over_a_banner_collides_for_that_time_only(self):
        self.assertMapped(self.boxed_proc, self.boxed)
        banner = [c for c in self.boxed["collisions"] if c["kind"] == "banner"]
        self.assertEqual({c["element"] for c in banner}, {"sub"})
        self.assertTrue(1.8 <= banner[0]["t0"] <= 2.5 and 3.1 <= banner[0]["t1"] <= 3.8, banner[0])

    def test_overlay_element_over_persistent_hud_collides(self):
        self.assertMapped(self.boxed_proc, self.boxed)
        hud = {c["element"] for c in self.boxed["collisions"] if c["kind"] == "hud"}
        self.assertEqual(hud, {"hook"})


class CollisionSummary(Asserts):
    def test_fragmented_collisions_merge_into_one_time_range_per_element(self):
        # Real footage splits one busy stretch into many small events; the editor needs one line per element.
        proc, result = hud_map(os.path.join(TMP, "two_banners.mp4"), "--boxes", os.path.join(TMP, "wide_sub.boxes.json"))
        self.assertMapped(proc, result)
        self.assertEqual(len([c for c in result["collisions"] if c["element"] == "sub"]), 2, result["collisions"])
        self.assertIn("summary", result)
        sub = next(s for s in result["summary"] if s["element"] == "sub")
        self.assertEqual(len(sub["ranges"]), 1, sub)
        t0, t1 = sub["ranges"][0]
        self.assertTrue(1.8 <= t0 <= 2.5 and 3.3 <= t1 <= 4.1, sub)
        self.assertAlmostEqual(sub["seconds"], t1 - t0, delta=0.05)
        self.assertFalse(sub["over_persistent_hud"])


class Backgrounds(Asserts):
    def test_pure_moving_noise_has_no_hud_and_no_events(self):
        proc, result = hud_map(os.path.join(TMP, "noise_only.mp4"))
        self.assertMapped(proc, result)
        self.assertEqual((result["hud"], result["events"]), ([], []))

    def test_a_still_camera_does_not_turn_the_background_into_hud(self):
        # Standing still freezes every background edge; counting that as HUD would make every layout collide.
        proc, result = hud_map(os.path.join(TMP, "still_then_moving.mp4"))
        self.assertMapped(proc, result)
        self.assertEqual((result["hud"], result["events"]), ([], []))


class MapImage(Asserts):
    def test_writes_a_map_image_beside_the_json_by_default(self):
        out = os.path.join(TMP, "with_png.json")
        proc = subprocess.run([sys.executable, SCRIPT, os.path.join(TMP, "noise_only.mp4"), "--json", out],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
        png = os.path.join(TMP, "with_png.png")
        self.assertTrue(os.path.exists(png), "no map image written")
        from PIL import Image
        with Image.open(png) as img:
            self.assertEqual(img.size, (540, 960))


class LandscapeSource(Asserts):
    def test_landscape_source_is_mapped_through_the_centred_916_crop(self):
        # Crop is x 656-1263 scaled by 1080/608: source box x700-899 y100-199 -> output ~[78, 178, 433, 355].
        proc, result = hud_map(os.path.join(TMP, "landscape.mp4"))
        self.assertMapped(proc, result)
        self.assertEqual(len(result["hud"]), 1, f"hud boxes: {result['hud']}")
        self.assertNear(result["hud"][0]["box"], [78, 178, 433, 355], 40)


if __name__ == "__main__":
    unittest.main()
