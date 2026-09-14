#!/usr/bin/env python3
"""Pick candidate cover-frame stills from a rendered clip: sharp, well-exposed, spread across the clip.

  pick_cover.py clip.mp4 --out-dir covers/
  pick_cover.py clip.mp4 --start 3 --end 11 --top 3 --out-dir covers/    # only look in the payoff window

Samples the clip at --fps candidate frames per second, scores each for sharpness (edge-detail variance)
and exposure (mean brightness), then returns the --top sharpest, well-exposed frames, at least
--min-gap seconds apart so they aren't all the same instant. Full-resolution PNGs, named by timestamp.

This only measures sharpness and exposure - it has no idea what's actually happening in the frame
(a sharp shot of a wall scores as well as a sharp shot of the kill). Pick a final cover from the
candidates by eye, favouring one that shows the clip's payoff or hook, not just whichever ranks first.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageFilter, ImageStat
except ImportError:
    sys.exit("pick_cover: needs Pillow - pip install pillow")


def die(msg):
    sys.exit(f"pick_cover: {msg}")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode:
        die(f"cannot read {path}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        die(f"no video stream in {path}")
    return {"w": int(v["width"]), "h": int(v["height"]),
            "duration": float(j["format"].get("duration") or v.get("duration") or 0)}


def extract_frames(src, start, end, fps, out_dir):
    pattern = os.path.join(out_dir, "f_%06d.png")
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{start:.3f}", "-i", src,
           "-t", f"{end - start:.3f}", "-vf", f"fps={fps}", pattern]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        die(f"ffmpeg frame extraction failed:\n{r.stderr.strip()[-800:]}")
    files = sorted(f for f in os.listdir(out_dir) if f.startswith("f_"))
    return [(start + i / fps, os.path.join(out_dir, f)) for i, f in enumerate(files)]


def score(path):
    img = Image.open(path).convert("L")
    edges = img.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).stddev[0]
    brightness = ImageStat.Stat(img).mean[0]
    return sharpness, brightness


def pick(candidates, top, min_gap, dark_floor, bright_ceiling):
    scored = [(t, path, *score(path)) for t, path in candidates]
    usable = [c for c in scored if dark_floor <= c[3] <= bright_ceiling]
    if not usable:
        print("warning: every candidate frame is very dark or blown out; exposure filter ignored", file=sys.stderr)
        usable = scored
    usable.sort(key=lambda c: c[2], reverse=True)
    picked = []
    for t, path, sharp, bright in usable:
        if all(abs(t - pt) >= min_gap for pt, _, _, _ in picked):
            picked.append((t, path, sharp, bright))
        if len(picked) == top:
            break
    return picked


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--start", type=float, help="seconds into the clip to start looking (default: 0.1)")
    ap.add_argument("--end", type=float, help="seconds into the clip to stop looking (default: near the end)")
    ap.add_argument("--fps", type=float, default=4.0, help="candidate frames sampled per second (default: 4)")
    ap.add_argument("--top", type=int, default=5, help="how many candidates to keep (default: 5)")
    ap.add_argument("--min-gap", type=float, default=1.0, help="minimum seconds between kept candidates")
    ap.add_argument("--dark-floor", type=float, default=20.0, help="reject candidates darker than this mean luma (0-255)")
    ap.add_argument("--bright-ceiling", type=float, default=235.0, help="reject candidates brighter than this mean luma")
    args = ap.parse_args()

    if not os.path.exists(args.clip):
        die(f"clip not found: {args.clip}")
    meta = probe(args.clip)
    start = args.start if args.start is not None else min(0.1, meta["duration"] / 4)
    end = args.end if args.end is not None else max(start + 0.1, meta["duration"] - 0.1)
    if not 0 <= start < end <= meta["duration"] + 0.01:
        die(f"--start/--end ({start:g}-{end:g}) is outside the clip (0-{meta['duration']:.2f}s)")

    os.makedirs(args.out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pick-cover-") as td:
        candidates = extract_frames(args.clip, start, end, args.fps, td)
        if not candidates:
            die("no candidate frames extracted - widen --start/--end or raise --fps")
        picked = pick(candidates, args.top, args.min_gap, args.dark_floor, args.bright_ceiling)
        if not picked:
            die("no candidates survived selection - lower --min-gap or --top")

        print(f"{len(candidates)} candidates sampled, {len(picked)} kept ({meta['w']}x{meta['h']}):")
        print(f"{'time':>8}  {'sharpness':>9}  {'brightness':>10}  file")
        for rank, (t, path, sharp, bright) in enumerate(picked, 1):
            name = f"cover_{t:06.2f}s.png".replace(" ", "0")
            dst = os.path.join(args.out_dir, name)
            shutil.copyfile(path, dst)
            print(f"{t:7.2f}s  {sharp:9.1f}  {bright:10.1f}  {dst}")


if __name__ == "__main__":
    main()
