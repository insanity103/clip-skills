#!/usr/bin/env python3
"""Check candidate cut/hit timestamps against a beat grid from find_beat_grid.py.

  check_beat_sync.py --grid grid.json --times "1.9,3.59,5.08" --out report.json
  check_beat_sync.py --grid grid.json --times-file cuts.json --tolerance-ms 60

--times-file is a JSON list of numbers, or of {"t": ..., "label": "..."} objects (label is echoed
back in the report). Reports each time's offset in ms from the nearest grid point (negative = early,
positive = late) and whether it's within --tolerance-ms. This is an eyes-on report, not a gate: it
never exits non-zero for "off beat" - landing off the beat is a creative choice, not a bug, and the
underlying grid can itself be low-confidence (see find_beat_grid.py's confidence figure).
"""
import argparse
import json
import os
import sys

def die(msg):
    sys.exit(f"check_beat_sync: {msg}")


def nearest(grid, t):
    best = min(grid, key=lambda g: abs(g - t))
    return best, (t - best) * 1000.0


def parse_times(args):
    if args.times:
        try:
            return [{"t": float(x), "label": None} for x in args.times.split(",")]
        except ValueError:
            die(f"bad --times '{args.times}': use a comma-separated list of numbers")
    data = json.load(open(args.times_file))
    out = []
    for item in data:
        if isinstance(item, (int, float)):
            out.append({"t": float(item), "label": None})
        else:
            out.append({"t": float(item["t"]), "label": item.get("label")})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grid", required=True, help="grid JSON from find_beat_grid.py")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--times", help="comma-separated seconds, e.g. \"1.9,3.59,5.08\"")
    src.add_argument("--times-file", help="JSON list of numbers or {t, label} objects")
    ap.add_argument("--tolerance-ms", type=float, default=60.0, help="on-beat threshold (default 60ms)")
    ap.add_argument("--out", help="also write the report as JSON")
    args = ap.parse_args()

    if not os.path.exists(args.grid):
        die(f"grid not found: {args.grid}")
    if args.times_file and not os.path.exists(args.times_file):
        die(f"times file not found: {args.times_file}")
    if args.tolerance_ms <= 0:
        die("--tolerance-ms must be positive")

    grid_data = json.load(open(args.grid))
    grid = grid_data.get("grid")
    if not grid:
        die(f"{args.grid} has no \"grid\" points")

    times = parse_times(args)
    if not times:
        die("no times to check")

    rows = []
    for item in times:
        g, offset_ms = nearest(grid, item["t"])
        rows.append({"t": item["t"], "label": item["label"], "nearest_grid": g,
                    "offset_ms": round(offset_ms, 1), "on_beat": abs(offset_ms) <= args.tolerance_ms})

    on_beat = sum(1 for r in rows if r["on_beat"])
    confidence = grid_data.get("confidence")
    print(f"beat grid: {grid_data.get('bpm', '?')} BPM, confidence {confidence}"
          + (" (LOW - treat this report as a rough guide, not a verdict)" if confidence is not None and confidence < 0.25 else ""))
    print(f"{'time':>8}  {'nearest beat':>12}  {'offset':>8}  {'on beat?':>8}  label")
    for r in rows:
        print(f"{r['t']:8.2f}  {r['nearest_grid']:12.2f}  {r['offset_ms']:+7.0f}ms  "
              f"{'yes' if r['on_beat'] else 'no':>8}  {r['label'] or ''}")
    print(f"\n{on_beat}/{len(rows)} within {args.tolerance_ms:g}ms of the nearest beat")

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"grid_bpm": grid_data.get("bpm"), "grid_confidence": confidence,
                       "tolerance_ms": args.tolerance_ms, "rows": rows,
                       "on_beat_count": on_beat, "total": len(rows)}, f, indent=2)


if __name__ == "__main__":
    main()
