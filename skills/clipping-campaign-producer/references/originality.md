# Originality, low quality and shadowbans — platform rules and what enforces each

Platforms decide recommendation eligibility privately and change it without notice. Nothing here can guarantee a post
is never flagged or buried. What it does: every rule the platforms have published, or that was observed costing reach in
a real campaign, is either blocked by a script or put in front of the user as a posting rule. Re-check the sources
before relying on a specific rule for a paid post — at last verification they said what is summarised below.

## What the platforms say

**TikTok — For You feed eligibility standards** ([source](https://www.tiktok.com/community-guidelines/en/fyf-standards/))
- Ineligible: unoriginal or reproduced content uploaded without new or creative edits, for example content with
  someone else's visible watermark or superimposed logo.
- Ineligible: low-quality content such as extremely short clips.
- Ineligible: content that manipulates engagement, for example "like-for-like" promises.
- Ineligible posts stay findable by search and followers; they are just not recommended.

**Instagram Reels**
- Reels visibly recycled from other apps (another app's logo or watermark) are left out of recommendations; a brand's
  own logo is fine ([source](https://www.socialmediatoday.com/news/instagram-clarifies-including-your-own-logo-on-a-reel-is-ok/730852/)).
- Reported Instagram guidance: low-resolution, watermarked, muted, bordered or mostly-text Reels, and Reels already
  posted on Instagram, are shown less ([as reported](https://www.lilachbullock.com/instagram-reel-not-eligible-for-recommendation/)).
- April 2026 originality update: accounts where most posts in a rolling 30 days are content they did not create lose
  recommendations; unique text, creative edits and voiceover count as original, while adding a watermark or changing
  speed does not ([TechCrunch](https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/)).
  Campaign b-roll is footage the user did not film, so the edit is what makes a clip theirs.

**YouTube Shorts** (see `platforms.md` for the policy links)
- "Reused content" — clips edited together with little or no narrative, or compiled from other sites — is not
  eligible for monetisation; mass-produced, repetitive uploads fall under "inauthentic content".

**Observed in a real campaign** (see `mw4_case_study.md`): letterbox with blurred fill flagged a whole round; clips
ending on long walking sections were flagged; a logo parked over the game's warning banner for almost the whole clip
was the strongest visual candidate for another flag.

## What enforces each rule

| Risk | Platforms | Enforced by |
|---|---|---|
| Borders, letterbox, blurred background fill | all | renderer only renders full-frame; `qa_clip.py` full_frame FAIL |
| Blurry or low-resolution video | TikTok, Instagram | renderer `upscales N.Nx` warning (exact); `qa_clip.py` sharpness (clearly blurry FAILs) |
| Muted / silent | Instagram | `qa_clip.py` audio FAIL |
| Re-posting a clip, or mostly the same footage | all | `qa_clip.py --against` every clip already made for the campaign: 80%+ FAIL, 50%+ WARN |
| No new creative edits | all | workflow: validated montage of beats, original hook text, per-clip framing |
| Dead air, low effort | reviewers, all | `find_beats.py --validate`; `qa_clip.py` dead_air |
| Too short | TikTok, briefs | `campaign.json` duration + `qa_clip.py` |
| Engagement bait | TikTok, briefs | `check_caption.py` engagement_bait |
| Another app's or creator's watermark, handle, promo code, face-cam | TikTok, Instagram | **nobody but you** - the eyes-on gate in the workflow |
| Mostly text | Instagram | overlay rules (text in the top third, small logo) - by eye |
| Undisclosed paid promotion | all | caption disclosure by script; platform toggle by the user (below) |

## Posting rules to give the user with every handover

1. Upload the rendered .mp4 itself to each platform — never a copy saved out of TikTok, CapCut, Instagram or YouTube
   (it carries that app's watermark).
2. Turn on the platform's paid-content setting: TikTok content disclosure (branded content), YouTube "paid
   promotion", Instagram "paid partnership" label.
3. Post each clip once per platform on one account. The same clip across several of your accounts reads as spam, and
   briefs cap reposts.
4. Never delete and re-upload a clip. Re-uploads look like duplicates, and briefs require 30 days live.
5. Space campaign clips out, and keep them a minority of an Instagram account's posts in any 30 days (inference from
   the aggregator rule above).
6. Keep likes visible; no paid boosting, story boosting or engagement groups.
7. A day after posting, check each post's recommendation status in the app (TikTok analytics and account status,
   Instagram account status). If one is marked not eligible, stop posting similar edits and re-run these checks —
   do not delete it.
