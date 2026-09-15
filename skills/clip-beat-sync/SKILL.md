---
name: clip-beat-sync
description: "Use when a clip needs its cuts, gunshots, or hit moments checked against the music's beat - or a claim like 'synced to the beat' needs verifying rather than assumed. Estimates a tempo/beat grid from a clip's own audio and reports how close given timestamps land to it, in milliseconds."
---

# Clip beat sync

Two scripts: `find_beat_grid.py` estimates a tempo and beat grid from a clip's audio; `check_beat_sync.py` reports how far a list of timestamps (cut points, gunshot moments, hit VFX) land from the nearest beat, in milliseconds. Formalizes what was previously a one-off manual analysis (onset-envelope autocorrelation) into something repeatable.

**This measures, it doesn't judge.** Landing off the beat is frequently a deliberate creative choice, not a mistake - `check_beat_sync.py` never exits non-zero for a bad sync, and neither script tells you what to change.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow numpy openpyxl; } # Debian/Ubuntu: sudo apt install python3-venv first
G=~/.claude/skills/clip-beat-sync/scripts/find_beat_grid.py
C=~/.claude/skills/clip-beat-sync/scripts/check_beat_sync.py
```

## Workflow

1. **Find the window that actually has music.** Gameplay clips often mix music with game audio, or the music doesn't cover the whole clip (see Notes) - check by ear or by spectrogram first, then point `--start`/`--end` at just that window.
2. **Build the grid:**
   ```bash
   $PY $G --clip clip.mp4 --start 0 --end 16 --out grid.json
   ```
   **Read the printed confidence before trusting the BPM.** It's an autocorrelation strength (0-1), not a percentage certainty - below ~0.25 means the audio has no clean isolated beat (usually because dense, non-musical transients like automatic gunfire dominate it), and the BPM figure is a guess, not a measurement. This happens often on gameplay audio; it is not a bug.
3. **Check timestamps against it** - cut points from your own edit, or gunshot/hit moments you found by ear or with `gameplay-clip-cutter`:
   ```bash
   $PY $C --grid grid.json --times "1.9,3.59,5.08" --tolerance-ms 60
   # or, with labels, from a file:
   $PY $C --grid grid.json --times-file hits.json --out report.json
   ```
4. **Read the per-row offsets, not just the on-beat count.** A handful of hits landing within ~20ms while most land 150ms+ off usually means a few moments were deliberately hand-placed on the beat and the rest just happen to fall where the gameplay put them - a real, common pattern, not a broken analysis.

## Rules

| Rule | Why |
|---|---|
| Always report the confidence figure alongside any BPM claim | A low-confidence BPM stated as fact is worse than not stating one - see the "don't over-claim" rule this whole repo follows for platform behavior |
| Restrict the analysis window to where the music actually is | Autocorrelating silence or a totally different audio section produces a meaningless grid, not an error - the script won't catch this for you |
| Never treat "off beat" as a finding to fix | This is a measurement tool; whether a given offset matters is a creative judgment outside its scope |

## Notes

- The tempo estimate comes from autocorrelating the audio's onset (loudness-rise) envelope - it works well on a clean, isolated track and much less reliably when gunfire or other rapid transients dominate, because automatic weapon fire has its own rhythm that isn't musical and can pull the autocorrelation toward a wrong period entirely.
- Verified against a fully-controlled synthetic click track at exact BPMs (`tests/test_find_beat_grid.py`) - not against real gameplay audio, where ground truth is unknown. Treat every real-clip result as an estimate to sanity-check by ear, not a verified measurement.
- A TikTok download's audio track can end well before the video does (seen firsthand: a 35s clip with only 20s of audio, silent for the rest). Check the audio actually covers your `--start`/`--end` window before reading anything into a grid built past where it ends.
