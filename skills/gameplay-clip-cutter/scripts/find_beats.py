#!/usr/bin/env python3
"""Turn an analyze_video.py timeline into cut decisions.

Finds scene boundaries (hard cuts, fades through black, audio-dip transitions between stringout clips),
action beats, dead air, and ranks clip candidates: single continuous windows and multi-beat montages.
Also validates a proposed edit before you render it.

  find_beats.py SRC.timeline.json                                   # rank candidates, 12-18s clips
  find_beats.py SRC.timeline.json --clip-min 10 --clip-max 25 --top 10
  find_beats.py SRC.timeline.json --validate "187:3,192.5:9.5,204.8:1.5"
  find_beats.py CLIP.timeline.json --ref SRC.timeline.json --dead-report   # dead air in a rendered clip
  add --json out.json to save everything machine-readably

Activity is driven mostly by loudness (gunfire, explosions, callouts). In first-person games the camera never
stops moving, so motion alone cannot separate a firefight from walking to the objective; audio can.
Loudness is judged relative to the analysed footage (its quiet floor and its loud peaks), so it adapts to
each game's mix. Short clips have no traversal to compare against: pass --ref with the source timeline.
"""
import argparse
import bisect
import json
import sys

GRID = 0.1
STRONG, WEAK = 3, 1


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def pct(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    return sorted_vals[min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))]


def moving_avg(xs, win):
    half, out, acc = win // 2, [], [0.0]
    for x in xs:
        acc.append(acc[-1] + x)
    for i in range(len(xs)):
        lo, hi = max(0, i - half), min(len(xs), i + half + 1)
        out.append((acc[hi] - acc[lo]) / (hi - lo))
    return out


def mmss(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:04.1f}"


