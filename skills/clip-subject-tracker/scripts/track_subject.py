#!/usr/bin/env python3
"""Track a subject across a whole clip using Meta's SAM 2 video predictor, and write a crop-track.json
ready for vertical-clip-renderer's --crop-track (an auto-crop that follows the subject).

  track_subject.py --clip clip.mp4 --start 91.5 --dur 4 --checkpoint sam2_hiera_small.pt \\
    --model-cfg sam2_hiera_s.yaml --point 540,1400 --out-dir track/

One prompt (a point and/or box) on the FIRST frame of the window is all this needs - SAM 2 propagates
the mask forward through the rest of the frames itself. Reuse a point you already confirmed with
clip-subject-mask (SAM 1) if you want to check the seed before committing to a multi-second propagation.

Writes:
  track/masks/frame_%05d.png   - one binary mask per frame (white = subject), for a behind-subject
                                  composite or just checking the tracking by eye (contact_sheet.py works
                                  on the mask frames directory too, or view a few directly)
  track/crop_track.json        - keyframed subject-center-x offsets, smoothed and downsampled to
                                  --keyframe-interval, in the exact {"t":...,"x":...} shape
                                  render_vertical.py --crop-track expects (t=0 at --start)

SAM 2 video propagation is slow without a GPU - realistically not something to run on a laptop for
more than a few seconds of footage. Nothing here checks output quality; look at a few mask frames
(or contact_sheet.py the masks directory) before trusting the crop-track on a real render.
"""
import argparse
import json
import os
import subprocess
import sys

def die(msg):
    sys.exit(f"track_subject: {msg}")


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


def probe_fps(clip):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=avg_frame_rate", "-of", "csv=p=0", clip], capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        die(f"cannot read frame rate from {clip}: {r.stderr.strip()[:300]}")
    num, den = r.stdout.strip().split("/")
    return float(num) / float(den) if float(den) else 30.0


def extract_frames(clip, start, dur, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{start:.3f}", "-i", clip,
                        "-t", f"{dur:.3f}", "-start_number", "0", os.path.join(out_dir, "%05d.jpg")],
                       capture_output=True, text=True)
    n = len([f for f in os.listdir(out_dir) if f.endswith(".jpg")])
    if r.returncode or n == 0:
        die(f"could not extract frames from {clip} ({start:g}-{start + dur:g}s):\n{r.stderr.strip()[-500:]}")
    return n


def bbox_center(mask):
    """(cx, cy) of a boolean mask, or None if the mask is empty (subject lost that frame)."""
    import numpy as np
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return float((xs.min() + xs.max()) / 2), float((ys.min() + ys.max()) / 2)


