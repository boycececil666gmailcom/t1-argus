"""Auto-start helpers — enable, disable, and query the system login hook.

Platform behaviour
------------------
Windows  Registry key  HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
macOS    LaunchAgent plist  ~/Library/LaunchAgents/com.argus.daemon.plist
Linux    XDG autostart      ~/.config/autostart/argus.desktop

Frozen vs. script mode
-----------------------
When Argus is packaged as a single executable by PyInstaller, sys.frozen is
True and sys.executable points to the .exe / binary.  In that case we register
the executable directly.  When running as a plain Python script we register
"python  src/main.py  start" instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

# region Constants

# What the OS should run at login.
# Frozen build  → ["path/to/argus.exe", "start"]
# Script mode   → ["path/to/python.exe", "path/to/src/main.py", "start"]
if getattr(sys, "frozen", False):
    _LAUNCH_CMD: list[str] = [str(Path(sys.executable).resolve()), "start"]
else:
    _THIS   = str(Path(sys.executable).resolve())
    _SCRIPT = str((Path(__file__).resolve().parent.parent / "main.py").resolve())
    _LAUNCH_CMD = [_THIS, _SCRIPT, "start"]

_WIN_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_WIN_REG_NAME = "ArgusDaemon"

_MACOS_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.argus.daemon.plist"
_MACOS_LABEL = "com.argus.daemon"

_LINUX_DESKTOP = Path.home() / ".config" / "autostart" / "argus.desktop"

# endregion

# region Public API


def is_enabled() -> bool:
    """Return True if Argus is registered to run at login on the current platform."""
    if sys.platform == "win32":
        return _win_is_registered()
    if sys.platform == "darwin":
        return _MACOS_PLIST.exists()
    return _LINUX_DESKTOP.exists()


def enable() -> None:
    """Register Argus to launch automatically at login."""
    if sys.platform == "win32":
        _win_install()
    elif sys.platform == "darwin":
        _darwin_install()
    else:
        _linux_install()


def disable() -> None:
    """Remove Argus from the login auto-start list."""
    if sys.platform == "win32":
        _win_uninstall()
    elif sys.platform == "darwin":
        _darwin_uninstall()
    else:
        _linux_uninstall()


def toggle() -> bool:
    """Toggle auto-start and return the new enabled state (True = enabled)."""
    if is_enabled():
        disable()
        return False
    enable()
    return True


# endregion

# region Windows


def _win_is_registered() -> bool:
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_REG_KEY)
        winreg.QueryValueEx(key, _WIN_REG_NAME)
        winreg.CloseKey(key)
        return True
    except (OSError, FileNotFoundError):
        return False


def _win_install() -> None:
    import winreg
    # Each argument is quoted individually so paths with spaces are safe.
    value = " ".join(f'"{a}"' for a in _LAUNCH_CMD)
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _WIN_REG_KEY, access=winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, _WIN_REG_NAME, 0, winreg.REG_SZ, value)
    winreg.CloseKey(key)


def _win_uninstall() -> None:
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _WIN_REG_KEY, access=winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, _WIN_REG_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass


# endregion

# region macOS


def _darwin_install() -> None:
    _MACOS_PLIST.parent.mkdir(parents=True, exist_ok=True)
    # Each element of _LAUNCH_CMD becomes its own <string> entry in the plist array.
    args_xml = "\n".join(f"        <string>{a}</string>" for a in _LAUNCH_CMD)
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"\n'
        '  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        f"    <key>Label</key>            <string>{_MACOS_LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n"
        "    <array>\n"
        f"{args_xml}\n"
        "    </array>\n"
        "    <key>RunAtLoad</key>        <true/>\n"
        "    <key>KeepAlive</key>        <false/>\n"
        f"    <key>StandardOutPath</key>  <string>{Path.home()}/.argus/daemon.log</string>\n"
        f"    <key>StandardErrorPath</key><string>{Path.home()}/.argus/daemon.log</string>\n"
        "</dict>\n"
        "</plist>\n"
    )
    _MACOS_PLIST.write_text(plist)


def _darwin_uninstall() -> None:
    if _MACOS_PLIST.exists():
        _MACOS_PLIST.unlink()


# endregion

# region Linux


def _linux_install() -> None:
    _LINUX_DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Argus Daemon\n"
        "Comment=Argus activity tracker daemon\n"
        f"Exec={' '.join(_LAUNCH_CMD)}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Hidden=false\n"
        "NoDisplay=false\n"
    )
    _LINUX_DESKTOP.write_text(desktop)


def _linux_uninstall() -> None:
    if _LINUX_DESKTOP.exists():
        _LINUX_DESKTOP.unlink()


# endregion
