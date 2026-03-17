"""Win32-based active window and idle time detection."""

import ctypes
import ctypes.wintypes
from typing import TypedDict

import psutil
import win32gui
import win32process


class WindowInfo(TypedDict):
    app_name: str
    window_title: str
    exe_path: str


def get_active_window() -> WindowInfo | None:
    """Return info about the current foreground window, or None on failure."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        window_title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        try:
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            # Strip .exe suffix for cleaner display
            app_name = proc.name().removesuffix(".exe")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            exe_path = ""
            app_name = "unknown"

        return WindowInfo(app_name=app_name, window_title=window_title, exe_path=exe_path)

    except Exception:
        return None


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("dwTime", ctypes.wintypes.DWORD),
    ]


def get_idle_seconds() -> float:
    """Return seconds elapsed since the last keyboard or mouse input."""
    lii = _LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    elapsed_ms = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return max(0.0, elapsed_ms / 1000.0)
