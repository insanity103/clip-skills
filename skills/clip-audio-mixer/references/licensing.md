# Licensing music and SFX for a posted clip

This only matters once a brief actually allows added audio (`campaign.json`'s `audio` field is
not `"original_only"`, or an organic/non-sponsored post with no brief at all). Check the brief's
exact wording first — "you may add music" and "use the provided audio track" are different rules.

## Where music is safe to use

- **A brief-supplied audio file.** If the brief hands you a track or says "use the provided
  audio", that's cleared for the campaign — use it as-is, don't substitute.
- **Platform commercial libraries**, not the general in-app sound library:
  - TikTok: the **Commercial Music Library** (separate from TikTok's regular Sounds library,
    which is for personal, non-commercial posts). A paid or branded post using a track from the
    regular Sounds library risks takedown even though the app lets you pick it — the regular
    library is licensed for personal use only.
  - YouTube: the **YouTube Audio Library** tracks marked "no attribution required" for the use
    case you have (some require credit in the description).
  - Instagram/Facebook: Meta's Sound Collection, same caveat as TikTok — check the license terms
    shown per-track, not just whether it's selectable.
- **A royalty-free library with a commercial/sponsored-content license** (Epidemic Sound, Artlist,
  Soundstripe, etc.) — these are built for exactly this use, but confirm the plan tier covers paid
  or branded content specifically; some tiers exclude ads/sponsorships.

## Where music is not safe, even if it "plays" in-app

- Commercial tracks (radio hits, popular songs) via a platform's regular sound-selection UI. The
  in-app player working is not the same as the license covering a sponsored post — Content ID
  (YouTube) and similar systems (TikTok, Instagram) can still flag, mute, or remove a monetized/
  branded post even when the same song is fine on a personal, non-monetized one.
- Licensed music baked into the game's own audio (in-game radio stations, licensed soundtracks —
  GTA, FIFA/FC, Forza's festival playlists). This is a source-footage problem, not a mixing one:
  `vertical-clip-renderer/references/sources.md` already flags this — mute or avoid that stretch
  of footage before it reaches this skill, don't try to cover it with a music bed.

## SFX

- Short SFX (whooshes, impacts, dings) are lower-risk than music but still check the source's
  license — many "free SFX" packs are free for personal use only. Prefer packs explicitly licensed
  for commercial/monetized content, or a brief-supplied SFX pack.
- Platform-provided SFX libraries (the same UI as their Sounds library) carry the same
  personal-vs-commercial distinction as music above.

## Always

- Confirm the exact license terms per track/pack before using it in a paid post — terms change,
  and a library being generally "royalty-free" doesn't guarantee sponsored-content coverage.
- Keep a record of which track/SFX pack and license was used per clip, in case a campaign's client
  asks, or a claim is filed.
