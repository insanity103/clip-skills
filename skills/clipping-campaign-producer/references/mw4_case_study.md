# MW4 beta campaign — case study

> The review of a real clipping campaign that these skills were built from. Paths such as `evidence/`, `analysis/` and
> `tests/hud_calibration/` refer to the build folder `~/Downloads/clip-skills/`, if it still exists.


What was made, what the platform rejected, and what the evidence actually supports.
Measurements come from the timelines in `analysis/`; images referenced are in `evidence/`.

---

## 1. What was produced

Three rounds. Segments are source seconds, `start:duration`.

| Round | Clip | Source | Edit | Outcome |
|---|---|---|---|---|
| v1 letterbox | 1-5 | all four | single windows, gameplay in a centred band with blurred fill | **all 5 flagged** |
| v2 full-frame | 1 | 01_TopPlays | `96.4:18` | **approved** |
| | 2 | 02_Batch2 | `152:18` | **approved** |
| | 3 | 03_Week2_A | `90:14` | **flagged** |
| | 4 | 04_Week2_B | `148:14` | **flagged** |
| | 5 | 04_Week2_B | `186:16` | **flagged** |
| v3 montage | 3 | 01_TopPlays | `91.5:4, 125.5:2.5, 133:9` | delivered, outcome unknown |
| | 4 | 04_Week2_B | `116:7.5, 124.5:8.5` | delivered, outcome unknown |
| | 5 | 04_Week2_B | `187:3, 192.5:9.5, 204.8:1.5` | delivered, outcome unknown |

All output 1080x1920 @ 60 fps, original audio, x264 crf 18 preset slow.

## 2. Why v1 was flagged — high confidence

Gameplay occupied roughly a third of the frame; the rest was a blurred, darkened copy of the same
footage (`evidence/cmp_clip1.png`, top row). Platforms explicitly deprioritise videos where borders or
blurred backgrounds fill significant screen space. Rebuilding full-frame — centre-crop to 9:16, upscale
1.78x, sharpen, slight push-in — got clips 1 and 2 approved with no other change. That is the single
most reliable lesson of the whole exercise.

## 3. Why three v2 clips were still flagged — mixed confidence

Measured with the calibrated validator (`find_beats.py --validate`, loudness levels taken from the whole
source). "Dead" = a stretch with no gunfire or impact: walking, reloading, looking around.

| Clip | Longest dead run | Dead share | Verdict | Outcome |
|---|---|---|---|---|
| 1 | 2.3s | 26% | WARN | approved |
| 2 | none ≥1s | 0% | WARN (crosses 2 clip boundaries) | approved |
| 3 v2 | **5.5s** | **52%** | FAIL | flagged |
| 4 v2 | 1.6s | 11% | PASS | flagged |
| 5 v2 | **4.1s** | **66%** | FAIL | flagged |

- **Clip 3 v2**: the double kill lands at ~8s and the last 5 seconds are walking through an empty
  courtyard, a gate and an empty room. Confirmed on the contact sheet, not just in the numbers.
- **Clip 5 v2**: opens on a LEVEL UP popup and 3 seconds of running; the fight is sporadic throughout.
- **Clip 4 v2, measured later with `hud_map.py` and confirmed frame by frame**: the MW4 logo sat over the
  game's own UI for 13.7 of its 14 seconds - the red "ENEMY NEARBY" warning for most of the clip, a player
  card at the start, and "DOUBLE KILL" at 9-10.5s (`tests/hud_calibration/gt_c4_logozone.png`). This is the strongest
  visual candidate for why it was flagged. Still a correlation: platforms do not say why.
- **Clip 4 v2**: *no measurable dead air*. Its cause is visual and remains unproven. Candidates seen on
  the sheet: long stretches of repositioning and staring at walls, the game's own "ENEMY NEARBY" banner
  colliding with the MW4 logo overlay, and HUD text clipped by the 9:16 crop. Content-matching against
  other creators posting the same official b-roll is also plausible and is not observable from here.

