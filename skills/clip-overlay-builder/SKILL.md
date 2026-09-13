---
name: clip-overlay-builder
description: "Use when a short vertical clip needs required on-screen text, a hook line, or a brand or game logo watermark; when a sponsor logo arrives as a JPG on black or white or as a checkerboard preview; when overlay text runs off-screen or sits under TikTok, Shorts or Reels buttons and captions; or when overlay text or a logo covers the game's own HUD, kill banners, medals or warnings."
---

# Clip overlay builder

The overlay is a transparent 1080x1920 PNG built from a JSON layout, then checked against the two things that can cover or clash with it: the platform's own UI, and the game's HUD.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow; } # Debian/Ubuntu: sudo apt install python3-venv first
O=~/.claude/skills/clip-overlay-builder/scripts
```

## Workflow

1. **Logo:** `$PY $O/prepare_logo.py "brand_logo.jpg" --out logo.png` — logos on black, white or a baked-in checkerboard become a trimmed transparent PNG. Light ink on a checkerboard preview cannot be separated: use the dark-ink version with `--recolor-neutral "#FFFFFF"` for dark footage.
2. **Layout spec** — required text near the top, logo in the lower middle:
   ```json
   {"margin": 60, "defaults": {"font": ["DIN Condensed Bold", "DejaVu Sans Condensed Bold"]},
    "elements": [
     {"id": "hook",  "type": "text",  "text": "SNIPER DOESN'T MISS", "size": 52, "color": "#FED000", "y": 150},
     {"id": "title", "type": "text",  "text": "MW4 OPEN BETA", "size": 108, "below": "hook", "gap": 6},
     {"id": "sub",   "type": "text",  "text": "THIS WEEKEND", "size": 78, "color": "#FED000", "below": "title", "gap": 6},
     {"id": "logo",  "type": "image", "src": "logo.png", "width": 320, "y": 1340}]}
   ```
3. **Build:** `$PY $O/build_overlay.py overlay.json --out overlay.png --check-safe tiktok,shorts,reels`
   A font list works on any machine: the first installed font is used and recorded in `overlay.boxes.json`, which is written beside the PNG. Text too wide shrinks, then wraps; overlapping or off-canvas elements are refused; elements under platform UI are listed.
4. **Check against the game's HUD** on a draft rendered WITHOUT the overlay (**vertical-clip-renderer**):
   `$PY $O/hud_map.py clip_draft.mp4 --boxes overlay.boxes.json`
   It prints, per element, how many seconds game UI sits under it and when, and writes a map image.
5. **Fix, then render the final** with the overlay: move an element, trim the beat, or accept a brief pop-up.

## Rules

| Rule | Why |
|---|---|
| Required text in the top third, below the platform's top bar | Most readable area, clear of the caption stack at the bottom |
| Nothing essential below y ≈ 1536 or in the right-hand button column | Platform UI covers it; `--check-safe` lists hits |
| Run `hud_map.py` on every edit before the final render | A flagged clip had the logo over the game's "ENEMY NEARBY" warning for 13.7 of 14 s; another hid its "DOUBLE KILL" payoff under the required text |
| Game UI under one element for more than ~30% of the clip: move it or re-pick beats | Brief medal pop-ups are tolerable; parking the logo on a persistent warning is not |
| Use the brief's wording exactly; add a hook line of your own unless the brief forbids other on-screen text | Required phrases are checked by `qa_clip.py`; original text helps make a sponsor clip an edit rather than a re-post |
| A brief's placement rules (corner logo, lower-third text, minimum logo width) override the defaults here | The brief is the contract; keep corner elements inside the platform safe zones (`--check-safe`) |
| Only the sponsor's logo and your own text — never another app's or creator's mark | TikTok and Instagram suppress clips carrying other platforms' or creators' watermarks |

## Reading hud_map output

- Boxes resolve to about 36 px; "under it or within ~36px" includes near misses.
- Calibrated on hand-labelled gameplay: 88% precision, 95% recall per element-second. Known false positive: a first-person weapon model held still behind a bottom-centre logo.
- Hardpoint and round-based modes carry far more HUD (scoreboards, objective timers) than free-for-all fights.

## Load references when

- **Writing a layout with corners, left/right alignment, long hooks, custom fonts, or checking safe-zone values:** read `references/layout.md`.
- **hud_map results look wrong for a new game:** read `references/layout.md` (HUD detection section) before changing its settings.
