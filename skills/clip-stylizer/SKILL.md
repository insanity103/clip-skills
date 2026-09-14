---
name: clip-stylizer
description: "Use when a creator wants their clip to have a stylized, trippy, or high-energy look instead of a clean unaltered render - a vertical echo/ghost double-exposure with boosted saturation and posterized color, the look used on organic (non-sponsored) continuous-take gameplay posts. Never use this on a clip going out under a paid brief."
---

# Clip stylizer

One consistent, clip-long filter reverse-engineered from a real posted clip: a semi-transparent ghost copy of the frame offset downward, plus boosted saturation and reduced color levels (banding). It's a substitute for montage editing on a single continuous take - see `gameplay-clip-cutter/references/organic_formats.md` (Archetype 1) for the format this technique comes from.

**This is a look, not a fix.** It doesn't change dead-air, reused-footage, or any other correctness problem, and it actively works against paid-brief requirements for clean, legible, unaltered footage. Never apply it to a clip going out under `clipping-campaign-producer`.

## Setup

```bash
command -v ffmpeg >/dev/null || echo "ffmpeg missing - macOS: brew install ffmpeg | Debian/Ubuntu: sudo apt install ffmpeg"
S=~/.claude/skills/clip-stylizer/scripts/apply_style.py
```

## Workflow

1. **Style before building any overlay**, not after - the whole frame gets restyled, including any burned-in text or logo, which would double it into the ghost copy too.
   ```bash
   python3 $S --clip clip.mp4 --out styled.mp4
   ```
2. **Tune to taste.** The defaults reproduce the reference clip's look; a subtler or stronger version:
   ```bash
   python3 $S --clip clip.mp4 --echo-opacity 0.2 --posterize 16 --out subtle.mp4     # lighter touch
   python3 $S --clip clip.mp4 --saturation 2.2 --posterize 6 --out extreme.mp4       # heavier
   ```
3. **Isolate one element** to check it in isolation: `--echo-opacity 0` for grading only, or `--posterize 0 --saturation 1.0 --contrast 1.0` for the echo alone.
4. **`--warmth`** pushes shadows toward orange (positive) or blue (negative) - useful for matching an indoor scene's amber cast; leave at 0 (default, off) unless a specific clip needs it.

## Rules

| Rule | Why |
|---|---|
| Never use on a clip with a brief attached | `clipping-campaign-producer` requires clean, legible, unaltered footage; this actively works against every readability check `qa_clip.py` and `hud_map.py` run |
| Style before overlay, not after | The filter restyles the whole frame; running it after `clip-overlay-builder` would double and discolor the required text/logo along with everything else |
| Video is always re-encoded | The filter graph requires it; audio passes through unchanged (`-c:a copy`) |
| Don't use as a substitute for actually cutting dead air | This changes how a continuous take *looks*, not its pacing - a boring take styled is still a boring take |

## Notes

- The echo offset (`--echo-offset`, default 0.27 - a fraction of frame height) and opacity were measured
  from a real clip; they land the ghost copy far enough down to read as a deliberate double-exposure
  without turning into a smear. Push `--echo-opacity` toward 0.5+ only for a very heavy version.
- Posterize levels (`--posterize`, default 10) control the banding: lower means more graphic/flat color
  separation, higher means smoother toward the source's real color range. `1` or `0` disables it.
