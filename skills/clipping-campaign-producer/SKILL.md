---
name: clipping-campaign-producer
description: "Use when working on a paid clipping campaign or sponsored creator brief (Whop Content Rewards, Clipping Culture, a studio's gameplay or trailer campaign) - turning a brief and supplied footage into posts, writing or checking captions, titles, hashtags and #Ad disclosures, checking finished clips before posting, or working out why a clip was rejected, shadowbanned, or flagged as unoriginal or low quality on TikTok, YouTube Shorts or Instagram Reels."
---

# Clipping campaign producer

A brief is a pass/fail contract, and platforms quietly bury clips that look recycled or low quality. Turn the brief into `campaign.json` once; then every clip and caption is checked by script against it before anything reaches the user.

**The user posts, not you.** Prepare files and copy-paste text; never upload or post for them. Posts usually must stay up 30 days, so a mistake cannot be deleted and redone.

**No check can guarantee a post is never flagged** — platforms do not publish their systems. What this workflow guarantees is that every known, checkable rule passed. Say exactly that; never promise more.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow; } # Debian/Ubuntu: sudo apt install python3-venv first
P=~/.claude/skills/clipping-campaign-producer/scripts
```

**New machine (macOS or Linux)?** Run `$PY $P/selftest.py` first - about a minute, one PASS/FAIL line per tool, with the install command for anything missing.

## Workflow

1. **Brief → `campaign.json`.** Read `references/campaign_schema.md` first. Copy phrases character for character. Rules the schema cannot hold go in `unmapped_rules`; ask the user about anything ambiguous before cutting.
2. **Footage and logo:** only the brief's official sources. Prepare the logo with **clip-overlay-builder**.
3. **Cut** — **REQUIRED SUB-SKILL: gameplay-clip-cutter.** Validate every EDL; never reuse beats an earlier clip in the campaign used.
4. **Overlay and render** — **REQUIRED SUB-SKILLS: clip-overlay-builder, vertical-clip-renderer.** Draft without overlay → `hud_map.py` → final with overlay (add `--fps` when `campaign.json` sets `render.fps`).
5. **QA gate — run on every clip, against every clip already made for this campaign:**
   ```bash
   $PY $P/qa_clip.py new1.mp4 new2.mp4 --campaign campaign.json --overlay-spec overlay.json \
     --ref SRC.timeline.json --against delivered/*.mp4 "delivered/previous (flagged)"/*.mp4
   ```
   Exit 1 = do not hand over. It checks format, length, letterbox/blur fill, blur, silent audio, dead air, re-used footage (80%+ FAILs), required on-screen text and logo.
6. **Eyes-on gate — scripts cannot see watermarks.** Build a sheet of each final (`$PY ~/.claude/skills/gameplay-clip-cutter/scripts/contact_sheet.py clip.mp4 --fps 1`) and confirm, in writing to the user: no other app's or creator's watermark, handle, promo code, face-cam or end card; the payoff is visible; the required text is readable.
7. **Captions per platform** — save each to a file and run
   `$PY $P/check_caption.py caption.txt --campaign campaign.json --platform tiktok` (Shorts: add `--title "..."`). Exit 1 = fix it. Engagement bait ("like for like", "tag a friend") is flagged.
8. **Hand over:** files in the user's folder (move replaced versions into a `previous/` subfolder — never delete); every caption and title written out in chat as copy-paste blocks; the posting rules from `references/originality.md`.

## Rules

| Rule | Why |
|---|---|
| Required caption phrase exact, including capitals and punctuation | Briefs forbid substitutions; reviewers reject near misses |
| Disclosure placed exactly as the brief says - encoded in `campaign.json` (default: own line, first hashtag, after the text) | Briefs differ (first word, right after the phrase, only one); `check_caption.py` enforces whichever the file says |
| Hashtag cap = the smaller of the brief's and the platform's | Instagram allows 5 per Reel |
| Re-cut a flagged clip from different footage, not the same beats | A re-cut reusing 89% of a flagged clip's footage also failed the dead-air check |
| Turn on each platform's paid-partnership / paid-promotion setting as well | The caption hashtag does not replace it; TikTok's policy requires the toggle |
| Report a flag's cause as measured risk factors, never as fact | Platforms do not say why |

## Load references when

- **Converting a brief** (always, before step 1): `references/campaign_schema.md`.
- **Before every handover, and whenever a clip was flagged, shadowbanned or not recommended:** `references/originality.md` — each platform's originality rules, which check covers each, and the posting rules scripts cannot enforce.
- **Writing captions or titles, or choosing hashtags:** `references/platforms.md`. Platform limits change: re-check a limit at its source before relying on it for a paid post.
- **A clip was flagged and you need a precedent:** `references/mw4_case_study.md` — what was flagged, what the measurements showed, what fixed it.
- **You want a worked example:** `examples/mw4/` (campaign.json, overlay spec, logo).