**Do not over-claim.** Platforms do not disclose flag reasons. Dead air correlates with 2 of 3 here;
one flagged clip has none, and one approved clip carried 26% dead time. Treat these as risk factors,
not a formula.

## 4. Risk in what was delivered (v3)

- **Clip 5 v3 is the weak one.** 12.5 of its 14 seconds come from the footage that was already flagged
  as v2 (89% overlap), it still opens with the same LEVEL UP popup and ~2s of quiet, and it measures 64%
  dead. The validator FAILs it. If anything gets flagged again, expect this one. Recommend re-cutting it
  from different footage entirely — e.g. the dense sequence right after 206.7s in `04_Week2_B`, which the
  beat finder ranks near the top of that source.
- **Clip 4 v3** is dark (mean luma 42-69 vs 70-120 for the others) with a heavy red damage vignette
  throughout. Dramatic, but murky on a phone screen.
- **Clip 3 v3** is dense, but its payoff is hidden: at 9.5s the game's "DOUBLE KILL" medal banner sits
  directly under the required "THIS WEEKEND" line (only "DO" is visible). Verified on a full-resolution
  frame of the delivered file (`examples/mw4/overlay_clip3_check.png`). Its hook line ("Sniper doesn't
  miss") also only matches the first of its three beats. The rebuilt overlay (tighter stacking) clears the
  banner by ~25px, by luck rather than by check - which is why `hud_map.py` exists.

- **Game UI under the required text is partly a footage problem, not only a layout problem.** In clip 3 v3 all
  four overlay elements sit over game UI for about half the clip: a round scoreboard (0-4s), the hardpoint
  objective timer and compass (4-6.5s), medal banners (8.5-12.3s), and weapon-pickup prompts under the logo.
  Hardpoint and round-based beats carry much more HUD than free-for-all fights - weigh that when choosing beats.

## 5. Things verified that turned out NOT to be problems

Worth recording because each looked like a finding at first.

- **"Two MW4 logos" in the final frames.** The second one is the player's in-game calling card in the
  HUD, which happens to be the MW4 beta card — not a burned-in watermark.
- **Creator gamertags on screen** (e.g. "MrConnorTube" under the logo in clip 4). Real, but they appear
  in essentially every source reel, including the approved clips, so they cannot explain the flags.
- **A burned-in numeric player ID** sits in the bottom-left corner of the beta footage. The centred 9:16
  crop removes it. It would reappear in any wider reframe.
- **A cut I had placed at 114.0s** was actually at 114.7s. The sheet that produced that reading had no
  timestamps on its tiles. Every contact sheet the new tool makes is labelled for this reason.

## 6. Open compliance questions for the user

- Some source footage carries **non-English HUD text** (Spanish "APOYAR", Korean kill banners) while the
  brief says English content only. Approved clip 2 may contain Korean HUD text, so it seems tolerated,
  but it is worth a question to the campaign manager rather than a guess.
- The brief forbids removing a post before 30 days, which is why re-cuts must be checked *before*
  posting, not after.

## 7. Process lessons that shaped the tools

- **Loudness, not motion, finds the action.** In a first-person game the camera never stops moving, so
  motion is high while walking. Gunfire is what separates a fight from traversal.
- **Stringouts are compilations.** They contain hard cuts, fades through black, and ~0.5s dissolves
  between different creators' clips. A beat that straddles one produces an unintended jump to another
  player mid-shot. Editors fade the audio across these joins, which is the most reliable way to find them.
- **Timestamps on every contact-sheet tile.** See §5.
- **Verify before concluding.** Three of the four "findings" in §5 came apart on inspection.
- **Encoder preset was costing hours.** x264 `preset slow` took 179s to make 5s of output on this
  machine; `veryfast` took 44s and `h264_videotoolbox` 37s, at the same visual target. The push-in effect
  costs almost nothing (42s without it).
- **Killing a background ffmpeg does not stop the shell loop that spawned it** — the loop just starts the
  next file. Kill the process group.
