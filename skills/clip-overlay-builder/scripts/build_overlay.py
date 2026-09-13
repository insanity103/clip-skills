#!/usr/bin/env python3
"""Build a full-frame transparent overlay (1080x1920 PNG) from a JSON layout: campaign text and logos.

  build_overlay.py spec.json --out overlay.png --check-safe tiktok,shorts,reels

Also writes overlay.boxes.json: each element's drawn box, final font size and lines. hud_map.py reads it
to check the overlay against the game's own HUD and banners. Overlapping or off-canvas elements are refused.

{"margin": 60,
 "defaults": {"font": ["DIN Condensed Bold", "DejaVu Sans Condensed Bold"], "color": "#FFFFFF", "stroke": 6, "shadow": 0.85},
 "elements": [
  {"id": "hook",  "type": "text",  "text": "SNIPER DOESN'T MISS", "size": 52, "color": "#FED000", "y": 150},
  {"id": "title", "type": "text",  "text": "MW4 OPEN BETA", "size": 108, "below": "hook", "gap": 6},
  {"id": "logo",  "type": "image", "src": "logo.png", "width": 320, "y": 1340}]}

Text: case is kept as written. A line too wide for the margins shrinks to "min_size" (default 70% of size),
then wraps to "max_lines" (default 2), and only then shrinks further. Place with "y" (top edge) or
"below": <id> + "gap"; "align": center|left|right. "font" is a .ttf/.otf/.ttc path or a family name from the
system font folders (macOS and Linux), or a list of them - the first installed one is used and recorded in
boxes.json. With no font given, a condensed-bold chain is tried (DIN Condensed on macOS, DejaVu Sans Condensed on
most Linux desktops). Every element gets a dark stroke/shadow by default so light text survives bright footage.
Safe zones are conservative approximations of platform UI (device-dependent); --zones adds or overrides them.
"""
import argparse
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
# first installed wins: DIN ships with macOS, DejaVu Sans Condensed with most Linux desktops
DEFAULT_FONTS = ["DIN Condensed Bold", "Barlow Condensed Bold", "Oswald Bold", "Roboto Condensed Bold",
                 "DejaVu Sans Condensed Bold", "Liberation Sans Narrow Bold"]
FONT_DIRS = ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", "~/Library/Fonts",
             "/usr/share/fonts", "/usr/local/share/fonts", "~/.local/share/fonts", "~/.fonts", "C:/Windows/Fonts"]

# [x0, y0, x1, y1] on 1080x1920. Conservative ends of published 2026 creator guidance; real UI varies by device.
SAFE_ZONES = {
    "tiktok": {"top bar": [0, 0, 1080, 130], "caption and username": [0, 1536, 1080, 1920],
               "action buttons": [960, 600, 1080, 1536]},
    "reels": {"top bar": [0, 0, 1080, 108], "caption and audio": [0, 1600, 1080, 1920],
              "action buttons": [960, 900, 1080, 1600]},
    "shorts": {"top bar": [0, 0, 1080, 140], "title, channel and subscribe": [0, 1632, 1080, 1920],
               "action buttons": [945, 900, 1080, 1632]},
}


def die(msg):
    sys.exit(f"build_overlay: {msg}")


def norm(name):
    return re.sub(r"[\s_\-]", "", name).lower()


_FONT_INDEX = {}


def font_index():
    if not _FONT_INDEX:
        for d in FONT_DIRS:
            d = os.path.expanduser(d)
            for root, _, files in os.walk(d) if os.path.isdir(d) else []:
                for f in files:
                    stem, ext = os.path.splitext(f)
                    if ext.lower() in (".ttf", ".otf", ".ttc"):
                        _FONT_INDEX.setdefault(norm(stem), os.path.join(root, f))
    return _FONT_INDEX


def find_font(names):
    names = [names] if isinstance(names, str) else list(names)
    for name in names:
        path = os.path.expanduser(name)
        if os.path.isfile(path):
            return path
        hit = font_index().get(norm(os.path.splitext(name)[0]))
        if hit:
            return hit
    die(f"none of these fonts is installed: {', '.join(names)} - give a .ttf/.otf path or install one "
        f"(Debian/Ubuntu: sudo apt install fonts-dejavu-core)")


def rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    if len(h) not in (6, 8):
        die(f"bad colour '{hex_color}': use #RRGGBB")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + ((int(h[6:8], 16),) if len(h) == 8 else (alpha,))


class Fonts:
    def __init__(self, path):
        self.path, self.cache = path, {}

    def at(self, size):
        if size not in self.cache:
            self.cache[size] = ImageFont.truetype(self.path, size)
        return self.cache[size]


PROBE = ImageDraw.Draw(Image.new("L", (1, 1)))


def ink(text, font, stroke):
    return PROBE.textbbox((0, 0), text, font=font, stroke_width=stroke)


def stroke_at(el, size):
    s = el["stroke"]
    return 0 if not s else max(1, round(s * size / el["size"]))


def widest(lines, fonts, el, size):
    return max(ink(line, fonts.at(size), stroke_at(el, size))[2] - ink(line, fonts.at(size), stroke_at(el, size))[0]
               for line in lines)


def best_split(text, fonts, el, size):
    words = text.split()
    options = [[" ".join(words[:i]), " ".join(words[i:])] for i in range(1, len(words))]
    return min(options, key=lambda ls: widest(ls, fonts, el, size))


def fit(el, fonts, max_w):
    size, text = el["size"], el["text"]
    floor = el.get("min_size") or max(12, round(size * 0.7))
    candidates = [[text]]
    if el.get("max_lines", 2) >= 2 and len(text.split()) > 1:
        candidates.append(best_split(text, fonts, el, size))
    for lines in candidates:
        for s in range(size, floor - 1, -1):
            if widest(lines, fonts, el, s) <= max_w:
                return s, lines
    for s in range(floor - 1, 11, -1):
        for lines in candidates:
            if widest(lines, fonts, el, s) <= max_w:
                print(f"warning: '{el['id']}' only fits at {s}px, below its {floor}px floor - shorten the text",
                      file=sys.stderr)
                return s, lines
    die(f"'{el['id']}' cannot fit inside the margins even at 12px")


def x_for(width, align, margin):
    if align == "left":
        return margin
    if align == "right":
        return W - margin - width
    return round((W - width) / 2)


