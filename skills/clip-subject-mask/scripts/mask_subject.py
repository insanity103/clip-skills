#!/usr/bin/env python3
"""Segment a subject (player, character) out of one frame using Meta's Segment Anything (SAM, ViT-B).

  mask_subject.py --frame frame.png --checkpoint sam_vit_b_01ec64.pth --point 540,1400 --out mask.png
  mask_subject.py --clip clip.mp4 --at 2.5 --checkpoint sam_vit_b_01ec64.pth --box 300,900,780,1900 --out mask.png
  mask_subject.py ... --out mask.png --preview preview.png    # also writes a check-it-by-eye overlay

One still image in, one mask out - this has no idea what happens in the rest of the clip. For a mask
that follows the subject across a whole moving clip (for a follow-crop or a behind-subject overlay),
this is the seed prompt for clip-subject-tracker (SAM 2), not the tool for the whole job by itself.

Needs a point and/or a box prompt - SAM has no built-in idea of "the player", it segments whatever
region your prompt points at. --label 1 marks a point as inside the subject (the default for every
point unless you pass --label 0 for that point, meaning "not this").

mask.png is a binary mask: white (255) = subject, black (0) = everything else. --preview overlays the
mask in translucent color plus your prompt points/box on the original frame, so you can confirm the
segmentation before anything downstream uses it.
"""
import argparse
import os
import subprocess
import sys

def die(msg):
    sys.exit(f"mask_subject: {msg}")


def parse_point(s):
    try:
        x, y = (float(v) for v in s.split(","))
    except ValueError:
        die(f"bad --point '{s}': use x,y")
    return x, y


def parse_box(s):
    try:
        x0, y0, x1, y1 = (float(v) for v in s.split(","))
    except ValueError:
        die(f"bad --box '{s}': use x1,y1,x2,y2")
    if x1 <= x0 or y1 <= y0:
        die(f"bad --box '{s}': x2,y2 must be greater than x1,y1")
    return x0, y0, x1, y1


def extract_frame(clip, t, out_png):
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{t:.3f}", "-i", clip,
                        "-frames:v", "1", out_png], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out_png):
        die(f"could not extract frame at {t:g}s from {clip}:\n{r.stderr.strip()[-500:]}")


def load_predictor(checkpoint, model_type, device):
    try:
        from segment_anything import sam_model_registry, SamPredictor
    except ImportError:
        die("segment-anything not installed - see SKILL.md Setup "
            "(pip install git+https://github.com/facebookresearch/segment-anything.git)")
    if not os.path.exists(checkpoint):
        die(f"checkpoint not found: {checkpoint} - see SKILL.md Setup for the download URL")
    sam = sam_model_registry[model_type](checkpoint=checkpoint)
    sam.to(device=device)
    return SamPredictor(sam)


def segment(predictor, image, points, labels, box):
    import numpy as np
    kwargs = {"multimask_output": True}
    if points:
        kwargs["point_coords"] = np.array(points)
        kwargs["point_labels"] = np.array(labels)
    if box:
        kwargs["box"] = np.array(box)
    predictor.set_image(image)
    masks, scores, _ = predictor.predict(**kwargs)
    return masks[int(scores.argmax())]


def save_mask(mask, out_path):
    import numpy as np
    from PIL import Image
    Image.fromarray((np.asarray(mask) * 255).astype("uint8"), mode="L").save(out_path)


def save_preview(image, mask, points, labels, box, out_path):
    import numpy as np
    from PIL import Image, ImageDraw
    base = Image.fromarray(image).convert("RGBA")
    tint = Image.new("RGBA", base.size, (0, 200, 255, 110))
    alpha = Image.fromarray((np.asarray(mask) * 255).astype("uint8"), mode="L")
    overlaid = Image.composite(tint, Image.new("RGBA", base.size, (0, 0, 0, 0)), alpha)
    out = Image.alpha_composite(base, overlaid)
    draw = ImageDraw.Draw(out)
    for (x, y), label in zip(points, labels):
        color = (0, 255, 0, 255) if label else (255, 0, 0, 255)
        draw.ellipse([x - 8, y - 8, x + 8, y + 8], outline=color, width=3)
    if box:
        draw.rectangle(list(box), outline=(255, 255, 0, 255), width=3)
    out.convert("RGB").save(out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--frame", help="a still image to segment")
    src.add_argument("--clip", help="extract the frame from this video first (use with --at)")
    ap.add_argument("--at", type=float, help="seconds into --clip to extract the frame from")
    ap.add_argument("--checkpoint", required=True, help="SAM checkpoint .pth file")
    ap.add_argument("--model-type", default="vit_b", choices=["vit_b", "vit_l", "vit_h"],
                     help="must match the checkpoint (default vit_b, the smallest/fastest)")
    ap.add_argument("--device", default="cpu", help="'cpu' or 'cuda' (default cpu - slow but always available)")
    ap.add_argument("--point", action="append", default=[], help="x,y prompt point; repeatable")
    ap.add_argument("--label", action="append", default=[], type=int,
                     help="1 (inside the subject) or 0 (not) for the --point at the same position; "
                          "defaults to 1 for any --point without a matching --label")
    ap.add_argument("--box", help="x1,y1,x2,y2 prompt box")
    ap.add_argument("--out", required=True, help="mask PNG: white = subject")
    ap.add_argument("--preview", help="also write a colored overlay + prompt markers for a sanity check")
    args = ap.parse_args()

    if args.clip and args.at is None:
        die("--clip needs --at")
    if not args.point and not args.box:
        die("need at least one --point or a --box")
    labels = list(args.label) + [1] * (len(args.point) - len(args.label))
    if len(labels) != len(args.point):
        die("more --label than --point")
    points = [parse_point(p) for p in args.point]
    box = parse_box(args.box) if args.box else None

    frame_path = args.frame
    tmp_frame = None
    if args.clip:
        tmp_frame = os.path.splitext(args.out)[0] + ".seed_frame.png"
        extract_frame(args.clip, args.at, tmp_frame)
        frame_path = tmp_frame
    elif not os.path.exists(args.frame):
        die(f"frame not found: {args.frame}")

    import numpy as np
    from PIL import Image
    image = np.array(Image.open(frame_path).convert("RGB"))

    predictor = load_predictor(args.checkpoint, args.model_type, args.device)
    mask = segment(predictor, image, points, labels, box)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    save_mask(mask, args.out)
    if args.preview:
        save_preview(image, mask, points, labels, box, args.preview)
    if tmp_frame and os.path.exists(tmp_frame):
        os.remove(tmp_frame)

    covered = float(np.asarray(mask).mean()) * 100
    print(f"{args.out}: {mask.shape[1]}x{mask.shape[0]}, {covered:.1f}% of the frame masked as subject")


if __name__ == "__main__":
    main()
