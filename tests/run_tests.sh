#!/usr/bin/env bash
# Run the full test suite against the INSTALLED skills (~/.claude/skills). About 10-20 minutes.
#   bash ~/clip-skills/tests/run_tests.sh                       # everything
#   bash ~/clip-skills/tests/run_tests.sh -p 'test_check_caption.py'   # one file
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SK="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
PY="${CLIPKIT_VENV:-$HOME/.venvs/clipkit}/bin/python"

export RENDER_VERTICAL_SCRIPT="$SK/vertical-clip-renderer/scripts/render_vertical.py"
export BUILD_OVERLAY_SCRIPT="$SK/clip-overlay-builder/scripts/build_overlay.py"
export PREPARE_LOGO_SCRIPT="$SK/clip-overlay-builder/scripts/prepare_logo.py"
export HUD_MAP_SCRIPT="$SK/clip-overlay-builder/scripts/hud_map.py"
export CHECK_CAPTION_SCRIPT="$SK/clipping-campaign-producer/scripts/check_caption.py"
export QA_CLIP_SCRIPT="$SK/clipping-campaign-producer/scripts/qa_clip.py"
export MIX_AUDIO_SCRIPT="$SK/clip-audio-mixer/scripts/mix_audio.py"
export PICK_COVER_SCRIPT="$SK/clip-cover-picker/scripts/pick_cover.py"
export APPLY_STYLE_SCRIPT="$SK/clip-stylizer/scripts/apply_style.py"
export MASK_SUBJECT_SCRIPT="$SK/clip-subject-mask/scripts/mask_subject.py"
export TRACK_SUBJECT_SCRIPT="$SK/clip-subject-tracker/scripts/track_subject.py"
export SELFTEST_SCRIPT="$SK/clipping-campaign-producer/scripts/selftest.py"
export CLIP_CUTTER_SCRIPTS="$SK/gameplay-clip-cutter/scripts"

cd "$HERE"
exec "$PY" -m unittest discover -s . "$@"
