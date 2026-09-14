#!/usr/bin/env python3
"""Apply a clip-long stylized filter: vertical echo/ghost double-exposure + saturation/posterize.

  apply_style.py --clip clip.mp4 --out styled.mp4
  apply_style.py --clip clip.mp4 --echo-opacity 0 --out styled.mp4       # posterize/saturation only
  apply_style.py --clip clip.mp4 --posterize 0 --out styled.mp4          # echo only, full color range
  apply_style.py --clip clip.mp4 --warmth 0.15 --out styled.mp4          # push shadows toward orange

Reverse-engineered from a real posted clip: a semi-transparent copy of the same frame, offset downward
and alpha-blended underneath the original, plus boosted saturation and reduced per-channel color levels
(banding/graphic-novel look). Video only - audio passes through unchanged. Re-encodes video (the filter
requires it); never use this on a clip that already has a burned-in overlay you need pixel-exact, since
the whole frame including any overlay gets restyled too - style before building the overlay, not after.

This is a look, not a fix: it does not make dead-air or reused-footage problems less true, and it
works against paid-brief requirements for clean, legible, unaltered footage - see the Rules table in
SKILL.md before using it on anything with a brief attached.
"""
import argparse
import json
import os
import subprocess
import sys

def die(msg):
    sys.exit(f"apply_style: {msg}")


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
            "has_audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def build_graph(h, echo_offset, echo_opacity, saturation, contrast, posterize, warmth):
    parts = []
    label = "0:v"
    if echo_opacity > 0:
        offset_px = round(echo_offset * h)
        parts.append(f"[{label}]split=2[base][echosrc]")
        parts.append(f"[echosrc]format=rgba,colorchannelmixer=aa={echo_opacity}[echoa]")
        parts.append(f"[base][echoa]overlay=x=0:y={offset_px}:format=auto[echoed]")
        label = "echoed"
    if saturation != 1.0 or contrast != 1.0:
        parts.append(f"[{label}]eq=saturation={saturation}:contrast={contrast}[graded]")
        label = "graded"
    if warmth != 0.0:
        parts.append(f"[{label}]colorbalance=rs={warmth}:bs={-warmth}[warm]")
        label = "warm"
    if posterize > 1:
        step = 256 // posterize
        half = step // 2
        expr = f"min(floor(val/{step})*{step}+{half}\\,255)"
        parts.append(f"[{label}]lutrgb=r='{expr}':g='{expr}':b='{expr}'[styled]")
        label = "styled"
    if not parts:
        die("nothing to apply: --echo-opacity, --saturation/--contrast, --posterize and --warmth are all no-ops")
    parts.append(f"[{label}]format=yuv420p[out]")
    return ";".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--echo-offset", type=float, default=0.27,
                     help="ghost copy's downward offset as a fraction of frame height (default 0.27)")
    ap.add_argument("--echo-opacity", type=float, default=0.35,
                     help="ghost copy's opacity, 0-1 (default 0.35; 0 disables the echo)")
    ap.add_argument("--saturation", type=float, default=1.7, help="1.0 = unchanged (default 1.7)")
    ap.add_argument("--contrast", type=float, default=1.05, help="1.0 = unchanged (default 1.05)")
    ap.add_argument("--posterize", type=int, default=10,
                     help="color levels per channel, 2-256 (default 10; 0 or 1 disables)")
    ap.add_argument("--warmth", type=float, default=0.0,
                     help="push shadows red/orange (positive) or blue (negative), -1 to 1 (default 0, off)")
    args = ap.parse_args()

    if not os.path.exists(args.clip):
        die(f"clip not found: {args.clip}")
    if not 0 <= args.echo_opacity <= 1:
        die("--echo-opacity must be between 0 and 1")
    if args.posterize not in (0, 1) and not 2 <= args.posterize <= 256:
        die("--posterize must be 0, 1, or between 2 and 256")

    meta = probe(args.clip)
    graph = build_graph(meta["h"], args.echo_offset, args.echo_opacity, args.saturation, args.contrast,
                        args.posterize, args.warmth)

    root, ext = os.path.splitext(args.out)
    tmp = f"{root}.partial{ext or '.mp4'}"
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", args.clip, "-filter_complex", graph,
           "-map", "[out]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
           "-pix_fmt", "yuv420p"]
    if meta["has_audio"]:
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += ["-movflags", "+faststart", tmp]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        if os.path.exists(tmp):
            os.remove(tmp)
        die(f"ffmpeg failed:\n{r.stderr.strip()[-800:]}")
    os.replace(tmp, args.out)
    print(f"{args.out}: {meta['w']}x{meta['h']}, echo={'on' if args.echo_opacity > 0 else 'off'}, "
          f"posterize={args.posterize if args.posterize > 1 else 'off'}")


if __name__ == "__main__":
    main()
