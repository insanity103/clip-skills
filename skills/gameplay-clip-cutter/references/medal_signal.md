# Medal banners as a detection signal

A Call of Duty multiplayer kill that meets specific conditions (not just any kill) triggers an
on-screen medal banner — an icon plus a word ("HEADSHOT", "REVENGE", "LONGSHOT", "DOMINATION",
"ASSASSIN", "SAVIOR", "POINT BLANK", and similar) that appears center-screen for roughly a second.
This is part of the game's own Combat Medal category, distinct from Multi-Kill, Streak, Scorestreak
and Game Mode medals, which reward other event types. Confirmed present, with the same on-screen
banner behavior, in Black Ops 6 and Black Ops 7 (Sep 2026); the medal system itself goes back
much further in the franchise and the multiplayer HUD/medal behavior is functionally the same
release to release, so treat this as safe to rely on for any recent title, not just the one a
specific source video happens to be.

## Why this is useful

A Combat Medal only fires for a kill under a specific, non-default condition — the game itself is
telling you "this kill was notable," not just "a kill happened." That makes the banner a second,
independent signal alongside `analyze_video.py`'s loudness timeline:

- **It doesn't depend on audio level.** A quiet melee/knife takedown (Assassin) or a kill through a
  wall (Blindfire-type medals) may not spike the loudness timeline the way gunfire does, but still
  triggers a banner — loudness alone would miss it.
- **It never fires on menus, shop/perk screens, or cutscenes.** Unlike loudness (which was fooled by
  the outro screen's music and by a Zombies vendor interaction's ambient sound, both false positives
  caught only by visual contact-sheet review earlier in this project), a medal banner is gameplay-only
  by construction — real player action produced it.
- **It's cheap to check visually.** On a contact sheet, the skull icon + banner text is easy to spot
  at a glance across tiles, faster than reading a loudness graph for the same window.

## How to use it

- Treat a medal banner as corroborating evidence when picking a candidate window, not as the thing
  to build the edit around. The banner confirms "something happened here worth looking at" — the
  actual gunfight/kill is still the content. Don't name, caption, or design a clip's hook around the
  fact that a medal appeared; a viewer doesn't care that the HUD said "HEADSHOT," they care about the
  kill itself.
- Still never place overlay text or a logo over the medal banner's screen region (center, roughly the
  top third to upper-half) — `hud_map.py` will flag this as a collision like any other HUD element.
  See `clip-overlay-builder`'s rules; a real case in this project had a hook line covering the
  HEADSHOT banner for 76% of a clip's runtime, well past the ~30% guidance.
- When triaging long footage, a burst of medal banners close together (a multi-kill streak) is a
  strong hint that a loudness-scored candidate in that same window is real combat, not a false
  positive — cross-check the two signals rather than trusting either alone.

## What this doesn't do

There's no automated medal-banner detector in this toolkit yet (no OCR/template-matching script) —
this is a visual-review heuristic for when you're already looking at a contact sheet, not a new
scored signal in `find_beats.py`. If a false-positive rate against loudness-only scoring turns out to
be a recurring problem, a template-match detector (the skull icon has a consistent shape) would be
the natural next step, but hasn't been built or validated.
