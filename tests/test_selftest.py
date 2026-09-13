"""Black-box tests for selftest.py - the check a new machine (e.g. Linux) runs after installing the skills.

Run: ~/.venvs/clipkit/bin/python -m unittest discover -s ~/Downloads/clip-skills/tests -p 'test_selftest.py' -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.environ.get("SELFTEST_SCRIPT") or os.path.expanduser(
    "~/Downloads/clip-skills/scripts-staging/clipping-campaign-producer/scripts/selftest.py")


class Selftest(unittest.TestCase):
    def test_passes_end_to_end_on_a_working_machine(self):
        proc = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, timeout=900)
        self.assertEqual(proc.returncode, 0, proc.stdout[-2500:] + proc.stderr[-800:])
        self.assertIn("all checks passed", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_missing_ffmpeg_fails_with_install_commands_for_linux_and_macos(self):
        empty = tempfile.mkdtemp()
        proc = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, timeout=120,
                              env={**os.environ, "PATH": empty})
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("FAIL  ffmpeg", proc.stdout)
        self.assertIn("sudo apt install ffmpeg", proc.stdout)
        self.assertIn("brew install ffmpeg", proc.stdout)


if __name__ == "__main__":
    unittest.main()
