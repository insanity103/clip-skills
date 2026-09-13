# hud_map.py calibration (MW4 beta footage)

Hand-labelled ground truth for when screen-fixed game UI sits under each overlay element (+16 px margin),
read from full-resolution frames every 0.5 s (`gt_*.png`). World-space killstreak markers are "dont_care".

Recreate the two no-overlay drafts (about 30 s each), then score:

```bash
R=~/.claude/skills/vertical-clip-renderer/scripts/render_vertical.py
S=~/Downloads/clip-skills/sources
~/.venvs/clipkit/bin/python $R --src $S/01_TopPlays.mp4 --edl "91.5:4,125.5:2.5,133:9" --x 35 --zoom 0.10 --quality draft --out c3v3_noov.mp4
~/.venvs/clipkit/bin/python $R --src $S/04_Week2_B.mp4 --edl "148:14" --x 30 --zoom 0.09 --quality draft --out c4v2_noov.mp4
~/.venvs/clipkit/bin/python calibrate_hud_map.py
```

Result that set the defaults (270x480 analysis, 3-sample stability, cell density 0.10, persistent share 0.8):
precision 0.88, recall 0.95, F1 0.91 over element-quarter-seconds. Known false-positive class: a first-person
weapon model held still under a bottom-centre logo. Boxes resolve to ~36 px, so near-misses are flagged too.
