import os
from pathlib import Path

# Where all Argus data lives
DATA_DIR = Path(os.environ.get("ARGUS_DATA", Path.home() / ".argus"))
DB_PATH = DATA_DIR / "argus.db"

# Daemon behaviour
POLL_INTERVAL = 5          # seconds between snapshots
IDLE_THRESHOLD = 60        # seconds of no input before marking as idle

# App → category mapping (process name prefix, case-insensitive)
CATEGORIES: dict[str, list[str]] = {
    "Browser":       ["chrome", "firefox", "msedge", "opera", "brave", "vivaldi", "iexplore"],
    "IDE / Editor":  ["code", "cursor", "pycharm", "idea", "clion", "rider", "vim", "nvim",
                      "sublime_text", "notepad++", "atom", "zed"],
    "Terminal":      ["windowsterminal", "cmd", "powershell", "wt", "alacritty", "conhost", "bash"],
    "Communication": ["discord", "slack", "teams", "zoom", "skype", "telegram", "signal",
                      "whatsapp", "mattermost"],
    "Design":        ["figma", "photoshop", "illustrator", "blender", "inkscape", "gimp",
                      "krita", "xd", "sketch"],
    "Gaming":        ["steam", "epicgameslauncher", "gog", "origin", "battlenet", "leagueclient",
                      "gameoverlayui"],
    "Productivity":  ["excel", "word", "powerpoint", "onenote", "notion", "obsidian",
                      "evernote", "outlook", "thunderbird"],
    "Media":         ["spotify", "vlc", "mpv", "mpc-hc", "netflix", "plex", "musicbee",
                      "foobar2000"],
    "File Manager":  ["explorer", "totalcmd", "doublecmd", "xplorer2"],
    "System":        ["taskmgr", "regedit", "mmc", "services", "eventvwr", "perfmon",
                      "resmon", "dxdiag"],
}


def categorise(app_name: str) -> str:
    lower = app_name.lower()
    for category, patterns in CATEGORIES.items():
        if any(lower.startswith(p) or p in lower for p in patterns):
            return category
    return "Other"
