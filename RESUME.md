# RESUME — clip skills (continue on the Linux PC)

Read this first. Everything the next session needs is in this folder; nothing depends on the Mac.

## Where things stand

Ten Claude Code skills for turning sponsor gameplay footage into vertical clips for paid clipping campaigns
(TikTok, YouTube Shorts, Instagram Reels), plus organic (non-sponsored) format knowledge and a stylizer for
non-brief content. Built, tested and installed on the Mac.

| Skill | What it does |
|---|---|
| gameplay-clip-cutter | finds the action in long footage by loudness; blocks dead air and cuts that jump between players; `references/organic_formats.md` documents when this pipeline doesn't apply |
| vertical-clip-renderer | full-frame 9:16 renders only (never letterbox); push-in, overlay, `--fps`, `--crop-track`; warns on low-resolution sources |
| clip-overlay-builder | required text and logo overlay; platform safe zones; collisions with the game's own HUD (`hud_map.py`) |
| clip-audio-mixer | music bed and/or timed SFX on top of a rendered clip, only for briefs that allow added audio; sidechain ducking, loudness-normalized |
| clip-cover-picker | scores candidate frames from a rendered clip for sharpness/exposure to pick a TikTok/Shorts/Reels cover still |
| clip-stylizer | vertical echo/ghost + saturation/posterize filter for organic (non-sponsored) clips; never for briefed content |
| clip-subject-mask | segments a subject out of one still frame with Meta's SAM (ViT-B); own PyTorch venv, not the shared one |
| clip-subject-tracker | propagates a mask across a whole clip with SAM 2, writes a `crop_track.json` for vertical-clip-renderer's `--crop-track`; own PyTorch venv, realistically GPU-only |
| campaign-tracker | logs posted clips per campaign to a `.xlsx`: 30-day live deadline, repost count vs. the brief's cap, engagement rate vs. its minimum |
| clipping-campaign-producer | brief → `campaign.json`; caption checker; pre-post QA gate; originality and posting rules; `selftest.py` |

Verified on the Mac (macOS, Python 3.14, ffmpeg 9.0): all 116 tests pass against the installed skills; framing
check correct on all 13 real campaign renders; correct captions for 4 other-genre test briefs pass and realistic
mistakes fail; self-test 18/18. **Verified on Linux (Ubuntu) 2026-09-13** — see "Linux verification" below;
116/116 tests pass there too, install.sh self-test passes.

## First steps on this PC

1. System tools: `sudo apt install python3 python3-venv ffmpeg fonts-dejavu-core` (Fedora/Arch: `README-LINUX.md`)
2. `bash ~/clip-skills/install.sh` — must end with `all checks passed`
3. `bash ~/clip-skills/tests/run_tests.sh` — full suite, 10-20 minutes
4. Write the results under "Linux verification" below.

If something fails, the likely causes, in order:
- **Font metrics.** Overlay tests were written against DIN Condensed; Linux uses DejaVu Sans Condensed, which is
  wider. `test_text_too_long_for_one_line_wraps_instead_of_shrinking_past_the_floor` is the sensitive one. Fix the
  test's font-specific expectation, not the real check.
- **Older distro ffmpeg** (before 5.x) may lack a test source filter or option. Check `ffmpeg -version`.
- **No libx264** (Fedora `ffmpeg-free`): install RPM Fusion's ffmpeg.

## Linux verification (2026-09-13, Ubuntu, Python 3.14.4, ffmpeg 8.0.1)

- install.sh self-test: **all checks passed**. Condensed bold font resolved to Liberation Sans Narrow Bold
  (`fonts-liberation-sans-narrow`, preinstalled on Ubuntu Desktop) — current Ubuntu's `fonts-dejavu-core` no
  longer ships a condensed face, so the DejaVu assumption below and in README-LINUX.md was updated.
