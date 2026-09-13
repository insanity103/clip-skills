#!/usr/bin/env python3
"""Find where the game's own HUD and pop-up banners sit in the vertical frame, and check an overlay against them.

  hud_map.py clip_draft_NO_overlay.mp4 --boxes overlay.boxes.json   # collisions for a rendered edit
  hud_map.py SOURCE.mp4 --start 90 --end 150 --x 35                 # where a game's HUD lives (9:16 crop)

HUD and banners are the edges that stay put while the camera moves. Persistent HUD (compass, minimap, ammo,
killfeed) is on screen most of the time; banners (medals, kill callouts, "ENEMY NEARBY") appear in a fixed
place for roughly 0.5-6 s. Moments where the camera holds still are skipped, because then the whole scene
holds still too. Analyse footage WITHOUT the overlay burned in: render a --quality draft copy without
--overlay first. Landscape (or any non-9:16) input goes through the renderer's centred 9:16 crop; --x shifts it.
Boxes are 1080x1920 output pixels on a 36x32 px grid - treat every edge as +-36 px.
Writes <json>.png too (unless --no-png): HUD in cyan, banners in magenta, overlay boxes yellow, collisions red.
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat

OUT_W, OUT_H = 1080, 1920
AW, AH = 270, 480
CX, CY = 9, 8
GW, GH = AW // CX, AH // CY
EDGE_MIN = 60
STILL_MOTION = 1.5
# calibrated on labelled MW4 beta footage (tests/hud_calibration): precision 0.88, recall 0.95
CELL_DENSITY = 0.10
PERSISTENT_SHARE = 0.8
MIN_EVENT_SAMPLES = 3


def die(msg):
    sys.exit(f"hud_map: {msg}")


def even(v):
    return int(v) // 2 * 2


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", path], capture_output=True, text=True)
    if r.returncode:
        die(f"cannot read {path}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    return int(j["streams"][0]["width"]), int(j["streams"][0]["height"]), float(j["format"].get("duration", 0))


def crop_filter(w, h, x_off):
    if abs(w / h - 9 / 16) < 0.01:
        return ""
    if w * 16 >= h * 9:
        cw, ch = even(round(h * 9 / 16)), even(h)
    else:
        cw, ch = even(w), even(round(w * 16 / 9))
    cx = min(max((w - cw) // 2 + x_off, 0), w - cw)
    return f"crop={cw}:{ch}:{cx}:{(h - ch) // 2},"


def frames(path, start, end, fps, x_off):
    w, h, dur = probe(path)
    end = dur if end is None else min(end, dur)
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", path, "-an",
           "-vf", f"fps={fps},{crop_filter(w, h, x_off)}scale={AW}:{AH}:flags=area,format=gray",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    i = 0
    while True:
        buf = p.stdout.read(AW * AH)
        if len(buf) < AW * AH:
            break
        yield start + i / fps, Image.frombytes("L", (AW, AH), buf)
        i += 1
    p.wait()


def edges(img):
    e = img.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v >= EDGE_MIN else 0)
    # the filter always fires along the frame border, which would read as a HUD ring round every clip
    ImageDraw.Draw(e).rectangle([0, 0, AW - 1, AH - 1], outline=0, width=2)
    return e.convert("1")


def cell_box(gx0, gy0, gx1, gy1):
    sx, sy = OUT_W / AW, OUT_H / AH
    return [round(gx0 * CX * sx), round(gy0 * CY * sy), round((gx1 + 1) * CX * sx), round((gy1 + 1) * CY * sy)]


def components(cells, neighbours):
    seen, out = set(), []
    for start in cells:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            c = stack.pop()
            comp.append(c)
            for n in neighbours(c):
                if n in cells and n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(comp)
    return out


def analyse(path, start, end, fps, x_off):
    times, active, skipped, keep = [], [], 0, {}
    window = []
    for t, img in frames(path, start, end, fps, x_off):
        window.append((t, img, edges(img)))
        if len(window) > 3:
            window.pop(0)
        if len(window) < 3:
            continue
        (_, a, ea), (tm, b, eb), (_, c, ec) = window
        if len(times) % 20 == 0 or not keep:
            keep[tm] = b
        if ImageStat.Stat(ImageChops.difference(a, c)).mean[0] < STILL_MOTION:
            skipped += 1
            continue
        stable = ImageChops.logical_and(ImageChops.logical_and(ea, eb), ec).convert("L")
        dens = stable.resize((GW, GH), Image.BOX).tobytes()
        times.append(tm)
        active.append(bytes(1 if v >= CELL_DENSITY * 255 else 0 for v in dens))
    return times, active, skipped, keep


def classify(times, active, fps):
    n = len(times)
    if not n:
        return [], []
    share = [sum(row[i] for row in active) / n for i in range(GW * GH)]
    persistent = {(i % GW, i // GW) for i, s in enumerate(share) if s >= PERSISTENT_SHARE}
    hud = []
    for comp in components(persistent, lambda c: [(c[0] + dx, c[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]):
        xs, ys = [c[0] for c in comp], [c[1] for c in comp]
        on = sum(share[y * GW + x] for x, y in comp) / len(comp)
        hud.append({"box": cell_box(min(xs), min(ys), max(xs), max(ys)), "on_screen": round(on, 2)})

    voxels = {(k, i % GW, i // GW) for k, row in enumerate(active) for i, v in enumerate(row)
              if v and (i % GW, i // GW) not in persistent}
    gap = 1.5 / fps

    def neighbours(v):
        k, x, y = v
        out = [(k, x + 1, y), (k, x - 1, y), (k, x, y + 1), (k, x, y - 1)]
        if k + 1 < n and times[k + 1] - times[k] <= gap:
            out.append((k + 1, x, y))
        if k > 0 and times[k] - times[k - 1] <= gap:
            out.append((k - 1, x, y))
        return out

    events = []
    for comp in components(voxels, neighbours):
        ks = sorted({v[0] for v in comp})
        cells = {(v[1], v[2]) for v in comp}
        if len(ks) < MIN_EVENT_SAMPLES or len(cells) < 2:
            continue
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        events.append({"t0": round(max(times[0], times[ks[0]] - 1 / fps), 2),
                       "t1": round(times[ks[-1]] + 1 / fps, 2),
                       "box": cell_box(min(xs), min(ys), max(xs), max(ys))})
    events.sort(key=lambda e: e["t0"])
    return hud, events


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def collide(elements, hud, events, margin):
    out = []
    for el in elements:
        b = [el["box"][0] - margin, el["box"][1] - margin, el["box"][2] + margin, el["box"][3] + margin]
        out += [{"element": el["id"], "kind": "hud", "box": h["box"]} for h in hud if overlaps(b, h["box"])]
        out += [{"element": el["id"], "kind": "banner", "t0": e["t0"], "t1": e["t1"], "box": e["box"]}
                for e in events if overlaps(b, e["box"])]
    return out


def summarize(elements, collisions, span, gap=0.5):
    out = []
    for el in elements:
        mine = [c for c in collisions if c["element"] == el["id"]]
        if not mine:
            continue
        ranges = []
        for a, b in sorted((c["t0"], c["t1"]) for c in mine if c["kind"] == "banner"):
            if ranges and a <= ranges[-1][1] + gap:
                ranges[-1][1] = max(ranges[-1][1], b)
            else:
                ranges.append([a, b])
        persistent = any(c["kind"] == "hud" for c in mine)
        secs = span if persistent else sum(b - a for a, b in ranges)
        out.append({"element": el["id"], "over_persistent_hud": persistent, "seconds": round(secs, 2),
                    "share": round(min(1.0, secs / span), 2) if span else 0.0,
                    "ranges": [[round(a, 2), round(b, 2)] for a, b in ranges]})
    return out


def draw_map(path, frame, hud, events, elements, collisions):
    base = (frame.resize((OUT_W // 2, OUT_H // 2)) if frame else Image.new("L", (OUT_W // 2, OUT_H // 2), 40))
    img = Image.eval(base, lambda v: v // 2).convert("RGB")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
        except OSError:
            font = ImageFont.load_default()
    half = lambda b: [v // 2 for v in b]
    hit = {c["element"] for c in collisions}
    for h in hud:
        d.rectangle(half(h["box"]), outline=(0, 230, 255), width=2)
    for e in events:
        d.rectangle(half(e["box"]), outline=(255, 0, 200), width=2)
        d.text((e["box"][0] // 2 + 3, e["box"][1] // 2 + 2), f"{e['t0']:g}-{e['t1']:g}s", font=font, fill=(255, 0, 200))
    for el in elements:
        d.rectangle(half(el["box"]), outline=(255, 40, 40) if el["id"] in hit else (255, 220, 0), width=3)
        d.text((el["box"][0] // 2 + 3, el["box"][3] // 2 - 16), el["id"], font=font, fill=(255, 220, 0))
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--x", type=int, default=0, help="crop offset in source px for non-9:16 input (as the renderer)")
    ap.add_argument("--fps", type=float, default=6.0, help="samples per second (default 6)")
    ap.add_argument("--boxes", help="overlay.boxes.json from build_overlay.py: report collisions")
    ap.add_argument("--margin", type=int, default=16, help="px added around overlay boxes before testing overlap")
    ap.add_argument("--json", help="output JSON (default <video>.hudmap.json)")
    ap.add_argument("--no-png", action="store_true", help="skip the map image")
    args = ap.parse_args()

    times, active, skipped, keep = analyse(args.video, args.start, args.end, args.fps, args.x)
    span = (min(args.end, probe(args.video)[2]) if args.end is not None else probe(args.video)[2]) - args.start
    hud, events = classify(times, active, args.fps)
    elements = json.load(open(args.boxes))["elements"] if args.boxes else []
    collisions = collide(elements, hud, events, args.margin) if args.boxes else []
    out = args.json or os.path.splitext(args.video)[0] + ".hudmap.json"
    result = {"video": os.path.abspath(args.video), "fps": args.fps, "grid_px": [36, 32], "moving_samples": len(times),
              "still_samples_skipped": skipped, "hud": hud, "events": events}
    summary = summarize(elements, collisions, span) if args.boxes else []
    if args.boxes:
        result["collisions"] = collisions
        result["summary"] = summary
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    if not args.no_png:
        frame = keep[sorted(keep)[len(keep) // 2]] if keep else None
        draw_map(os.path.splitext(out)[0] + ".png", frame, hud, events, elements, collisions)

    if not times:
        print("warning: no moving footage in range - nothing to map", file=sys.stderr)
    print(f"{os.path.basename(args.video)}: {len(times)} moving samples ({skipped} still skipped), "
          f"{len(hud)} HUD region(s), {len(events)} banner event(s) -> {out}")
    for h in hud:
        print(f"  HUD     {h['box']}  on screen {h['on_screen']:.0%}")
    if events:
        print(f"  {len(events)} banner events - see the JSON and the map image for boxes and times")
    for s in summary:
        if s["over_persistent_hud"]:
            print(f"  COLLISION  {s['element']}: sits on permanent game HUD")
        else:
            when = ", ".join(f"{a:g}-{b:g}s" for a, b in s["ranges"])
            print(f"  COLLISION  {s['element']}: game UI under it or within ~36px for {s['seconds']:g}s of {span:.1f}s "
                  f"({s['share']:.0%}) at {when}")
    if args.boxes and not summary:
        print("  no overlay element sits over game HUD or banners")


if __name__ == "__main__":
    main()
