# Genre Playbook: Finding and Framing Gameplay Clips

> Drafted by MiMo (Xiaomi); fact-checked by Claude on 2026-09-13. Genre guidance is experience-based, not measured, except where it cites the MW4 campaign. Items marked **[corrected]** were wrong in the draft. The loudness-based beat finder was only calibrated on a tactical shooter.

Guidance for an AI clip-finding and editing tool producing 10–20 s vertical clips (1080×1920, 9:16) from gameplay footage. Each genre section covers: clip structure, audio detection, UI collision after 16:9 → 9:16 centre crop, and what makes a clip look low-effort.

The centre crop keeps the middle **~32%** of a 16:9 frame's width (608 of 1920 px) and removes ~34% from each side. **[corrected]** Where UI elements land after the crop is described as top / upper-middle / centre / lower-middle / bottom, left or right.

---

## Tactical / Military Shooter (CoD, Battlefield, Rainbow Six Siege, Counter-Strike)

### Clip structure
- **Hook (first 2 s)**: Immediate threat — enemy pushing, flashbang popping, numbers disadvantage (1v3+). The viewer must see the danger before the play.
- **Middle**: Mechanical showcase — flicks, spray transfers, grenade timing, clutch defuse.
- **Payoff**: Kill feed confirming the multi-kill, round win banner, or teammates reacting.
- **Shareability**: Perceived impossibility. "I could never do that." Kill feed filling in real-time makes scale legible.

### Audio cues
- **Works well**: Gunfire, grenades, explosions produce sharp transient spikes (roughly 5–15 dB above ambient - unmeasured heuristic). Burst-fire peaks, AWP thump, C4 detonation. Clean separation between combat and walking/holding angles.
- **Fails**: Pre-aim holding (visually tense, acoustically silent). Suppressed weapons (lower peak). Tactical rounds won via rotation/timing, not gunfire. Footstep-heavy moments. Recommendation: supplement loudness with kill-feed OCR.

### UI collision after crop
- **Survives**: Centre-top compass/directional indicator (CoD, BF), hit markers and crosshair (centre), score/event popups ("Double Kill" — upper-centre).
- **Cropped**: Minimap (top-left in CoD/BF), ammo counter (bottom-right), killfeed (top-right in all titles — partially or fully cropped).
- **R6 Siege**: Operator gadget bar (bottom-centre) survives but small.
- **Collision risk**: Overlay text at centre conflicts with hit markers and kill-streak banners. Top-bar text conflicts with compass strip.

### Low-effort tells
- Single kill with no context. Clip starts mid-sprint with no audio cue. Kill feed in cropped region so viewer can't see multi-kill. Slow-mo on unimpressive sprays. Death-cam/respawn timer left in. Airhorn/meme SFX on already-exciting clips. Pub-stomping footage that looks like bots.

---

## Battle Royale (Fortnite, Apex Legends, PUBG, Warzone)

### Clip structure
- **Hook (first 2 s)**: Scale of threat — third-party arriving, last alive on squad, pushing a full team solo. "Clutch or die" framing: the viewer must feel it could go either way.
- **Middle**: Movement tech (Apex wall-bounces, tap-strafes), build/edit speed (Fortnite), positioning outplay or long-range snipe (Warzone/PUBG).
- **Payoff**: Victory Royale / Champion screen, squad wipe confirmation, dramatic self-rez/respawn. Kill count or high-damage badge adds social proof.

### Audio cues
- **Works well**: Excellent loudness separation — long quiet looting/rotation phases punctuated by loud engagements (a large loudness gap in Apex/Warzone - unmeasured heuristic). Shield crack (Apex — distinctive glass-break transient), storm damage ticks (Fortnite), grenade/ability ultimates.
- **Fails**: Third-party cleanup (few quiet shots on downed players — key clip, low audio). Healing/battery mid-fight (acoustically calm, narratively important). Fortnite building is quiet but edit plays ARE the clip. Vehicle audio in Warzone/PUBG is sustained loudness, masking nearby fights. Best practice: use loudness for fight windows, visual heuristics for best 15 s within.

