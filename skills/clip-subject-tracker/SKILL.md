---
name: clip-subject-tracker
description: "Use when the 9:16 crop should follow a moving subject across a whole clip instead of a fixed offset - propagates a mask through every frame with Meta's SAM 2 and writes a crop-track.json for vertical-clip-renderer's --crop-track. Needs a separate PyTorch-based setup, not the shared clipkit venv, and is realistically GPU-only for anything but a few seconds of footage."
---

# Clip subject tracker

Runs Meta's SAM 2 video predictor: one prompt (point/box) on the first frame of a window, propagated automatically through every subsequent frame. Outputs a per-frame mask sequence and a smoothed, keyframed `crop_track.json` that plugs directly into `vertical-clip-renderer --crop-track`.

**Heavier than clip-subject-mask, and video-specific.** SAM (v1, `clip-subject-mask`) segments one still frame and has no notion of motion. SAM 2 is a different model built for exactly this - propagating a mask across a video - and needs its own checkpoint and package. Don't reach for SAM 1 for a moving subject; it can't track.

**Realistically a GPU tool.** SAM 2 video propagation on CPU is slow - fine to try on a couple of seconds to see if it's worth it, impractical as a routine step for longer footage on a laptop.

## Setup

```bash
python3 -m venv ~/.venvs/clipkit-sam2       # separate from clipkit-sam (SAM 1) and the shared clipkit venv
~/.venvs/clipkit-sam2/bin/pip install torch torchvision   # a CUDA build (pytorch.org) if you have a GPU - strongly recommended here
~/.venvs/clipkit-sam2/bin/pip install git+https://github.com/facebookresearch/segment-anything-2.git

mkdir -p ~/.cache/sam2
curl -L -o ~/.cache/sam2/sam2_hiera_small.pt \
  https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_small.pt   # ~185MB; see the repo for tiny/base_plus/large
# the matching config ships inside the sam2 package install (sam2_hiera_s.yaml) - pass its name, not a path

PY=~/.venvs/clipkit-sam2/bin/python
T=~/.claude/skills/clip-subject-tracker/scripts/track_subject.py
```

## Workflow

1. **Confirm the seed prompt first with clip-subject-mask** (SAM 1) on the window's first frame - a bad prompt wastes an entire propagation, and checking one frame is seconds versus minutes.
2. **Track the window:**
   ```bash
   $PY $T --clip SRC.mp4 --start 91.5 --dur 4 --checkpoint ~/.cache/sam2/sam2_hiera_small.pt \
     --model-cfg sam2_hiera_s.yaml --point 540,1400 --out-dir track/
   ```
3. **Look at the masks before trusting the track** - a few frames from `track/masks/`, or run `gameplay-clip-cutter/scripts/contact_sheet.py` against the `track/frames/` directory it also leaves behind. SAM 2 can lose the subject partway through (occlusion, a cut it wasn't warned about); a lost frame holds the last known position rather than snapping to zero, but that's a fallback, not a fix - re-seed or shorten the window if tracking visibly drifts.
4. **Feed the track straight into the renderer:**
   ```bash
   $PY_CLIPKIT ~/.claude/skills/vertical-clip-renderer/scripts/render_vertical.py \
     --src SRC.mp4 --edl "91.5:4" --crop-track track/crop_track.json --quality draft --out draft.mp4
   ```
   (`vertical-clip-renderer` runs under the regular `clipkit` venv, not this one - the two skills don't need to share an environment, only the `crop_track.json` file.)
5. **Draft first.** Same rule as every other render in this repo: check the draft before spending a final-quality encode on a track that might need re-seeding.

## Rules

| Rule | Why |
|---|---|
| One window (--start/--dur) at a time, not a whole long source | Propagation cost scales with frame count; track only the beat you're actually going to use |
| Look at the mask frames before trusting crop_track.json | SAM 2 can lose the subject silently - the track still gets written, just wrong |
| `--keyframe-interval` stays coarse (default 0.4s) | A per-frame track is noisy and produces an unreadably long filter expression in the renderer for no visible benefit at 30fps - see `render_vertical.py`'s own docstring |
| GPU strongly preferred | CPU propagation is realistically a few-seconds-of-footage tool, not a routine step |

## Notes

- `crop_track.json`'s `t` values are seconds into the *window* (`--start`), matching `--crop-track`'s expectation of "seconds into the beat, 0 at its start" - if the beat you render doesn't start at the same source time as `--start` here, the track won't line up.
- Nothing here has been run against real SAM 2 weights in this repo's own test environment (no GPU, no checkpoint download there) - frame extraction, the bbox/smoothing/keyframing math that builds `crop_track.json`, and mask writing are tested against synthetic per-frame data (`tests/test_track_subject.py`); the actual SAM 2 propagation is the one part you're verifying yourself, on your own machine.
- The per-frame mask sequence this writes (`track/masks/`) is also the raw material for a behind-subject overlay composite (text/logo that appears to pass behind the moving subject, not just sit on top) - that compositing step isn't built yet. The masks are there if you want to build it: multiply each source frame by its mask to get a subject-only RGBA cutout video, then `ffmpeg overlay` that on top of the gameplay+text composite so the subject occludes the text wherever they overlap.