def draw_text(canvas, el, y, margin):
    fonts = Fonts(find_font(el["font"]))
    size, lines = fit(el, fonts, W - 2 * margin)
    font, stroke = fonts.at(size), stroke_at(el, size)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    top, gap, boxes, placed = y, round(0.12 * size), [], []
    for line in lines:
        l, t, r, b = ink(line, font, stroke)
        x = x_for(r - l, el.get("align", "center"), margin)
        placed.append((x - l, top - t, line))
        boxes.append([x, top, x + (r - l), top + (b - t)])
        top += (b - t) + gap
    if el["shadow"]:
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        for x, yy, line in placed:
            sd.text((x, yy), line, font=font, fill=(0, 0, 0, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        canvas.alpha_composite(soften(shade, max(4, round(size * 0.1)), el["shadow"]))
    for x, yy, line in placed:
        d.text((x, yy), line, font=font, fill=rgba(el["color"]), stroke_width=stroke,
               stroke_fill=rgba(el.get("stroke_color", "#000000")))
    canvas.alpha_composite(layer)
    box = [min(b[0] for b in boxes), boxes[0][1], max(b[2] for b in boxes), boxes[-1][3]]
    return box, {"size": size, "lines": lines, "font": fonts.path}


def soften(layer, radius, opacity):
    blurred = layer.filter(ImageFilter.GaussianBlur(radius))
    blurred.putalpha(blurred.getchannel("A").point(lambda v: round(v * opacity)))
    return blurred


def draw_image(canvas, el, y, margin, base):
    src = os.path.expanduser(el["src"])
    src = src if os.path.isabs(src) else os.path.join(base, src)
    if not os.path.exists(src):
        die(f"'{el['id']}': image not found: {src}")
    img = Image.open(src).convert("RGBA")
    width = int(el["width"])
    img = img.resize((width, max(1, round(img.height * width / img.width))), Image.LANCZOS)
    x = x_for(width, el.get("align", "center"), margin)
    if el["shadow"]:
        silhouette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        silhouette.paste(Image.new("RGBA", img.size, (0, 0, 0, 255)), (x, y), img)
        canvas.alpha_composite(soften(silhouette, max(4, round(width * 0.03)), el["shadow"]))
    canvas.alpha_composite(img, (x, y))
    return [x, y, x + width, y + img.height], {"src": src}


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def safe_zone_hits(elements, zones, platforms):
    hits = []
    for p in platforms:
        if p not in zones:
            die(f"no safe-zone definition for '{p}' (known: {', '.join(sorted(zones))})")
        for zone, rect in zones[p].items():
            for e in elements:
                if overlaps(e["box"], rect):
                    area = (min(e["box"][2], rect[2]) - max(e["box"][0], rect[0])) * \
                           (min(e["box"][3], rect[3]) - max(e["box"][1], rect[1]))
                    hits.append({"element": e["id"], "platform": p, "zone": zone, "overlap_px": area})
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", required=True, help="overlay PNG path; boxes go to <name>.boxes.json beside it")
    ap.add_argument("--check-safe", help="comma-separated platforms: tiktok,shorts,reels")
    ap.add_argument("--zones", help="JSON of extra/overriding zones: {platform: {zone: [x0,y0,x1,y1]}}")
    args = ap.parse_args()

    spec = json.load(open(args.spec))
    base = os.path.dirname(os.path.abspath(args.spec))
    margin = int(spec.get("margin", 60))
    defaults = {"font": DEFAULT_FONTS, "color": "#FFFFFF", "stroke": 6, "shadow": 0.85, **spec.get("defaults", {})}
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    done = {}
    for n, raw in enumerate(spec["elements"], 1):
        el = {**defaults, "id": f"element{n}", **raw}
        if "below" in el:
            if el["below"] not in done:
                die(f"'{el['id']}' is below '{el['below']}', which is not defined earlier")
            y = done[el["below"]]["box"][3] + int(el.get("gap", 0))
        elif "y" in el:
            y = int(el["y"])
        else:
            die(f"'{el['id']}' needs 'y' or 'below'")
        if el.get("type") == "text":
            box, extra = draw_text(canvas, el, y, margin)
        elif el.get("type") == "image":
            box, extra = draw_image(canvas, el, y, margin, base)
        else:
            die(f"'{el['id']}': type must be text or image")
        if box[1] < 0 or box[3] > H or box[0] < 0 or box[2] > W:
            die(f"'{el['id']}' runs off the {W}x{H} canvas (box {box}) - move it inside the frame")
        for other in done.values():
            if overlaps(box, other["box"]):
                die(f"'{el['id']}' {box} overlaps '{other['id']}' {other['box']} - change 'y' or use 'below'")
        done[el["id"]] = {"id": el["id"], "type": el["type"], "box": box, **extra}

    zones = dict(SAFE_ZONES)
    if args.zones:
        zones.update(json.load(open(args.zones)))
    platforms = [p.strip() for p in args.check_safe.split(",")] if args.check_safe else []
    elements = list(done.values())
    hits = safe_zone_hits(elements, zones, platforms)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    canvas.save(args.out)
    side = re.sub(r"\.png$", "", args.out, flags=re.I) + ".boxes.json"
    with open(side, "w") as f:
        json.dump({"canvas": [W, H], "margin": margin, "elements": elements, "safe_zone_hits": hits}, f, indent=1)
    for e in elements:
        detail = f"{e['size']}px, {len(e['lines'])} line(s)" if e["type"] == "text" else "image"
        print(f"  {e['id']:<12} box {e['box']}  {detail}")
    for h in hits:
        print(f"  WARNING {h['element']} sits under {h['platform']} UI ({h['zone']}, {h['overlap_px']} px overlap)")
    print(args.out)


if __name__ == "__main__":
    main()
