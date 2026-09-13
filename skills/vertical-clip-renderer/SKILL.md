---
name: vertical-clip-renderer
description: "Use when turning horizontal (16:9 or ultrawide) gameplay or video footage into full-frame 9:16 vertical clips for TikTok, YouTube Shorts or Instagram Reels, stitching several beats from one or more sources into one clip, burning a transparent overlay onto a clip, or when a vertical render shows letterbox bars or a blurred background fill, looks soft, or takes too long."
---

# Vertical clip renderer

Every frame is filled with footage: crop to 9:16, scale to 1080x1920, sharpen, slow push-in, overlay, encode.

**Never letterbox or blur-fill.** A round of five clips with gameplay in a centred band over a blurred copy was flagged in full; the same moments rendered full-frame were approved. TikTok, Shorts and Reels all treat borders as low-quality, recycled video.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow; } # Debian/Ubuntu: sudo apt install python3-venv first
R=~/.claude/skills/vertical-clip-renderer/scripts/render_vertical.py
```

## Workflow

1. **Draft without overlay** (VideoToolbox on macOS, x264 veryfast on Linux; also the input `hud_map.py` needs):
   `$PY $R --src "SRC.mp4" --edl "91.5:4,125.5:2.5,133:9" --x 35 --quality draft --out clip_draft.mp4`
2. **Check the crop at the moments that matter:** add `--preview-at 9.5 --out frame.png` for one full-resolution still at output time 9.5 s (no encode). Shift `--x` (source pixels, + moves right) until the action is inside; a single beat's offset goes in the EDL as `start:dur:x`.
3. **Read stderr.** `upscales N.Nx` means the source is below 1080p for this crop: the clip will be soft, and platforms demote low-resolution video. Find a better source before posting.
4. **Final with overlay:** the same edit with `--overlay overlay.png --quality final --out clip.mp4`. If the brief sets a frame rate, add `--fps 30` (or `"fps": 30` in edit JSON); otherwise the source rate is kept, up to 60.
5. **Several clips:** put the edits in a jobs file and run `--jobs batch.json`; they render one after another.

Edit JSON (beats from any sources; relative paths resolve against the JSON):
```json
{"out": "clip3.mp4", "overlay": "overlay.png", "zoom": 0.08,
 "beats": [{"src": "a.mp4", "start": 91.5, "dur": 4, "x": 35}, {"src": "b.mp4", "start": 12, "dur": 6}]}
```

## What the script guarantees (covered by tests)

- 1080x1920 H.264 High yuv420p; source frame rate kept (mixed sources: 60 or 30); AAC 48 kHz stereo
- Each beat seeks to its own start; beats joined with short audio fades; the push-in carries across cuts
- A source without audio gets silence; the overlay must be a full-frame 9:16 PNG (a bare logo is refused)
- A failed or cancelled render leaves no half-written clip behind

## Rules

| Rule | Why |
|---|---|
| Draft first, final last | Drafts are several times faster; finals use x264 medium for upload quality |
| One render at a time on a laptop | Parallel encodes are slower overall and starve the machine |
| Keep the push-in subtle (default 0.08) | Adds movement without looking like an effect |
| Give each clip in a campaign its own framing (`--x`, zoom) and beats | Near-identical clips read as re-posts |
| Post the rendered file itself on every platform | A file saved back out of TikTok/CapCut carries a watermark platforms suppress |

## Load references when

- **The source is not 16:9 1080p, is HDR or 10-bit, has black bars baked in, or has several audio tracks:** read `references/sources.md` before rendering.
- **A render is slow or comes out soft:** read `references/sources.md` (encoders and upscaling).
