# clips-inbox

Drop raw footage or clips here for review/editing in a session, instead of routing them through
chat uploads. Point me at a file in this folder (or just say "check clips-inbox") and I'll pick it
up with `gameplay-clip-cutter`/`vertical-clip-renderer` the same way as any other source.

Works for both roles this project has used so far:
- **Analysis**: long raw footage to triage for candidate moments (`analyze_video.py`, `find_beats.py`,
  `contact_sheet.py`).
- **Rendering source**: a short high-quality trim to cut a final vertical clip from.

## Notes

- Video files placed here are **not committed to git** (see `.gitignore`) — this is scratch media,
  not repo content. They stay only in this sandbox and are lost when the session ends, so treat this
  as a drop-off point per session, not persistent storage.
- No hard size limit from the repo's side, but very large files (multi-GB stringouts) may be slow to
  move into a sandbox depending on how they get here. A compressed "scout" copy for initial triage,
  then high-quality trims of just the useful windows, worked well in past sessions — see `RESUME.md`
  and this session's own transcript for that two-stage workflow.
- I still can't fetch a URL or watch a live stream — a file has to actually land in this folder (or
  be uploaded in chat) before I can look at it.
