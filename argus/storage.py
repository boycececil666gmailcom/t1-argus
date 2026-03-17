"""SQLite persistence layer."""

import sqlite3
import time
from contextlib import contextmanager

from .config import DATA_DIR, DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL    NOT NULL,
    app_name      TEXT    NOT NULL,
    window_title  TEXT,
    exe_path      TEXT,
    idle          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ts ON snapshots(ts);
"""


@contextmanager
def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(_SCHEMA)


def record(*, app_name: str, window_title: str, exe_path: str, idle: bool) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO snapshots (ts, app_name, window_title, exe_path, idle) VALUES (?,?,?,?,?)",
            (time.time(), app_name, window_title, exe_path, int(idle)),
        )


def query_range(start_ts: float, end_ts: float, include_idle: bool = False) -> list[sqlite3.Row]:
    """Return all snapshots in [start_ts, end_ts). Excludes idle by default."""
    idle_filter = "" if include_idle else "AND idle = 0"
    with _conn() as con:
        return con.execute(
            f"SELECT * FROM snapshots WHERE ts >= ? AND ts < ? {idle_filter} ORDER BY ts",
            (start_ts, end_ts),
        ).fetchall()


def db_stats() -> dict:
    """Return rough stats about the database."""
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        oldest = con.execute("SELECT MIN(ts) FROM snapshots").fetchone()[0]
        newest = con.execute("SELECT MAX(ts) FROM snapshots").fetchone()[0]
    return {"total_snapshots": total, "oldest_ts": oldest, "newest_ts": newest}
