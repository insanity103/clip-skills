#!/usr/bin/env bash
# Install the seven clip skills for Claude Code (Linux or macOS), set up their Python environment, then self-test.
#   bash ~/clip-skills/install.sh
# Existing copies of these skills are moved to ~/.claude/skills-backup/, never deleted.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
BACKUP="$HOME/.claude/skills-backup"
VENV="${CLIPKIT_VENV:-$HOME/.venvs/clipkit}"
SKILLS=(gameplay-clip-cutter vertical-clip-renderer clip-overlay-builder clip-audio-mixer clip-cover-picker clip-stylizer clipping-campaign-producer)

missing=()
for tool in python3 ffmpeg ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "Missing: ${missing[*]} - install them, then run this again:"
  echo "  Debian/Ubuntu:  sudo apt install python3 python3-venv ffmpeg fonts-dejavu-core"
  echo "  Fedora:         sudo dnf install python3 dejavu-sans-fonts   (ffmpeg with libx264: RPM Fusion)"
  echo "  Arch:           sudo pacman -S python ffmpeg ttf-dejavu"
  echo "  macOS:          brew install python ffmpeg"
  exit 1
fi

mkdir -p "$DEST"
stamp="$(date +%Y%m%d-%H%M%S)"
for s in "${SKILLS[@]}"; do
  if [ -e "$DEST/$s" ]; then
    mkdir -p "$BACKUP"
    mv "$DEST/$s" "$BACKUP/$s-$stamp"
    echo "moved your existing $s to $BACKUP/$s-$stamp"
  fi
  cp -R "$HERE/skills/$s" "$DEST/$s"
  chmod +x "$DEST/$s/scripts/"*.py
done
echo "installed ${#SKILLS[@]} skills into $DEST"

if [ ! -x "$VENV/bin/python" ]; then
  if ! python3 -m venv "$VENV"; then
    echo "Could not create $VENV. Debian/Ubuntu: sudo apt install python3-venv - then run this again."
    exit 1
  fi
fi
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade pillow
echo "python environment ready: $VENV"
echo

"$VENV/bin/python" "$DEST/clipping-campaign-producer/scripts/selftest.py"
