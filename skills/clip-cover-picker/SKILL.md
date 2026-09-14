---
name: clip-cover-picker
description: "Use when a rendered clip needs a cover/thumbnail frame picked for TikTok, Shorts or Reels - the still users see in a profile grid or before a video autoplays; or when a chosen cover frame turned out blurry, too dark, or too bright."
---

# Clip cover picker

Every platform lets a creator pick a specific frame as the clip's cover instead of defaulting to frame zero, which is often a hard cut mid-motion. This scores candidate frames for sharpness and exposure and hands back a short list to choose from - it doesn't know what's *in* the frame.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow; } # Debian/Ubuntu: sudo apt install python3-venv first
C=~/.claude/skills/clip-cover-picker/scripts/pick_cover.py
```

## Workflow

1. **Run it on the finished clip** (the final render, overlay and all - not the draft):
   ```bash
   $PY $C clip.mp4 --out-dir covers --top 5
   ```
   Prints a ranked table (time, sharpness, brightness) and writes full-resolution PNGs to `covers/`.
2. **Narrow to the payoff window** if the clip has an obvious best moment (a kill, a clutch, a build reveal) rather than searching the whole clip:
   ```bash
   $PY $C clip.mp4 --start 8 --end 11 --out-dir covers --top 3
   ```
3. **Look at the candidates.** The script only measures sharpness and exposure - a sharp frame of a wall scores the same as a sharp frame of the kill. Pick the one that actually shows the hook or payoff, not just the top-ranked file.
4. **Hand the chosen PNG to the user** to set as the cover in-app (TikTok, Shorts and Reels cover pickers all take an uploaded still or a frame from the video); this skill doesn't post anything.

## Rules

| Rule | Why |
|---|---|
| Run against the final render, not the draft | The draft may use a faster/rougher encode; the cover should match what actually gets posted |
| Default sampling window skips the very first and last ~0.1s | The exact start/end frame is more likely to land on a hard cut or encoder edge artifact than a frame just inside it |
| `--min-gap` keeps candidates spread out (default 1s) | Otherwise the top 5 can all be the same instant a few frames apart |
| Exposure filter (too dark / blown out) is ignored with a warning if it would reject every candidate | A genuinely dark clip (horror, night map) still needs a cover; better a dark one than none |
| Never treat the top-ranked candidate as automatically correct | Sharpness and brightness say nothing about composition, motion blur read as "action", or whether the frame spoils vs. teases the payoff |

## Notes

- Sharpness is edge-detail variance (a Pillow `FIND_EDGES` pass), not a calibrated metric - it's a ranking signal between frames of the *same* clip, not a number to compare across clips or games.
- A clip that's soft everywhere (every candidate scores low) usually means the source was upscaled - see `vertical-clip-renderer`'s own low-resolution warning; picking a "least bad" cover doesn't fix that.
