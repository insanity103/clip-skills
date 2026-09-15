---
name: campaign-tracker
description: "Use when a paid clipping campaign needs its posted clips tracked over time - the 30-day-must-stay-live deadline, per-clip repost count against the brief's cap, and engagement rate against the brief's minimum. Keeps a per-campaign .xlsx log; use after clipping-campaign-producer's handover, not instead of it."
---

# Campaign tracker

`clipping-campaign-producer` hands posting rules (min days live, max reposts, minimum engagement rate) to the user at handover as text - nothing tracks them afterward. This keeps a small `.xlsx` log per campaign so "can I take this down yet", "have I reposted this clip too many times", and "is this clip actually meeting the brief's engagement bar" have an answer weeks later, not just at the moment of posting.

Native to this repo (openpyxl only, no other dependency) - not a copy of any external skill.

## Setup

```bash
PY=~/.venvs/clipkit/bin/python
[ -x "$PY" ] || { python3 -m venv ~/.venvs/clipkit && ~/.venvs/clipkit/bin/pip install pillow numpy openpyxl; } # Debian/Ubuntu: sudo apt install python3-venv first
I=~/.claude/skills/campaign-tracker/scripts/init_tracker.py
L=~/.claude/skills/campaign-tracker/scripts/log_post.py
```

## Workflow

1. **One tracker per campaign**, created once from `campaign.json` (the same file `clipping-campaign-producer` built):
   ```bash
   $PY $I --campaign campaign.json --out trackers/mw4.xlsx
   ```
2. **Log each clip as it's posted:**
   ```bash
   $PY $L --tracker trackers/mw4.xlsx --campaign campaign.json --clip-id c3 --platform tiktok \
     --url "https://tiktok.com/@handle/video/123" --posted 2026-09-15
   ```
3. **Update the numbers when the user checks back** (same call, current views/likes):
   ```bash
   $PY $L --tracker trackers/mw4.xlsx --campaign campaign.json --clip-id c3 --platform tiktok \
     --url "https://tiktok.com/@handle/video/123" --posted 2026-09-15 --views 4200 --likes 38
   ```
   This adds a new row rather than editing the old one - the sheet is a log, not a single current-state table. That's deliberate: it keeps a history of when you checked, not just the latest number.
4. **Open the file** in Excel, Numbers, or Google Sheets to see live-until dates and PASS/FAIL engagement status - the formulas compute there, not in this script (see Notes).

## Rules

| Rule | Why |
|---|---|
| Log a post even with 0 views/likes | The live-until date and repost count matter from posting day, not from whenever you first check stats |
| The repost-limit check warns, never blocks | The post already happened in the real world by the time you're logging it; the tracker's job is to catch and flag a violation, not stand in the way of recording reality |
| A new check-in is a new row, not an edit | Keeps a history of measurements instead of only ever showing the latest number |
| Never use this in place of `clipping-campaign-producer`'s QA/caption gates | This tracks what happened *after* posting; it has no opinion on whether a clip or caption should have been posted in the first place |

## Notes

- Engagement Rate, Live-Until Date, and Status are written as Excel formulas (`openpyxl` writes the formula text, it doesn't evaluate it) - they show as the formula string, not a computed value, until you open the file in a real spreadsheet program. `tests/test_campaign_tracker.py` checks the formula text is correct, not that it evaluates correctly - that part is on whatever program actually opens the file.
- `posting.min_engagement_rate` (e.g. `0.002` for a brief's "0.20%") is a `campaign.json` field this skill introduced - see `clipping-campaign-producer/references/campaign_schema.md`. Omit it and the Status column just reports "pending"/"n/a" instead of PASS/FAIL.