class Timeline:
    def __init__(self, path, ref_levels=None):
        d = json.load(open(path))
        self.path, self.d = path, d
        self.mode = d["mode"]
        self.t0, self.t1 = float(d["start"]), float(d["end"])
        n = max(1, int(round((self.t1 - self.t0) / GRID)))
        self.grid = [round(self.t0 + i * GRID, 3) for i in range(n)]
        at, adb = d["audio"]["t"], d["audio"]["db"]
        self.db = self._nearest(at, adb, -60.0) if at else [-60.0] * n
        self.db = [max(-60.0, x) for x in self.db]
        v = d["video"]
        self.vt = v["t"]
        self.v = {k: v[k] for k in ("motion", "luma", "red", "jump", "step")}
        self.red = self._hold(self.vt, v["red"], 0.0)
        self.luma = self._hold(self.vt, v["luma"], 80.0)
        self.levels = ref_levels or self._levels()
        self.act = self._activity()

    def _nearest(self, ts, vals, default):
        out, j = [], 0
        for g in self.grid:
            while j + 1 < len(ts) and abs(ts[j + 1] - g) <= abs(ts[j] - g):
                j += 1
            out.append(vals[j] if ts and abs(ts[j] - g) <= 0.15 else default)
        return out

    def _hold(self, ts, vals, default):
        out = []
        for g in self.grid:
            k = bisect.bisect_right(ts, g + 1e-6) - 1
            out.append(vals[k] if 0 <= k < len(vals) else default)
        return out

    def _levels(self):
        s = sorted(self.db)
        return {"floor": pct(s, 0.15), "hot": pct(s, 0.90), "source": "self"}

    def _activity(self):
        floor, hot = self.levels["floor"], self.levels["hot"]
        span = max(8.0, hot - floor)
        loud = moving_avg([clamp((x - floor) / span) for x in self.db], 5)
        burst = moving_avg([1.0 if x >= hot - 6 else 0.0 for x in self.db], 11)
        return [0.6 * a + 0.4 * b for a, b in zip(loud, burst)]

    def idx(self, t):
        return max(0, min(len(self.grid) - 1, int(round((t - self.t0) / GRID))))

    def boundaries(self):
        """Where one stringout clip ends and another begins.

        Calibrated on 15 visually confirmed transitions in edited gameplay compilations: 14 were reported
        (13 strong, 1 verify); ~70% of strong reports were real cuts. Treat every boundary as a lead to check.
          black-frame   luma collapses: fade through black, death or loading screen          strong
          hard-cut      a one-sample visual jump that persists and is not part of a run       strong
                        (pans are runs of jumps, muzzle flashes revert); scope-ins and
                        full-screen HUD (streak maps, tablets) also match - known false class
          hard-cut-2f   the same spread over two samples (short dissolve / motion blur)       strong
          audio-cliff   game audio loud right up to the edge, then silent in one step,        strong
                        with any visual jump nearby: editors cut audio between clips
          audio-fade    loud-to-silent over ~1s, or a cliff with no visual change: also       verify
                        how firefights end in-game, so it needs eyes
        """
        full = self.mode == "full"
        cands = []
        L, J, S = self.v["luma"], self.v["jump"], self.v["step"]
        n = len(self.vt)
        for i, t in enumerate(self.vt):
            if L[i] <= 15 and (i == 0 or L[i - 1] > 15):
                cands.append([t, "black-frame", STRONG])
                continue
            if not full:
                if J[i] >= 0.35 and S[i] >= 0.85 * J[i]:
                    cands.append([t, "hard-cut?", WEAK])
                continue
            prev_j = J[i - 1] if i > 0 else 0.0
            next_j = J[i + 1] if i + 1 < n else 0.0
            if J[i] >= 0.18 and S[i] >= 0.85 * J[i] and prev_j <= 0.6 * J[i] and next_j <= 0.6 * J[i]:
                cands.append([t, "hard-cut", STRONG])
            elif (i + 2 < n and J[i] >= 0.15 and J[i + 1] >= 0.15 and J[i] + J[i + 1] >= 0.45
                  and S[i + 1] >= 0.3 and prev_j <= 0.5 * max(J[i], J[i + 1]) and J[i + 2] <= 0.5 * max(J[i], J[i + 1])):
                cands.append([t, "hard-cut-2f", STRONG])
        for i, g in enumerate(self.grid):
            x = self.db[i]
            if x > -42 or x != min(self.db[max(0, i - 3):i + 4]) or i < 3:
                continue
            instant = min(self.db[i - 3:i]) >= -24
            prior = self.db[max(0, i - 10):i]
            if instant:
                lo, hi = bisect.bisect_left(self.vt, g - 0.3), bisect.bisect_right(self.vt, g + 0.3)
                seen = full and any(J[k] >= 0.09 for k in range(lo, hi))
                cands.append([g, "audio-cliff" if seen else "audio-cliff?", STRONG if seen else WEAK])
            elif max(prior) >= -20 and x <= max(prior) - 22:
                cands.append([g, "audio-fade", WEAK])
        cands.sort()
        kept = []
        for c in cands:
            if kept and c[0] - kept[-1][0] < 1.0:
                if c[2] > kept[-1][2]:
                    kept[-1] = c
                continue
            kept.append(c)
        return [{"t": round(c[0], 2), "kind": c[1], "strength": "strong" if c[2] == STRONG else "verify"} for c in kept]

    def dead_runs(self, lo_t=None, hi_t=None, thr=0.25, min_len=1.5):
        lo = self.idx(self.t0 if lo_t is None else lo_t)
        hi = self.idx(self.t1 if hi_t is None else hi_t)
        runs, start = [], None
        for i in range(lo, hi + 1):
            dead = i < len(self.act) and self.act[i] < thr
            if dead and start is None:
                start = i
            if (not dead or i == hi) and start is not None:
                end = i if dead else i - 1
                if (end - start + 1) * GRID >= min_len:
                    runs.append((self.grid[start], self.grid[end] + GRID))
                start = None
        return runs

    def mean_act(self, a, b):
        i, j = self.idx(a), self.idx(b)
        seg = self.act[i:max(i + 1, j)]
        return sum(seg) / len(seg)


def scenes_from(tl, bounds):
    cuts = [b["t"] for b in bounds if b["strength"] == "strong"]
    edges = [tl.t0] + [c for c in cuts if tl.t0 + 0.5 < c < tl.t1 - 0.5] + [tl.t1]
    return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1) if edges[i + 1] - edges[i] >= 1.0]


