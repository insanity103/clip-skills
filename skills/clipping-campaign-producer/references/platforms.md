# Platform Specs: TikTok, YouTube Shorts, Instagram Reels

> Drafted by MiMo (Xiaomi) from public sources; fact-checked by Claude on 2026-09-13. Items marked **[corrected]** were wrong or outdated in the draft. Pixel safe zones are estimates - no platform publishes them.

Last compiled: 2026-09-13. Every number has a source URL and check date. Items without a verifiable source are marked **(unverified)**.

---

## TikTok

### Upload specs

- Max upload: up to 60 min for select users (trials started Mar 2024); in-app recording max 10 min. No official "short-form eligibility" cutoff — the For You page is not gated by duration.
  - Source: https://www.shopify.com/blog/how-long-can-a-tiktok-be (checked Sep 10 2026)
- Recommended resolution: 1080×1920 (9:16). Minimum: 540×960.
  - Source: https://www.shopify.com/blog/tiktok-video-size (checked Sep 10 2026)
- Frame rate: 30 fps recommended; 60 fps accepted. No official max published. **(unverified)**
- File size: iOS 287.6 MB, Android 72 MB, web 1 GB, ads 500 MB.
  - Source: https://www.shopify.com/blog/tiktok-video-size (checked Sep 10 2026)
- Codecs: MP4, MOV (organic). H.264 universal; H.265 via MOV on iOS. Audio codec not published — AAC-LC is de facto standard. **(unverified for AAC)**
  - Source: https://www.shopify.com/blog/tiktok-video-size (checked Sep 10 2026)

### Text limits

- Caption: **4,000 characters** (raised from 2,200); the feed truncates after the first line or two. **[corrected]**
  - Sources: https://typecount.com/blog/tiktok-caption-character-limit and https://textcharactercounter.com/tiktok-character-limit/ (2026 guides, checked 2026-09-13)
- No separate hashtag count cap — limited only by the 4,000-char caption. Recommended 2–6 hashtags.
  - Source: https://www.shopify.com/blog/best-hashtags-for-tiktok (checked Sep 10 2026)
- Ad description limit: 100 characters, no special characters/emojis.
  - Source: https://www.shopify.com/blog/tiktok-video-size (checked Sep 10 2026)

### Screen safe zones (1080×1920) **(estimated — not published by TikTok)**

`build_overlay.py --check-safe` uses top [0,0,1080,130], bottom [0,1536,1080,1920], buttons [960,600,1080,1536] - the MW4 layout that was approved (logo at y 1340-1472) clears them. The wider ranges below are worst cases (long captions, small phones).

- **Top bar** (username, follow, search): conservative [0, 0, 1080, 180], typical [0, 0, 1080, 140]
- **Bottom caption/hashtag area**: conservative [0, 1570, 900, 1920], typical [0, 1620, 850, 1920]
- **Right action column** (like, comment, share, bookmark, sound disc): conservative [920, 600, 1080, 1570], typical [940, 700, 1080, 1500]
- Values derived from CapCut templates, Adobe Premiere TikTok presets, and creator forums. Vary by device, OS version, app version.

### Paid-promotion disclosure

