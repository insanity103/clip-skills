#!/usr/bin/env python3
"""Turn a brand logo delivered on black, white, or a baked-in transparency checkerboard into a trimmed,
transparent PNG.

  prepare_logo.py logo_on_black.jpg --out logo.png
  prepare_logo.py logo_preview_on_checkerboard.jpg --out logo.png
  prepare_logo.py dark_ink_version.jpg --recolor-neutral "#FFFFFF" --out logo_for_dark_footage.png
  prepare_logo.py logo.png --out logo_trimmed.png      # already transparent: trimmed, alpha kept

Alpha comes from each pixel's distance to the background behind it, and colour is un-premultiplied, so
anti-aliased edges keep their real colour instead of a dark or pale fringe. Faint JPEG noise below --floor
is dropped. Brand portals often export "large" previews of transparent logos as JPGs with the grey/white
checkerboard burned in: light ink on those cannot be separated, so use the dark-ink version and
--recolor-neutral to make a white variant for dark gameplay (brand colours are left untouched).
"""
import argparse
import os
import statistics
import sys

from PIL import Image


def die(msg):
    sys.exit(f"prepare_logo: {msg}")


def pixels(img):
    return list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())


def ring(img, width=3):
    w, h = img.size
    px = img.load()
    return [((x, y), px[x, y]) for y in range(h) for x in range(w)
            if x < width or y < width or x >= w - width or y >= h - width]


def is_neutral_light(p):
    return max(p) - min(p) <= 10 and min(p) >= 150


def runs(classes):
    out, start = [], 0
    for i in range(1, len(classes) + 1):
        if i == len(classes) or classes[i] != classes[start]:
            out.append((start, i - start))
            start = i
    return out


def checker_model(img, hi, lo):
    w, h = img.size
    px = img.load()
    cls = lambda p: 1 if abs(min(p) - hi) <= abs(min(p) - lo) else 0
    row = runs([cls(px[x, 1]) for x in range(w)])
    col = runs([cls(px[1, y]) for y in range(h)])
    inner = [n for _, n in row[1:-1]] + [n for _, n in col[1:-1]]
    if len(inner) < 2:
        return None
    cell = statistics.median_low(inner)
    px0, py0 = row[0][1] % cell, col[0][1] % cell
    parity = (((1 - px0) // cell + (1 - py0) // cell) % 2) ^ cls(px[1, 1])

    def bg_at(x, y):
        return hi if (((x - px0) // cell + (y - py0) // cell) % 2) ^ parity else lo

    light = [(xy, p) for xy, p in ring(img) if is_neutral_light(p)]
    agree = sum(1 for (x, y), p in light if abs(min(p) - bg_at(x, y)) <= 6)
    return bg_at if light and agree >= 0.95 * len(light) else None


def background_model(img):
    edge = [p for _, p in ring(img)]
    if sum(1 for p in edge if max(p) <= 40) >= 0.8 * len(edge):
        return "black", None
    light = [min(p) for p in edge if is_neutral_light(p)]
    if len(light) < 0.8 * len(edge):
        return None, None
    hi = statistics.median_high(light)
    darker = [v for v in light if v <= hi - 8]
    if len(darker) < 0.05 * len(light):
        return "white", (lambda x, y: hi)
    bg_at = checker_model(img, hi, statistics.median_low(darker))
    return ("checker", bg_at) if bg_at else (None, None)


def extract_on_black(img, floor):
    out = []
    for r, g, b in pixels(img):
        a = max(r, g, b)
        if a <= floor:
            out.append((0, 0, 0, 0))
        else:
            out.append((min(255, round(r * 255 / a)), min(255, round(g * 255 / a)), min(255, round(b * 255 / a)), a))
    return out


def extract_on_light(img, bg_at, floor):
    w, out = img.width, []
    for i, (r, g, b) in enumerate(pixels(img)):
        bg = bg_at(i % w, i // w)
        a = round((bg - min(r, g, b)) * 255 / bg) if min(r, g, b) < bg else 0
        if a <= floor:
            out.append((0, 0, 0, 0))
            continue
        k = a / 255
        out.append(tuple(min(255, max(0, round((c - (1 - k) * bg) / k))) for c in (r, g, b)) + (a,))
    return out


def light_ink_on_checker(img, bg_at):
    w = img.width
    return sum(1 for i, p in enumerate(pixels(img)) if is_neutral_light(p) and min(p) > bg_at(i % w, i // w) + 8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logo")
    ap.add_argument("--out", required=True)
    ap.add_argument("--floor", type=int, default=16, help="ignore pixels this close to the background (0-255)")
    ap.add_argument("--recolor-neutral", metavar="#RRGGBB",
                    help="repaint black/grey/white parts of the logo this colour; coloured parts stay as they are")
    args = ap.parse_args()

    src = Image.open(args.logo)
    rgba = src.convert("RGBA")
    if rgba.getchannel("A").getextrema()[0] < 250:
        kind, img = "transparent", rgba
    else:
        rgb = src.convert("RGB")
        kind, bg_at = background_model(rgb)
        if kind is None:
            die(f"{os.path.basename(args.logo)}: background is not plain black, plain white, or a light "
                f"checkerboard - ask for the logo as a transparent PNG or on black/white")
        if kind == "checker":
            stray = light_ink_on_checker(rgb, bg_at)
            if stray > 0.001 * rgb.width * rgb.height:
                die(f"{os.path.basename(args.logo)} has light ink on a checkerboard preview ({stray} px brighter "
                    f"than the squares behind them), which cannot be separated - use the dark-ink version, with "
                    f"--recolor-neutral \"#FFFFFF\" if you need it white")
        img = Image.new("RGBA", rgb.size)
        img.putdata(extract_on_black(rgb, args.floor) if kind == "black" else extract_on_light(rgb, bg_at, args.floor))
    if args.recolor_neutral:
        h = args.recolor_neutral.lstrip("#")
        if len(h) != 6:
            die("--recolor-neutral needs a colour like #FFFFFF")
        target = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        img.putdata([target + (p[3],) if p[3] and max(p[:3]) - min(p[:3]) <= 40 else p for p in pixels(img)])
    box = img.getchannel("A").getbbox()
    if box is None:
        die("nothing left after removing the background")
    img = img.crop(box)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    img.save(args.out)
    print(f"{args.out}: {img.width}x{img.height} (background: {kind})")


if __name__ == "__main__":
    main()
