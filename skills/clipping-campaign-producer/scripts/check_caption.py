#!/usr/bin/env python3
"""Check a post caption (and a YouTube title) against a campaign's caption rules before anything is posted.

  check_caption.py caption.txt --campaign campaign.json [--platform tiktok|reels|shorts] [--title "..."] [--json out.json]
  pbpaste | check_caption.py - --campaign campaign.json --platform tiktok        # macOS clipboard
  xclip -o -selection clipboard | check_caption.py - --campaign campaign.json   # Linux (wl-paste on Wayland)

Exit status 1 on any FAIL. Checks:
  required_phrase      every required phrase appears exactly as written; the closest near miss is shown
  required_tag         @handles present as whole handles (case-insensitive; @brandleague does not count as @brand)
  disclosure_present   one of the brief's disclosure hashtags, spelled exactly as the brief lists it
  disclosure_own_line  the disclosure alone on its own line (unless disclosure.own_line is false)
  disclosure_first     no other hashtag before it, and post text before it (disclosure.position "after_text", default)
  disclosure_position  the very first word of the caption (disclosure.position "start")
  disclosure_after_phrase / disclosure_only_one   when the brief says so (disclosure.after_phrase / only_one)
  tags_position        required @tags first or last in the caption (caption.tags_position "start" / "end")
  extra_hashtags       hashtags other than the disclosure within the brief's cap
  engagement_bait      "like for like"-style promises FAIL; "tag a friend", "like if", "comment X to" WARN
  language             letters from non-Latin scripts in an English-only campaign
  caption_length / title_length / hashtag_limit   platform limits (approximate; platforms change them)
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata

# Checked 2026-09-13 - see references/platforms.md for sources. Instagram's 5-tag cap dates from December 2025.
LIMITS = {
    "tiktok": {"caption": 4000},
    "reels": {"caption": 2200, "hashtags": 5},
    "shorts": {"caption": 5000, "title": 100, "hashtags": 60},
}
HASHTAG = re.compile(r"(?<![\w#])#\w+")
HANDLE = re.compile(r"(?<![\w@])@[A-Za-z0-9_.]+")
# TikTok's For You feed standards name "like-for-like" promises; campaign briefs ban bait posting outright.
BAIT_FAIL = re.compile(r"\b(like|follow|sub|subscribe)\s*(?:for|4)\s*\1\b|\b(?:l4l|f4f|s4s)\b", re.I)
BAIT_WARN = re.compile(r"\b(?:tag (?:a|your) (?:friend|mate|bestie|someone)|like (?:this |it )?if|double tap if|"
                       r"comment (?:below|\"?\w+\"? (?:for|to|if))|share (?:this|it) (?:if|with)|follow for (?:more|part)|"
                       r"drop a (?:like|comment)|smash (?:that|the) like)\b", re.I)


def closest(text, phrase):
    best, snippet = 0.0, ""
    n = len(phrase)
    for line in text.splitlines():
        for i in range(0, max(1, len(line) - n + 1)):
            window = line[i:i + n]
            m = difflib.SequenceMatcher(None, window.lower(), phrase.lower())
            if m.quick_ratio() > best and m.ratio() > best:
                best, snippet = m.ratio(), window
    return best, snippet


def check(caption, rules, platform, title):
    issues = []

    def add(level, name, msg):
        issues.append({"check": name, "level": level, "msg": msg})

    for phrase in rules.get("required_phrases", []):
        if phrase not in caption:
            score, near = closest(caption, phrase)
            hint = f' - closest text is "{near}"' if score >= 0.75 else ""
            add("FAIL", "required_phrase", f'missing exact phrase "{phrase}"{hint}')

    handles = {h.rstrip(".").lower() for h in HANDLE.findall(caption)}
    for tag in rules.get("required_tags", []):
        if tag.lower() not in handles:
            add("FAIL", "required_tag", f"missing tag {tag}")

    tags = [(m.start(), m.group()) for m in HASHTAG.finditer(caption)]
    options = rules.get("disclosure", {}).get("options", [])
    disclosure = next(((pos, t) for pos, t in tags if t in options), None)
    if options and disclosure is None:
        loose = [t for _, t in tags if t.lower() in {o.lower() for o in options}]
        hint = f" ({loose[0]} is not spelled the way the brief writes it)" if loose else ""
        add("FAIL", "disclosure_present", f"no disclosure hashtag - use one of {', '.join(options)} exactly{hint}")
    extras = [t for pos, t in tags if disclosure is None or pos != disclosure[0]]
    disc = rules.get("disclosure", {})
    position = disc.get("position", "after_text")
    own_line = disc.get("own_line", position == "after_text")
    if disclosure:
        pos, tag = disclosure
        line_start = caption.rfind("\n", 0, pos) + 1
        line_end = caption.find("\n", pos)
        line = caption[line_start:line_end if line_end != -1 else len(caption)]
        if own_line and line.strip() != tag:
            add("FAIL", "disclosure_own_line", f"{tag} must be alone on its own line, not inside \"{line.strip()[:60]}\"")
        before = [t for p, t in tags if p < pos]
        if before:
            add("FAIL", "disclosure_first", f"{tag} must be the first hashtag - {', '.join(before)} comes before it")
        if position == "start":
            if caption[:pos].strip():
                add("FAIL", "disclosure_position", f"{tag} must be the very first word of the caption")
        elif not caption[:pos].strip():
            add("FAIL", "disclosure_first", f"{tag} must come after the post text, not before it")
        if disc.get("after_phrase"):
            ends = [caption.find(p) + len(p) for p in rules.get("required_phrases", []) if p in caption]
            if ends and not any(e <= pos and not caption[e:pos].strip() for e in ends):
                add("FAIL", "disclosure_after_phrase", f"{tag} must come straight after the required phrase")
        found = [t for _, t in tags if t in options]
        if disc.get("only_one") and len(found) > 1:
            add("FAIL", "disclosure_only_one", f"only one disclosure is allowed - found {', '.join(found)}")

    required = [t.lower() for t in rules.get("required_tags", [])]
    where = rules.get("tags_position", "anywhere")
    if required and where in ("start", "end"):
        words = [w.rstrip(".,!?;:").lower() for w in caption.split()]
        if where == "start" and words and position == "start" and words[0] in {o.lower() for o in options}:
            words = words[1:]
        edge = words[:len(required)] if where == "start" else words[-len(required):]
        if sorted(edge) != sorted(required):
            add("FAIL", "tags_position", f"{' '.join(rules['required_tags'])} must be the "
                                         f"{'first' if where == 'start' else 'last'} thing in the caption")

    cap = rules.get("max_extra_hashtags")
    if cap is not None and len(extras) > cap:
        add("FAIL", "extra_hashtags", f"{len(extras)} hashtags besides the disclosure ({' '.join(extras)}); the brief allows {cap}")

    bait = BAIT_FAIL.search(caption)
    soft = None if bait else BAIT_WARN.search(caption)
    if bait:
        add("FAIL", "engagement_bait", f'"{bait.group(0)}" is a like-for-like style promise - TikTok makes such posts '
                                       f"ineligible for the For You feed and campaigns ban bait posting")
    elif soft:
        add("WARN", "engagement_bait", f'"{soft.group(0)}" reads as engagement bait, which platforms demote - '
                                       f"cut it unless the brief asks for it")

    if rules.get("language", "").lower() in ("en", "english"):
        letters = [c for c in caption if c.isalpha()]
        foreign = [c for c in letters if not unicodedata.name(c, "").startswith("LATIN")]
        if foreign:
            share = len(foreign) / len(letters)
            add("FAIL" if share > 0.2 else "WARN", "language",
                f"non-Latin letters in an English-only campaign: {''.join(foreign)[:30]}")

    limits = LIMITS.get(platform or "", {})
    if "caption" in limits and len(caption) > limits["caption"]:
        add("FAIL", "caption_length", f"{len(caption)} characters; {platform} allows about {limits['caption']}")
    if "hashtags" in limits and len(tags) > limits["hashtags"]:
        add("FAIL", "hashtag_limit", f"{len(tags)} hashtags; {platform} limit is {limits['hashtags']}")
    if title is not None and "title" in limits and len(title) > limits["title"]:
        add("FAIL", "title_length", f"title is {len(title)} characters; {platform} allows {limits['title']}")

    verdict = "FAIL" if any(i["level"] == "FAIL" for i in issues) else "WARN" if issues else "PASS"
    return {"verdict": verdict, "issues": issues,
            "stats": {"characters": len(caption), "hashtags": [t for _, t in tags], "handles": sorted(handles)}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caption", help="caption text file, or - for stdin")
    ap.add_argument("--campaign", required=True, help="campaign.json with a 'caption' section")
    ap.add_argument("--platform", choices=sorted(LIMITS))
    ap.add_argument("--title", help="YouTube Shorts title to length-check")
    ap.add_argument("--json", help="write the result as JSON")
    args = ap.parse_args()

    caption = sys.stdin.read() if args.caption == "-" else open(args.caption, encoding="utf-8").read()
    caption = caption.replace("\r\n", "\n").strip("\n")
    rules = json.load(open(args.campaign))["caption"]
    result = check(caption, rules, args.platform, args.title)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=1, ensure_ascii=False)
    print(f"caption: {result['verdict']}  ({result['stats']['characters']} chars, hashtags: "
          f"{' '.join(result['stats']['hashtags']) or 'none'})")
    for i in result["issues"]:
        print(f"  {i['level']:<4}  {i['check']}: {i['msg']}")
    sys.exit(1 if result["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
