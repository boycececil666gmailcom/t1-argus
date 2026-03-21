"""
Build script — packages Argus into a single self-contained executable.

Usage
-----
    python build.py

Output
------
    dist/argus          (Linux / macOS)
    dist/argus.exe      (Windows)

Requirements
------------
    pip install pyinstaller
    (All runtime dependencies are bundled automatically — end users need
    nothing installed except the executable itself.)

Linux note
----------
    The tracker needs two system packages that cannot be bundled:
        sudo apt install xdotool xprintidle   # Ubuntu / Debian
        sudo dnf install xdotool xprintidle   # Fedora
    Include this note when distributing the Linux build.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC  = ROOT / "src"
DIST = ROOT / "dist"

# ── PyInstaller arguments ─────────────────────────────────────────────────────

cmd = [
    sys.executable, "-m", "PyInstaller",

    # Single file — everything packed into one executable.
    "--onefile",

    # Output locations.
    "--name",       "argus",
    "--distpath",   str(DIST),
    "--workpath",   str(ROOT / "build"),   # temporary build artefacts
    "--specpath",   str(ROOT),             # .spec file lands here

    # Textual bundles its own CSS theme files; tell PyInstaller to include them.
    "--collect-data", "textual",

    # Rich also ships data files (syntax-highlight themes etc.).
    "--collect-data", "rich",
]

# pywin32 modules are dynamically imported on Windows; list them explicitly
# so PyInstaller picks them up even though they aren't statically visible.
if sys.platform == "win32":
    for mod in ["win32api", "win32con", "win32gui", "win32process",
                "pywintypes", "win32timezone"]:
        cmd += ["--hidden-import", mod]

# Entry point
cmd.append(str(SRC / "main.py"))

# ── Run ───────────────────────────────────────────────────────────────────────

print("Building Argus...")
print(f"  Source : {SRC / 'main.py'}")
print(f"  Output : {DIST}/argus{'exe' if sys.platform == 'win32' else ''}\n")

result = subprocess.run(cmd)

if result.returncode == 0:
    suffix = ".exe" if sys.platform == "win32" else ""
    print(f"\nDone -> dist/argus{suffix}")
else:
    print("\nBuild failed. See output above for details.")
    sys.exit(result.returncode)