- **Toggle name**: "Branded content" / "Content disclosure" (under "More options" on the post screen). **(partially unverified — exact UI path varies by app version)**
- Adds a "Paid partnership" label below the creator's username.
- TikTok's Branded Content Policy requires the in-app toggle; #Ad hashtag alone is not sufficient per their policy.
  - Source: TikTok Branded Content Policy (https://www.tiktok.com/legal/page/global/branded-content-policy/en — JS-rendered, content could not be fetched)
- **Creator reports (unverified)**: Some creators report reduced FYP distribution when the branded content toggle is enabled. TikTok officially denies algorithmic penalty.

### Why clips get flagged/suppressed

**Platform official:**
- Unoriginal content (reposted from other platforms, visible foreign watermarks) is not eligible for FYP recommendation.
  - Source: https://www.shopify.com/blog/tiktok-algorithm (checked Sep 10 2026)
- Low-quality content (blurry, watermarks from other apps, mostly text/static images) is suppressed.
- Undisclosed paid promotions can be removed.
- Creator Rewards Program requires original content, 1+ minute length, community guidelines compliance.
  - Source: Widely cited; official terms page (https://www.tiktok.com/legal/page/us/creator-rewards-program-terms/en) returned empty via fetch **(partially unverified)**

**Creator reports (unverified):**
- Videos with YouTube/Instagram/CapCut watermarks get reduced distribution.
- "300 view jail": new accounts or low-engagement accounts reportedly capped at ~200–300 views. Not officially acknowledged.
- Very short videos (<15 s) reportedly underperform vs 1+ min content since TikTok's longer-content push.
- Excessive unrelated hashtags may trigger spam detection.
- AI-generated content without the required label may be penalized.

### 2025–2026 changes

- 50% of watch time now on videos 1+ min (TikTok Creator Academy statement, Jun 2024; still current).
  - Source: https://www.shopify.com/blog/how-long-can-a-tiktok-be (checked Sep 10 2026)
- Creator Rewards Program replaced Creator Fund (~2024), requiring 1+ min original content. **(launch date unverified)**
- Algorithm increasingly favors niche communities and longer watch time over broad viral hashtags (Dec 2025).
  - Source: https://www.shopify.com/blog/tiktok-algorithm (checked Sep 10 2026)
- New features added: Footnotes, PineDrama, Nearby feed (2025–2026).
  - Source: TikTok Support site navigation, checked Sep 10 2026

---

## YouTube Shorts

### Upload specs

- Max duration: 3 minutes (Shorts eligibility since Oct 15, 2024). Must be vertical or square aspect ratio.
  - Source: https://support.google.com/youtube/answer/15424877 (checked Jul 2025)
- Max resolution: 1080p for Shorts.
  - Source: https://support.google.com/youtube/answer/10059070 (checked Jul 2025)
- Aspect ratio: 9:16 (vertical) or 1:1 (square) qualify as Shorts. 16:9 is treated as long-form.
  - Source: https://support.google.com/youtube/answer/12779649 (checked Jul 2025)
- Frame rate: 24, 25, 30, 48, 50, 60 fps (and others). Upload in the same frame rate as recorded.
  - Source: https://support.google.com/youtube/answer/1722171 (checked Jul 2025)
- Codecs: H.264 (High Profile), progressive scan, yuv420p. Audio: AAC-LC, Opus, or Eclipsa Audio. Container: MP4 (Fast Start).
  - Source: https://support.google.com/youtube/answer/1722171 (checked Jul 2025)
- Recommended bitrate: 8 Mbps (standard fps), 12 Mbps (high fps) for 1080p SDR.
  - Source: https://support.google.com/youtube/answer/1722171 (checked Jul 2025)
- File size: No Shorts-specific limit documented. General upload limit is 256 GB or 12 h for verified accounts.
  - Source: https://support.google.com/youtube/answer/71673 **(unverified — URL inferred, not fetched)**

### Text limits

- Title: max 100 characters.
  - Source: https://support.google.com/youtube/answer/10343433 (checked Jul 2025)
- Description: max 5,000 characters.
  - Source: https://support.google.com/youtube/answer/57407 (checked Jul 2025)
- Hashtags: hard cap 60 per video. If exceeded, **all** hashtags on that video are ignored. Up to 3 displayed above the title. Over-tagging may result in video removal from search/uploads.
  - Source: https://support.google.com/youtube/answer/6390658 (checked Jul 2025)

### Screen safe zones (1080×1920) **(unverified — not published by YouTube)**

- **Top bar** (status bar, progress bar, close/share): conservative [0, 0, 1080, 200], typical [0, 0, 1080, 140]
- **Bottom overlay** (handle, title, subscribe, description, music): conservative [0, 1400, 1080, 1920], typical [0, 1550, 1080, 1920]. Multi-line titles can push overlay to ~y=1400.
- **Right action column** (like, comment, share, remix, audio disc): conservative [880, 500, 1080, 1400], typical [930, 600, 1080, 1350]
- Derived from creator tool analyses and community measurements. Vary significantly by device (notch, navigation bar, font size, accessibility settings).

### Paid-promotion disclosure

- **Toggle name**: "Paid promotion" checkbox — "Yes, my video includes branded content."
- **Location**: Upload details → Show more → Paid Promotion → check box → "Set Up" for optional age/location restrictions.
  - Source: https://support.google.com/youtube/answer/154235 (checked Jul 2025)
- Adds an "Includes paid promotion" overlay at the start of the video.
- YouTube's disclosure and #Ad are independent mechanisms. YouTube references FTC/ASA/DGCCRF but does not mandate #Ad specifically. Best practice: use both.
  - Source: https://support.google.com/youtube/answer/154235 (checked Jul 2025)
- YouTube's systems may auto-detect undisclosed branded content and apply a label.
  - Source: https://support.google.com/youtube/answer/154235 (checked Jul 2025)

### Why clips get flagged/suppressed

**Platform official:**
- **Reused Content**: repurposing content without significant original commentary, substantive modifications, or educational/entertainment value. Explicitly includes "clips of moments from your favorite show edited together with little or no narrative" and "short videos compiled from other social media websites."
  - Source: https://support.google.com/youtube/answer/1311392 (checked Jul 2025)
- **Inauthentic Content** (renamed from "Repetitious Content" Jul 15, 2025): mass-produced, generic, repetitive, or manipulative content. Includes AI-generated content from generic templates.
  - Source: https://support.google.com/youtube/answer/1311392 (checked Jul 2025)
- **Shorts monetization ineligibility**: "Non-original Shorts, such as unedited clips from others' movies or TV shows, reuploading other creators' content, or compilations with no original content added."
  - Source: https://support.google.com/youtube/answer/12504220 (checked Jul 2025)
- Shorts over 1 min with active copyright claims are **blocked globally** (not just demonetised).
  - Source: https://support.google.com/youtube/answer/15424877 (checked Jul 2025)
- No published minimum resolution or bitrate for monetisation. Quality guidelines focus on originality, not technical specs.

**Creator reports (unverified):**
- Gaming clip compilations without voice-over/face-cam frequently flagged under "reused content."
- Shorts reuploaded from TikTok (with watermark visible) reportedly get suppressed.
- Mass-uploading dozens of Shorts/day with minimal variation → monetisation suspension under "inauthentic content."
- "Clip farming" crackdown in 2025: increased enforcement against clipping long-form streams without transformative commentary.
- Letterboxed/non-vertical content gets significantly reduced distribution in Shorts feed.

### 2025–2026 changes

- **Mar 31, 2025**: Shorts views now count on play/replay start (no minimum watch time). Old metric renamed "Engaged views." YPP eligibility still based on Engaged views.
  - Source: https://support.google.com/youtube/answer/10059070 (checked Jul 2025)
- **Jul 15, 2025**: "Repetitious content" renamed to "Inauthentic content."
  - Source: https://support.google.com/youtube/answer/1311392 (checked Jul 2025)
- **Oct 15, 2024**: 3-minute Shorts enabled.
  - Source: https://support.google.com/youtube/answer/15424877 (checked Jul 2025)
- New features: "Get feedback" button (hook/pacing analysis), "Edit with AI," related video links on Shorts, Brand Partnerships external links, likeness detection during upload checks.
  - Source: https://support.google.com/youtube/answer/10343433, https://support.google.com/youtube/answer/57407 (checked Jul 2025)

---

## Instagram Reels

### Upload specs

- In-app recording max: 3 minutes (increased from 90 s in Jan 2025). Upload max: 15 minutes. Videos >15 min may be treated as video posts.
  - Source: https://blog.hootsuite.com/instagram-reels/ citing Instagram Creators blog (checked Sep 13 2026)
- Recommended resolution: 1080×1920 (9:16). Minimum 720p.
  - Source: https://blog.hootsuite.com/instagram-reel-size-length/ (checked Sep 13 2026)
- Aspect ratio: 9:16 full-screen; also accepted between 1.91:1 and 9:16. Cropped to 4:5 in main feed.
  - Source: https://blog.hootsuite.com/instagram-reel-size-length/ (checked Sep 13 2026)
- Frame rate: minimum 30 fps (Hootsuite); 23–60 fps (Sprout Social).
  - Source: https://sproutsocial.com/insights/social-media-video-specs-guide/ (checked May 13 2026)
- File size: 4 GB max (native Instagram).
  - Source: https://sproutsocial.com/insights/social-media-video-specs-guide/ (checked May 13 2026)
- Codecs: MP4, MOV. Specific video codec (H.264 vs H.265) not publicly specified by Instagram. **(unverified)**
  - Source: no authoritative source found
- Content over 1080 px wide is downscaled to 1080 px.
  - Source: https://blog.hootsuite.com/instagram-reel-size-length/ citing Instagram Help (checked Sep 13 2026)

### Text limits

- Caption: 2,200 characters (including spaces and emojis).
  - Source: https://blog.hootsuite.com/instagram-reel-size-length/ (checked Sep 13 2026)
- Hashtags: **at most 5 per post or Reel, caption and comments combined**, enforced since December 2025 (earlier tests capped some accounts at 3). Extra tags block publishing or get stripped. **[corrected from 30]**
  - Sources: https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/ and https://later.com/blog/ultimate-guide-to-using-instagram-hashtags/ (checked 2026-09-13)
  - Campaign impact: #Ad plus 3 extra hashtags = 4, which fits; a brief allowing more than 4 extras cannot be followed on Reels.
- Recommended hashtag count: 3–5 (now the hard ceiling).
  - Source: https://blog.hootsuite.com/instagram-hashtags/ (checked Sep 13 2026)
- Users can no longer follow hashtags (removed Dec 13, 2024). Hashtags still serve as algorithm signals.
  - Source: https://blog.hootsuite.com/instagram-hashtags/ (checked Sep 13 2026)

### Screen safe zones (1080×1920)

**Partially sourced from Meta:**
- Meta (via Sprout Social, Joana Rocha — Senior Technical Partner Manager): "Keep the bottom 35% of your 9:16 creative free of text, logos and other key elements."
  - Source: https://sproutsocial.com/insights/instagram-reels/ (published Nov 4 2024)
- Sprout Social (Reels ads): "Leave 14% (250 px) at the top and 20% (340 px) at the bottom free of text and logos."
  - Source: https://sproutsocial.com/insights/social-media-video-specs-guide/ (published May 13 2026)

**Conservative estimates:**
- Top bar: [0, 0, 1080, 270] (~14% of height, per Sprout Social ads guidance)
- Bottom caption area: [0, 1580, 1080, 1920] (~18% of height, ~340 px per Sprout Social)
- Right action column: [900, 270, 1080, 1580] (~right 17%)

**Typical estimates:**
- Top bar: [0, 0, 1080, 200]
- Bottom caption area: [0, 1350, 1080, 1920] (~30% — aligns with Meta's "bottom 35%" guidance)
- Right action column: [930, 200, 1080, 1350] (~right 14%)

- **Important**: In the main feed, Reels are cropped to 4:5 (1080×1350), losing top/bottom ~285 px each. Keep essential content within the centre 4:5 crop.

### Paid-promotion disclosure

- **Toggle name**: "Add paid partnership label" — search and select the brand partner.
  - Source: Meta Business Help Center (page not directly fetchable; documented by Hootsuite/Sprout Social)
- Adds "Paid partnership with @[brand]" at the top of the Reel, visible to all viewers.
- The tagged brand gets access to Insights/metrics; brands can approve or reject the tag.
- Platform label satisfies disclosure requirements. #Ad/#Sponsored hashtags are complementary but not required when the label is active.
  - Source: established policy knowledge cross-referenced by Hootsuite/Sprout
- **Creator reports (unverified)**: Some creators report different distribution for content with paid partnership labels. Meta has not confirmed.

### Why clips get flagged/suppressed

**Platform official:**
- Reels "visibly recycled from other apps" (for example carrying another app's logo or watermark, such as TikTok's) are left out of recommendations. **[corrected]** Instagram has clarified that your own or a brand's logo on a Reel is fine - so a sponsor's required game logo is not the problem this rule targets.
  - Sources: https://www.socialmediatoday.com/news/instagram-clarifies-including-your-own-logo-on-a-reel-is-ok/730852/ and https://wersm.com/instagram-will-deprioritize-content-recycled-from-other-apps/ (checked 2026-09-13)
- Algorithm favours "original, made-for-Instagram content" and "down-ranks anything that looks recycled from other platforms."
  - Source: https://blog.hootsuite.com/instagram-algorithm/ (published Jul 15 2026)
- Account Status feature lets creators check if content is eligible for recommendations.
  - Source: https://blog.hootsuite.com/instagram-algorithm/ citing Mosseri (checked Sep 13 2026)
- Algorithm favours quality visuals.
  - Source: https://blog.hootsuite.com/instagram-reel-size-length/ (checked Sep 13 2026)

**Creator reports (unverified):**
- Reels with TikTok watermarks reportedly get 50–80% less reach.
- Reposting the same video cross-platform without removing watermarks triggers the unoriginal filter.
- Some creators flagged for "unoriginal content" when reposting their OWN content from other platforms.
- Instagram's "Best Practices" feature in creator studio provides feedback when content is flagged.
- Creators who exclusively post original content report significantly better reach.

### 2025–2026 changes

- **Jan 2025**: Reels extended to 3 minutes (from 90 s) for in-app recording.
  - Source: https://blog.hootsuite.com/instagram-reels/ (checked Sep 13 2026)
- **Dec 2025**: "Your Algorithm" user controls — users can review, add, or down-rank Reels topics.
  - Source: https://blog.hootsuite.com/instagram-algorithm/ (checked Sep 13 2026)
- **Late 2025**: AI-powered translations for Reels (Hindi, Portuguese, English, Spanish initially).
- **2025–2026**: Shares ("sends") elevated as the top ranking signal for Feed and Reels.
  - Source: https://blog.hootsuite.com/instagram-algorithm/ citing Mosseri (checked Sep 13 2026)
- **Late 2024–2025**: Trial Reels feature — Reels shown only to non-followers first; promoted to followers if they perform well.
  - Source: https://blog.hootsuite.com/instagram-algorithm/ citing Instagram Help (checked Sep 13 2026)
- **Dec 13, 2024**: Users can no longer follow hashtags.
  - Source: https://blog.hootsuite.com/instagram-hashtags/ (checked Sep 13 2026)
- Expert recommendation: keep Reels under 90 s for best algorithmic performance despite 3-min max.
  - Source: https://blog.hootsuite.com/instagram-algorithm/ (checked Sep 13 2026)

---

## Comparison table

| | TikTok | YouTube Shorts | Instagram Reels |
|---|---|---|---|
| **Max short-form duration** | No cutoff; 10 min in-app, 60 min upload | 3 min (since Oct 2024) | 3 min in-app, 15 min upload |
| **Resolution** | 1080×1920 (min 540×960) | 1080p max | 1080×1920 (min 720p) |
| **Aspect ratio** | 9:16 recommended | 9:16 or 1:1 required | 9:16; cropped to 4:5 in feed |
| **Frame rate** | 30 fps rec.; 60 accepted | 24–60+ fps | 30 fps min; up to 60 |
| **Container/codec** | MP4, MOV; H.264 | MP4; H.264 High Profile | MP4, MOV; codec unverified |
| **Audio codec** | AAC (unverified) | AAC-LC, Opus, Eclipsa | Not published |
| **Max file size** | iOS 287.6 MB / Android 72 MB / Web 1 GB | 256 GB (general) | 4 GB |
| **Caption length** | 4,000 chars | Title 100 + desc 5,000 | 2,200 chars |
| **Hashtag cap** | None (caption limit) | 60 (all ignored if exceeded) | **5** (since Dec 2025) |
| **Recommended hashtags** | 2–6 | 3 displayed above title | 3–5 |
| **Platform disclosure** | "Branded content" toggle → "Paid partnership" label | "Paid promotion" checkbox → "Includes paid promotion" overlay | "Add paid partnership label" → "Paid partnership with @[brand]" |
| **Disclosure mandatory?** | Yes | Yes | Yes |
| **#Ad needed too?** | TikTok says toggle is required; FTC says add #Ad regardless | YouTube says use both | Platform label sufficient; FTC says add #Ad regardless |
| **Foreign watermarks** | Suppressed in FYP | Flagged as "reused content"; suppressed | Down-ranked in recommendations |
| **Short-form rewards** | Creator Rewards (1+ min, original) | Shorts ad revenue sharing (Engaged views) | **(unverified — no public Reels bonus program as of Sep 2026)** |
| **Safe zone: top (conservative)** | [0, 0, 1080, 180] | [0, 0, 1080, 200] | [0, 0, 1080, 270] |
| **Safe zone: bottom (conservative)** | [0, 1570, 900, 1920] | [0, 1400, 1080, 1920] | [0, 1580, 1080, 1920] |
| **Safe zone: right (conservative)** | [920, 600, 1080, 1570] | [880, 500, 1080, 1400] | [900, 270, 1080, 1580] |

---

## Check before posting

- [ ] 9:16 full-frame, 1080×1920, no letterboxing or pillarboxing
- [ ] No watermarks from other platforms (TikTok logo, CapCut logo, etc.)
- [ ] Platform disclosure toggle/checkbox enabled
- [ ] #Ad or #Sponsored hashtag present, alone on its own line, first among hashtags (per campaign brief)
- [ ] Campaign-required caption phrase copied exactly (no paraphrasing)
- [ ] Brand @tag present
- [ ] Hashtag count within platform limits (TikTok: caption fits in 4,000 chars; YouTube: 60 or fewer; Instagram: 5 or fewer)
- [ ] Required on-screen text placed outside safe zones (top ~200 px and bottom ~350 px)
- [ ] Game logo watermark visible but not covering critical UI
- [ ] Original audio only (game SFX); no copyrighted music outside platform libraries
- [ ] Clip length meets campaign minimum (≥10 s) and platform maximum
- [ ] Likes visible (not hidden by account settings)
- [ ] English only (per campaign brief)
- [ ] Posts stay up for at least 30 days (per campaign brief)
- [ ] Resolution sharp — source footage at 1080p+ before centre-crop

---

## Open questions

1. TikTok's exact AAC audio codec spec — not published on any public spec page. We assume AAC-LC based on container norms.
2. TikTok's recommended/max frame rate — not officially published. 30 fps is industry consensus; 60 fps works in practice.
3. TikTok's Creator Rewards Program exact eligibility thresholds (follower count, view count) — terms page returned empty via fetch.
4. Instagram's specific video codec requirement (H.264 vs H.265) — no authoritative source names it.
5. Instagram's current Reels bonus/monetisation program for creators — no public program found as of Sep 2026. The Reels Play bonus was reported ended in some markets.
6. Exact safe-zone pixel values across all three platforms — none are officially published. All values are estimates from creator tooling communities. Device variation is significant.
7. TikTok safe zones after the centre crop in our output tool (we produce 1080×1920 natively, not letterboxed — safe zones should be tested on-device).
8. Whether YouTube's "Includes paid promotion" overlay affects Shorts recommendation/distribution — no official statement found.
9. Whether Instagram's "Paid partnership" label affects Reels distribution — no official confirmation from Meta.
10. Whop Content Rewards / Clipping Culture specific campaign briefs — we have general norms but not a specific active campaign's rules. The brief rules in this document (exact caption phrase, brand @tag, #Ad first, ≤3 extra hashtags, game logo watermark, original audio, ≥10 s, 30-day retention, likes visible, English only) come from the user's campaign experience.
