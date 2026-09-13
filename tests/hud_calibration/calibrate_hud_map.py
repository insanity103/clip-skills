#!/usr/bin/env python3
"""Score hud_map.py's shipped settings against ground_truth.json (run from this folder, drafts present)."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.environ.get("HUD_MAP_SCRIPT") or os.path.expanduser("~/.claude/skills/clip-overlay-builder/scripts/hud_map.py")
GT = json.load(open(os.path.join(HERE, "ground_truth.json")))["clips"]


def covered(ivals, t):
    return any(a <= t <= b for a, b in ivals)


tp = fp = fn = 0
for name, c in GT.items():
    video = os.path.join(HERE, c["video"])
    if not os.path.exists(video):
        sys.exit(f"missing {c['video']} - render it first (see README.md)")
    out = os.path.join(HERE, f"_{name}.json")
    subprocess.run([sys.executable, SCRIPT, video, "--boxes", os.path.join(HERE, c["boxes"]), "--json", out, "--no-png"],
                   check=True, capture_output=True)
    res = json.load(open(out))
    for s in res["summary"]:
        eid = s["element"]
        if "score_only" in c and eid not in c["score_only"]:
            continue
        pred = [(0, 1e9)] if s["over_persistent_hud"] else s["ranges"]
        truth, dc = c["truth"].get(eid, []), c.get("dont_care", {}).get(eid, [])
        a = b = m = 0
        t = 0.0
        while t <= c["duration"]:
            if not covered(dc, t):
                g, p = covered(truth, t), covered(pred, t)
                a, b, m = a + (g and p), b + (p and not g), m + (g and not p)
            t += 0.25
        print(f"{name}.{eid:<6} TP {a:3d}  FP {b:3d}  FN {m:3d}")
        tp, fp, fn = tp + a, fp + b, fn + m
p, r = tp / max(1, tp + fp), tp / max(1, tp + fn)
print(f"precision {p:.2f}  recall {r:.2f}  F1 {2 * p * r / max(1e-9, p + r):.2f}")
