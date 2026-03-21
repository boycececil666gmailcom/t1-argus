"""Textual TUI for Argus — single-page dashboard with integrated live tracking."""

# region Imports

from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Label, Rule, Static

from .autostart import is_enabled as autostart_is_enabled
from .autostart import toggle as autostart_toggle
from .config import DATA_DIR, IDLE_THRESHOLD, POLL_INTERVAL, categorise
from .config import load_settings, save_settings
from .i18n import LANGUAGES, cycle_language, get_language, set_language, t
from .report import _aggregate, _bar, _fmt
from .storage import db_stats, init_db, query_range, record

# endregion

# region Constants

_UI_REFRESH = 5.0  # seconds between UI auto-refreshes

# Built-in Textual themes — all ship with the library, no extras needed.
_THEMES: list[str] = [
    "textual-dark",
    "textual-light",
    "nord",
    "gruvbox",
    "catppuccin-mocha",
    "catppuccin-latte",
    "dracula",
    "tokyo-night",
    "monokai",
    "solarized-dark",
    "solarized-light",
    "flexoki",
]

# endregion

# region Background Polling

_stop_event = threading.Event()


def _start_polling() -> None:
    """Spawn a daemon thread that polls the active window and writes snapshots to the DB.

    Uses a threading.Event so the loop exits cleanly when the TUI closes.
    Signal handlers are intentionally omitted — they must only run on the main thread.
    """
    def _loop() -> None:
        from .tracker import get_active_window, get_idle_seconds

        init_db()
        while not _stop_event.wait(POLL_INTERVAL):
            try:
                idle = get_idle_seconds()
                win = get_active_window()
                if win:
                    record(
                        app_name=win["app_name"],
                        window_title=win["window_title"],
                        exe_path=win["exe_path"],
                        idle=idle > IDLE_THRESHOLD,
                    )
            except Exception:
                pass

    threading.Thread(target=_loop, name="argus-poll", daemon=True).start()


# endregion

# region Helpers


def _autostart_label() -> str:
    """Return the Auto Start button label reflecting the current state."""
    try:
        enabled = autostart_is_enabled()
    except Exception:
        enabled = False
    return t("auto_start_on") if enabled else t("auto_start_off")


def _lang_label() -> str:
    """Return the language button label, e.g. 'EN  English'."""
    code = get_language()
    return f"{code.upper()}  {LANGUAGES[code]}"


# endregion

# region Widgets


class StatusWidget(Static):
    """Live panel showing the current foreground window, category, idle state, and DB size."""

    def refresh_data(self) -> None:
        """Re-query and redraw with the latest window and idle info."""
        try:
            from .tracker import get_active_window, get_idle_seconds

            win = get_active_window()
            idle = get_idle_seconds()
        except Exception:
            win = None
            idle = 0.0

        stats = db_stats()
        snap_text = f"{stats['total_snapshots']:,}" if stats["total_snapshots"] else "0"

        if win:
            cat = categorise(win["app_name"])
            idle_label = (
                f"[bold red]{t('idle', f'{idle:.0f}')}[/]"
                if idle > IDLE_THRESHOLD
                else f"[green]{t('active_sec', f'{idle:.0f}')}[/]"
            )
            title = win["window_title"]
            if len(title) > 68:
                title = title[:68] + "…"
            content = (
                f"  [bold cyan]{t('app')}[/]       {win['app_name']}     "
                f"[bold cyan]{t('category')}[/]  {cat}\n"
                f"  [bold cyan]{t('window')}[/]    {title}\n"
                f"  [bold cyan]{t('idle_header')}[/]      {idle_label}     "
                f"[bold cyan]{t('snapshots')}[/]  {snap_text}"
            )
        else:
            content = (
                f"  [dim]{t('no_window')}[/]\n"
                f"  [bold cyan]{t('snapshots')}[/]  {snap_text}"
            )

        self.update(content)


# endregion

# region App


