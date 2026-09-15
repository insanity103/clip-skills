#!/usr/bin/env python3
"""Estimate a music tempo and beat grid from a clip's (or a bare audio file's) audio track.

  find_beat_grid.py --clip clip.mp4 --out grid.json
  find_beat_grid.py --clip clip.mp4 --start 0 --end 16 --out grid.json   # only the window that has music
  find_beat_grid.py --audio track.wav --out grid.json

Onset-envelope autocorrelation, not a full beat tracker: builds a short-time loudness envelope,
takes its frame-to-frame rise (onset strength), and autocorrelates that to find the strongest
regular period in --min-bpm/--max-bpm. This works well on a clean, isolated music track and much
less reliably on gameplay audio dominated by rapid, non-musical transients (automatic gunfire,
explosions) - the "confidence" figure in the output is exactly this: a low value means don't trust
the BPM, not that the tool is broken. Always look at it before treating the grid as ground truth.
"""
import argparse
import json
import os
import subprocess
import sys

def die(msg):
    sys.exit(f"find_beat_grid: {msg}")


def extract_audio(clip, start, end, out_wav):
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", clip]
    if end is not None:
        dur = end - (start or 0)
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-ac", "1", "-ar", "22050", "-vn", out_wav]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode or not os.path.exists(out_wav):
        die(f"could not extract audio from {clip}:\n{r.stderr.strip()[-500:]}")


def read_wav_mono_f32(path):
    import wave
    import numpy as np
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        sw = w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2:
        die(f"expected 16-bit PCM wav, got {sw * 8}-bit")
    audio = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
    return audio, sr


def onset_envelope(audio, sr, hop_ms=10, win_ms=20):
    import numpy as np
    hop = max(1, int(sr * hop_ms / 1000))
    win = max(1, int(sr * win_ms / 1000))
    n = max(0, (len(audio) - win) // hop)
    if n < 2:
        die("audio window too short to analyze")
    env = np.empty(n, dtype="float64")
    for i in range(n):
        seg = audio[i * hop:i * hop + win]
        env[i] = float(np.sqrt(np.mean(seg.astype("float64") ** 2)))
    times = np.arange(n) * hop / sr
    diff = np.diff(env)
    diff[diff < 0] = 0
    return times[:-1], diff, hop_ms / 1000.0


def find_tempo(onset, hop_s, min_bpm, max_bpm):
    import numpy as np
    o = onset - onset.mean()
    ac = np.correlate(o, o, mode="full")[len(o) - 1:]
    if ac[0] == 0:
        die("silent or constant audio - nothing to find a tempo in")
    ac = ac / ac[0]
    lo = max(1, int(round((60.0 / max_bpm) / hop_s)))
    hi = min(len(ac) - 1, int(round((60.0 / min_bpm) / hop_s)))
    if hi <= lo:
        die(f"--min-bpm/--max-bpm range too narrow for this audio's length")
    best_lag = lo + int(np.argmax(ac[lo:hi]))
    period = best_lag * hop_s
    confidence = float(ac[best_lag])
    return 60.0 / period, period, confidence


def find_peaks(x, times, min_dist_s, hop_s, percentile):
    import numpy as np
    thresh = np.percentile(x, percentile)
    min_dist = max(1, int(round(min_dist_s / hop_s)))
    peaks = []
    i = 1
    while i < len(x) - 1:
        if x[i] > thresh and x[i] >= x[i - 1] and x[i] >= x[i + 1]:
            peaks.append(float(times[i]))
            i += min_dist
        else:
            i += 1
    return peaks


def build_grid(anchor, period, window_end):
    import numpy as np
    return [round(float(t), 3) for t in np.arange(anchor, window_end, period)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--clip", help="video file to pull audio from")
    src.add_argument("--audio", help="a bare audio file (any ffmpeg-readable format)")
    ap.add_argument("--start", type=float, help="seconds into the source to start analyzing")
    ap.add_argument("--end", type=float, help="seconds into the source to stop analyzing")
    ap.add_argument("--min-bpm", type=float, default=70.0)
    ap.add_argument("--max-bpm", type=float, default=180.0)
    ap.add_argument("--out", required=True, help="grid JSON to write")
    args = ap.parse_args()

    source = args.clip or args.audio
    if not os.path.exists(source):
        die(f"file not found: {source}")
    if args.end is not None and args.start is not None and args.end <= args.start:
        die("--end must be after --start")
    if args.min_bpm <= 0 or args.max_bpm <= args.min_bpm:
        die("--max-bpm must be greater than --min-bpm, both positive")

    root, ext = os.path.splitext(args.out)
    tmp_wav = f"{root}.tmp_audio.wav"
    extract_audio(source, args.start, args.end, tmp_wav)
    try:
        audio, sr = read_wav_mono_f32(tmp_wav)
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)

    dur = len(audio) / sr
    times, onset, hop_s = onset_envelope(audio, sr)
    bpm, period, confidence = find_tempo(onset, hop_s, args.min_bpm, args.max_bpm)
    peaks = find_peaks(onset, times, min_dist_s=0.08, hop_s=hop_s, percentile=95)
    anchor = peaks[0] if peaks else 0.0
    grid = build_grid(anchor, period, dur)

    result = {
        "source": source,
        "window": [args.start or 0.0, (args.start or 0.0) + dur],
        "bpm": round(bpm, 1),
        "period_s": round(period, 4),
        "confidence": round(confidence, 3),
        "anchor_s": round(anchor, 3),
        "grid": grid,
        "sharp_transients": [round(p, 3) for p in peaks],
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    note = ("LOW - this audio likely has no clean isolated beat (dense gunfire/noise dominates); "
            "treat the BPM as a rough guess, not ground truth" if confidence < 0.25 else
            "moderate - spot-check a few grid points by ear" if confidence < 0.5 else "reasonably strong")
    print(f"{args.out}: {bpm:.1f} BPM over {dur:.1f}s, confidence {confidence:.3f} ({note})")


if __name__ == "__main__":
    main()
