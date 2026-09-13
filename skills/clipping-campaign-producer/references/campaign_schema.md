# campaign.json — the brief as a file the scripts check against

Write it once per campaign, before cutting anything. Copy every phrase from the brief character for character.
Worked example: `examples/mw4/campaign.json`.

## Fields

| Field | Type | Checked by | Meaning |
|---|---|---|---|
| `name` | string | - | campaign title |
| `platforms` | list of `tiktok`, `reels`, `shorts` | you | run `check_caption.py --platform` once per platform |
| `source_rule` | string | you | where footage may come from (usually: the official folder only) |
| `duration.min`, `duration.max` | seconds | `qa_clip.py` | clip length limits from the brief |
| `audio` | `"original_only"` or free text | you | the renderer never adds music; flag licensed music in game audio by ear |
| `language` | `"en"` etc. | you | language of the post as a whole |
| `caption.required_phrases` | list of strings | `check_caption.py` | must appear exactly, case and punctuation included |
| `caption.required_tags` | list of `@handles` | `check_caption.py` | whole handles, case-insensitive |
| `caption.disclosure.options` | list of hashtags | `check_caption.py` | allowed disclosures, spelled as the brief lists them; always the first hashtag |
| `caption.disclosure.position` | `"after_text"` (default) or `"start"` | `check_caption.py` | after the post text, or the very first word of the caption |
| `caption.disclosure.own_line` | bool | `check_caption.py` | alone on its own line; defaults to true for `after_text`, false for `start` |
| `caption.disclosure.after_phrase` | bool | `check_caption.py` | must come straight after the required phrase (only whitespace between) |
| `caption.disclosure.only_one` | bool | `check_caption.py` | a second disclosure hashtag FAILs |
| `caption.tags_position` | `"anywhere"` (default), `"start"`, `"end"` | `check_caption.py` | required @tags first (after a leading disclosure) or last in the caption |
| `render.fps` | number | `render_vertical.py --fps`, `qa_clip.py` | output frame rate the brief requires; omit to keep the source rate (max 60) |
| `caption.max_extra_hashtags` | number or `null` | `check_caption.py` | hashtags besides the disclosure; `0` = none allowed; `null` = the brief sets no cap (platform limits still apply) |
| `caption.language` | `"en"` | `check_caption.py` | letters from non-Latin scripts are flagged |
| `onscreen.required_text_any` | list of lists of strings | `qa_clip.py --overlay-spec` | the overlay text must contain every phrase of at least one inner list (case and spacing ignored) |
| `onscreen.logo_required` | bool | `qa_clip.py --overlay-spec` | the overlay spec must include an image element |
| `posting.min_days_live`, `likes_visible`, `max_reposts`, `paid_boosting` | numbers / bools | you, at handover | posting rules to hand to the user |
| `unmapped_rules` | list of strings | you | every brief rule the fields above cannot hold - each one is applied by hand and repeated to the user at handover |

## Brief wording → field

| Brief says | Write |
|---|---|
| "Every caption must include the exact phrase …" | `caption.required_phrases: ["…"]` |
| "Tag @brand in the caption" | `caption.required_tags: ["@brand"]` |
| "#Ad, #Advertisement or #Sponsored … alone on its own line … first hashtag" | `caption.disclosure.options: ["#Ad", "#Advertisement", "#Sponsored"]` |
| "#Sponsored must be the very first word of the caption" | `disclosure: {"options": ["#Sponsored"], "position": "start"}` |
| "Exactly one disclosure hashtag, as the first hashtag" (no own-line rule) | `disclosure: {..., "own_line": false, "only_one": true}` |
| "Disclosure immediately after the required phrase" | `disclosure: {..., "after_phrase": true}` |
| "Tags before any other text" / "Tags at the very end of the caption" | `caption.tags_position: "start"` / `"end"` |
| "Conform to 30 fps" / "Output must stay 60 fps" | `render.fps: 30` / `render.fps: 60` |
| "Up to 3 additional hashtags" / "No other hashtags" | `max_extra_hashtags: 3` / `0` |
| "On-screen text must include 'A' and 'B' (or a close variation like 'C')" | `onscreen.required_text_any: [["A", "B"], ["C"]]` |
| "At least 10 seconds" / "15-30 seconds" | `duration: {"min": 10}` / `{"min": 15, "max": 30}` |
| "Watermark with the official logo" | `onscreen.logo_required: true` |
| "Logo in the top-right corner", "no slow motion", "mute voice chat", "remove licensed music", "use the provided audio file", "no other on-screen text" | `unmapped_rules` (implement in the overlay spec / edit - see the renderer's `references/sources.md` for audio tracks - then check by eye) |
| "Crop 21:9 to 16:9 before the vertical crop" | nothing: a centred 9:16 crop from the full height gives the identical picture |
| "Post must stay live 30 days", "likes visible", "no paid boosting" | `posting.*` |

## Ask the user (or tell them to ask the campaign manager) before cutting when

- The brief allows a "close variation" of required text without spelling one out - use the exact wording, or get the variation approved.
- Footage contains non-English game UI while the brief says English only.
- The brief's hashtag allowance exceeds a platform's limit (Instagram: 5 per Reel) - the lower limit wins.
- Anything contradicts the platforms' own rules (for example, a request that would hide the disclosure).
