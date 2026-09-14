# Platform Retention Research: Length, Hooks, Pacing

> Compiled from public 2026 short-form editing guides (TikTok/Reels/Shorts gaming-clip data and pacing studies), not measured against this pipeline's own campaigns. Cross-check against `genre_playbook.md` and `mw4_case_study.md` (clipping-campaign-producer) before treating a number here as a hard threshold — those two are calibrated on real flagged/approved clips, this file is not. Applies across FPS/shooter titles and beyond; genre-specific structure still lives in `genre_playbook.md`.

## Length

- Sweet spot for gaming clips: **15–34 s** for maximum reach, up to 30–60 s when the moment needs setup/context.
- Fast-paced titles (Valorant, Apex, CoD-style shooters): stay at the short end, **15–30 s**.
- Slower or story-driven content (sandbox builds, RP, horror): can run **60–90 s** without hurting completion rate.
- This lines up with `find_beats.py`'s default `--clip-min 12 --clip-max 18`; briefs asking for longer "context" clips are the case to override the default range, not the norm.

## The hook (first 2–3 seconds)

- Viewers decide whether to keep watching almost immediately — trim every frame before the actual hook (danger, threat, stakes, or the setup for a build reveal).
- Treat each clip as a standalone unit with its own hook and payoff, not a fragment of a longer video. This matches `genre_playbook.md`'s per-genre "Hook (first 2 s)" sections — it is the general version of the same rule.

## Pacing and cuts

- General short-form guidance: a cut, zoom, or visual change roughly every **1.5–4 s**, so the frame is never static long enough for a viewer to lose the thread and scroll away.
- "Pattern interrupts" — a zoom-in on the key moment, a caption callout, a slow-mo punch on the payoff — work well roughly every 4 s.
- Gameplay clips already get most of this from cutting to action beats (`find_beats.py`) and the push-in (`render_vertical.py --zoom`); this is the reasoning for why those exist, not a new requirement to add.

## On-screen text and safe zones

- Keep essential text out of the **bottom ~150 px** of a 1080×1920 frame — platform UI (caption stack, like/share column) sits there. This is consistent with, and slightly more specific about the bottom edge than, `clip-overlay-builder`'s "nothing essential below y ≈ 1536" rule — treat the overlay builder's `--check-safe` output as the authority since it's per-platform and measured against actual UI, not this general guidance.

## Audio

- Background music (when a brief allows any) at **10–20% volume** relative to voice/game audio, matched in energy to the clip's intensity.
- Most paid clipping briefs (see `clipping-campaign-producer`) forbid added music entirely and require original game audio only — that requirement overrides this section.

## Content types that perform

- Highlight plays, funny fails, quick tips/tutorials, and reactions are the categories that consistently perform well.
- Clips with a clear narrative hook (not just a raw highlight) get higher completion rates — supports `genre_playbook.md`'s emphasis on hook framing per genre over just picking the loudest beat.

## How to use this file

- Use it as a sanity check when a brief is silent on length, pacing, or cut frequency — not as an override for brief requirements, campaign-specific calibration in `mw4_case_study.md`, or the platform safe-zone values enforced by `build_overlay.py --check-safe`.
- If a specific number here (e.g. "150 px", "15–34 s") ever conflicts with a measured result from `qa_clip.py` or a flagged/approved clip, trust the measured result and update this file rather than the other way around.

## Sources

- [Best Length for TikTok Gaming Clips in 2026 (Data-Backed Guide) — Clypse](https://clypse.ai/blog/best-tiktok-gaming-clip-length-2026)
- [Complete Guide to Short-Form Video for Gamers (2026) — Clypse](https://clypse.ai/blog/complete-guide-short-form-video-gamers-2026)
- [Viral Gameplay in 2026: Why Live Gaming Clips Dominate YouTube Shorts and TikTok Feeds — Tech Times](https://www.techtimes.com/articles/313453/20251218/viral-gameplay-2026-why-live-gaming-clips-dominate-youtube-shorts-tiktok-feeds.htm)
- [How to Improve TikTok Watch Time (Retention Tips) — Reeldrift](https://reeldrift.pro/learn/tiktok-retention-tips)
- [Short-Form Video Pacing: The Editing Rhythm Guide (2026) — Shortzly](https://shortzly.com/blog/short-form-video-pacing-editing-guide)
- [How to Post Gaming Clips to TikTok (Full Workflow) — insights.gg](https://insights.gg/blog/how-to-post-gaming-clips-to-tiktok)
