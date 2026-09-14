---
name: gameplay-clip-cutter
description: "Use when picking the best moments out of long gameplay footage (sponsor stringouts, b-roll reels, VODs, compilations, match recordings) to cut 10-60 second vertical clips, when checking a proposed edit for dead air or for cuts that jump into a different player's clip, or when a short-form clip was flagged as low quality or unoriginal and has to be re-cut."
---

# Gameplay clip cutter

Measure the footage, look at timestamped frames, validate the exact edit — before anything is rendered.

**Core idea:** in first-person games the camera never stops moving, so motion cannot tell a firefight from walking. Loudness can. Gunfire, impacts and callouts mark action; long quiet stretches are dead air, and dead air is what gets otherwise good clips flagged as low quality.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow; } # Debian/Ubuntu: sudo apt install python3-venv first
command -v ffmpeg >/dev/null || echo "ffmpeg missing - macOS: brew install ffmpeg | Debian/Ubuntu: sudo apt install ffmpeg"
S=~/.claude/skills/gameplay-clip-cutter/scripts
```

## Workflow

1. **Triage the whole source** (fast mode, ~5x realtime):
   `$PY $S/analyze_video.py "SRC.mp4" --mode fast --out SRC.timeline.json`
2. **Rank candidates:** `$PY $S/find_beats.py SRC.timeline.json --clip-min 12 --clip-max 18 --top 8`
   Prints clip boundaries inside the source, action beats, best single windows and montage EDLs.
3. **Re-analyse the stretch you might use** in full mode (~realtime; boundary detection needs it):
   `$PY $S/analyze_video.py "SRC.mp4" --mode full --start 90 --end 143 --out win.timeline.json`
4. **Look before deciding:** `$PY $S/contact_sheet.py "SRC.mp4" --start 90 --end 143 --fps 2 --guide916`
   Every tile shows its source time; the green box is what survives the 9:16 crop.
5. **Validate the exact edit**, with the whole-source timeline as loudness reference:
   `$PY $S/find_beats.py win.timeline.json --validate "91.5:4,125.5:2.5,133:9" --ref SRC.timeline.json`
   Fix every FAIL. A WARN means look again at that beat.
6. Hand the EDL (`start:dur,...` in source seconds) to **vertical-clip-renderer**.

## Rules that decide whether a clip survives

| Rule | Why |
|---|---|
| No quiet run of 3 s or more, and under 35% quiet overall | A clip ending on 5.4 s of walking was flagged; approved clips carried at most ~2.5 s runs and ~26% quiet |
| Open on action, end on the payoff (kill, medal, streak, KO, finish line) | Quiet first 2 s or last 1.5 s is the weakest part of a scroll-stopping clip; the validator WARNs |
| Cut traversal out: stitch beats rather than keep one long window | Stitched re-cuts replaced the dead-air windows that were flagged |
| A beat never straddles a clip boundary unless the jump is deliberate | Stringouts compile different players; a straddling beat jumps to another player mid-shot |
| Each new clip uses beats no earlier clip in the campaign used | Platforms hide re-posted and reused footage; `qa_clip.py` FAILs 80%+ overlap |
| Prefer beats with little game UI in the top third and lower middle | Required text and the logo go there; scoreboards, objective timers and medal banners collide |
| Confirm on full-resolution frames before re-cutting | Several apparent problems (a second watermark, a cut placed 0.7 s early) dissolved when checked |

## Reading the output

- Boundaries marked `strong` are usually real; `verify` ones need a contact sheet. Known false alarms: sniper scope-ins and fast turns that pop HUD elements.
- `red-at-end` on a beat: it may end on a death or damage screen — check its last second.
- PASS measures sound only. One flagged clip had no dead air at all; its likely cause was visual (see **clip-overlay-builder**).

## Load references when

- **The game is not a shooter, or loudness seems to miss the action** (racing engines, MOBA ability spam, horror tension, fighting-game footsies): read `references/genre_playbook.md` before trusting the ranking.
- **A verdict looks wrong, or you want to change a threshold:** read `references/calibration.md` first — the thresholds encode real approved and flagged outcomes.
- **A brief doesn't specify clip length, cut frequency, or on-screen text placement:** read `references/platform_retention.md` — general 2026 short-form editing research (length, hooks, pacing, safe zones) to fall back on. Not calibrated like `calibration.md` or `mw4_case_study.md` — defer to those and to `qa_clip.py`/`--check-safe` where they conflict.

## Common mistakes

- Choosing cut points from unlabelled frame grids. Use `contact_sheet.py`; it timestamps every tile.
- Validating a short window without `--ref`, then trusting its dead-air verdict (it has no quiet traversal to compare against).
- Validating beats outside the analysed range — analyse the whole span the montage draws from.
- Killing a background ffmpeg but not the shell loop that started it. Kill the process group.
