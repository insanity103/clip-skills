#!/usr/bin/env python3
"""Mix a music bed and/or timed SFX into an already-rendered clip. Video is never re-encoded.

  mix_audio.py --clip clip.mp4 --music track.mp3 --music-db -16 --out clip_music.mp4
  mix_audio.py --clip clip.mp4 --music track.mp3 --music-start 24 --duck --out clip_music.mp4
  mix_audio.py --clip clip.mp4 --sfx sfx.json --out clip_sfx.mp4
  mix_audio.py --clip clip.mp4 --music track.mp3 --sfx sfx.json --out clip_full.mp4

Only use this when the brief's `audio` field is not "original_only" - most paid clipping briefs forbid
added music entirely (see clipping-campaign-producer/references/campaign_schema.md). Game audio (or the
clip's existing track) is always kept; this only adds to it, never replaces it.

sfx.json: [{"at": 2.3, "file": "whoosh.wav", "db": 0}, ...] - "at" is the output-clip time in seconds
the effect starts at (e.g. a cut point or the payoff frame); "db" is an optional per-effect gain.

--duck sidechain-ducks the music under the clip's own audio (gunfire, callouts, crowd) so the game
audio still reads as the primary track and the music dips under it rather than masking it.

Output audio is loudness-normalized (single-pass loudnorm, -14 LUFS / -1.5 dBTP - the common social
video target) so adding tracks can't push the mix into clipping or out ahead of platform loudness norms.
"""
import argparse
import json
import os
import subprocess
import sys

TARGET_LUFS = -14.0
TARGET_TP = -1.5


def die(msg):
    sys.exit(f"mix_audio: {msg}")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode:
        die(f"cannot read {path}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    return {"has_video": v is not None, "has_audio": a is not None,
            "duration": float(j["format"].get("duration") or 0)}


def load_sfx(path, clip_dur):
    entries = json.load(open(path))
    out = []
    for i, e in enumerate(entries, 1):
        if "at" not in e or "file" not in e:
            die(f"sfx entry {i} needs 'at' and 'file'")
        if not os.path.exists(e["file"]):
            die(f"sfx entry {i}: file not found: {e['file']}")
        if not 0 <= e["at"] < clip_dur:
            die(f"sfx entry {i}: at={e['at']:g} is outside the clip (0-{clip_dur:.2f}s)")
        out.append({"file": e["file"], "at": float(e["at"]), "db": float(e.get("db", 0))})
    return out


def build_graph(clip_dur, has_clip_audio, music, music_db, music_start, duck, sfx):
    parts = []
    inputs = []  # (extra ffmpeg -i args)
    next_idx = 1  # 0 is the clip itself

    clip_audio = "[0:a]" if has_clip_audio else None
    if not has_clip_audio:
        parts.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={clip_dur:.3f}[gsrc]")
        clip_audio = "[gsrc]"

    music_label = None
    if music:
        inputs.append(["-ss", f"{music_start:.3f}", "-i", music])
        idx = next_idx
        next_idx += 1
        fade = min(0.3, clip_dur / 4)
        parts.append(f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"atrim=duration={clip_dur:.3f},apad,atrim=duration={clip_dur:.3f},"
                     f"volume={music_db}dB,afade=t=in:d={fade:.3f},afade=t=out:st={clip_dur - fade:.3f}:d={fade:.3f}"
                     f"[mraw]")
        if duck:
            parts.append(f"{clip_audio}asplit=2[gA][gSC]")
            clip_audio = "[gA]"
            parts.append(f"[mraw][gSC]sidechaincompress=threshold=0.05:ratio=8:attack=5:release=300[mduck]")
            music_label = "[mduck]"
        else:
            music_label = "[mraw]"

    sfx_labels = []
    for n, s in enumerate(sfx):
        inputs.append(["-i", s["file"]])
        idx = next_idx
        next_idx += 1
        delay_ms = round(s["at"] * 1000)
        label = f"sfx{n}"
        parts.append(f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"volume={s['db']}dB,adelay={delay_ms}|{delay_ms}[{label}]")
        sfx_labels.append(f"[{label}]")

    streams = [clip_audio] + ([music_label] if music_label else []) + sfx_labels
    n = len(streams)
    if n == 1:
        parts.append(f"{streams[0]}asetpts=PTS-STARTPTS[aout]")
    else:
        parts.append(f"{''.join(streams)}amix=inputs={n}:duration=first:normalize=0,"
                     f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11[aout]")
    return ";".join(parts), inputs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clip", required=True, help="already-rendered clip (from vertical-clip-renderer)")
    ap.add_argument("--music", help="music track to mix in as a bed under the clip's own audio")
    ap.add_argument("--music-db", type=float, default=-16.0,
                     help="music gain relative to the mix, in dB (default -16dB, roughly the low end of "
                          "the 10-20%% research guideline; raise toward -14dB for a more present bed)")
    ap.add_argument("--music-start", type=float, default=0.0, help="seconds into the music file to start from")
    ap.add_argument("--duck", action="store_true",
                     help="sidechain-duck the music under the clip's own audio so game sound still reads as primary")
    ap.add_argument("--sfx", help="JSON list of {at, file, db} timed sound effects")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.clip):
        die(f"clip not found: {args.clip}")
    meta = probe(args.clip)
    if not meta["has_video"]:
        die(f"{args.clip} has no video stream")
    if not args.music and not args.sfx:
        die("nothing to mix: pass --music, --sfx, or both")
    if args.music and not os.path.exists(args.music):
        die(f"music not found: {args.music}")

    sfx = load_sfx(args.sfx, meta["duration"]) if args.sfx else []
    graph, extra_inputs = build_graph(meta["duration"], meta["has_audio"], args.music, args.music_db,
                                       args.music_start, args.duck, sfx)

    root, ext = os.path.splitext(args.out)
    tmp = f"{root}.partial{ext or '.mp4'}"
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", args.clip]
    for extra in extra_inputs:
        cmd += extra
    cmd += ["-filter_complex", graph, "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
            "-t", f"{meta['duration']:.3f}", tmp]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        if os.path.exists(tmp):
            os.remove(tmp)
        die(f"ffmpeg failed:\n{r.stderr.strip()[-800:]}")
    os.replace(tmp, args.out)
    print(f"{args.out}: mixed {'music ' if args.music else ''}{'(ducked) ' if args.duck else ''}"
          f"{f'+ {len(sfx)} sfx' if sfx else ''}".strip())


if __name__ == "__main__":
    main()
