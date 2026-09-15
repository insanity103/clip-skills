---
name: clip-subject-mask
description: "Use when a single frame needs the player/character precisely segmented out from the background - for a text-behind-subject effect on a still hook frame, a masked cover treatment, or as the seed prompt for clip-subject-tracker (SAM 2) before tracking a subject across a whole clip. Needs a separate PyTorch-based setup, not the shared clipkit venv."
---

# Clip subject mask

Runs Meta's Segment Anything (SAM, ViT-B checkpoint) on one still frame with a point or box prompt, and writes a binary subject mask. One frame in, one mask out - it has no idea what happens before or after that frame.

**A real dependency jump.** Every other skill in this repo runs on ffmpeg and Pillow alone. This one needs PyTorch and a downloaded model checkpoint (375MB for ViT-B, the default). It gets its own venv (`clipkit-sam`), never the shared `clipkit` one `install.sh` sets up automatically - this skill's setup is a manual step you run yourself when you actually want to use it.

## Setup

```bash
python3 -m venv ~/.venvs/clipkit-sam
~/.venvs/clipkit-sam/bin/pip install torch torchvision   # CPU build is fine; see pytorch.org for a CUDA build if you have a GPU
~/.venvs/clipkit-sam/bin/pip install git+https://github.com/facebookresearch/segment-anything.git

mkdir -p ~/.cache/sam
curl -L -o ~/.cache/sam/sam_vit_b_01ec64.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth   # 375MB
# larger/more accurate, if ViT-B isn't precise enough on a hard case:
#   vit_l (1.2GB): https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth
#   vit_h (2.4GB): https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

PY=~/.venvs/clipkit-sam/bin/python
S=~/.claude/skills/clip-subject-mask/scripts/mask_subject.py
```

## Workflow

1. **Pick a prompt point or box.** Open the frame (or extract one: `--clip clip.mp4 --at 2.5`) in any image viewer and read off pixel coordinates for a point clearly inside the subject, or a box roughly around them.
2. **Run it, always with `--preview`:**
   ```bash
   $PY $S --clip clip.mp4 --at 2.5 --checkpoint ~/.cache/sam/sam_vit_b_01ec64.pth \
     --point 540,1400 --out mask.png --preview preview.png
   ```
3. **Check `preview.png` before using the mask for anything.** It shows the mask tinted over the frame plus your prompt point/box - SAM segments whatever region the prompt points at, which is not always what you meant (a hand can pull in the whole weapon model, a point near an edge can grab the background instead).
4. **Missed the subject?** Add a negative point (`--point x,y --label 0`) on the region that got wrongly included, or tighten a `--box` around just the subject, and re-run.
5. **Tracking the subject across a whole clip, not just one frame?** This mask's prompt point is the seed for **clip-subject-tracker** (SAM 2) - confirm it here first since checking one frame is much cheaper than re-running a multi-second propagation.

## Rules

| Rule | Why |
|---|---|
| Always check `--preview` before using a mask | SAM has no concept of "the player" - it segments the prompted region literally, and a bad prompt produces a confidently wrong mask |
| Use ViT-B unless it's visibly wrong on a hard frame | It's 3-6x smaller and faster than ViT-L/ViT-H; only step up if precision actually suffers |
| This skill never touches the actual clip file | It only reads one frame and writes a mask PNG - compositing that mask into a render is a separate step |
| CPU inference on one frame is seconds, not minutes | Unlike clip-subject-tracker's video propagation, a single-frame SAM call is practical on a laptop |

## Notes

- `mask.png` is binary: white (255) = subject, black (0) = everything else. No anti-aliased edge - if you need a soft edge for compositing, blur the mask afterward with whatever tool builds the composite.
- Nothing here has been run against a real checkpoint in this repo's own CI/test environment (no GPU, no multi-hundred-MB downloads there) - the CLI parsing, frame extraction, and mask/preview compositing are tested against synthetic data (`tests/test_mask_subject.py`); the actual SAM call is the one part you're verifying yourself, on your own machine, the first time you run this.
