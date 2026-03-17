#!/usr/bin/env python
"""
Argus — the hundred-eyed daemon.

Usage:
  python main.py start          # run daemon in foreground
  python main.py report         # today's report
  python main.py report --date 2026-03-15
  python main.py week           # this week's report
  python main.py status         # current window + idle time
  python main.py install        # add to Windows startup
  python main.py uninstall      # remove from Windows startup
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="argus",
    help="Argus — always-on activity tracker and behavior reporter.",
    add_completion=False,
)
console = Console()

_TASK_NAME = "ArgusDaemon"
_THIS = Path(sys.executable).resolve()
_SCRIPT = Path(__file__).resolve()


# ── commands ──────────────────────────────────────────────────────────────────

@app.command()
def start() -> None:
    """Start the Argus daemon (runs in foreground; Ctrl+C to stop)."""
    from argus.daemon import run
    run()


@app.command()
def report(
    date: str = typer.Option(
        None, "--date", "-d",
        help="Date to report — YYYY-MM-DD (default: today).",
    ),
) -> None:
    """Show a daily activity report."""
    from argus.report import daily_report

    d = _parse_date(date) if date else datetime.now()
    daily_report(d)


@app.command()
def week(
    date: str = typer.Option(
        None, "--date", "-d",
        help="Any date within the desired week — YYYY-MM-DD (default: this week).",
    ),
) -> None:
    """Show a weekly activity report."""
    from argus.report import weekly_report

    d = _parse_date(date) if date else datetime.now()
    weekly_report(d)


@app.command()
def status() -> None:
    """Show what you're doing right now and your current idle time."""
    from argus.report import status_panel
    from argus.tracker import get_active_window, get_idle_seconds

    win = get_active_window()
    idle = get_idle_seconds()
    status_panel(win, idle)


@app.command()
def install() -> None:
    """Register Argus as a Windows startup task (runs at login, hidden)."""
    import subprocess

    cmd = (
        f'schtasks /Create /TN "{_TASK_NAME}" /TR '
        f'\\"{_THIS}\\" \\"{_SCRIPT}\\" start '
        f'/SC ONLOGON /RL HIGHEST /F'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"[bold green]✓[/bold green] Argus scheduled as '{_TASK_NAME}'.")
        console.print(f"  It will start automatically at next login.")
    else:
        console.print(f"[bold red]✗[/bold red] Failed:\n{result.stderr}")
        raise typer.Exit(1)


@app.command()
def uninstall() -> None:
    """Remove the Argus Windows startup task."""
    import subprocess

    result = subprocess.run(
        f'schtasks /Delete /TN "{_TASK_NAME}" /F',
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print(f"[bold green]✓[/bold green] Task '{_TASK_NAME}' removed.")
    else:
        console.print(f"[bold red]✗[/bold red] Could not remove:\n{result.stderr}")
        raise typer.Exit(1)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        console.print(f"[red]Invalid date '{s}'. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
