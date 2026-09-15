# clips-inbox

A real drop-off point for footage, using git to move files between your machine and a Claude Code
session — not just an internal staging folder.

## How to actually use it

1. Clone this repo (or pull, if you already have it) and check out this branch:
   ```
   git clone https://github.com/insanity103/clip-skills.git
   cd clip-skills
   git checkout claude/serene-curie-u72xef   # or whatever branch the session tells you it's on
   ```
2. Copy a video file into `clips-inbox/`.
3. Commit and push:
   ```
   git add clips-inbox/your-file.mp4
   git commit -m "Add clip for review"
   git push
   ```
4. Tell the session to pull — I'll fetch the branch and the file lands in my sandbox.

## Caveats

- **GitHub blocks files over 100MB outright and warns above 50MB.** This works for the same kind of
  short, compressed trims that worked as chat uploads earlier in this project — not multi-GB raw
  stringouts. For long source footage, the two-stage scout-then-trim workflow documented in
  `RESUME.md` still applies.
- **Committed video files stay in git history permanently** (or until someone rewrites history),
  which bloats the repo over time. Fine for a scratch/review workflow; worth cleaning up
  (`git rm` + a follow-up commit, or a history rewrite if it gets out of hand) once a clip's done
  with.
- I still can't fetch a URL or watch a live stream — a file has to actually be pushed to this
  folder (or uploaded in chat) before I can look at it.
