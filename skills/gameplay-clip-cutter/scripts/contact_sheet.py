#!/usr/bin/env python3
"""Timestamped contact sheets for eyeballing footage quickly.

Every tile is labelled with its exact source time, so what you see maps straight to cut points.

  contact_sheet.py VIDEO --start 90 --end 110 --fps 2          # 0.5s resolution around a beat
  contact_sheet.py VIDEO --every 10                              # whole-file overview, 1 tile / 10s (keyframe-fast)
  contact_sheet.py VIDEO --times 12.5,40,77.25 --width 480      # specific moments, bigger
  add --guide916 to outline what survives a centered 9:16 crop (HUD outside the box will be lost)
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
]


def font(size):
    for f in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffprobe failed: {r.stderr.strip()}")
    return float(r.stdout.strip())


def stamp(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}" if m else f"{s:.2f}s"


def grab_range(path, start, end, fps, width, keyframes_only):
    with tempfile.TemporaryDirectory() as td:
        pattern = os.path.join(td, "f%05d.png")
        cmd = ["ffmpeg", "-v", "error", "-nostdin"]
        if keyframes_only:
            cmd += ["-skip_frame", "nokey"]
        cmd += ["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", path, "-an",
                "-vf", f"fps={fps},scale={width}:-2:flags=bicubic", pattern]
        r = subprocess.run(cmd, capture_output=True, text=True)
        files = sorted(f for f in os.listdir(td) if f.endswith(".png"))
        if not files:
            sys.exit(f"no frames extracted: {r.stderr.strip()[:300]}")
        return [(start + i / fps, Image.open(os.path.join(td, f)).convert("RGB")) for i, f in enumerate(files)]


def grab_times(path, times, width):
    out = []
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(times):
            p = os.path.join(td, f"t{i}.png")
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                            "-vf", f"scale={width}:-2:flags=bicubic", p], capture_output=True)
            if os.path.exists(p):
                out.append((t, Image.open(p).convert("RGB")))
    return out


def compose(frames, cols, title, guide916, approx=False):
    tw, th = frames[0][1].size
    pad, head = 4, 34
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, head + rows * (th + pad) + pad), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    d.text((pad + 2, 8), title, font=font(18), fill=(255, 215, 0))
    lf = font(max(12, tw // 14))
    for i, (t, im) in enumerate(frames):
        x, y = pad + (i % cols) * (tw + pad), head + (i // cols) * (th + pad)
        sheet.paste(im, (x, y))
        if guide916 and tw > th:
            gw = round(th * 9 / 16)
            gx = x + (tw - gw) // 2
            d.rectangle([gx, y, gx + gw, y + th - 1], outline=(0, 255, 160), width=2)
        label = ("~" if approx else "") + stamp(t)
        box = d.textbbox((0, 0), label, font=lf)
        d.rectangle([x, y, x + box[2] + 8, y + box[3] + 6], fill=(0, 0, 0))
        d.text((x + 4, y + 2), label, font=lf, fill=(255, 255, 255))
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--fps", type=float, help="tiles per second of footage (default 1)")
    ap.add_argument("--every", type=float, help="one tile every N seconds (overview; nearest keyframe, labels marked ~)")
    ap.add_argument("--times", help="comma-separated timestamps instead of a range")
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--width", type=int, default=240, help="tile width px")
    ap.add_argument("--guide916", action="store_true", help="outline the centered 9:16 crop region")
    ap.add_argument("--out", help="output PNG (default: <video>.sheet.<range>.png)")
    args = ap.parse_args()

    base = os.path.splitext(os.path.basename(args.video))[0]
    if args.times:
        times = [float(x) for x in args.times.split(",") if x.strip()]
        frames = grab_times(args.video, times, args.width)
        tag = "times"
    else:
        end = args.end if args.end is not None else duration(args.video)
        if args.every:
            frames = grab_range(args.video, args.start, end, 1.0 / args.every, args.width, keyframes_only=True)
        else:
            frames = grab_range(args.video, args.start, end, args.fps or 1.0, args.width, keyframes_only=False)
        tag = f"{args.start:g}-{end:g}"
    if not frames:
        sys.exit("no frames")
    title = f"{base}   {tag}   {len(frames)} tiles"
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.video)), f"{base}.sheet.{tag}.png")
    compose(frames, args.cols, title, args.guide916, approx=bool(args.every and not args.times)).save(out)
    print(out)


if __name__ == "__main__":
    main()