- run_tests.sh: **116/116 passed, 0 skipped** (first run reported "OK (skipped=16)" — the whole
  `BuildOverlay` class in `tests/test_build_overlay.py` was silently skipping because its hardcoded
  `FONT_CANDIDATES` didn't include Liberation. Added that path, which surfaced one real font-metric failure
  (`test_text_too_long_for_one_line_wraps_instead_of_shrinking_past_the_floor`: this font needed 74px against
  a hardcoded 76px floor) — fixed with a small tolerance per the "fix the test, not the check" rule below,
  not by changing `build_overlay.py`. Second full run: 116/116, 0 skipped, 0 failed.
- Also restored the executable bit on every `.py` script under `skills/` and `tests/` — the Mac→Linux
  transfer (a plain copy, not `git clone`; this folder has no `.git`) had stripped it. Harmless functionally
  (everything's invoked as `python3 script.py`) but fixed for consistency with the Mac state.
- **Takeaway for next time:** a "skipped" test count in this suite's summary line reads exactly like a pass —
  check `FONT_CANDIDATES` in `test_build_overlay.py` first if a rerun on a new machine reports skips again.

## Remaining work, in order

1. **Verify on Linux** (above).
2. **Publish the review page** — the user asked for it; not done yet. Content: `FINDINGS.md` plus `evidence/`.
   Design already decided — build it, don't redesign:
   - Report treatment, light and dark themes. Look of a broadcast QC sheet: PASS/WARN/FAIL chips, timecode-style
     numbers, the campaign's overlay yellow `#FED000` as the only accent (highlighter use; `#7A5A00` for accent text
     on light).
   - Type: Archivo at condensed width (wdth 75, weight 700) for headings; Source Serif 4 body; IBM Plex Mono data.
   - Light: paper `#EDF0F2`, surface `#F8FAFB`, ink `#14202B`, muted `#536270`, rule `#CBD3DA`; pass `#1E7A4F`,
     warn `#A66A00`, fail `#C23B22`. Dark: `#0F161C`, `#151F27`, ink `#E6EDF2`, muted `#93A3B0`, rule `#26343F`,
     accent `#FED000`, pass `#4CC38A`, warn `#F0B429`, fail `#FF6B52`.
   - Title: "Why the MW4 Clips Got Flagged". Sections: rounds at a glance → three causes with confidence and evidence
     (letterbox `cmp_clip1.png`; dead-air table + `cmp_clip3.png`; logo over ENEMY NEARBY `gt_c4_logozone.png` —
     the "MW4" in some of its tiles is the in-game calling card, not an overlay) → risk in the delivered v3 clips
     (clip 5 weakest; clip 3's DOUBLE KILL hidden under THIS WEEKEND `delivered_clip3_9.5s.png`; clip 4 dark) →
     checked and ruled out → what protects the next campaign (4 skills + originality table from
     `skills/clipping-campaign-producer/references/originality.md`) → posting rules → open questions.
   - Evidence captions were checked against the images.
3. **Optional — ask the user first:**
   - Bundle one free OFL font (e.g. Barlow Condensed Bold from Google Fonts) so overlays match on Mac and Linux.
     Needs a download.
   - Re-cut delivered clip 5: QA verdict FAIL (64% dead air; 89% same footage as its flagged version).
   - Overlay features some briefs need: a backing bar behind text; a check that overlays cover under N% of frame.
   - HDR tone-mapping: the Mac's Homebrew ffmpeg lacks `zscale`; many Linux builds have it — test the recipe in
     `skills/vertical-clip-renderer/references/sources.md` and promote its marker.

## Hard-won rules — do not relearn these

- Never letterbox or blur-fill. Full-frame 9:16 only (all five letterboxed clips were flagged).
- Dead air: FAIL at a 3 s quiet run or 35% quiet overall (calibrated on real approved/flagged outcomes).
- Run `hud_map.py` against the overlay on every edit (clip 4's logo sat on a game warning for 13.7 of 14 s).
- Look at full-resolution, timestamped frames before claiming anything about footage.
- Quote `description:` in SKILL.md frontmatter — an unquoted ` #` makes YAML silently truncate it.
- Platforms never say why a clip is flagged: report risk factors, never a cause, never a guarantee.
- The user posts; never post for them. Captions go to the user as copy-paste text in chat.
- Test skill scripts first (red, then green) and mutation-check new tests; several real bugs were caught that way.

## About the user

- Earns from paid clipping campaigns (Whop Content Rewards, Clipping Culture); posts to TikTok, Shorts and Reels.
- Wants copy-paste-ready captions in chat, verified claims, and short action-first updates.
- Uses the i-have-adhd output style. On Linux: `claude plugin marketplace add ayghri/i-have-adhd`,
  `claude plugin install i-have-adhd@i-have-adhd`, then `touch ~/.claude/.i-have-adhd-always` for always-on.
- Also uses the superpowers plugin (`claude plugin install superpowers@claude-plugins-official`).
- Delegates side research to Xiaomi MiMo; its drafts need fact-checking (two batches contained errors that would
  have broken clips — stretched crops, a wrong 4K recipe, outdated platform limits).

## What is in this folder

```
RESUME.md          this file
README-LINUX.md    install steps for Linux
install.sh         installs the skills, venv and runs the self-test
FINDINGS.md        the review: what was flagged, why, with evidence
brief.txt          the MW4 campaign brief
skills/            the ten skills (what install.sh copies)
tests/             116 tests, fixtures, 4 other-genre test briefs, run_tests.sh, hud_calibration notes
evidence/          images for the review page
analysis/          signal timelines of the MW4 sources and clips (for re-validating edits)
```

Not included (too big): the 6 GB MW4 source stringouts and the rendered clips. They stay on the Mac in
`~/Downloads/clip-skills/sources/` and `~/Downloads/mw4 clips/`.