### UI collision after crop
- **Apex**: Minimap top-left (cropped), health/shield bottom-centre (survives), abilities/inventory bottom-right (cropped), killfeed top-right (cropped). Damage numbers centre (survive).
- **Fortnite**: Health/shield bottom-left (partially cropped), materials bottom-right (cropped), building piece indicator bottom-centre (survives).
- **Warzone**: Nearly identical to CoD — minimap top-left (cropped), ammo bottom-right (cropped), compass top-centre (survives).
- **Collision risk**: Bottom text overlays clash with shield/health bars (Apex, Fortnite). Top text collides with ring/circle timer. Centre text conflicts with damage numbers.

### Low-effort tells
- Looting footage (opening a chest, finding a legendary). Single kill without "last alive" context. Full lobby drop before action. Warzone loadout drop clips. Running across the map. Default-skin kills against new players. Not showing team/alive count. Slow-mo on body-shot snipes. Low-bitrate footage from stream replays (BR sightlines crush at low bitrate).

---

## Hero Shooter (Overwatch 2, Valorant, Marvel Rivals)

### Clip structure
- **Hook (first 2 s)**: Ult activation (voice line + visual tells the viewer exactly what's coming) or "how is this player alive" moment (clutch escape, 1vX).
- **Middle**: Ability combos, flicks between targets, cooldown timing.
- **Payoff**: Teamfight win — objective flipping, "Team Kill" (OW2), round win (Valorant), MVP replay. Show hero nameplate/identity so viewers can contextualise.

### Audio cues
- **Works well**: Ult voice lines are loud, distinctive, and almost always precede the best 15 s — use them as clip-start markers. Ability usage produces moderate spikes (flashbangs, dashes, healing bursts). Announcer calls ("Team Kill", "Ace").
- **Fails**: Valorant lurk plays (3k from behind — almost no audio until kills). OW2 support plays (Ana sleep dart, Bap lamp — game-winning, acoustically subtle). Setup utility (Sova arrows, Cypher cameras — low audio, high clip value). Buy phase / walking in Valorant is very quiet.

### UI collision after crop
- **OW2**: Killfeed top-right (cropped), objective progress top-centre (survives), health bottom-left (partially cropped), abilities bottom-right (cropped), ultimate charge bottom-left (partially cropped), score/time top-centre (survives).
- **Valorant**: Minimap top-left (cropped), abilities/credits bottom-right (cropped), health bottom-left (partially cropped), killfeed top-right (cropped), spike timer top-centre (survives), round score top-centre (survives).
- **Marvel Rivals**: Similar to OW2 layout.
- **Collision risk**: Bottom-right text collides with ability UI in all three. Top-centre text collides with objective/round UI. Safest zones: upper-left quadrant, lower-centre below crosshair.

### Low-effort tells
- Basic single-ability kill (Soldier helix, Reyna Leer). Not identifying the hero/agent. Unranked/QP footage with still opponents. Mercy-boosted kill without Mercy POV. OW2 "press Q" Dragonblade with no dash resets. Valorant buy-phase footage. Missing killfeed so viewer can't tell if it was a team wipe. Walking from spawn left in. Slow-mo on a straightforward ult.

---

## MOBA (League of Legends, Dota 2, Mobile Legends: Bang Bang)

### Clip structure
- **Hook (first 2 s)**: Communicate what's at stake — gank arriving, teamfight starting, 1v2/1v3 that shouldn't be winnable. MOBA viewers need hero matchup context to appreciate the play; TikTok viewers don't. Best clips are visually self-explanatory: big particle effects, multiple health bars disappearing, a chase across the map.
- **Middle**: Outplay — animation cancels, flash predictions, kiting, ult combos.
- **Payoff**: Objective falling (Baron, tower, inhib), ace announcement, "Legendary / Penta Kill" callout.

### Audio cues
- **Works poorly**: This is the **worst genre for loudness-only detection**. Near-constant ambient combat (minion waves, ability farming, tower shots) raises the noise floor. Reliable markers: champion kill announcements ("ENEMY SLAIN" voiceover), multi-kill callouts ("DOUBLE KILL"), objective announcements, teamfight peaks when multiple ultimates fire simultaneously.
- **Fails**: Solo lane outplays (same acoustic profile as regular ability trading). Split-push plays (acoustically silent). Clutch Flash/Zhonya's (quiet "pop"). Jungle steals (brief spike but setup is silent). Dota item activations (subtle audio). Recommendation: loudness is nearly useless as primary signal. Must combine with kill-feed OCR, gold-swing detection, or objective-timer proximity.

### UI collision after crop
- **Densest HUD of any genre.** LoL: minimap bottom-right (cropped), ability bar bottom-centre (survives), item inventory bottom-right (cropped), champion portraits top-left (partially cropped), KDA bottom-left (partially cropped), announcer text top-centre (survives). Dota 2: minimap bottom-right (cropped), abilities bottom-centre (survive), buyback/gold bottom-right (cropped). MLBB: minimap top-left (cropped), abilities bottom-centre (survive).
- **Collision risk**: Top text conflicts with in-game announcer banners. Bottom text conflicts with ability bars. Safest overlay: upper-left corner (empty sky/map) or dead centre between crosshair and ability bar.

### Low-effort tells
- Laning-phase kill with no context. Not showing score/gold differential. Starting mid-teamfight without the engage. Highlight from a 15-kill-lead stomp. "Press R" combos with no visible skill. Shop/inventory UI left visible. 20 seconds of farming minions. No hero nameplate/portrait. MLBB AI/low-rank matches. Player dies immediately after the highlight and it's left in.

---

## Sports (FIFA/FC, NBA 2K, Madden, Rocket League)

### Clip structure
- **Hook (first 2 s)**: The moment of skill — skill-move chain in FIFA, dribble combo in 2K, aerial in Rocket League — or situational context (down by 1, 10 seconds left). Sports rules are universally understood, so no gaming literacy needed.
- **Middle**: Build-up to execution.
- **Payoff**: Goal/point replay, celebration animation, scoreboard confirming the clutch.

### Audio cues
- **Mixed reliability.** FIFA/FC: crowd noise swells during attacks, spikes on goals. Net-swish is reliable. NBA 2K: crowd/commentary spikes on dunks, blocks, steals. Madden: crowd spikes on TDs, picks, sacks. Rocket League: EXPLOSION on goals is the clearest action marker in any sports game.
- **Fails**: FIFA skill-move chains in midfield (crowd doesn't react until the shot). 2K defensive plays (acoustically unremarkable). Madden pre-snap reads (silent). Rocket League ground plays (quieter than aerials). Sports clips benefit most from event detection (goal scored, touchdown) rather than pure loudness.

### UI collision after crop
- **FIFA/FC**: Score overlay top-centre (survives — most persistent UI in any sports game), player name top-centre (survives), radar/minimap bottom-left (partially cropped). Stamina bottom-right (cropped).
- **NBA 2K**: Score/time top-centre (survives), shot meter bottom-centre (survives), player indicator above player (centre, survives).
- **Madden**: Play clock/score top-centre (survives), play art overlays centre-field.
- **Rocket League**: Boost meter bottom-centre (survives), score/time top-centre (survives).
- **Collision risk**: FIFA score overlay collides with any top-of-frame text. 2K shot meter at bottom-centre conflicts with lower overlays. Rocket League boost meter at bottom-centre is constant. Safest zones: upper-left quadrant (crowd/sky), small gap below score bar.

### Low-effort tells
- Tap-in goal (FIFA), wide-open layup (2K), basic ground shot (Rocket League). Full replay when action was 3 seconds. FIFA pace-abuse through-balls (generic, widely hated). 2K green-release with no dribble moves. CPU-generated Madden play where user did nothing. Rocket League from low ranks where opponents don't challenge. Not showing the scoreboard. Starting too early (30 s of midfield build-up). Penalty shootout clips (low skill expression). Too-zoomed-out camera angle.

---

## Racing (Forza Horizon, Gran Turismo, Mario Kart, Need for Speed)

### Clip structure
- **Hook (first 2 s)**: Car already at speed, tight pack, or vehicle about to go airborne. Bumper-cam following a rival. No countdowns, no empty straights.
- **Middle**: Dramatic overtake, near-disaster, physics-defying drift.
- **Payoff**: Finish line by a nose, catastrophic crash, needle-threading drift, last-second item hit (Mario Kart). Must resolve the tension.

### Audio cues
- **Works well**: Crash moments (sharp transient spike), nitrous/boost activation (an audible engine-note jump - unmeasured heuristic), finish-line crowd roar. Racing has clean action/audio correlation for crashes and boost.
- **Fails**: Drafting and slipstream passes are nearly silent — huge gameplay moments with no audio delta. Clean overtakes on a straight have no cue. Wind noise at high speed creates a sustained loud floor that flattens dynamic range, making discrete peaks hard to isolate. Mario Kart item hits are quiet despite being decisive. Pit stops in sim-racers are quiet but important.

### UI collision after crop
- **Forza/GT**: Position/minimap top-left (cropped), speedometer bottom-right or bottom-left (partially cropped, at very bottom of 9:16), lap counter/timer top-centre (survives).
- **Mario Kart**: Item box top-left (cropped), minimap top-right (cropped/partial), lap counter top-centre (survives), position indicator top-left (partially clipped).
- **NFS**: Speed/nitro bar bottom (survives, collides with bottom overlays), minimap bottom-left (partially cropped).
- Centre of frame is mostly clean (road ahead). Top-centre and bottom-centre occupied by small HUD elements.

### Low-effort tells
- Full straight with no overtakes. Race start countdown. Single routine pass with no drama. Clip ends mid-corner with no resolution. HUD-heavy telemetry overlays (looks like a screen recording). Full slow-motion replay instead of real-time with brief slow-mo at peak.

---

## Fighting (Street Fighter, Tekken, Mortal Kombat, Super Smash Bros)

### Clip structure
- **Hook (first 2 s)**: Health bar disparity — one fighter almost dead (pixel health). Or open on the start of a massive combo. Low-health character waking up from knockdown is instant tension.
- **Middle**: Combo execution, reads, reactions.
- **Payoff**: KO animation, perfect parry into punish (SF6), Rage Art comeback (Tekken 8), Fatal Blow at pixel health (MK1), off-screen spike (Smash). MUST end on the KO screen or decisive hit.

### Audio cues
- **Works well**: Combo sequences create rapid-fire loud transients — easy to detect. Super art activations preceded by dramatic spike. Announcer calls ("K.O.!", "PERFECT!"). Fatal Blows/Rage Arts have cinematically loud activation. Tekken 8 Heat activation has a crystalline shatter.
- **Fails**: Neutral/footsies gameplay — strategic poking and spacing — is **quiet**. Huge skill expression in near-silence. Whiff punishes (single quiet hits). Throw techs (soft sounds). Hard reads have zero audio signature. Projectile wars create sustained loud floor (repetitive, masks peaks).

### UI collision after crop
- Health bars survive fully at top of screen in virtually every fighting game.
- **SF6**: Health bars top-left and top-right (survive), Drive Gauge beneath (survives), Super meter at bottom (survives), timer top-centre (survives).
- **Tekken 8**: Health bars top, Heat/Rage at sides, timer top-centre — all survive clean.
- **MK1**: Health bars top, Fatal Blow indicator beneath — very clean.
- **Smash**: Damage percentages bottom-left and bottom-right (very bottom edge, may be obscured by bottom-bar text). Stock icons vary by layout.
- Centre vertical strip is almost entirely the arena — very clean for overlays. Caution: Smash characters fill the frame visually.

### Low-effort tells
- Single round with no health context ("two people fight, one wins"). Character intros or stage transitions with no gameplay. Raw super move with no setup (supers hitting is expected). Training mode combo on standing dummy (players can tell). No slow-mo on the decisive hit. Laggy online match with rollback stuttering.

---

## Horror / Story-Driven (Resident Evil, The Last of Us, Silent Hill, Until Dawn, Alan Wake)

### Clip structure
- **Hook (first 2 s)**: Something wrong in the environment — a door that shouldn't be open, a shadow, a character staring at something off-screen. The hook is about *wrongness*, not action. Or a character's face showing fear.
- **Middle**: Escalating dread.
- **Payoff**: Jumpscare, brutal death, plot twist reveal, genuine player reaction, emotional gut-punch. Must resolve the tension — ending before the scare is anti-climactic.

### Audio cues
- **Works for combat/jumpscares**: Jumpscare stingers (sharp high-freq spikes — designed to be loud). Gunshots in RE (extremely loud relative to ambient). Boss reveals. Chase sequences (Mr. X footsteps — rhythmic loud pattern). Boss music swells (Alan Wake).
- **Fails badly for everything else**: This is the **worst genre for loudness-only detection**. The most important moments are often **quiet** — a corridor with distant scraping, a whisper, the absence of music. Tension-building silence IS the content. Environmental storytelling (finding a body, reading a note) is audio-quiet but clip-worthy. TLOU's most powerful moments are quiet conversations. Until Dawn's decision moments happen in relative silence.

### UI collision after crop
- Horror games have **minimal HUD** — the cleanest genre for vertical cropping.
- **RE Village/RE4 Remake**: Ammo/health bottom-right (partially or fully cropped at bottom edge). Typewriter/save icon top-right (cropped).
- **TLOU**: Extremely minimal. Listening mode indicator is subtle. Health appears only when damaged, bottom-left (survives, small).
- **Silent Hill 2 Remake**: Radio static, health — all bottom-area, minimal.
- **Until Dawn/Dark Pictures**: Relationship/butterfly icons top-right (partially/fully cropped). QTE prompts centre-screen (survive).
- **Alan Wake 2**: Ammo/darkness gauge bottom-right (partially cropped).
- Centre of frame is almost always clean. Top-centre usually empty. **Most overlay-friendly genre.**

### Low-effort tells
- Jumpscare with no buildup (startling, not scary — the anticipation IS the clip). Long walking/exploration with nothing happening. Loading screens, inventory management, map-checking. Death to a generic enemy (skill issue, not a moment). Starting too early before atmosphere establishes (5 s of dead silence loses scrollers). Real-time puzzle-solving (visually boring). Overusing slow-motion on scares (kills the jump timing — horror works in real-time).

---

## Sandbox / Survival (Minecraft, Rust, ARK, Terraria, Valheim)

### Clip structure
- **Hook (first 2 s)**: Show the payoff FIRST or the setup with obvious stakes — massive base about to be raided (Rust), creeper walking up behind a builder (Minecraft), tame going wrong (ARK), boss spawning (Valheim). Or a build reveal — "before" 0.5 s, "after" fills the rest.
- **Middle**: The emergent event unfolding.
- **Payoff**: Base falls, creeper explodes, tame succeeds, boss drops loot, build reveal pulls back to show scope. Must have a clear ending — destruction, completion, or emergent punchline.

### Audio cues
- **Works well**: Explosions (TNT, creeper, C4 in Rust — massive transient spikes). Combat hits. Creature roars (ARK's large dinos). Boss music activation (Valheim). Death sounds (player grunts + item scatter in Minecraft). Creeper hiss-then-explosion is a perfect two-part signature.
- **Fails**: The **entire building/crafting loop** is quiet. 30 min of Minecraft building = flat audio. Rust door-camping (strategically important, audio-dead). PvP stalking until first shot. Redstone clicks. Exploration (walking, mining, gathering) — gentle, repetitive, no peaks. ARK taming sequences (long quiet waits). Many best sandbox moments are **visual** (builds, landscapes, traps) with zero audio spike.

### UI collision after crop
- Moderate HUD density, spread across edges. Bottom edge is universally crowded.
- **Minecraft**: Hotbar bottom-centre (survives, collides with bottom overlays), health/hunger above hotbar (survives), experience bar bottom-centre (survives), oxygen top-centre (survives when underwater), chat bottom-left (partially cropped).
- **Rust**: Health/hunger/thirst bottom-left (partially cropped), hotbar bottom-centre (survives), compass top-centre (survives), team indicators top (survive).
- **ARK**: Health/stamina/food/water bottom-left cluster (partially cropped but largely survive), taming progress bar over creature centre (survives), minimap bottom-left (partially cropped).
- **Terraria**: Health/mana top-left (partially clipped), hotbar top (survives), minimap top-right (cropped).
- **Valheim**: Health/stamina/eitr bottom-left (partially cropped), hotbar bottom (survives), boss health bar top-centre (survives when active).
- Top-centre and centre are usually cleanest. Bottom edge universally crowded.

### Low-effort tells
- Raw mining/gathering footage. Slow-pan base tour with no reveal structure. Empty-server Rust footage (no stakes). Redstone contraption the viewer can't understand. Raid clip starting at the explosion without showing the base before (destruction without context). Death without the events leading to it. Inventory/crafting UI left visible. Generic mob fights (killing 3 zombies in Minecraft is not a clip; surviving a surprise enderman swarm is).

---

## Cross-genre notes for the clip-finding tool

- **Loudness-based detection works best** for tactical shooters and battle royale (high dB delta combat vs idle) and **worst** for MOBAs (constant ability spam), horror (important moments are quiet), and racing (engine noise is sustained loud floor).
- The **safest universal overlay placement** after a 16:9 → 9:16 crop is the **upper-left quadrant** — typically empty sky/map/crowd in every genre. **Most dangerous** zones are top-centre (score/objective UI survives in every genre) and bottom-centre (ability bars, health bars, boost meters survive in every genre).
- The 16:9 → 9:16 crop reliably **removes** minimaps (almost always bottom-right or top-left), ammo/ability UI (bottom-right), and killfeeds (top-right) across all genres. The clip tool should not rely on these elements being present.
- Every genre has **false-positive events** that are loud or visually prominent but make bad clips: FIFA tap-in goals, OW2 basic ult-presses, Fortnite looting, CoD single kills, MOBA farming phases, horror jumpscares without buildup.
- Hero shooters and MOBAs suffer from "context deficit" — viewers need to know which character is being played. Clips without hero/agent identity (nameplate, portrait, distinctive visuals) underperform on social.
- Dead air is a universal rejection risk. From one Call of Duty campaign: a clip ending on 5 s of walking was flagged; approved clips carried quiet stretches of up to ~2.5 s and ~26% quiet time. `find_beats.py --validate` FAILs a 3 s quiet run or 35% quiet overall. **[corrected]** Unconfirmed for other genres.

---

## Open questions

1. How well does loudness-based detection work on specific titles within each genre? We have general rules but not per-title calibrated thresholds.
2. For MOBAs, what OCR/kill-feed event detection is feasible in the clip-finding pipeline? The genre guidance says loudness is "nearly useless" but we don't know the tool's actual capabilities.
3. How does the clip-finding tool handle in-game licensed music (GTA radio, FIFA soundtrack, Forza Horizon festival tracks)? These can trigger Content ID on YouTube but are part of the game audio.
4. For horror games, how do we detect "tension-building silence" as clip-worthy when the whole point is that it's quiet? Visual heuristics (character animations, environmental cues) may be needed.
5. What is the actual quiet-time percentage in a typical approved clip vs a flagged one? The campaign data says ~26% quiet time and ~2.5 s max quiet stretch, but this was from one Call of Duty campaign — do these thresholds hold for other genres?
6. After the 16:9 → 9:16 crop, how much resolution loss occurs from the centre crop + scale-up if the source is 1080p? A centre crop of a 1080p source is 608 px wide, a 1.78x upscale to 1080 × 1920 (the renderer sharpens to compensate; approved MW4 clips were made this way). **[corrected]** The sharpen pass in the output tool should help, but quality impact is unclear.
7. Genre-specific clip duration sweet spots: is 10–20 s equally appropriate across genres, or do some (MOBA, horror) need more setup time?
8. How do we handle games that span multiple genres (e.g., Fortnite = battle royale + building/sandbox, Warzone = tactical shooter + battle royale)?
