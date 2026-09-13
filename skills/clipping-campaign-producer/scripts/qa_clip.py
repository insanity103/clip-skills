#!/usr/bin/env python3
"""Last check on rendered clips before posting: format, framing, audio, length, dead air, reused footage and the
brief's on-screen requirements.

  qa_clip.py clip1.mp4 clip2.mp4 --campaign campaign.json --overlay-spec overlay.json
  qa_clip.py clip5.mp4 --campaign campaign.json --against "previous (flagged)/clip 5.mp4" --ref SRC.timeline.json

Exit status 1 if any clip FAILs. Checks:
  format         H.264 yuv420p at 1080x1920 (other 9:16 sizes WARN), at most 60 fps
  duration       inside the campaign's duration.min / duration.max
  fps            equal to the campaign's render.fps when the brief sets one
  full_frame     black bars, or a sharp gameplay band over a blurred copy - the letterbox layout that got every
                 clip in its round flagged
  sharpness      fine detail in the centre of the frame: blurry or upscaled-from-low-res footage FAILs, soft WARNs
  audio          an audio stream that is not silent
  dead_air       the calibrated dead-air rules from gameplay-clip-cutter (pass --ref with the source timeline for
                 trustworthy loudness levels); skipped with a WARN if those scripts cannot be found
  overlap        share of this clip's gameplay also found in the other clips given, or in --against clips (pass
                 every clip already made for the campaign): 80%+ FAILs as a re-post, 50%+ WARNs
  onscreen_text  one of the campaign's onscreen.required_text_any sets, read from the overlay spec's text
  logo           an image element in the overlay spec when onscreen.logo_required
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops, ImageFilter, ImageStat

AW, AH = 270, 480
HERE = os.path.dirname(os.path.abspath(__file__))


def cutter_dir():
    for d in (os.environ.get("CLIP_CUTTER_SCRIPTS"), os.path.join(HERE, "..", "..", "gameplay-clip-cutter", "scripts"),
              os.path.expanduser("~/.claude/skills/gameplay-clip-cutter/scripts")):
        if d and os.path.exists(os.path.join(d, "find_beats.py")):
            return os.path.abspath(d)
    return None


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode:
        return None
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        return None
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    return {"vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"), "w": int(v["width"]), "h": int(v["height"]),
            "fps": float(num) / float(den) if float(den) else 0.0,
            "duration": float(j["format"].get("duration") or v.get("duration") or 0),
            "acodec": a.get("codec_name") if a else None}


def frames(path, fps=2):
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-an", "-vf", f"fps={fps},scale={AW}:{AH},format=gray",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    data = subprocess.run(cmd, capture_output=True).stdout
    n = len(data) // (AW * AH)
    return [Image.frombytes("L", (AW, AH), data[i * AW * AH:(i + 1) * AW * AH]) for i in range(n)]


def column_means(img):
    col = img.convert("F").resize((1, AH), Image.BOX)
    return list(col.get_flattened_data() if hasattr(col, "get_flattened_data") else col.getdata())


def row_profile(img):
    grad = ImageChops.difference(img.crop((1, 0, AW, AH)), img.crop((0, 0, AW - 1, AH)))
    return column_means(img), column_means(grad)


def framing(imgs):
    bars = blurred = 0
    for img in imgs:
        luma, sharp = row_profile(img)
        flat = [l < 18 and s < 2 for l, s in zip(luma, sharp)]
        top = next((i for i, f in enumerate(flat) if not f), AH)
        bottom = next((i for i, f in enumerate(reversed(flat)) if not f), AH)
        if top + bottom >= 0.10 * AH:
            bars += 1
            continue
        mid = statistics.median(sharp[int(AH * 0.40):int(AH * 0.60)])
        ends = max(statistics.median(sharp[int(AH * 0.05):int(AH * 0.25)]),
                   statistics.median(sharp[int(AH * 0.75):int(AH * 0.95)]))
        # MW4 calibration: every full-frame frame scored ends/mid >= 0.82, every letterbox frame <= 0.67
        if mid >= 2 and ends < 0.5 * mid:
            blurred += 1
    n = max(1, len(imgs))
    if bars + blurred >= 0.6 * n:
        kind = ("black bars above and below the gameplay" if bars >= blurred
                else "gameplay in a sharp band over a blurred copy (letterbox fill)")
        return f"{kind} in {bars + blurred} of {n} sampled frames - render full-frame 9:16 instead"
    return None


def sharpness(path, meta, samples=8):
    """Fine-detail share of the centre 540 px square: soft or upscaled-from-low-res footage loses fine detail first."""
    s = min(540, meta["w"], meta["h"])
    vals = []
    for k in range(samples):
        t = meta["duration"] * (k + 0.5) / samples
        r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf",
                            f"crop={s}:{s}:{(meta['w'] - s) // 2}:{(meta['h'] - s) // 2},format=gray",
                            "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
        if len(r.stdout) != s * s:
            continue
        img = Image.frombytes("L", (s, s), r.stdout)
        if ImageStat.Stat(img).stddev[0] < 4:
            continue  # black screen, fade or flat menu: says nothing about focus
        coarse = ImageStat.Stat(ImageChops.difference(img, img.filter(ImageFilter.GaussianBlur(4)))).mean[0]
        fine = ImageStat.Stat(ImageChops.difference(img, img.filter(ImageFilter.GaussianBlur(1)))).mean[0]
        vals.append(fine / coarse if coarse >= 0.2 else 0.0)  # picture content with no detail left at all
    return statistics.median(vals) if vals else None


def dhash(img):
    band = img.crop((0, int(AH * 0.30), AW, int(AH * 0.65))).resize((9, 8), Image.BOX).tobytes()
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (band[y * 9 + x] > band[y * 9 + x + 1])
    return bits


def overlap(hashes, other):
    if not hashes or not other:
        return 0.0
    return sum(1 for h in hashes if min(bin(h ^ o).count("1") for o in other) <= 10) / len(hashes)


def max_volume(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostdin", "-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"max_volume:\s*(-?[\d.]+|-inf) dB", r.stderr)
    return -91.0 if not m or m.group(1) == "-inf" else float(m.group(1))


def dead_air(path, duration, ref, tools):
    with tempfile.TemporaryDirectory() as td:
        tl, out = os.path.join(td, "clip.timeline.json"), os.path.join(td, "validate.json")
        r = subprocess.run([sys.executable, os.path.join(tools, "analyze_video.py"), path, "--mode", "full", "--out", tl],
                           capture_output=True, text=True)
        if r.returncode:
            return [("WARN", f"dead-air analysis failed: {r.stderr.strip()[-200:]}")]
        cmd = [sys.executable, os.path.join(tools, "find_beats.py"), tl, "--validate", f"0:{max(0.1, duration - 0.05):.2f}",
               "--min-total", "0", "--json", out]
        if ref:
            cmd += ["--ref", ref]
        subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.exists(out):
            return [("WARN", "dead-air validation produced no result")]
        issues = json.load(open(out))["validation"]["issues"]
    return [(i["level"], i["msg"]) for i in issues if "dead air" in i["msg"] and i["level"] in ("FAIL", "WARN")]


def norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def onscreen(spec, rules):
    issues = []
    texts = " | ".join(norm(e.get("text", "")) for e in spec.get("elements", []) if e.get("type") == "text")
    sets = rules.get("required_text_any", [])
    if sets and not any(all(norm(p) in texts for p in s) for s in sets):
        options = " or ".join(" + ".join(f'"{p}"' for p in s) for s in sets)
        issues.append(("FAIL", "onscreen_text", f"overlay text needs {options}"))
    if rules.get("logo_required") and not any(e.get("type") == "image" for e in spec.get("elements", [])):
        issues.append(("FAIL", "logo", "the brief requires the logo on screen but the overlay has no image element"))
    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--overlay-spec", help="the build_overlay.py spec JSON used for these clips")
    ap.add_argument("--against", nargs="*", default=[], help="other clips to check reused footage against (e.g. flagged ones)")
    ap.add_argument("--ref", help="source timeline JSON for loudness levels in the dead-air check")
    ap.add_argument("--json", help="write results as JSON")
    args = ap.parse_args()

    campaign = json.load(open(args.campaign))
    spec = json.load(open(args.overlay_spec)) if args.overlay_spec else None
    tools = cutter_dir()
    hashes = {p: [dhash(f) for f in frames(p)] for p in dict.fromkeys(args.clips + args.against) if os.path.exists(p)}
    results = []
    for path in args.clips:
        issues = []

        def add(level, check, msg):
            issues.append({"check": check, "level": level, "msg": msg})

        meta = probe(path) if os.path.exists(path) else None
        if meta is None:
            add("FAIL", "format", "not a readable video file")
            results.append({"clip": os.path.abspath(path), "verdict": "FAIL", "issues": issues})
            continue
        if meta["vcodec"] != "h264" or meta["pix_fmt"] != "yuv420p":
            add("FAIL", "format", f"{meta['vcodec']} {meta['pix_fmt']} - upload copies should be H.264 yuv420p")
        if (meta["w"], meta["h"]) != (1080, 1920):
            if abs(meta["w"] / meta["h"] - 9 / 16) < 0.01:
                add("WARN", "format", f"{meta['w']}x{meta['h']} is 9:16 but not 1080x1920")
            else:
                add("FAIL", "format", f"{meta['w']}x{meta['h']} is not a 9:16 vertical frame")
        if meta["fps"] > 60.5:
            add("FAIL", "format", f"{meta['fps']:.2f} fps - keep uploads at 60 fps or less")
        want_fps = campaign.get("render", {}).get("fps")
        if want_fps and abs(meta["fps"] - float(want_fps)) > 0.05:
            add("FAIL", "fps", f"{meta['fps']:.2f} fps - the brief requires {float(want_fps):g} fps "
                               f"(render with --fps {float(want_fps):g})")

        dur = campaign.get("duration", {})
        if meta["duration"] < dur.get("min", 0) - 0.05:
            add("FAIL", "duration", f"{meta['duration']:.1f}s is under the brief's {dur['min']}s minimum")
        if "max" in dur and meta["duration"] > dur["max"] + 0.05:
            add("FAIL", "duration", f"{meta['duration']:.1f}s is over the brief's {dur['max']}s maximum")

        problem = framing(frames(path, fps=max(0.5, 8 / max(1.0, meta["duration"]))))
        if problem:
            add("FAIL", "full_frame", problem)

        # calibrated: 5 delivered MW4 clips 0.15-0.21, heavy blur 0.04. Mild softness overlaps sharp footage, so only
        # clearly blurry clips FAIL; low-resolution sources are caught exactly by render_vertical's upscale warning.
        sharp = sharpness(path, meta)
        if sharp is None:
            add("WARN", "sharpness", "not measured - every sampled frame was flat (black or a single colour)")
        elif sharp < 0.13:
            add("FAIL" if sharp < 0.09 else "WARN", "sharpness",
                f"footage is {'blurry' if sharp < 0.09 else 'slightly soft'} (sharpness {sharp:.2f}; sharp clips measure "
                f"0.15+) - TikTok and Instagram do not recommend blurry or low-resolution video; use a 1080p-or-better source")

        if meta["acodec"] is None:
            add("FAIL", "audio", "no audio stream - platforms and the brief expect the original game audio")
        else:
            peak = max_volume(path)
            if peak <= -50:
                add("FAIL", "audio", f"audio track is silent (peak {peak:.0f} dB)")
            if meta["acodec"] != "aac":
                add("WARN", "audio", f"audio codec is {meta['acodec']}, AAC is the safe choice")
            if tools:
                for level, msg in dead_air(path, meta["duration"], args.ref, tools):
                    add(level, "dead_air", msg)
            else:
                add("WARN", "dead_air", "not checked - gameplay-clip-cutter scripts not found")

        mine = hashes.get(path, [])
        for other in dict.fromkeys(args.clips + args.against):
            if os.path.realpath(other) == os.path.realpath(path) or other not in hashes:
                continue
            share = overlap(mine, hashes[other])
            if share >= 0.8:
                add("FAIL", "overlap", f"{share:.0%} of this clip's gameplay is already in {os.path.basename(other)} - "
                                       f"platforms hide re-posted and reused clips; re-cut from different beats")
            elif share >= 0.5:
                add("WARN", "overlap", f"{share:.0%} of this clip's gameplay also appears in {os.path.basename(other)}")

        if spec is not None:
            for level, check, msg in onscreen(spec, campaign.get("onscreen", {})):
                add(level, check, msg)
        elif campaign.get("onscreen"):
            add("WARN", "onscreen_text", "on-screen requirements not checked - pass --overlay-spec")

        verdict = "FAIL" if any(i["level"] == "FAIL" for i in issues) else "WARN" if issues else "PASS"
        results.append({"clip": os.path.abspath(path), "verdict": verdict, "issues": issues,
                        "stats": {"duration": round(meta["duration"], 2), "size": [meta["w"], meta["h"]],
                                  "fps": round(meta["fps"], 3)}})

    overall = "FAIL" if any(r["verdict"] == "FAIL" for r in results) else \
        "WARN" if any(r["verdict"] == "WARN" for r in results) else "PASS"
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"verdict": overall, "clips": results}, f, indent=1)
    for r in results:
        print(f"{os.path.basename(r['clip'])}: {r['verdict']}")
        for i in r["issues"]:
            print(f"  {i['level']:<4}  {i['check']}: {i['msg']}")
    sys.exit(1 if overall == "FAIL" else 0)


if __name__ == "__main__":
    main()
