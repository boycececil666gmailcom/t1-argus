"""Cross-platform active window and idle time detection.

Platform support:
  Windows — pywin32 + ctypes (Win32 API, no extra tools needed)
  Linux   — xdotool + xprintidle (install via: sudo apt install xdotool xprintidle)
            Wayland note: xdotool requires XWayland; native Wayland support is limited.
"""

# region Imports

import sys
from typing import TypedDict

# endregion

# region Fields / Private — Windows

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    import psutil
    import win32gui
    import win32process

    class _LASTINPUTINFO(ctypes.Structure):
        """Win32 LASTINPUTINFO structure for querying the last input event time."""
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwTime", ctypes.wintypes.DWORD),
        ]

# endregion

# region Private Methods — Windows


def _active_window_win32() -> "WindowInfo | None":
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        window_title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            app_name = proc.name().removesuffix(".exe")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            exe_path = ""
            app_name = "unknown"
        return WindowInfo(app_name=app_name, window_title=window_title, exe_path=exe_path)
    except Exception:
        return None


def _idle_seconds_win32() -> float:
    lii = _LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    elapsed_ms = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return max(0.0, elapsed_ms / 1000.0)


# endregion

# region Private Methods — Linux (X11)
#
# Requires system packages: xdotool  xprintidle
#   Ubuntu / Debian:  sudo apt install xdotool xprintidle
#   Fedora / RHEL:    sudo dnf install xdotool xprintidle
#   Arch:             sudo pacman -S xdotool xprintidle
#
# Wayland: xdotool works under XWayland but not under a native Wayland compositor.


def _active_window_linux() -> "WindowInfo | None":
    import subprocess

    import psutil

    try:
        win_id = subprocess.check_output(
            ["xdotool", "getactivewindow"], text=True, timeout=2,
        ).strip()
        pid = int(subprocess.check_output(
            ["xdotool", "getwindowpid", win_id], text=True, timeout=2,
        ).strip())
        title = subprocess.check_output(
            ["xdotool", "getwindowname", win_id], text=True, timeout=2,
        ).strip()
    except Exception:
        return None

    try:
        proc = psutil.Process(pid)
        app_name = proc.name()
        exe_path = proc.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        app_name = "unknown"
        exe_path = ""

    return WindowInfo(app_name=app_name, window_title=title, exe_path=exe_path)


def _idle_seconds_linux() -> float:
    import subprocess

    try:
        ms = int(subprocess.check_output(["xprintidle"], text=True, timeout=2).strip())
        return ms / 1000.0
    except Exception:
        return 0.0


# endregion

# region Public Methods / API


class WindowInfo(TypedDict):
    """Snapshot of the currently active window."""
    app_name: str
    window_title: str
    exe_path: str


def get_active_window() -> WindowInfo | None:
    """Return info about the current foreground window.

    Returns:
        A WindowInfo dict with app_name, window_title, and exe_path,
        or None if the foreground window cannot be determined.
    """
    if sys.platform == "win32":
        return _active_window_win32()
    return _active_window_linux()


def get_idle_seconds() -> float:
    """Return seconds elapsed since the last keyboard or mouse input.

    Returns:
        Idle duration in seconds (minimum 0.0).
    """
    if sys.platform == "win32":
        return _idle_seconds_win32()
    return _idle_seconds_linux()


# endregion