def find_beats(tl, scenes, thr=0.45):
    beats = []
    for s0, s1 in scenes:
        i0, i1 = tl.idx(s0), tl.idx(s1)
        runs, start, gap = [], None, 0
        for i in range(i0, i1):
            if tl.act[i] >= thr:
                if start is None:
                    start = i
                gap, last = 0, i
            elif start is not None:
                gap += 1
                if gap > 10:
                    runs.append((start, last))
                    start = None
        if start is not None:
            runs.append((start, last))
        for a, b in runs:
            bs = max(s0 + 0.15, tl.grid[a] - 0.5)
            be = min(s1 - 0.15, tl.grid[b] + GRID + 0.7)
            if be - bs < 1.5:
                continue
            seg = tl.act[tl.idx(bs):tl.idx(be)]
            tail_red = max(tl.red[tl.idx(be - 1.0):tl.idx(be)] or [0])
            beats.append({"start": round(bs, 2), "end": round(be, 2), "dur": round(be - bs, 2),
                          "mean": round(sum(seg) / len(seg), 3), "peak": round(max(seg), 3),
                          "score": round(sum(seg) / len(seg) * min(1.0, (be - bs) / 3.0) + 0.3 * max(seg), 3),
                          "scene": [round(s0, 2), round(s1, 2)],
                          "red_at_end": round(tail_red, 2)})
    return beats


def window_candidates(tl, scenes, bounds, lo, hi, top):
    weak = [b["t"] for b in bounds if b["strength"] == "verify"]
    dead = [1.0 if a < 0.25 else 0.0 for a in tl.act]
    acc_a, acc_d = [0.0], [0.0]
    for a, dd in zip(tl.act, dead):
        acc_a.append(acc_a[-1] + a)
        acc_d.append(acc_d[-1] + dd)
    runs = tl.dead_runs(min_len=0.5)
    cands = []
    for s0, s1 in scenes:
        L = float(lo)
        while L <= hi + 1e-6:
            s = s0 + 0.15
            while s + L <= s1 - 0.15 + 1e-6:
                i, j = tl.idx(s), tl.idx(s + L)
                n = max(1, j - i)
                mean = (acc_a[j] - acc_a[i]) / n
                dead_frac = (acc_d[j] - acc_d[i]) / n
                longest = max([min(e, s + L) - max(b, s) for b, e in runs if b < s + L and e > s] or [0.0])
                hook = tl.mean_act(s, s + 2.0)
                end = tl.mean_act(s + L - 1.5, s + L)
                if longest <= 2.0 and dead_frac <= 0.25:
                    score = mean - 0.8 * dead_frac - 0.15 * max(0.0, longest - 1.0) + 0.25 * hook + 0.15 * end
                    cands.append({"start": round(s, 2), "end": round(s + L, 2), "dur": round(L, 1),
                                  "score": round(score, 3), "mean": round(mean, 3), "dead_frac": round(dead_frac, 2),
                                  "longest_dead": round(longest, 1), "hook": round(hook, 2), "end_act": round(end, 2),
                                  "verify_boundaries": [w for w in weak if s < w < s + L]})
                s += 0.5
            L += 1.0
    cands.sort(key=lambda c: -c["score"])
    kept = []
    for c in cands:
        if all(min(c["end"], k["end"]) - max(c["start"], k["start"]) < 0.3 * c["dur"] for k in kept):
            kept.append(c)
        if len(kept) >= top:
            break
    return kept


