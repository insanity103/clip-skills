# Clip skills on Linux

1. **Install the system tools** (once, about 2 minutes):
   - Debian/Ubuntu: `sudo apt install python3 python3-venv ffmpeg fonts-dejavu-core`
   - Fedora: `sudo dnf install python3 dejavu-sans-fonts`, plus ffmpeg from RPM Fusion (Fedora's `ffmpeg-free` has no libx264)
   - Arch: `sudo pacman -S python ffmpeg ttf-dejavu`
2. **Unpack and install** (about 2 minutes):
   `tar xzf clip-skills-linux.tar.gz -C ~ && bash ~/clip-skills/install.sh`
   It copies the nine skills into `~/.claude/skills`, sets up `~/.venvs/clipkit`, and ends with a self-test.
   Two of the nine (`clip-subject-mask`, `clip-subject-tracker`) need a separate, much heavier PyTorch-based
   setup you run yourself when you want them - see their own SKILL.md files; this step doesn't touch that.
   You want the last line to read `all checks passed`.
3. **Optional full test suite** (10-20 minutes): `bash ~/clip-skills/tests/run_tests.sh`
4. **Resume the work in Claude Code:** run `claude` inside `~/clip-skills` and say
   `resume clip skills - read RESUME.md`

## Differences from the Mac

- Overlay text uses a condensed bold fallback instead of DIN Condensed (Mac-only): DejaVu Sans Condensed Bold
  where it's installed, otherwise Liberation Sans Narrow Bold (ships by default on current Ubuntu Desktop,
  package `fonts-liberation-sans-narrow`, no separate apt install needed) - `fonts-dejavu-core` alone no
  longer includes a condensed face on Ubuntu 24.04+. Same layout, slightly wider letters either way. Say so
  in the Linux session if you want one free font bundled so both machines match exactly.
- Draft renders use x264 (no Apple VideoToolbox), so drafts are slower; finals are identical.
- Clipboard caption checks: `xclip -o -selection clipboard | ...` (or `wl-paste | ...` on Wayland) instead of `pbpaste`.