class ArgusApp(App):
    """Argus dashboard — live status, today's activity, and this week's breakdown."""

    TITLE = "Argus"

    CSS = """
    Screen {
        background: $surface;
    }

    #scroll {
        padding: 0 1;
    }

    StatusWidget {
        border: round $primary;
        padding: 1 2;
        margin: 1 0;
        height: auto;
    }

    Rule {
        margin: 1 0 0 0;
        color: $primary-darken-2;
    }

    .section-label {
        text-style: bold;
        color: $primary;
        margin: 0 0 0 1;
        padding: 0;
    }

    .summary {
        color: $text-disabled;
        margin: 0 1 1 1;
    }

    .cols {
        height: auto;
        margin: 0;
    }

    .col {
        width: 1fr;
        height: auto;
    }

    DataTable {
        height: auto;
        max-height: 14;
        margin: 0 1 0 0;
    }

    #weekly-days {
        max-height: 9;
        margin: 0 0 1 0;
    }

    #toolbar {
        height: 3;
        align: right middle;
        margin: 0 0 0 0;
        padding: 0 1;
    }

    #db-path {
        width: 1fr;
        content-align: left middle;
        color: $text-disabled;
    }

    #btn-autostart {
        min-width: 20;
    }

    #btn-language {
        min-width: 16;
    }

    #btn-open-db {
        min-width: 16;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_db_folder", "Open DB"),
        Binding("l", "cycle_language", "Language"),
        Binding("a", "toggle_autostart", "Auto Start"),
        Binding("t", "cycle_theme", "Theme"),
    ]

    # region Compose

    def compose(self) -> ComposeResult:
        """Build the single-page layout: status → toolbar → today → this week."""
        yield Header(show_clock=True)
        with ScrollableContainer(id="scroll"):
            yield StatusWidget(id="status")
            with Horizontal(id="toolbar"):
                yield Label(str(DATA_DIR), id="db-path")
                yield Button(_autostart_label(), id="btn-autostart")
                yield Button(_lang_label(), id="btn-language")
                yield Button(t("open_db_folder"), id="btn-open-db")

            yield Rule()
            yield Label("", id="today-label", classes="section-label")
            with Horizontal(classes="cols"):
                with Vertical(classes="col"):
                    yield DataTable(id="today-apps", show_cursor=False)
                with Vertical(classes="col"):
                    yield DataTable(id="today-cats", show_cursor=False)
            yield Label("", id="today-summary", classes="summary")

            yield Rule()
            yield Label("", id="week-label", classes="section-label")
            yield DataTable(id="weekly-days", show_cursor=False)
            with Horizontal(classes="cols"):
                with Vertical(classes="col"):
                    yield DataTable(id="weekly-cats", show_cursor=False)
                with Vertical(classes="col"):
                    yield DataTable(id="weekly-apps", show_cursor=False)
            yield Label("", id="week-summary", classes="summary")

        yield Footer()

    # endregion

    # region Initialization

    def on_mount(self) -> None:
        """Add table columns, load initial data, and start the auto-refresh timer."""
        self.sub_title = t("subtitle")
        self._setup_tables()
        self._refresh()
        self.set_interval(_UI_REFRESH, self._refresh)

    # endregion

    # region Private Methods

    def _setup_tables(self) -> None:
        """Add column headers to every DataTable (call after language change too)."""
        cols_apps = (t("app"), t("time"), t("bar"), t("pct"))
        cols_cats = (t("category"), t("time"), t("bar"))

        self.query_one("#today-apps",   DataTable).add_columns(*cols_apps)
        self.query_one("#today-cats",   DataTable).add_columns(*cols_cats)
        self.query_one("#weekly-days",  DataTable).add_columns(t("day"), t("active"), t("top_app"))
        self.query_one("#weekly-cats",  DataTable).add_columns(*cols_cats)
        self.query_one("#weekly-apps",  DataTable).add_columns(*cols_apps)

    def _rebuild_for_language(self) -> None:
        """Rebuild all language-sensitive UI after a language switch."""
        self.sub_title = t("subtitle")
        self.query_one("#btn-open-db",   Button).label = t("open_db_folder")
        self.query_one("#btn-language",  Button).label = _lang_label()
        self.query_one("#btn-autostart", Button).label = _autostart_label()
        for sel in ("#today-apps", "#today-cats", "#weekly-days", "#weekly-cats", "#weekly-apps"):
            self.query_one(sel, DataTable).clear(columns=True)
        self._setup_tables()
        self._refresh()

    def _refresh(self) -> None:
        """Refresh the status widget, today's tables, and the weekly tables."""
        self.query_one(StatusWidget).refresh_data()
        self._refresh_today()
        self._refresh_week()

    def _refresh_today(self) -> None:
        """Reload today's app and category tables from the DB."""
        today = datetime.now()
        self.query_one("#today-label", Label).update(
            t("today_label", today.strftime("%A, %B %d %Y"))
        )

        start = datetime(today.year, today.month, today.day)
        end   = start + timedelta(days=1)
        rows  = query_range(start.timestamp(), end.timestamp())
        apps, cats = _aggregate(rows)
        total = sum(apps.values())

        self._fill_apps("#today-apps", apps, total, limit=10)
        self._fill_cats("#today-cats", cats, total)
        self.query_one("#today-summary", Label).update(
            t("total_active_today", _fmt(total), len(rows))
            if rows
            else t("no_data_today")
        )

    def _refresh_week(self) -> None:
        """Reload this week's day-by-day table, categories, and top apps from the DB."""
        today  = datetime.now()
        monday = today - timedelta(days=today.weekday())
        monday = datetime(monday.year, monday.month, monday.day)
        sunday = monday + timedelta(days=6)

        self.query_one("#week-label", Label).update(
            t("week_label", monday.strftime("%b %d"), sunday.strftime("%b %d, %Y"))
        )

        week_apps: dict[str, float] = {}
        week_cats: dict[str, float] = {}

        days_tbl = self.query_one("#weekly-days", DataTable)
        days_tbl.clear()

        for offset in range(7):
            day      = monday + timedelta(days=offset)
            day_rows = query_range(day.timestamp(), (day + timedelta(days=1)).timestamp())
            apps, cats = _aggregate(day_rows)

            for k, v in apps.items():
                week_apps[k] = week_apps.get(k, 0) + v
            for k, v in cats.items():
                week_cats[k] = week_cats.get(k, 0) + v

            total_day = sum(apps.values())
            top       = max(apps, key=apps.get) if apps else "—"
            day_label = day.strftime("%a %b %d")
            if day.date() == today.date():
                day_label = f"▶ {day_label}"
            days_tbl.add_row(day_label, _fmt(total_day) if total_day else "—", top)

        week_total = sum(week_apps.values())
        self._fill_cats("#weekly-cats", week_cats, week_total)
        self._fill_apps("#weekly-apps", week_apps, week_total, limit=10)
        self.query_one("#week-summary", Label).update(
            t("weekly_total", _fmt(week_total))
            if week_total
            else t("no_data_week")
        )

    def _fill_apps(self, sel: str, apps: dict, total: float, limit: int = 10) -> None:
        """Clear and repopulate an apps DataTable sorted by time descending."""
        tbl = self.query_one(sel, DataTable)
        tbl.clear()
        for name, secs in sorted(apps.items(), key=lambda x: -x[1])[:limit]:
            frac = secs / total if total else 0
            tbl.add_row(name, _fmt(secs), _bar(frac, 20), f"{frac * 100:.1f}%")

    def _fill_cats(self, sel: str, cats: dict, total: float) -> None:
        """Clear and repopulate a categories DataTable sorted by time descending."""
        tbl = self.query_one(sel, DataTable)
        tbl.clear()
        for cat, secs in sorted(cats.items(), key=lambda x: -x[1]):
            frac = secs / total if total else 0
            tbl.add_row(cat, _fmt(secs), _bar(frac, 20))

    # endregion

    # region Public Methods / API

    def action_refresh(self) -> None:
        """Manually trigger a full refresh of all widgets."""
        self._refresh()

    def action_open_db_folder(self) -> None:
        """Open the Argus data directory in the system file manager."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(DATA_DIR)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(DATA_DIR)], check=False)
        else:
            subprocess.run(["xdg-open", str(DATA_DIR)], check=False)

    def action_toggle_autostart(self) -> None:
        """Toggle the system login auto-start and update the button label."""
        try:
            enabled = autostart_toggle()
            self.query_one("#btn-autostart", Button).label = _autostart_label()
            msg = t("autostart_enabled") if enabled else t("autostart_disabled")
            self.notify(msg)
        except Exception as exc:
            self.notify(t("autostart_error", str(exc)), severity="error")

    def action_cycle_language(self) -> None:
        """Advance to the next UI language, persist the choice, and rebuild the UI."""
        code = cycle_language()
        save_settings({"language": code})
        self._rebuild_for_language()

    def action_cycle_theme(self) -> None:
        """Advance to the next built-in Textual theme and persist the choice."""
        try:
            current = self.theme or _THEMES[0]
            idx = _THEMES.index(current) if current in _THEMES else 0
            next_theme = _THEMES[(idx + 1) % len(_THEMES)]
            self.theme = next_theme
            save_settings({"theme": next_theme})
            self.notify(next_theme)
        except Exception as exc:
            self.notify(str(exc), severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route button presses to the appropriate action.

        Args:
            event: The button press event carrying the button's ID.
        """
        if event.button.id == "btn-open-db":
            self.action_open_db_folder()
        elif event.button.id == "btn-autostart":
            self.action_toggle_autostart()
        elif event.button.id == "btn-language":
            self.action_cycle_language()

    # endregion


# endregion


def run() -> None:
    """Load persisted settings, start background polling, then launch the TUI.

    The polling thread writes snapshots to the DB every POLL_INTERVAL seconds.
    It is stopped cleanly via a threading.Event when the app exits.
    """
    settings = load_settings()
    set_language(settings.get("language", "en"))

    saved_theme = settings.get("theme", _THEMES[0])
    if saved_theme not in _THEMES:
        saved_theme = _THEMES[0]

    _start_polling()
    try:
        app = ArgusApp()
        app.theme = saved_theme
        app.run()
    finally:
        _stop_event.set()
