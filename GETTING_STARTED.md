# Getting Started with Notifier

Notifier lets you set up reminders that pop up on your desktop — no accounts, no cloud, nothing running in the background except a small local server. Reminders are powered by your system's cron, so they fire even if you close the browser tab. Vibecoded.

---

## Prerequisites

**Python 3 with tkinter** (required for popups):
- macOS (Homebrew): `brew install python-tk`
- Linux (Debian/Ubuntu): `sudo apt install python3-tk`

**macOS only — cron Full Disk Access:** On macOS 13+, cron needs Full Disk Access to read and write `~/.reminders*.json`. Go to System Settings → Privacy & Security → Full Disk Access and enable `/usr/sbin/cron`.

---

## 1. Install

Open a terminal and run:

```bash
cd ~/Desktop/playground/notifier
./install.sh
```

That's it. The install script sets up a background service that starts automatically every time you log in.

---

## 2. Open the UI

Visit **http://localhost:8765** in your browser.

You'll see an empty list with a **+ New Reminder** button in the top right.

---

## 3. Create your first reminder

Click **+ New Reminder** and fill in:

| Field | What to enter |
|-------|--------------|
| **Name** | A short label, e.g. *Drink Water* |
| **Message** | What you want to see when it fires, e.g. *Stay hydrated!* |
| **Schedule** | Choose a preset — *Every 30 mins*, *Daily at 09:00*, etc. |
| **Notify via** | Leave **Popup** checked (default). Optionally also check **Desktop** for a system tray notification. |

Hit **Add Reminder**. It will appear in the list and start firing immediately at its next scheduled time.

---

## 4. Reminder types

### Standard reminder
Shows a small popup in the bottom-right corner of your screen. You can:
- **Snooze** — reminds you again in 10 minutes (persisted, survives reboots)
- **Dismiss** — closes it
- It auto-closes after 30 seconds if you do nothing

### Blocking reminder
For reminders you shouldn't be able to ignore — like taking a screen break or drinking water. Enable it under **Behaviour → Blocking**.

The entire screen goes black with your message in the centre.

- **Dismissable on** — press Esc or click anywhere to close early
- **Dismissable off** — no escape; it closes on its own after the set duration

---

## 5. Managing reminders

From the reminder list you can:

- **Toggle on/off** — the switch on the right pauses a reminder without deleting it
- **Edit** — click the pencil icon to change anything
- **Delete** — click the bin icon (asks for confirmation)

---

## 6. Schedule options

| Option | Example | When it fires |
|--------|---------|---------------|
| Interval | Every 30 mins | Repeatedly, every N minutes or hours |
| Daily | Daily at 09:00 | Once a day at a fixed time |
| Weekdays | Weekdays at 09:30 | Monday to Friday at a fixed time |
| Weekly | Mondays at 10:00 | Once a week on a chosen day |
| Custom | `0 */2 9-17 * * 1-5` | Any valid cron expression |

---

## 7. Stopping and starting the service

The service runs in the background automatically. If you ever need to control it:

| Action | macOS | Linux |
|--------|-------|-------|
| Status | `launchctl list \| grep reminders` | `systemctl --user status reminders` |
| Stop | `launchctl stop com.user.reminders` | `systemctl --user stop reminders` |
| Start | `launchctl start com.user.reminders` | `systemctl --user start reminders` |
| Logs | `tail -f /tmp/reminders.log` | `journalctl --user -u reminders -f` |
| Uninstall | `launchctl unload ~/Library/LaunchAgents/com.user.reminders.plist && rm ~/Library/LaunchAgents/com.user.reminders.plist` | `systemctl --user disable --now reminders && rm ~/.config/systemd/user/reminders.service` |

Reminders continue firing from cron even when the service is stopped — you just won't be able to reach the web UI until it's running again.

---

## 8. Troubleshooting

**Popup doesn't appear**
Run this in a terminal to test directly:
```bash
cd ~/Desktop/playground/notifier
./notify.sh "Test" "Hello!" "popup" "false" "7" "true"
```
If the popup appears, cron is the issue — see the [README](README.md#notifications-from-cron) for display detection fixes.

**UI not loading at http://localhost:8765**

macOS:
```bash
launchctl list | grep reminders
launchctl start com.user.reminders
```
Linux:
```bash
systemctl --user status reminders
systemctl --user start  reminders
```

**I want to remove a reminder permanently**
Delete it from the UI. The crontab entry is removed automatically.

**I want to uninstall everything**

macOS:
```bash
launchctl unload ~/Library/LaunchAgents/com.user.reminders.plist
rm ~/Library/LaunchAgents/com.user.reminders.plist
rm ~/.reminders.json
rm ~/.reminders-snooze.json
```
Linux:
```bash
systemctl --user disable --now reminders
rm ~/.config/systemd/user/reminders.service
rm ~/.reminders.json
rm ~/.reminders-snooze.json
```
