#!/usr/bin/env python3
"""Log one posted clip into a campaign's tracker workbook (built by init_tracker.py).

  log_post.py --tracker tracker.xlsx --campaign campaign.json --clip-id c3 --platform tiktok \\
    --url "https://tiktok.com/@handle/video/123" --posted 2026-09-15

  log_post.py ... --views 4200 --likes 38     # update the numbers when you check back later

Engagement rate and the live-until date are written as formulas (Likes/Views, Posted Date + the
campaign's min_days_live) so they recompute if you edit the numbers directly in the sheet -
openpyxl doesn't evaluate them itself, so they read back as the formula text until you open the
file in Excel, Google Sheets, or LibreOffice.

Warns (does not block) if this clip-id has already been logged --max-reposts times or more - the
post presumably already happened; this is a check to catch it, not a gate to prevent it.
"""
import argparse
import datetime
import json
import os
import sys

def die(msg):
    sys.exit(f"log_post: {msg}")


def parse_date(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        die(f"bad --posted '{s}': use YYYY-MM-DD")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracker", required=True, help="tracker .xlsx from init_tracker.py")
    ap.add_argument("--campaign", required=True, help="campaign.json")
    ap.add_argument("--clip-id", required=True, help="your own short id for this clip, e.g. c3")
    ap.add_argument("--platform", required=True, choices=["tiktok", "reels", "shorts"])
    ap.add_argument("--url", required=True)
    ap.add_argument("--posted", required=True, help="YYYY-MM-DD")
    ap.add_argument("--views", type=int, default=0)
    ap.add_argument("--likes", type=int, default=0)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if not os.path.exists(args.tracker):
        die(f"tracker not found: {args.tracker} - create one with init_tracker.py first")
    if not os.path.exists(args.campaign):
        die(f"campaign file not found: {args.campaign}")
    if args.views < 0 or args.likes < 0:
        die("--views and --likes must not be negative")

    try:
        from openpyxl import load_workbook
    except ImportError:
        die("openpyxl not installed - pip install openpyxl")

    campaign = json.load(open(args.campaign))
    posting = campaign.get("posting", {})
    min_days_live = posting.get("min_days_live")
    min_engagement_rate = posting.get("min_engagement_rate")
    max_reposts = posting.get("max_reposts")

    posted_date = parse_date(args.posted)

    wb = load_workbook(args.tracker)
    if "Posts" not in wb.sheetnames:
        die(f"{args.tracker} has no \"Posts\" sheet - is this a tracker from init_tracker.py?")
    posts = wb["Posts"]

    prior = sum(1 for row in posts.iter_rows(min_row=2, values_only=True)
               if row and row[0] == args.clip_id)
    if max_reposts is not None and prior + 1 > max_reposts:
        print(f"warning: {args.clip_id} has now been logged {prior + 1} time(s) - the brief allows "
              f"at most {max_reposts}", file=sys.stderr)

    r = posts.max_row + 1
    posts.cell(r, 1, args.clip_id)
    posts.cell(r, 2, args.platform)
    posts.cell(r, 3, args.url)
    posts.cell(r, 4, posted_date)
    posts.cell(r, 4).number_format = "yyyy-mm-dd"
    if min_days_live is not None:
        posts.cell(r, 5, f"=D{r}+{int(min_days_live)}")
        posts.cell(r, 5).number_format = "yyyy-mm-dd"
    posts.cell(r, 6, args.views)
    posts.cell(r, 7, args.likes)
    posts.cell(r, 8, f'=IFERROR(G{r}/F{r},"")')
    posts.cell(r, 8).number_format = "0.00%"
    if min_engagement_rate is not None:
        posts.cell(r, 9, min_engagement_rate)
        posts.cell(r, 9).number_format = "0.00%"
        posts.cell(r, 10, f'=IF(F{r}=0,"pending",IF(H{r}>=I{r},"PASS","FAIL"))')
    else:
        posts.cell(r, 10, f'=IF(F{r}=0,"pending","n/a")')
    posts.cell(r, 11, args.notes)

    wb.save(args.tracker)
    print(f"{args.tracker}: logged {args.clip_id} on {args.platform}, posted {args.posted}"
          + (f" (repost {prior + 1}/{max_reposts})" if max_reposts is not None and prior else ""))


if __name__ == "__main__":
    main()
