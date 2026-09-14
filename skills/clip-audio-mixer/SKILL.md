---
name: clip-audio-mixer
description: "Use when a brief explicitly allows added music or sound effects on a clip (not the default - most paid clipping briefs require original game audio only), when a rendered clip needs a music bed, timed whoosh/impact SFX on its cuts, or CapCut-style punch feel; or when an already-mixed clip sounds too quiet, too loud, or has music masking the game's own audio."
---

# Clip audio mixer

Mixes a music bed and/or timed SFX into a clip **already rendered** by `vertical-clip-renderer`. It never touches video (copies the stream) and never removes the clip's own audio — it only adds to it.

**Default assumption is no added audio.** Most paid clipping briefs require original game audio only, and `vertical-clip-renderer` never adds music on its own. Only reach for this skill when `campaign.json`'s `audio` field is something other than `"original_only"`, the brief explicitly says added music/SFX is allowed, or there's no brief at all (organic content).

## Setup

```bash
command -v ffmpeg >/dev/null || echo "ffmpeg missing - macOS: brew install ffmpeg | Debian/Ubuntu: sudo apt install ffmpeg"
M=~/.claude/skills/clip-audio-mixer/scripts/mix_audio.py
```

## Workflow

1. **Check the brief first.** If `audio` in `campaign.json` is `"original_only"` or unset, stop — this skill doesn't apply. If it names a specific track or file, use exactly that.
2. **Clear the track or SFX pack.** Read `references/licensing.md` before picking music — a platform's regular sound-picker UI being selectable does not mean it's licensed for a sponsored or monetized post.
3. **Music bed:**
   ```bash
   python3 $M --clip clip.mp4 --music track.mp3 --music-start 24 --music-db -16 --duck --out clip_mixed.mp4
   ```
   `--music-start` picks where in the track to begin (e.g. skip the intro, land on a chorus). `--duck` sidechain-ducks the music under the clip's own audio so gunfire/callouts still read clearly — use it unless the music itself is the point of the clip.
4. **Timed SFX** (whooshes/impacts on cuts, punch-ins): write a JSON list of `{"at": <output-clip seconds>, "file": "sfx.wav", "db": 0}` and pass `--sfx sfx.json`. `at` should land exactly on the cut or zoom it's accenting.
   ```bash
   python3 $M --clip clip.mp4 --sfx sfx.json --out clip_sfx.mp4
   ```
5. **Both together:** pass `--music` and `--sfx` in the same call — one mixed output, one loudness pass.
6. **Listen to it.** The script bounds loudness (see `references/mixing.md`) but can't judge whether the music suits the clip or whether ducking pumps audibly — check by ear before handing over.
7. **Re-run this clip through `qa_clip.py`** (clipping-campaign-producer) if it's going into a campaign — added audio doesn't exempt a clip from the silent-audio, dead-air, or duration checks.

## Rules

| Rule | Why |
|---|---|
| Never use this when a brief says original audio only | The default across this repo's campaigns; added music is the exception, not the norm |
| Verify the license, not just that the platform lets you pick the track | A sponsored/monetized post using a personal-use-only sound risks takedown even though the UI allowed it |
| Use `--duck` unless the music is the point of the clip | Game audio (kills, callouts, crowd) is usually what the viewer needs to hear; unducked music can bury it |
| Keep SFX gain modest and on-cut, not louder than the mix | A dominant or mistimed SFX reads as a mistake, not a produced edit |
| Video is never re-encoded (`-c:v copy`) | The renderer already produced the final picture; this skill only changes audio |
| Licensed music baked into the game's own footage (in-game radio, licensed soundtrack) is a source problem, not a mixing one | Mute or avoid that stretch at the cutting stage (`gameplay-clip-cutter`, `vertical-clip-renderer/references/sources.md`) — this skill can't fix audio already in the picture |

## Load references when

- **Picking a track, SFX pack, or checking whether a platform's sound library is safe to use on a paid post:** `references/licensing.md`.
- **Choosing `--music-db`, deciding whether to use `--duck`, timing SFX, or a clip's mix sounds off:** `references/mixing.md`.
