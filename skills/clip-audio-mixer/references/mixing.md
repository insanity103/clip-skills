# Mixing music and SFX: levels, ducking, timing

Backs up the defaults in `mix_audio.py`. Drawn from general 2026 short-form editing research (see
`gameplay-clip-cutter/references/platform_retention.md`), not measured against a specific campaign
— if a brief or a client gives you an exact spec (a target LUFS, a fixed music level), that wins.

## Music level

- General guidance: background music at **10–20% perceived volume** relative to the primary
  audio (here, the game/voice track) — roughly **-20dB to -14dB** relative gain. `--music-db`
  defaults to -16dB, the middle of that range.
- Push toward -14dB only for a clip where the music itself is part of the appeal (a montage cut to
  a specific song's drop); stay at -20dB or lower when the game audio (gunfire, callouts, crowd
  reactions) needs to stay clearly primary.
- Don't trust the relative-gain number alone on a clip with wildly varying game-audio loudness — a
  quiet exploration clip needs less music headroom than a firefight. `--duck` (below) handles this
  automatically; a fixed `--music-db` does not.

## Ducking (`--duck`)

- Sidechain-compresses the music under the clip's own audio, so a gunshot, kill confirmation, or
  callout automatically pushes the music down for that moment and it recovers after.
- Use it whenever the clip's own audio carries information the viewer needs to hear clearly (kill
  feed sounds, dialogue, a game's own callouts) — which is most gameplay clips. Skip it only for a
  clip where the music is the point and the game audio is pure ambience.
- The default attack/release (5ms attack, 300ms release) reacts fast to transients (gunfire,
  impacts) without audibly pumping on sustained sound (music, ambient game audio).

## SFX timing

- Place a whoosh or impact SFX **on the cut**, not slightly before or after it — `sfx.json`'s `at`
  is the exact output-clip timestamp, matching what a viewer sees change on screen.
- A punch-in or zoom (from `vertical-clip-renderer`'s `--zoom`, or a hard cut between beats) reads
  as flat without a matching sound; this is most of what makes CapCut-style edits feel more
  "produced" than a plain cut.
- Don't stack more than one or two SFX per cut — a single clean hit reads as intentional, several
  overlapping ones read as noisy and can push the loudnorm pass into over-compressing the whole mix.
- Keep SFX gain modest (`db: -3` to `0` in `sfx.json`) relative to the music bed — an SFX that's
  louder than everything else reads as a mistake, not an accent.

## Final loudness

- `mix_audio.py` always runs a single-pass `loudnorm` on the finished mix (target -14 LUFS /
  -1.5 dBTP), the common target across TikTok, Reels and Shorts. This is a safety net against
  clipping or an over-loud mix when music and SFX stack on top of game audio — it is not a
  replacement for reasonable `--music-db`/`db` values, and single-pass loudnorm is an approximation
  (it doesn't do the two-pass analyze-then-normalize loudnorm does). If a brief specifies an exact
  loudness target, verify the output against it directly rather than trusting the default.

## Sanity-check the result

- Listen to the mixed output next to the original clip before handing it over — nothing here can
  confirm the music suits the clip's energy, or that ducking didn't leave an audible pump on a
  sustained sound. This skill measures and bounds loudness; it doesn't judge taste.
