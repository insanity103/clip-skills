# Calibration: where the cutter's thresholds come from

Read this before overriding a verdict or changing a threshold. Everything below was measured on one tactical-shooter
campaign (Call of Duty beta footage, 4 official stringouts, 13 rendered clips with known platform outcomes). Treat the
numbers as tested for that genre and as a starting point, unverified, for others.

## Signals (analyze_video.py)

| Signal | Rate | Use |
|---|---|---|
| audio dB (RMS) | 10 Hz, both modes | activity: gunfire, impacts, callouts |
| motion (mean luma change) | full: 10 Hz; fast: keyframes (~1 Hz) | camera/scene change - NOT action in first-person games |
| luma | per sample | black frames (fades, deaths, loading) |
| red fraction | per sample | damage vignettes and death screens |
| jump / step | per sample | hard cuts between stringout clips (full mode only) |

## Activity score (find_beats.py)

- Loudness is scaled between the footage's own quiet floor (15th percentile dB) and loud level (90th percentile),
  so it adapts to each game's mix. `--ref` borrows those levels from a whole-source timeline.
- activity = 0.6 x smoothed loudness + 0.4 x share of the last ~1 s within 6 dB of the loud level.
- Dead air = activity below 0.25; a beat = activity at or above 0.45 with gaps under 1 s bridged.

## Dead-air verdicts vs platform outcomes

| Clip | Longest quiet run | Quiet share | Verdict | Outcome |
|---|---|---|---|---|
| 1 | 2.3 s | 26% | WARN | approved |
| 2 | none over 1 s | 0% | WARN (crosses 2 boundaries) | approved |
| 3 (first cut) | 5.5 s | 52% | FAIL | flagged |
| 4 (first cut) | 1.6 s | 11% | PASS | flagged - cause was visual, not audible |
| 5 (first cut) | 4.1 s | 66% | FAIL | flagged |

Thresholds chosen from this: FAIL at a 3 s quiet run or 35% quiet overall; WARN at 2 s. They separate the two
dead-air flags from both approvals. They cannot explain clip 4: dead air is one risk factor, not the whole story.

## Boundary detection

Checked against 15 visually confirmed transitions in the stringouts: 14 reported (13 strong, 1 verify), and about
70% of strong reports were real cuts. False-alarm classes: sniper scope-ins, fast turns, full-screen HUD (streak
maps, tablets). Audio is the most reliable join signal - editors cut or fade audio between clips.

## Re-calibrating for a new genre

1. Collect clips from that game whose outcome is known (approved / flagged), with their EDLs.
2. `analyze_video.py` the sources (full mode over each clip's span) and `find_beats.py --validate` each EDL with `--ref`.
3. Compare verdicts with outcomes. Adjust `validate()` in find_beats.py only if a threshold misclassifies known clips,
   and record the new table here.
4. For genres where loudness does not track action, read `genre_playbook.md` and lean on contact sheets instead.