def smooth_and_keyframe(centers_x, fps, interval, source_w, window=5):
    """centers_x: per-frame subject center-x in source px, or None for a lost frame (held from the
    last known position). Returns keyframes as {"t","x"} with x already converted to the offset-from-
    centered-crop render_vertical.py expects (subject_x - source_w/2), moving-average smoothed, then
    sampled every `interval` seconds instead of every frame."""
    filled = []
    last = source_w / 2
    for c in centers_x:
        last = c if c is not None else last
        filled.append(last)
    smoothed = []
    for i in range(len(filled)):
        lo, hi = max(0, i - window // 2), min(len(filled), i + window // 2 + 1)
        smoothed.append(sum(filled[lo:hi]) / (hi - lo))
    n = len(smoothed)
    if n == 0:
        die("no frames to build a track from")
    step = max(1, round(interval * fps))
    idxs = list(range(0, n, step))
    if idxs[-1] != n - 1:
        idxs.append(n - 1)
    return [{"t": round(i / fps, 3), "x": round(smoothed[i] - source_w / 2)} for i in idxs]


def write_masks(masks, out_dir):
    import numpy as np
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    for i, mask in enumerate(masks):
        Image.fromarray((np.asarray(mask) * 255).astype("uint8"), mode="L").save(
            os.path.join(out_dir, f"frame_{i:05d}.png"))


def load_predictor(checkpoint, model_cfg, device):
    try:
        from sam2.build_sam import build_sam2_video_predictor
    except ImportError:
        die("sam2 not installed - see SKILL.md Setup "
            "(pip install git+https://github.com/facebookresearch/segment-anything-2.git)")
    if not os.path.exists(checkpoint):
        die(f"checkpoint not found: {checkpoint} - see SKILL.md Setup for the download URL")
    return build_sam2_video_predictor(model_cfg, checkpoint, device=device)


def propagate(predictor, frames_dir, points, labels, box):
    """Runs the real SAM 2 video predictor. Yields (frame_idx, mask) in frame order."""
    import numpy as np
    state = predictor.init_state(video_path=frames_dir)
    kwargs = {"inference_state": state, "frame_idx": 0, "obj_id": 1}
    if points:
        kwargs["points"] = np.array(points, dtype=np.float32)
        kwargs["labels"] = np.array(labels, dtype=np.int32)
    if box:
        kwargs["box"] = np.array(box, dtype=np.float32)
    predictor.add_new_points_or_box(**kwargs)
    for frame_idx, obj_ids, mask_logits in predictor.propagate_in_video(state):
        yield frame_idx, (mask_logits[0] > 0.0).cpu().numpy().squeeze()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--start", type=float, required=True, help="seconds into --clip the window starts")
    ap.add_argument("--dur", type=float, required=True, help="window length in seconds")
    ap.add_argument("--checkpoint", required=True, help="SAM 2 checkpoint .pt file")
    ap.add_argument("--model-cfg", required=True, help="SAM 2 model config, e.g. sam2_hiera_s.yaml")
    ap.add_argument("--device", default="cpu", help="'cpu' or 'cuda' (default cpu - very slow for video)")
    ap.add_argument("--point", action="append", default=[], help="x,y prompt point on the first frame; repeatable")
    ap.add_argument("--label", action="append", default=[], type=int, help="1 or 0 per --point, default 1")
    ap.add_argument("--box", help="x1,y1,x2,y2 prompt box on the first frame")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--keyframe-interval", type=float, default=0.4,
                     help="seconds between crop-track keyframes (default 0.4 - see render_vertical.py "
                          "on why this should stay coarse)")
    args = ap.parse_args()

    if not os.path.exists(args.clip):
        die(f"clip not found: {args.clip}")
    if args.dur <= 0:
        die("--dur must be positive")
    if not args.point and not args.box:
        die("need at least one --point or a --box")
    labels = list(args.label) + [1] * (len(args.point) - len(args.label))
    if len(labels) != len(args.point):
        die("more --label than --point")
    points = [parse_point(p) for p in args.point]
    box = parse_box(args.box) if args.box else None

    fps = probe_fps(args.clip)
    frames_dir = os.path.join(args.out_dir, "frames")
    n = extract_frames(args.clip, args.start, args.dur, frames_dir)

    predictor = load_predictor(args.checkpoint, args.model_cfg, args.device)
    masks, centers = [], []
    for frame_idx, mask in propagate(predictor, frames_dir, points, labels, box):
        masks.append(mask)
        centers.append(bbox_center(mask))

    from PIL import Image
    source_w = Image.open(os.path.join(frames_dir, "00000.jpg")).width
    track = smooth_and_keyframe([c[0] if c else None for c in centers], fps, args.keyframe_interval, source_w)

    write_masks(masks, os.path.join(args.out_dir, "masks"))
    track_path = os.path.join(args.out_dir, "crop_track.json")
    with open(track_path, "w") as f:
        json.dump(track, f, indent=2)
    lost = sum(1 for c in centers if c is None)
    print(f"{args.out_dir}: {n} frames tracked, {len(track)} keyframes written to {track_path}"
          + (f" ({lost} frame(s) lost the subject, held last position)" if lost else ""))


if __name__ == "__main__":
    main()
