#!/usr/bin/env python3
"""Check this machine can run the four clip skills: tools, Python packages, fonts, then one tiny end-to-end run.

  ~/.venvs/clipkit/bin/python ~/.claude/skills/clipping-campaign-producer/scripts/selftest.py

Works on macOS and Linux and takes about a minute. One line per check, with the command that fixes anything
missing; exit status 1 if any check fails.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPTS = {
    "analyze": ("gameplay-clip-cutter", "analyze_video.py"),
    "beats": ("gameplay-clip-cutter", "find_beats.py"),
    "sheet": ("gameplay-clip-cutter", "contact_sheet.py"),
    "render": ("vertical-clip-renderer", "render_vertical.py"),
    "overlay": ("clip-overlay-builder", "build_overlay.py"),
    "logo": ("clip-overlay-builder", "prepare_logo.py"),
    "hud": ("clip-overlay-builder", "hud_map.py"),
    "qa": ("clipping-campaign-producer", "qa_clip.py"),
    "caption": ("clipping-campaign-producer", "check_caption.py"),
}
S = {k: os.path.join(SKILLS, skill, "scripts", name) for k, (skill, name) in SCRIPTS.items()}
FIX = {
    "ffmpeg": "macOS: brew install ffmpeg | Debian/Ubuntu: sudo apt install ffmpeg | "
              "Fedora: sudo dnf install ffmpeg (from RPM Fusion) | Arch: sudo pacman -S ffmpeg",
    "libx264": "this ffmpeg build has no libx264 - Fedora: replace ffmpeg-free with RPM Fusion's ffmpeg",
    "pillow": f"{sys.executable} -m pip install pillow   (no venv yet? python3 -m venv ~/.venvs/clipkit - "
              f"Debian/Ubuntu may first need: sudo apt install python3-venv)",
    "font": "Debian/Ubuntu: sudo apt install fonts-dejavu-core | Fedora: sudo dnf install dejavu-sans-fonts | "
            "Arch: sudo pacman -S ttf-dejavu",
    "skills": "copy all four skill folders into ~/.claude/skills (the Linux package's install.sh does this)",
}
results = []


def report(ok, name, detail="", fix=""):
    results.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{': ' + detail if detail else ''}", flush=True)
    if not ok and fix:
        print(f"        fix: {fix}", flush=True)
    return bool(ok)


def run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(args, 127, "", str(e))


def tail(proc):
    return (proc.stderr or proc.stdout).strip().splitlines()[-1][:160] if (proc.stderr or proc.stdout).strip() else ""


def finish():
    failed = results.count(False)
    print("all checks passed - the clip skills are ready on this machine" if not failed
          else f"{failed} check(s) failed - fix the lines marked FAIL, then run this again")
    sys.exit(1 if failed else 0)


def main():
    print(f"clip skills self-test - {sys.platform}, Python {sys.version.split()[0]}, skills in {SKILLS}")
    report(sys.version_info >= (3, 8), "python 3.8 or newer", sys.version.split()[0], "install Python 3.8+")
    missing = [os.path.relpath(p, SKILLS) for p in S.values() if not os.path.exists(p)]
    report(not missing, "all four skills installed", ", ".join(missing), FIX["skills"])
    try:
        import PIL
        report(True, "pillow", PIL.__version__)
    except ImportError:
        report(False, "pillow", f"not importable by {sys.executable}", FIX["pillow"])
    if not report(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe on PATH", fix=FIX["ffmpeg"]):
        finish()
    encoders = run(["ffmpeg", "-hide_banner", "-encoders"]).stdout
    report(" libx264 " in encoders, "ffmpeg includes the libx264 encoder", fix=FIX["libx264"])
    if missing or False in results:
        finish()

    sys.path.insert(0, os.path.dirname(S["overlay"]))
    import build_overlay
    font = next((build_overlay.font_index().get(build_overlay.norm(n)) for n in build_overlay.DEFAULT_FONTS
                 if build_overlay.font_index().get(build_overlay.norm(n))), None)
    report(font, "condensed bold font for overlays", font or "none of " + ", ".join(build_overlay.DEFAULT_FONTS), FIX["font"])

    with tempfile.TemporaryDirectory(prefix="clipkit-selftest-") as td:
        src, tl = os.path.join(td, "source.mp4"), os.path.join(td, "source.timeline.json")
        r = run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=6",
                 "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-c:v", "libx264", "-preset", "ultrafast",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", src])
        if not report(r.returncode == 0, "make 6 s of test footage", tail(r)):
            finish()

        r = run([sys.executable, S["analyze"], src, "--mode", "full", "--out", tl])
        report(r.returncode == 0 and os.path.exists(tl), "gameplay-clip-cutter: analyze_video.py", tail(r) if r.returncode else "")
        r = run([sys.executable, S["beats"], tl, "--validate", "0.5:5", "--min-total", "0"])
        report(r.returncode == 0 and "VERDICT" in r.stdout, "gameplay-clip-cutter: find_beats.py", tail(r) if r.returncode else "")
        r = run([sys.executable, S["sheet"], src, "--start", "0", "--end", "4", "--out", os.path.join(td, "sheet.png")])
        report(r.returncode == 0, "gameplay-clip-cutter: contact_sheet.py", tail(r) if r.returncode else "")

        logo_src, logo = os.path.join(td, "logo_on_black.png"), os.path.join(td, "logo.png")
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (400, 160), (0, 0, 0))
        ImageDraw.Draw(img).rectangle([40, 40, 360, 120], fill=(255, 208, 0))
        img.save(logo_src)
        r = run([sys.executable, S["logo"], logo_src, "--out", logo])
        report(r.returncode == 0 and os.path.exists(logo), "clip-overlay-builder: prepare_logo.py", tail(r) if r.returncode else "")

        spec, ov = os.path.join(td, "overlay.json"), os.path.join(td, "overlay.png")
        with open(spec, "w") as f:
            json.dump({"elements": [{"id": "title", "type": "text", "text": "SELF TEST", "size": 100, "y": 200},
                                    {"id": "logo", "type": "image", "src": logo, "width": 320, "y": 1340}]}, f)
        r = run([sys.executable, S["overlay"], spec, "--out", ov, "--check-safe", "tiktok,shorts,reels"])
        report(r.returncode == 0 and os.path.exists(ov), "clip-overlay-builder: build_overlay.py", tail(r) if r.returncode else "")

        draft, final = os.path.join(td, "draft.mp4"), os.path.join(td, "final.mp4")
        r = run([sys.executable, S["render"], "--src", src, "--edl", "0.5:2,3:2.5", "--quality", "draft", "--out", draft])
        report(r.returncode == 0 and os.path.exists(draft), "vertical-clip-renderer: draft render", tail(r) if r.returncode else "")
        r = run([sys.executable, S["hud"], draft, "--boxes", os.path.join(td, "overlay.boxes.json"),
                 "--json", os.path.join(td, "hud.json"), "--no-png"])
        report(r.returncode == 0, "clip-overlay-builder: hud_map.py", tail(r) if r.returncode else "")
        r = run([sys.executable, S["render"], "--src", src, "--edl", "0.5:2,3:2.5", "--overlay", ov,
                 "--quality", "final", "--out", final])
        report(r.returncode == 0 and os.path.exists(final), "vertical-clip-renderer: final render with overlay",
               tail(r) if r.returncode else "")
        if os.path.exists(final):
            probe = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", final]).stdout)
            v = next(s for s in probe["streams"] if s["codec_type"] == "video")
            report((v["width"], v["height"], v["codec_name"]) == (1080, 1920, "h264"), "final clip is 1080x1920 H.264",
                   f"{v['width']}x{v['height']} {v['codec_name']}")

        camp, cap = os.path.join(td, "campaign.json"), os.path.join(td, "caption.txt")
        with open(camp, "w") as f:
            json.dump({"duration": {"min": 1}, "caption": {"required_phrases": ["Play the self test today"],
                       "required_tags": ["@clipkit"], "disclosure": {"options": ["#Ad"]}, "max_extra_hashtags": 3,
                       "language": "en"}}, f)
        with open(cap, "w") as f:
            f.write("Clean round. @clipkit Play the self test today\n\n#Ad\n\n#SelfTest")
        r = run([sys.executable, S["caption"], cap, "--campaign", camp])
        report(r.returncode == 0 and "PASS" in r.stdout, "clipping-campaign-producer: check_caption.py", tail(r) if r.returncode else "")
        qa_json = os.path.join(td, "qa.json")
        r = run([sys.executable, S["qa"], final, "--campaign", camp, "--json", qa_json])
        ran = os.path.exists(qa_json) and json.load(open(qa_json)).get("clips")
        report(ran, "clipping-campaign-producer: qa_clip.py runs", "" if ran else tail(r))
    finish()


if __name__ == "__main__":
    main()
