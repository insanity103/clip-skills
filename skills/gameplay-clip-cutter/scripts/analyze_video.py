#!/usr/bin/env python3
"""Measure what happens moment-to-moment in a video so beats, dead air and hard cuts can be found without watching all of it.

Signals per sample:
  audio_db  RMS loudness (dBFS) - gunfire, explosions, callouts
  motion    mean abs luma change vs previous sample - camera/scene activity
  luma      mean brightness - dark/murky footage
  red       fraction of strongly red pixels - damage vignettes, death screens
  scene     ffmpeg scene-change score (full mode) - hard cuts between clips in a stringout

Modes:
  full  decode --rate fps (default 10). Accurate; ~realtime on a slow laptop.
  fast  keyframes only (~1/s) + 10 Hz audio. ~5x faster; use for first pass on long sources.

Usage:
  analyze_video.py SOURCE.mp4 [--mode fast|full] [--start S] [--end E] [--rate 10] [--out X.timeline.json]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops, ImageStat

RED_LUT = [255 if v > 45 else 0 for v in range(256)]


def fesc(path):
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffprobe failed on {path}: {r.stderr.strip()}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        sys.exit(f"no video stream in {path}")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    return {
        "path": os.path.abspath(path),
        "duration": float(j["format"].get("duration") or v.get("duration") or 0),
        "width": int(v["width"]),
        "height": int(v["height"]),
        "fps": round(float(num) / float(den), 3) if float(den) else 0.0,
        "vcodec": v.get("codec_name"),
        "has_audio": a is not None,
    }


def window(start, end):
    args = []
    if start > 0:
        args += ["-ss", f"{start:.3f}"]
    if end is not None:
        args += ["-t", f"{end - start:.3f}"]
    return args


def frame_metrics(img, prev_gray):
    g = img.convert("L")
    motion = ImageStat.Stat(ImageChops.difference(g, prev_gray)).mean[0] if prev_gray is not None else 0.0
    r, gg, b = img.split()
    mask = ImageChops.darker(ImageChops.subtract(r, gg).point(RED_LUT), ImageChops.subtract(r, b).point(RED_LUT))
    thumb = g.resize((16, 9) if img.width > img.height else (9, 16), Image.BOX).tobytes()
    return g, motion, ImageStat.Stat(g).mean[0], ImageStat.Stat(mask).mean[0] / 255.0, thumb


def cut_scores(thumbs, k):
    """Hard cuts persist; flashes and whip-pans don't.

    jump = change between consecutive samples; step = change between the mean of the k samples
    before and the k samples after. A real cut has a large jump AND a step nearly as large.
    """
    n, px = len(thumbs), len(thumbs[0]) if thumbs else 0
    jump, step = [0.0] * n, [0.0] * n
    for i in range(1, n):
        a, b = thumbs[i - 1], thumbs[i]
        jump[i] = sum(abs(a[j] - b[j]) for j in range(px)) / (255.0 * px)
        lo, hi = max(0, i - k), min(n, i + k)
        if i - lo < 2 or hi - i < 2:
            continue
        pre = [sum(thumbs[t][j] for t in range(lo, i)) / (i - lo) for j in range(px)]
        post = [sum(thumbs[t][j] for t in range(i, hi)) / (hi - i) for j in range(px)]
        step[i] = sum(abs(pre[j] - post[j]) for j in range(px)) / (255.0 * px)
    return jump, step


def audio_levels(path, start, end, rate):
    n = max(1, int(round(8000 / rate)))
    with tempfile.TemporaryDirectory() as td:
        meta = os.path.join(td, "audio.txt")
        af = (f"aformat=channel_layouts=mono,aresample=8000,asetnsamples=n={n}:p=0,"
              f"astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file={fesc(meta)}")
        cmd = ["ffmpeg", "-v", "error", "-nostdin", *window(start, end), "-i", path, "-vn", "-af", af, "-f", "null", "-"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode or not os.path.exists(meta):
            print(f"warning: audio analysis failed: {r.stderr.strip()[:300]}", file=sys.stderr)
            return [], []
        ts, db = [], []
        cur = None
        for line in open(meta):
            m = re.search(r"pts_time:([0-9.]+)", line)
            if m:
                cur = float(m.group(1))
                continue
            if "RMS_level=" in line and cur is not None:
                val = line.strip().split("=", 1)[1]
                db.append(-90.0 if "inf" in val else max(-90.0, float(val)))
                ts.append(round(start + cur, 3))
        return ts, db


def read_frames(cmd, size, stderr):
    w, h = size
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr)
    rows, thumbs, prev, fsz = [], [], None, w * h * 3
    while True:
        buf = p.stdout.read(fsz)
        if len(buf) < fsz:
            break
        prev, motion, luma, red, thumb = frame_metrics(Image.frombuffer("RGB", (w, h), buf, "raw", "RGB", 0, 1), prev)
        rows.append([motion, luma, red])
        thumbs.append(thumb)
    p.wait()
    return p.returncode, rows, thumbs


def video_full(path, start, end, rate, size):
    w, h = size
    with tempfile.TemporaryFile("w+") as err:
        cmd = ["ffmpeg", "-v", "error", "-nostdin", *window(start, end), "-i", path, "-an",
               "-vf", f"fps={rate},scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        code, rows, thumbs = read_frames(cmd, size, err)
        if code and not rows:
            err.seek(0)
            sys.exit(f"ffmpeg video decode failed: {err.read()[:400]}")
    return [round(start + i / rate, 3) for i in range(len(rows))], rows, thumbs


def video_keyframes(path, start, end, size):
    w, h = size
    with tempfile.TemporaryDirectory() as td:
        errp = os.path.join(td, "info.txt")
        with open(errp, "w") as err:
            cmd = ["ffmpeg", "-v", "info", "-nostdin", "-skip_frame", "nokey", *window(start, end), "-i", path,
                   "-an", "-vf", f"scale={w}:{h}:flags=area,showinfo", "-fps_mode", "passthrough",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            code, rows, thumbs = read_frames(cmd, size, err)
        pts = [float(x) for x in re.findall(r"pts_time:\s*([0-9.]+)", open(errp).read())]
    n = min(len(pts), len(rows))
    return [round(start + t, 3) for t in pts[:n]], rows[:n], thumbs[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--mode", choices=["fast", "full"], help="default: fast for sources over 4 min, else full")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--rate", type=float, default=10.0, help="samples/sec in full mode (default 10)")
    ap.add_argument("--out", help="default: <video>.timeline.json (or <video>.<start>-<end>.timeline.json)")
    args = ap.parse_args()

    meta = probe(args.video)
    end = min(args.end, meta["duration"]) if args.end is not None else None
    span = (end if end is not None else meta["duration"]) - args.start
    mode = args.mode or ("fast" if span > 240 else "full")
    portrait = meta["height"] > meta["width"]
    size = (90, 160) if portrait else (160, 90)

    t0 = time.time()
    a_t, a_db = audio_levels(args.video, args.start, end, 10.0) if meta["has_audio"] else ([], [])
    out = {"meta": meta, "mode": mode, "start": args.start, "end": end if end is not None else meta["duration"],
           "audio": {"rate": 10.0, "t": a_t, "db": [round(x, 2) for x in a_db]}}
    if mode == "full":
        v_t, rows, thumbs = video_full(args.video, args.start, end, args.rate, size)
        out["video"] = {"rate": args.rate, "t": v_t}
        jump, step = cut_scores(thumbs, k=max(2, int(round(args.rate * 0.4))))
    else:
        v_t, rows, thumbs = video_keyframes(args.video, args.start, end, size)
        out["video"] = {"rate": None, "t": v_t}
        jump, step = cut_scores(thumbs, k=2)
    out["video"]["motion"] = [round(r[0], 3) for r in rows]
    out["video"]["luma"] = [round(r[1], 2) for r in rows]
    out["video"]["red"] = [round(r[2], 4) for r in rows]
    out["video"]["jump"] = [round(x, 4) for x in jump]
    out["video"]["step"] = [round(x, 4) for x in step]
    out["elapsed_sec"] = round(time.time() - t0, 1)

    if args.out:
        dest = args.out
    else:
        base = os.path.splitext(args.video)[0]
        dest = f"{base}.timeline.json" if args.start == 0 and args.end is None else f"{base}.{args.start:g}-{out['end']:g}.timeline.json"
    with open(dest, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"{os.path.basename(args.video)}: {mode} mode, {len(v_t)} video samples, {len(a_t)} audio samples, "
          f"{span:.1f}s analysed in {out['elapsed_sec']}s -> {dest}")


if __name__ == "__main__":
    main()
