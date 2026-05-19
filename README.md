# cronbell

> Cron-backed desktop reminders with a local web UI — no cloud, no account, no background app.

**Linux only.** cronbell relies on `crontab`, `systemd --user`, `tkinter`, and X11/Wayland display detection. It does not run on macOS or Windows.

---

## What it does

You set reminders through a browser UI at `http://localhost:8765`. Each reminder becomes a real cron job. When it fires, you get a popup, a desktop notification, or a full-screen takeover — your choice per reminder.

- **Recurring reminders** — every N minutes, daily, weekdays, weekly, or any cron expression
- **One-off reminders** — fire once at a specific date and time, then clean up automatically
- **Blocking reminders** — full-screen black overlay for things you shouldn't ignore (drink water, rest your eyes). Configurable duration, with a dismissable or non-dismissable mode
- **Snooze** — pick 5 / 10 / 30 min or 1 hour; snooze state is persisted to disk and survives reboots
- **Follow-up** — one-off reminders show a "Follow up →" button that opens the UI pre-filled so you can reschedule or create a new reminder
- **Notify via** — per-reminder checklist: popup (bottom-right), desktop notification, or both
- **Dark mode** — toggle in the UI, saved in the browser

---

## Requirements

| Requirement | Notes |
|-------------|-------|
| **Linux** | Required — cron, systemd, and display detection are Linux-specific |
| **Python 3.6+** with `tkinter` | `sudo apt install python3-tk` |
| `notify-send` | Optional, for desktop tray notifications — `sudo apt install libnotify-bin` |
| A desktop environment | X11 or Wayland (for popup windows) |

---

## Install

```bash
git clone https://github.com/<you>/cronbell.git
cd cronbell
./install.sh
```

Open **http://localhost:8765**. The service starts automatically on every login.

---

## How it works

1. The web UI talks to a small local HTTP server (`reminders.py`) via a REST API.
2. Reminders are stored in `~/.reminders.json`. On every change, the server rewrites a managed block inside your crontab.
3. At the scheduled time, cron calls `notify.sh`, which dispatches to a popup (`popup.py`) or full-screen blocker (`blocker.py`).
4. Snooze entries go to `~/.reminders-snooze.json`. A separate cron job (`snooze_checker.py`) runs every minute, fires overdue snooze entries, and removes them.

---

## Files

```
cronbell/
├── reminders.py        # HTTP server + embedded web UI
├── notify.sh           # Notification dispatcher (called by cron)
├── popup.py            # Bottom-right popup with snooze / dismiss / follow-up
├── blocker.py          # Full-screen blocking takeover
├── snooze_checker.py   # Fires and cleans up snooze queue + one-off reminders
├── install.sh          # Installs the systemd user service
└── reminders.service   # systemd unit template
```

---

## Docs

- [Getting Started](GETTING_STARTED.md) — first-time setup and walkthrough
- [Reference](docs/reference.md) — full technical reference: data model, REST API, crontab format, arg contract, troubleshooting

---

## Roadmap

- **v2** — phone push notifications (ntfy.sh) with cross-device sync
