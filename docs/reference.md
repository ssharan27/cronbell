# Reference

Technical reference for cronbell. For first-time setup see [Getting Started](../GETTING_STARTED.md) or the [README](../README.md).

> **Linux only** — depends on `crontab`, `systemd --user`, X11/Wayland display detection, and `tkinter`.

## Files

| File | Purpose |
|------|---------|
| `reminders.py` | Self-contained HTTP server + embedded HTML/CSS/JS UI |
| `notify.sh` | Notification dispatcher called by cron |
| `popup.py` | Bottom-right popup with snooze / dismiss |
| `blocker.py` | Full-screen blocking takeover |
| `snooze_checker.py` | Cron-driven snooze queue processor |
| `install.sh` | Installs the systemd user service |
| `reminders.service` | systemd unit template |

## Requirements

- Python 3.6+ with `tkinter` (`python3-tk`)
- `crontab` in PATH (standard on Linux)
- `notify-send` for desktop notifications (optional)

```bash
# Debian/Ubuntu
sudo apt install python3-tk libnotify-bin

# Fedora/RHEL
sudo dnf install python3-tkinter libnotify
```

## Quick start

```bash
cd ~/Desktop/playground/notifier
./install.sh          # installs as a systemd user service
```

Then open **http://localhost:8765**.

The service starts automatically on login and restarts if it crashes.

## How it works

1. **UI** — browser talks to the local HTTP server via a REST API (`/api/reminders`).
2. **Storage** — reminders persisted to `~/.reminders.json`; snooze queue in `~/.reminders-snooze.json`.
3. **Cron** — on every change, the server rewrites its managed crontab block (fenced by `# REMINDERS_MANAGER_START` / `# REMINDERS_MANAGER_END`) without touching other entries. A `snooze_checker.py` line is also injected to run every minute.
4. **Dispatch** — cron calls `notify.sh`, which routes to either the popup or the full-screen blocker depending on the reminder's behaviour settings.

## Notification channels

Each reminder has a **Notify via** checklist:

| Channel | Default | Behaviour |
|---------|---------|-----------|
| Popup | ✅ | Bottom-right tkinter window, snooze + dismiss buttons, auto-closes in 30s |
| Desktop | ☐ | System tray notification via `notify-send` |

Both can be enabled together.

## Blocking reminders

A reminder can be marked **Blocking** — intended for interrupting reminders like "drink water" or "rest your eyes".

- Full-screen black takeover with white title and message
- **Duration** — configurable (default 7s)
- **Dismissable** — if on, Esc or click closes early; if off, it runs the full duration with no escape

When blocking is enabled, the popup/desktop channels are bypassed — the full-screen takeover is the notification.

Blocking reminders show a red `⛔ Xs` badge and red left stripe on their card.

## Snooze

Clicking **Snooze** on a popup or blocker writes an entry to `~/.reminders-snooze.json` with a `wake_at` timestamp (10 minutes from now). The `snooze_checker.py` script runs every minute via cron, fires any overdue entries by calling `notify.sh` with the original settings, and removes them from the queue.

Snooze survives reboots and logouts — it is not a background process.

```json
// ~/.reminders-snooze.json entry
{
  "id": "uuid",
  "name": "Drink Water",
  "message": "Stay hydrated!",
  "notify_via": "popup",
  "blocking": "true",
  "blocking_duration": "7",
  "dismissable": "true",
  "wake_at": "2026-05-12T10:30:00"
}
```

## Schedule types

| Type | Example cron | Description |
|------|-------------|-------------|
| Interval | `*/30 * * * *` | Every N minutes or hours |
| Daily | `0 9 * * *` | Once a day at a fixed time |
| Weekdays | `0 9 * * 1-5` | Mon–Fri at a fixed time |
| Weekly | `0 10 * * 1` | One day per week at a fixed time |
| Custom | anything | Raw cron expression |

## Data file

`~/.reminders.json` — full reminder object shape:

```json
{
  "id": "uuid",
  "name": "Stand-up",
  "message": "Time for stand-up!",
  "cron": "30 9 * * 1-5",
  "schedule_label": "Weekdays at 09:30",
  "notify_via": ["popup"],
  "blocking": false,
  "blocking_duration": 7,
  "dismissable": true,
  "enabled": true,
  "created_at": "2026-05-12T09:00:00"
}
```

## Crontab line format

The managed block writes one line per enabled reminder:

```
{cron} notify.sh "{name}" "{message}" "{notify_via}" "{blocking}" "{blocking_duration}" "{dismissable}"
* * * * * python3 snooze_checker.py >> /dev/null 2>&1
```

## Notifications from cron

Cron runs without a GUI session. `notify.sh` auto-detects `DISPLAY` and `DBUS_SESSION_BUS_ADDRESS` from the user's running processes. To test manually:

```bash
# Standard popup
./notify.sh "Test" "Hello" "popup" "false" "7" "true"

# Blocking, dismissable
./notify.sh "Water" "Drink water!" "popup" "true" "7" "true"

# Blocking, non-dismissable
./notify.sh "Eyes" "Look away from screen" "popup" "true" "5" "false"
```

If cron-fired notifications don't appear, hard-code your session values in `notify.sh`:

```bash
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
```

## REST API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `GET` | `/api/reminders` | — | List all reminders |
| `POST` | `/api/reminders` | reminder object | Create a reminder |
| `PUT` | `/api/reminders/:id` | partial object | Update a reminder |
| `DELETE` | `/api/reminders/:id` | — | Delete a reminder |

## systemd service

### Install

```bash
./install.sh
```

### Manage

```bash
systemctl --user status  reminders
systemctl --user stop    reminders
systemctl --user start   reminders
systemctl --user restart reminders
journalctl --user -u     reminders -f
```

### Uninstall

```bash
systemctl --user disable --now reminders
rm ~/.config/systemd/user/reminders.service
```

> The server binds to `127.0.0.1` only — not accessible from other machines on the network.

---

## Roadmap

- **v2** — phone push notifications (ntfy.sh or similar) with cross-device sync
