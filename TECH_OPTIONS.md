# Tech Options for Argus

Four viable stacks to consider. All handle the core Windows requirement:
active window detection via `GetForegroundWindow` + `GetWindowText` Win32 API.

---

## Option A — Python + SQLite + Textual (TUI)

**Vibe:** pragmatic, fast to build, rich ecosystem

| Concern | Solution |
|---|---|
| Active window detection | `pywin32` (`win32gui.GetForegroundWindow`) |
| Idle detection | `pywin32` — `GetLastInputInfo` |
| Storage | `SQLite` via `sqlite3` (stdlib) |
| Scheduling | `schedule` or `threading.Timer` |
| Reports / TUI | `Textual` (rich terminal UI) or `Rich` for CLI output |
| Web dashboard (optional) | `FastAPI` + a simple HTML/JS frontend |
| Daemon / autostart | Windows Task Scheduler or NSSM |

**Pros:** You already have Python projects here; fastest path from zero to working daemon; massive library ecosystem for data analysis (`pandas`, `matplotlib`)  
**Cons:** Higher idle memory (~40–80 MB); packaging a single `.exe` via PyInstaller is doable but messy

---

## Option B — Go + SQLite + Bubble Tea (TUI)

**Vibe:** fast, single binary, clean concurrency model

| Concern | Solution |
|---|---|
| Active window detection | `golang.org/x/sys/windows` — call Win32 APIs directly |
| Idle detection | `GetLastInputInfo` via `syscall` |
| Storage | `modernc.org/sqlite` (pure Go, no CGo needed) |
| Scheduling | `time.Ticker` goroutine |
| Reports / TUI | `Bubble Tea` + `Lip Gloss` (Charm ecosystem) |
| Web dashboard (optional) | `net/http` + embedded HTML |
| Daemon / autostart | Windows Service via `golang.org/x/sys/windows/svc` |

**Pros:** Single binary (~8 MB), very low memory footprint (~5–15 MB at runtime); concurrency is a first-class citizen; fast compile times; beautiful TUI with Charm  
**Cons:** Slightly more verbose than Python for data munging; less mature data-viz libraries

---

## Option C — Rust + SQLite + Ratatui (TUI)

**Vibe:** maximum performance, minimum resource use, bragging rights

| Concern | Solution |
|---|---|
| Active window detection | `windows` crate (official Microsoft bindings) |
| Idle detection | `GetLastInputInfo` via `windows` crate |
| Storage | `rusqlite` |
| Scheduling | `tokio` async runtime with intervals |
| Reports / TUI | `Ratatui` (formerly tui-rs) |
| Web dashboard (optional) | `axum` + embedded SPA |
| Daemon / autostart | `windows-service` crate |

**Pros:** Near-zero runtime overhead; single binary; memory-safe by design; excellent for a long-running daemon  
**Cons:** Steepest learning curve; longer initial dev time; Windows API bindings can be verbose

---

## Option D — Node.js + SQLite + Web Dashboard

**Vibe:** rich UI, familiar if you know JS, easiest for beautiful reports

| Concern | Solution |
|---|---|
| Active window detection | `active-win` npm package (wraps Win32 APIs) |
| Idle detection | `desktop-idle` npm package |
| Storage | `better-sqlite3` |
| Scheduling | `node-cron` or `setInterval` |
| Reports / Dashboard | Local web server (`express`) + `Chart.js` or `D3.js` |
| Daemon / autostart | `pm2` process manager or Windows Task Scheduler |

**Pros:** Best-looking reports with web tech; easy to build interactive dashboards; large npm ecosystem  
**Cons:** Node.js must be installed; higher memory (~100–200 MB); not a true system daemon — more of a managed process

---

## Comparison at a glance

| | Python | Go | Rust | Node.js |
|---|---|---|---|---|
| Dev speed | ★★★★★ | ★★★★ | ★★ | ★★★★ |
| Runtime memory | ~60 MB | ~10 MB | ~5 MB | ~150 MB |
| Binary size | ~30 MB (PyInstaller) | ~8 MB | ~5 MB | N/A |
| TUI quality | Textual (great) | Bubble Tea (great) | Ratatui (great) | N/A |
| Web dashboard | FastAPI | net/http | axum | Express (best) |
| Windows daemon | Task Scheduler | Native service | Native service | pm2 |
| Learning curve | Low | Medium | High | Low |

---

## Recommendation

- **You want it running ASAP** → **Option A (Python)**
- **You want a lean, professional daemon** → **Option B (Go)**
- **You want maximum control + performance** → **Option C (Rust)**
- **You want the nicest visual reports** → **Option D (Node.js)**