def montage_candidates(tl, beats, lo, hi, top):
    pool = sorted(beats, key=lambda b: -b["score"])[:14]
    seen, out = set(), []
    for seed in pool[:8]:
        chosen, total = [seed], seed["dur"]
        for b in pool:
            if b is seed or any(min(b["end"], c["end"]) > max(b["start"], c["start"]) for c in chosen):
                continue
            if total + b["dur"] <= hi + 2.0:
                chosen.append(b)
                total += b["dur"]
            if total >= lo:
                break
        if total < lo or len(chosen) < 2:
            continue
        segs = [[c["start"], c["end"]] for c in chosen]
        while sum(e - s for s, e in segs) > hi + 1e-6:
            k = max(range(len(segs)), key=lambda q: segs[q][1] - segs[q][0])
            s, e = segs[k]
            if e - s <= 1.6:
                break
            if tl.mean_act(s, s + 0.3) < tl.mean_act(e - 0.3, e):
                segs[k][0] = round(s + 0.1, 2)
            else:
                segs[k][1] = round(e - 0.1, 2)
        segs.sort()
        key = tuple((round(s), round(e)) for s, e in segs)
        if key in seen:
            continue
        seen.add(key)
        dur = sum(e - s for s, e in segs)
        mean = sum(tl.mean_act(s, e) * (e - s) for s, e in segs) / dur
        out.append({"beats": [[round(s, 2), round(e - s, 2)] for s, e in segs], "dur": round(dur, 1),
                    "mean": round(mean, 3), "hook": round(tl.mean_act(segs[0][0], min(segs[0][1], segs[0][0] + 2)), 2),
                    "edl": ",".join(f"{s:g}:{e - s:.2f}".rstrip("0").rstrip(".") for s, e in segs)})
    out.sort(key=lambda m: -(m["mean"] + 0.25 * m["hook"]))
    diverse, used = [], []
    for m in out:
        starts = {round(b[0]) for b in m["beats"]}
        if all(len(starts & u) <= len(starts) // 2 for u in used):
            diverse.append(m)
            used.append(starts)
    return diverse[:top]


def parse_edl(edl):
    beats = []
    for part in edl.split(","):
        s, d = part.strip().split(":")
        beats.append((float(s), float(s) + float(d)))
    return beats


def validate(tl, bounds, edl, min_total=10.0):
    """FAIL = likely to read as low-effort or break the brief; WARN = weaker edit; NOTE = check by eye.

    Thresholds come from clips whose platform outcome is known: approved clips carried quiet stretches of
    up to ~2.5s and ~25% quiet time; a flagged clip ended on 5.4s of walking (50% quiet).
    """
    beats = parse_edl(edl)
    issues, report, total, dead_total = [], [], 0.0, 0.0

    def add(level, msg):
        issues.append({"level": level, "msg": msg})

    for n, (s, e) in enumerate(beats, 1):
        if s < tl.t0 - 0.05 or e > tl.t1 + 0.05:
            add("FAIL", f"beat {n} ({s:g}-{e:g}) is outside the analysed range {tl.t0:g}-{tl.t1:g}: analyse it first")
            continue
        inside = [b for b in bounds if s + 0.15 < b["t"] < e - 0.15]
        dead = tl.dead_runs(s, e, min_len=1.0)
        red_tail = max(tl.red[tl.idx(e - 0.8):tl.idx(e)] or [0])
        black_after = any(e <= b["t"] <= e + 1.0 and b["kind"] == "black-frame" for b in bounds)
        report.append({"beat": n, "start": s, "end": e, "dur": round(e - s, 2), "mean_act": round(tl.mean_act(s, e), 2),
                       "crosses": inside, "dead_runs": [[round(a, 1), round(b, 1)] for a, b in dead]})
        for b in inside:
            if b["strength"] == "strong":
                add("WARN", f"beat {n} crosses a clip boundary ({b['kind']} at {b['t']:g}s): an unintended jump to "
                            f"another player/match mid-beat - trim to one side or make it a deliberate montage cut")
            else:
                add("NOTE", f"beat {n}: possible boundary at {b['t']:g}s ({b['kind']}) - confirm on a contact sheet")
        for a, b in dead:
            run = b - a
            dead_total += run
            add("FAIL" if run >= 3.0 else "WARN" if run >= 2.0 else "NOTE",
                f"beat {n}: {run:.1f}s of dead air at {a:g}-{b:g}s (walking, reloading, looking around)")
        if red_tail > 0.45 or black_after:
            add("NOTE", f"beat {n} may end on a death or damage screen (red={red_tail:.2f}) - check the last second")
        total += e - s
    if beats and total > 0:
        if dead_total / total >= 0.35:
            add("FAIL", f"{dead_total / total:.0%} of the edit is dead air - cut the traversal between beats")
        s0 = beats[0][0]
        hook = tl.mean_act(s0, min(beats[0][1], s0 + 2.0))
        if hook < 0.25:
            add("WARN", f"quiet opening (first 2s activity {hook:.2f}) - make sure frame one shows action, not setup")
        e1 = beats[-1][1]
        if tl.mean_act(max(beats[-1][0], e1 - 1.5), e1) < 0.25:
            add("WARN", "ends on low activity - end on the payoff (kill, medal, streak call-in)")
        if total < min_total:
            add("FAIL", f"total {total:.1f}s is under the {min_total:g}s minimum")
    verdict = "FAIL" if any(i["level"] == "FAIL" for i in issues) else "WARN" if any(i["level"] == "WARN" for i in issues) else "PASS"
    return {"total_dur": round(total, 2), "verdict": verdict, "beats": report, "issues": issues}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline")
    ap.add_argument("--clip-min", type=float, default=12.0)
    ap.add_argument("--clip-max", type=float, default=18.0)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--validate", help='proposed edit as "start:dur,start:dur" in source seconds')
    ap.add_argument("--min-total", type=float, default=10.0, help="minimum edit length required by the brief")
    ap.add_argument("--ref", help="timeline whose loudness levels define quiet/loud (use the source's for short clips)")
    ap.add_argument("--dead-report", action="store_true", help="just list dead-air runs and per-second activity")
    ap.add_argument("--json", help="write results as JSON")
    args = ap.parse_args()

    ref = None
    if args.ref:
        r = Timeline(args.ref)
        ref = dict(r.levels, source=args.ref)
    tl = Timeline(args.timeline, ref)
    span = tl.t1 - tl.t0
    if ref is None and span < 60:
        print(f"note: only {span:.0f}s analysed - loudness is judged against this footage alone; "
              f"pass --ref <source timeline> for trustworthy dead-air calls", file=sys.stderr)
    bounds = tl.boundaries()
    scenes = scenes_from(tl, bounds)
    result = {"timeline": args.timeline, "mode": tl.mode, "range": [tl.t0, tl.t1], "levels": tl.levels,
              "boundaries": bounds}

    print(f"{args.timeline}\n  {tl.mode} mode, {mmss(tl.t0)}-{mmss(tl.t1)}, loudness floor {tl.levels['floor']:.1f} dB, "
          f"loud {tl.levels['hot']:.1f} dB ({'from ref' if ref else 'from this footage'})")
    strong = [b for b in bounds if b["strength"] == "strong"]
    print(f"  boundaries: {len(strong)} strong, {len(bounds) - len(strong)} to verify")
    for b in bounds:
        print(f"    {b['t']:8.2f}s  {mmss(b['t']):>7}  {b['kind']:<17} {b['strength']}")

    if args.dead_report:
        runs = tl.dead_runs(min_len=1.0)
        result["dead_runs"] = runs
        print(f"  dead air (activity < 0.25 for >= 1s): {len(runs)} run(s), "
              f"{sum(e - s for s, e in runs):.1f}s of {span:.1f}s")
        for s, e in runs:
            print(f"    {s:7.1f}-{e:.1f}s  ({e - s:.1f}s)")
        print("  per-second activity:")
        for sec in range(int(tl.t0), int(tl.t1)):
            a = tl.mean_act(sec, sec + 1)
            print(f"    {sec:6d}s {a:4.2f} {'#' * int(a * 30)}")
    elif args.validate:
        v = validate(tl, bounds, args.validate, args.min_total)
        result["validation"] = v
        print(f"  validate {args.validate}  ->  {v['total_dur']}s total   VERDICT: {v['verdict']}")
        for b in v["beats"]:
            print(f"    beat {b['beat']}: {b['start']:g}-{b['end']:g} ({b['dur']}s) activity {b['mean_act']}")
        for i in sorted(v["issues"], key=lambda i: ["FAIL", "WARN", "NOTE"].index(i["level"])):
            print(f"    {i['level']:<4}  {i['msg']}")
        if v["verdict"] == "PASS":
            print("    no issues found - still eyeball each beat edge on a contact sheet")
    else:
        beats = find_beats(tl, scenes)
        wins = window_candidates(tl, scenes, bounds, args.clip_min, args.clip_max, args.top)
        monts = montage_candidates(tl, beats, args.clip_min, args.clip_max, args.top)
        result.update(beats=beats, windows=wins, montages=monts)
        print(f"  {len(beats)} action beats:")
        for b in sorted(beats, key=lambda b: b["start"]):
            flag = "  red-at-end" if b["red_at_end"] > 0.45 else ""
            print(f"    {b['start']:8.2f}-{b['end']:<8.2f} {b['dur']:5.1f}s  score {b['score']:.2f}  peak {b['peak']:.2f}{flag}")
        print(f"  best single windows ({args.clip_min:g}-{args.clip_max:g}s, no strong boundary inside):")
        for w in wins:
            extra = f"  verify@{w['verify_boundaries']}" if w["verify_boundaries"] else ""
            print(f"    {w['start']:8.2f}-{w['end']:<8.2f} {w['dur']:4.1f}s  score {w['score']:.2f}  act {w['mean']:.2f}  "
                  f"dead {w['dead_frac']:.0%} (max {w['longest_dead']}s)  hook {w['hook']:.2f}{extra}")
        print("  montage suggestions (beats in source time, chronological):")
        for m in monts:
            print(f"    {m['edl']:<40} {m['dur']:4.1f}s  act {m['mean']:.2f}  hook {m['hook']:.2f}")
        print("  next: eyeball candidates with contact_sheet.py --start S --end E --fps 2 --guide916, "
              "then --validate the edit you pick")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
