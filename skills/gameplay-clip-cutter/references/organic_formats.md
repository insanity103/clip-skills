# Organic formats: when this isn't a highlight-montage job

Every rule elsewhere in this skill — dead-air FAIL at a 3s quiet run or 35% quiet overall, stitch
short beats, open on action and end on the payoff — is calibrated for **one job**: cutting a dense
highlight montage from sponsor stringout footage for a paid clipping brief. Most organic (non-
sponsored) creator gameplay content on TikTok/Shorts/Reels is not that job, and forcing it through
`find_beats.py --validate` will reject clips that are working exactly as intended.

Drafted from a direct frame-by-frame and audio review of eight real posted clips (seven creators, three
games — Warzone, Black Ops 7, and Apex Legends), not a general survey. Treat the archetypes below as
confirmed patterns to recognize, not an exhaustive list.

## Archetype 1: continuous POV take

One uncut (or nearly uncut) take of real-time play, often ending on the game's own cinematic replay
feature (Warzone/MW's "BEST PLAY", similar features in other titles) as a natural capstone rather than
a custom-edited payoff. One observed clip had exactly two hard cuts in 39 seconds: intro-hook-card →
raw gameplay, and gameplay → the game's own replay.

- **Don't run dead-air validation on this.** The audio floor in the reviewed clip never dropped below
  about -13dB RMS anywhere — dense multiplayer ambience (footsteps, nearby fights, voice lines) fills
  what would be "quiet" in a solo/tactical stringout. `find_beats.py` would find nothing resembling a
  3s dead run, which is correct here, not a sign the tool is broken.
- **The hook is short, not the whole clip.** A single caption line for the first ~3-4s, then nothing —
  unlike a sponsor overlay, which is required for the clip's full duration (`clip-overlay-builder`).
- **A clip-long stylized filter can replace montage editing as the "produced" feel** — see
  `clip-stylizer` for one specific technique (echo/ghost + saturation/posterize) observed doing this.

## Archetype 2: absurdist/meme moment montage

Fast cuts (near-1-per-second) between *unrelated* funny or exaggerated moments — bunny-hopping,
taunts, weird ragdoll physics, whatever reads as "how it feels to play X" — not a chain of kills from
one continuous session. Two independently reviewed clips used this format, both Black Ops 7, both with
a persistent meme-style caption ("Genuinely how playing bo7 multiplayer feels", "BO7 multiplayer be fun
sometimes") held for roughly the first 8-10 seconds, well past the "first 2s" hook window this skill's
`genre_playbook.md` assumes for kill-highlight content.

- **Beats don't need to come from one source or one session.** `gameplay-clip-cutter`'s "each beat
  never straddles a clip boundary unless the jump is deliberate" rule is backwards here — the jump
  between unrelated moments *is* the format.
- **No loudness signal to chase.** The cuts land on whatever moment is funniest, not on gunfire peaks.

## Archetype 3: picture-in-picture facecam

One reviewed clip (same absurdist-montage style as Archetype 2) reserved the top roughly one-third of
the 9:16 frame for a persistent facecam box, with gameplay filling only the remaining lower portion —
not full-frame gameplay with a corner logo like every layout `clip-overlay-builder/references/layout.md`
currently documents. The hook caption sat directly below the facecam box, not in the top third of the
full frame.

- **This is a layout gap, not a rule violation.** Nothing here is wrong about it; `clip-overlay-builder`
  simply has no facecam-reservation layout to draw from yet if a brief or a creator wants one.

## Archetype 4: split-screen with a paired reaction/meme clip

A different layout from the Archetype 3 facecam box: gameplay fills the top ~60% of the 9:16 frame and
the bottom ~35-40% is a second, *separate, pre-existing* video — a reaction/meme clip, not the
creator's own webcam — stacked underneath as commentary, with a persistent hook caption over the
gameplay half ("POV of dealing with these bo7 shotgun users"). The bottom clip supplies the reaction
instead of a facecam, which is a much lower-effort way to get the same "someone's reacting to this"
feel.

- Same consequence as Archetype 3 for `clip-overlay-builder`: no layout here currently accounts for
  gameplay occupying less than the full frame height.
- Whatever plays in the reaction half needs its own originality check if a brief is ever involved
  (see `clipping-campaign-producer/references/originality.md`) — it's someone else's footage.

## Archetype 5: layered captions and screen annotations

One reviewed clip ("Day 2 of smoking out NukeTown...") combined several caption/annotation techniques
in one edit, worth distinguishing from the single-hook-line pattern in Archetypes 1-2:

- **A persistent title caption for the entire clip** (not a 2-10s hook) — functions like an episode
  label for a recurring content series ("Day 2 of...").
- **Separate situational reaction captions** appearing only at specific mid-clip moments tied to what's
  happening on screen (bold red text + emoji: "The Enemy Team Was Getting So Mad", "Mission
  Accomplished I can't See Anything"), layered on top of the persistent title rather than replacing it.
- **A drawn call-out annotation** (a red circle and arrow) over a lobby/loadout screen in the first
  few seconds, directing the viewer's attention to a specific choice before gameplay starts.
- **Deliberate blur-censoring** of a HUD region (other players' names/squad list) held for the whole
  clip — a privacy practice, not a quality issue if a QA check ever flags it as an unexplained blur.

None of this is covered by `clip-overlay-builder`, which assumes one overlay spec valid for the whole
clip's duration with no per-moment timing and no annotation/censoring element types.

## A live example of the letterbox mistake

A different reviewed clip (apparently a 16:9 Twitch VOD cross-posted to TikTok without reframing) was
plain letterboxed - black bars top and bottom, not even a blurred fill - exactly the mistake
`vertical-clip-renderer` exists to prevent and that `FINDINGS.md` documents getting real sponsor clips
flagged. Cross-posted Twitch/YouTube 16:9 footage dropped into a 9:16 canvas with no crop work is a
common, real source of this mistake, not just a hypothetical - if a creator hands you 16:9 source
footage to turn into a vertical post, that's exactly when to reach for `vertical-clip-renderer` rather
than letting an editor's default "fit" behavior letterbox it.

## Archetype 6: raw multi-match session dump

Several matches concatenated back-to-back with essentially no custom editing: each match's own native
end-of-match scoreboard screen and "REPLAY"/"BEST PLAY" segments left in untouched, hard-cut straight
into the next match's gameplay. The game's own UI *is* the content - kill banners, "WEEKLY CHALLENGE
COMPLETE" popups, "LEVEL UP" toasts, the end-game K/D scoreboard held on screen for several seconds.

- **Every HUD-collision instinct in this skillset points the wrong way here.** `clip-overlay-builder`
  and `gameplay-clip-cutter` both treat game UI (medal banners, scoreboards, challenge popups) as
  something to avoid colliding with required text. In this archetype there is no required text, and
  the UI events are the payoff, not clutter.

## Archetype 7: multi-act color-graded montage

A second, independently reviewed clip (35.6s, Apex Legends) used a structure none of the archetypes
above cover: several distinct "acts," each holding its own color grade, stitched into one montage -
amber gameplay, then a desaturated/grayscale operator cosmetic showcase (third-person, posing, no
combat), then blue gameplay, then a bright/high-contrast "act" built around the game's own drop-ship
elimination transition screen breaking open into a black-silhouette skydive, then blue gameplay again.
The grade change itself signals "new scene" the way a hard cut alone wouldn't - a structural technique
on top of, not instead of, the jump cuts and echo/ghost filter documented elsewhere in this file.

- **In-engine slow motion, kept as a deliberate highlight beat.** Two moments (a mantle/fall animation,
  and the skydive) show gradual, fine-grained pose change across a full 1-2 seconds where a normal cut
  shows one frame - this is the game's own slow-mo (kill-cam/drop-ship style), captured and kept, not
  added with a speed-ramp filter in post. `gameplay-clip-cutter`'s loudness-based beat finder would not
  flag a quiet slow-mo cinematic as a "beat worth keeping" - recognizing one is a manual/visual call.
- **A native game transition screen, curated rather than dumped wholesale.** Unlike Archetype 6's raw
  multi-match session, only *one* specific transition (the elimination/drop screen) was kept, as a
  single deliberate beat inside an otherwise cut-down highlight reel - closer to "one native UI moment
  used as a scene break" than "leave every native screen in."
- **To reproduce the multi-act look with this repo's existing tools:** cut each act as its own set of
  beats, run **clip-stylizer**'s `apply_style.py` separately per act with different `--saturation`/
  `--warmth` (e.g. `--saturation 0` for a grayscale act), then stitch the differently-styled outputs as
  beats from different source files in one `vertical-clip-renderer` edit JSON - no new tool needed, this
  is a workflow recipe against what already exists.
- **Gunshot/cut-to-beat sync was real but partial**, not every hit quantized to the beat - a few hits
  landed within 20-60ms of the estimated grid (near-perfect, likely hand-placed), most landed
  100-350ms off (gameplay-driven, not beat-driven). Verify a specific clip's sync with **clip-beat-sync**
  rather than assuming "synced to the music" means every hit is grid-locked - it usually means a few are.

## A download artifact to not mistake for technique

Both reviewed clips ended with TikTok's own native end-card (a progress bar / search-this-sound UI)
baked into the last 2-5 seconds, and both carried a "TikTok @handle" watermark. Both are byproducts of
how the file was downloaded/saved, not something the creator posted or edited in. Trim the end-card off
before using a downloaded clip as reference footage, and don't read the save-watermark as evidence about
the original post's quality or repost status.

A second, unrelated download issue showed up on the Archetype 7 clip: its audio track ran out at 19.8s
while the video continued to 35.6s - the back half of the video had no sound at all. This was a
technical export/download problem, not an editing choice; if a downloaded clip's audio seems to vanish
partway through, check the actual audio stream duration before assuming a silent section was intentional.

## When to still use the sponsor-brief pipeline

If a brief exists (`clipping-campaign-producer`), none of the above overrides it — required text,
clean unaltered footage, and the dead-air/originality checks in `qa_clip.py` still apply regardless of
which organic format inspired the edit. These archetypes are for organic/no-brief content, or for
understanding why a piece of reference footage a creator sent you doesn't fit the montage pipeline.
