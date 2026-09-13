#!/usr/bin/env python3
"""Render beats into a full-frame vertical (1080x1920) clip: crop, push-in, sharpen, overlay, encode.

The frame is always filled with footage. Never letterbox or blur-fill: that is what got clips flagged.

  render_vertical.py --src SRC.mp4 --edl "91.5:4,125.5:2.5:40,133:9" --overlay ov.png --out clip.mp4
  render_vertical.py --edit clip.json            # beats from several sources, per-beat crop offsets
  render_vertical.py --jobs batch.json           # several clips, strictly one after another
  render_vertical.py ... --preview-at 6.5 --out frame.png      # one still at output time 6.5s, no encode

EDL: comma-separated start:dur[:x] in source seconds. x shifts that beat's crop right (+) or left (-) in
source pixels and is clamped to the frame; --x is the default for beats without one.
Edit JSON: {"out": "clip.mp4", "overlay": "ov.png", "zoom": 0.08, "x": 0,
            "beats": [{"src": "a.mp4", "start": 91.5, "dur": 4, "x": 35}, ...]}
Relative paths resolve against the JSON file. Jobs JSON: {"jobs": [edit, edit, ...]}.
In --src mode --zoom/--x/--overlay apply; in --edit/--jobs mode the JSON carries them.

--quality final   x264 medium crf 18: the upload copy
--quality draft   hardware (VideoToolbox) or x264 veryfast: several times faster, for checking an edit
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time

OUT_W, OUT_H = 1080, 1920
DEFAULT_ZOOM = 0.08


def die(msg):
    sys.exit(f"render_vertical: {msg}")


def even(v):
    return int(v) // 2 * 2


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode:
        die(f"cannot read {path}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        die(f"no video stream in {path}")
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    return {"w": int(v["width"]), "h": int(v["height"]), "rate": v.get("avg_frame_rate"),
            "fps": float(num) / float(den) if float(den) else 0.0,
            "duration": float(j["format"].get("duration") or v.get("duration") or 0),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def canvas(zoom):
    """Push-in works by cropping into a canvas this much larger than the output, so it never upscales."""
    return (even(OUT_W * (1 + zoom)), even(OUT_H * (1 + zoom))) if zoom > 0 else (OUT_W, OUT_H)


def crop_box(w, h, x_off):
    if w * 16 >= h * 9:
        cw, ch = even(round(h * 9 / 16)), even(h)
    else:
        cw, ch = even(w), even(round(w * 16 / 9))
    want = (w - cw) // 2 + x_off
    cx = min(max(want, 0), w - cw)
    return cw, ch, cx, (h - ch) // 2, cx != want


def sharpen_amount(upscale):
    return 0.9 if upscale >= 1.5 else 0.5 if upscale >= 1.15 else 0.0


def output_rate(metas, override=None):
    if override:
        return f"{override:g}", float(override)
    fastest = max(metas, key=lambda m: m["fps"])
    if len({m["rate"] for m in metas}) == 1 and fastest["fps"] <= 60.5:
        return fastest["rate"], fastest["fps"]
    return ("60", 60.0) if fastest["fps"] > 30.5 else ("30", 30.0)


def parse_edl(text, src, default_x):
    beats = []
    for part in text.split(","):
        bits = part.strip().split(":")
        if len(bits) not in (2, 3):
            die(f"bad EDL entry '{part.strip()}': use start:dur or start:dur:x")
        beats.append({"src": src, "start": float(bits[0]), "dur": float(bits[1]),
                      "x": int(float(bits[2])) if len(bits) == 3 else default_x})
    return beats


def load_edit(spec, base):
    def res(p):
        if p is None:
            return None
        p = os.path.expanduser(p)
        return p if os.path.isabs(p) else os.path.join(base, p)

    return {"out": res(spec["out"]), "overlay": res(spec.get("overlay")),
            "zoom": float(spec.get("zoom", DEFAULT_ZOOM)), "fps": float(spec["fps"]) if spec.get("fps") else None,
            "beats": [{"src": res(b["src"]), "start": float(b["start"]), "dur": float(b["dur"]),
                       "x": int(b.get("x", spec.get("x", 0)))} for b in spec["beats"]]}


def check(edit):
    if not edit["beats"]:
        die("the edit has no beats")
    metas = {}
    for n, b in enumerate(edit["beats"], 1):
        if b["src"] not in metas:
            if not os.path.exists(b["src"]):
                die(f"beat {n}: source not found: {b['src']}")
            metas[b["src"]] = probe(b["src"])
        m = metas[b["src"]]
        if b["dur"] <= 0 or b["start"] < 0 or b["start"] + b["dur"] > m["duration"] + 0.05:
            die(f"beat {n} ({b['start']:g}:{b['dur']:g}) is outside {os.path.basename(b['src'])} "
                f"(0-{m['duration']:.2f}s)")
    if edit["overlay"]:
        if not os.path.exists(edit["overlay"]):
            die(f"overlay not found: {edit['overlay']}")
        o = probe(edit["overlay"])
        if abs(o["w"] / o["h"] - 9 / 16) > 0.01:
            die(f"overlay {os.path.basename(edit['overlay'])} is {o['w']}x{o['h']}: it must be a full-frame 9:16 "
                f"transparent PNG (a bare logo would be stretched over the whole frame) - build it with build_overlay.py")
    return [metas[b["src"]] for b in edit["beats"]]


def post_chain(label, zoom, total, rate, fps, upscale):
    if zoom > 0:
        nf = max(1, round(total * fps))
        chain = (f"[{label}]zoompan=z='1+{zoom}*on/{nf}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                 f":s={OUT_W}x{OUT_H}:fps={rate}")
    else:
        chain = f"[{label}]null"
    amt = sharpen_amount(upscale)
    return chain + (f",unsharp=5:5:{amt}:5:5:0.0" if amt else "") + ",setsar=1"


def build_graph(edit, metas, rate, fps):
    zoom = edit["zoom"]
    zw, zh = canvas(zoom)
    parts, pads, ups = [], [], []
    total = sum(b["dur"] for b in edit["beats"])
    for i, (b, m) in enumerate(zip(edit["beats"], metas)):
        cw, ch, cx, cy, clamped = crop_box(m["w"], m["h"], b["x"])
        if clamped:
            print(f"warning: beat {i + 1} crop offset {b['x']} clamped to the frame edge", file=sys.stderr)
        ups.append(OUT_W / cw)
        if OUT_W / cw > 2.0:
            print(f"warning: beat {i + 1} upscales {OUT_W / cw:.1f}x ({m['w']}x{m['h']} source) - expect a soft clip; "
                  f"TikTok and Instagram demote blurry, low-resolution video. Use a 1080p-or-better source.",
                  file=sys.stderr)
        parts.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={rate},crop={cw}:{ch}:{cx}:{cy},"
                     f"scale={zw}:{zh}:flags=lanczos,setsar=1,format=yuv420p[v{i}]")
        d, fade = b["dur"], min(0.06, b["dur"] / 4)
        head = f"[{i}:a]asetpts=PTS-STARTPTS," if m["audio"] else "anullsrc=r=48000:cl=stereo,"
        parts.append(f"{head}aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
                     f"atrim=duration={d:.3f},afade=t=in:d={fade:.3f},afade=t=out:st={d - fade:.3f}:d={fade:.3f}[a{i}]")
        pads.append(f"[v{i}][a{i}]")
    n = len(edit["beats"])
    parts.append(f"{''.join(pads)}concat=n={n}:v=1:a=1[vc][ac]")
    chain = post_chain("vc", zoom, total, rate, fps, min(ups))
    if edit["overlay"]:
        parts.append(chain + "[vz]")
        parts.append(f"[{n}:v]scale={OUT_W}:{OUT_H},format=rgba[ov];[vz][ov]overlay=0:0,format=yuv420p[v]")
    else:
        parts.append(chain + ",format=yuv420p[v]")
    parts.append(f"[ac]afade=t=in:d=0.15,afade=t=out:st={max(0.0, total - 0.3):.3f}:d=0.3[a]")
    return ";".join(parts), total


def has_encoder(name):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return any(line.split()[1:2] == [name] for line in r.stdout.splitlines() if line.strip())


def encoder_args(quality, fps):
    gop = str(max(1, round(fps * 2)))
    if quality == "final":
        video = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-level:v", "4.2"]
    elif has_encoder("h264_videotoolbox"):
        video = ["-c:v", "h264_videotoolbox", "-b:v", "12M"]
    else:
        video = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"]
    return video + ["-g", gop, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart"]


def run_ffmpeg(cmd, tmp):
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        _, err = proc.communicate()
    except BaseException:
        proc.kill()
        proc.wait()
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    if proc.returncode:
        if os.path.exists(tmp):
            os.remove(tmp)
        die(f"ffmpeg failed:\n{err.strip()[-800:]}")


def summarize(path, elapsed):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
                                   path], capture_output=True, text=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    print(f"{path}: {v['width']}x{v['height']} {v['avg_frame_rate']} fps, {float(j['format']['duration']):.2f}s, "
          f"audio {'aac ' + a['sample_rate'] + ' Hz' if a else 'NONE'}, {int(j['format']['size']) / 1e6:.1f} MB, "
          f"rendered in {elapsed:.0f}s")


def render(edit, quality):
    metas = check(edit)
    rate, fps = output_rate(metas, edit.get("fps"))
    graph, total = build_graph(edit, metas, rate, fps)
    out = edit["out"]
    root, ext = os.path.splitext(out)
    tmp = f"{root}.partial{ext or '.mp4'}"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    for b in edit["beats"]:
        cmd += ["-ss", f"{b['start']:.3f}", "-t", f"{b['dur']:.3f}", "-i", b["src"]]
    if edit["overlay"]:
        cmd += ["-i", edit["overlay"]]
    cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "[a]", *encoder_args(quality, fps), "-f", "mp4", tmp]
    print(f"rendering {os.path.basename(out)}: {len(edit['beats'])} beat(s), {total:.2f}s, {quality}", flush=True)
    t0 = time.time()
    run_ffmpeg(cmd, tmp)
    os.replace(tmp, out)
    summarize(out, time.time() - t0)


def preview(edit, t, out_png):
    metas = check(edit)
    total = sum(b["dur"] for b in edit["beats"])
    if not 0 <= t < total:
        die(f"--preview-at {t:g} is outside the edit (0-{total:.2f}s)")
    acc = 0.0
    for b, m in zip(edit["beats"], metas):
        if t < acc + b["dur"]:
            break
        acc += b["dur"]
    zoom = edit["zoom"]
    zw, zh = canvas(zoom)
    z = 1 + zoom * t / total
    cw, ch, cx, cy, _ = crop_box(m["w"], m["h"], b["x"])
    amt = sharpen_amount(OUT_W / cw)
    chain = (f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={zw}:{zh}:flags=lanczos,crop=w=iw/{z:.5f}:h=ih/{z:.5f},"
             f"scale={OUT_W}:{OUT_H}:flags=lanczos" + (f",unsharp=5:5:{amt}:5:5:0.0" if amt else "") + ",setsar=1")
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{b['start'] + t - acc:.3f}", "-i", b["src"]]
    if edit["overlay"]:
        cmd += ["-i", edit["overlay"]]
        graph = chain + f"[vz];[1:v]scale={OUT_W}:{OUT_H},format=rgba[ov];[vz][ov]overlay=0:0,format=rgb24[v]"
    else:
        graph = chain + ",format=rgb24[v]"
    r = subprocess.run(cmd + ["-filter_complex", graph, "-map", "[v]", "-frames:v", "1", out_png],
                       capture_output=True, text=True)
    if r.returncode or not os.path.exists(out_png):
        die(f"preview failed:\n{r.stderr.strip()[-800:]}")
    print(out_png)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--src", help="single source video (use with --edl)")
    mode.add_argument("--edit", help="edit JSON (beats from any sources)")
    mode.add_argument("--jobs", help="jobs JSON: several edits rendered one after another")
    ap.add_argument("--edl", help='"start:dur[:x],..." in source seconds (with --src)')
    ap.add_argument("--overlay", help="full-frame 1080x1920 transparent PNG (with --src)")
    ap.add_argument("--out", help="output .mp4 (or .png with --preview-at)")
    ap.add_argument("--x", type=int, default=0, help="default crop offset in source px (with --src)")
    ap.add_argument("--zoom", type=float, default=DEFAULT_ZOOM, help="push-in amount over the clip, 0 = none")
    ap.add_argument("--fps", type=float, help="output frame rate when a brief requires one (default: the source's, max 60)")
    ap.add_argument("--quality", choices=["final", "draft"], default="final")
    ap.add_argument("--preview-at", type=float, help="write one still at this output time instead of a video")
    args = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    if args.src:
        if not args.edl or not args.out:
            die("--src needs --edl and --out")
        edits = [{"out": args.out, "overlay": args.overlay, "zoom": args.zoom, "fps": None,
                  "beats": parse_edl(args.edl, args.src, args.x)}]
    elif args.edit:
        spec = json.load(open(args.edit))
        edits = [load_edit(spec, os.path.dirname(os.path.abspath(args.edit)))]
        if args.out:
            edits[0]["out"] = args.out
    else:
        spec = json.load(open(args.jobs))
        base = os.path.dirname(os.path.abspath(args.jobs))
        edits = [load_edit(j, base) for j in (spec["jobs"] if isinstance(spec, dict) else spec)]

    if args.fps:
        for edit in edits:
            edit["fps"] = args.fps
    if args.preview_at is not None:
        if len(edits) != 1 or not args.out:
            die("--preview-at needs a single edit and --out frame.png")
        preview(edits[0], args.preview_at, args.out)
        return
    for edit in edits:
        render(edit, args.quality)


if __name__ == "__main__":
    main()
