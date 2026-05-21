# cronbell

> Cron-backed desktop reminders with a local web UI — no cloud, no account, no background app. Vibecoded.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

**macOS and Linux.** cronbell relies on `crontab`, `tkinter` for popup windows, and a platform-native background service (launchd on macOS, systemd on Linux).

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

| Requirement | macOS | Linux |
|-------------|-------|-------|
| **Python 3.6+** with `tkinter` | `brew install python-tk` | `sudo apt install python3-tk` |
| Desktop notifications | built-in (`osascript`) | `sudo apt install libnotify-bin` |
| Background service | launchd (built-in) | systemd (built-in) |
| **macOS 13+ only:** cron Full Disk Access | System Settings → Privacy & Security → Full Disk Access → enable `/usr/sbin/cron` | — |

---

## Install

### 1. Install dependencies

```bash
# macOS (Homebrew)
brew install python-tk

# Debian / Ubuntu
sudo apt install python3-tk libnotify-bin

# Fedora / RHEL
sudo dnf install python3-tkinter libnotify
```

### 2. Clone the repo

```bash
git clone https://github.com/ssharan27/cronbell.git
cd cronbell
```

### 3. Run the install script

```bash
./install.sh
```

On **macOS** this writes `~/Library/LaunchAgents/com.user.reminders.plist` and loads it with launchctl.
On **Linux** this writes `~/.config/systemd/user/reminders.service` and enables it with systemctl.

### 4. Open the UI

Go to **http://localhost:8765** in your browser. The service starts automatically on every login — no need to run anything manually again.

### Verify it's running

```bash
# macOS
launchctl list | grep reminders

# Linux
systemctl --user status reminders
```

### Uninstall

```bash
# macOS
launchctl unload ~/Library/LaunchAgents/com.user.reminders.plist
rm ~/Library/LaunchAgents/com.user.reminders.plist
rm -f ~/.reminders.json ~/.reminders-snooze.json

# Linux
systemctl --user disable --now reminders
rm ~/.config/systemd/user/reminders.service
rm -f ~/.reminders.json ~/.reminders-snooze.json
```

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
├── reminders.py                 # HTTP server + embedded web UI
├── notify.sh                    # Notification dispatcher (called by cron)
├── popup.py                     # Bottom-right popup with snooze / dismiss / follow-up
├── blocker.py                   # Full-screen blocking takeover
├── snooze_checker.py            # Fires and cleans up snooze queue + one-off reminders
├── install.sh                   # Installs the platform-native background service
├── reminders.service            # systemd unit template (Linux)
└── com.user.reminders.plist     # launchd unit template (macOS)
```

---

## Docs

- [Getting Started](GETTING_STARTED.md) — first-time setup and walkthrough
- [Reference](docs/reference.md) — full technical reference: data model, REST API, crontab format, arg contract, troubleshooting

---

## Roadmap

- **v2** — phone push notifications (ntfy.sh) with cross-device sync
