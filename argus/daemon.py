"""The always-on polling daemon."""

import signal
import time

from rich.console import Console

from .config import IDLE_THRESHOLD, POLL_INTERVAL
from .storage import init_db, record
from .tracker import get_active_window, get_idle_seconds

console = Console()
_running = True


def _handle_signal(sig, frame):  # noqa: ARG001
    global _running
    _running = False


def run() -> None:
    init_db()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    console.rule("[bold cyan]Argus[/bold cyan]")
    console.print(f"  Daemon started  ·  poll every [bold]{POLL_INTERVAL}s[/bold]  ·  idle threshold [bold]{IDLE_THRESHOLD}s[/bold]")
    console.print("  Press [bold]Ctrl+C[/bold] to stop.\n")

    prev_app = None

    while _running:
        idle_secs = get_idle_seconds()
        is_idle = idle_secs > IDLE_THRESHOLD

        win = get_active_window()

        if win:
            record(
                app_name=win["app_name"],
                window_title=win["window_title"],
                exe_path=win["exe_path"],
                idle=is_idle,
            )

            # Log to console only when app changes (keeps output readable)
            label = win["app_name"]
            if is_idle:
                label = f"[dim]{label} (idle {idle_secs:.0f}s)[/dim]"

            if label != prev_app:
                console.print(f"  [cyan]→[/cyan] {label}")
                prev_app = label

        time.sleep(POLL_INTERVAL)

    console.print("\n[bold]Argus stopped.[/bold] Data saved to ~/.argus/argus.db")
