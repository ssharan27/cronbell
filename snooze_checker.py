#!/usr/bin/env python3
"""
Runs every minute via cron.
1. Fires overdue snooze entries from ~/.reminders-snooze.json and removes them.
2. Fires due one-off reminders from ~/.reminders.json; removes or marks them based on auto_cleanup.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SNOOZE_FILE    = Path.home() / ".reminders-snooze.json"
REMINDERS_FILE = Path.home() / ".reminders.json"
NOTIFY_SH      = str(Path(__file__).parent / "notify.sh")


def _fire(name, message, notify_via, blocking, blocking_duration, dismissable,
          one_off="false", reminder_id=""):
    subprocess.Popen([
        "bash", NOTIFY_SH,
        name, message,
        notify_via if isinstance(notify_via, str) else ",".join(notify_via),
        blocking, str(blocking_duration), dismissable,
        one_off, reminder_id,
    ])


def process_snooze_queue():
    if not SNOOZE_FILE.exists():
        return
    try:
        entries = json.loads(SNOOZE_FILE.read_text())
    except Exception:
        return

    now, pending = datetime.now(), []
    for entry in entries:
        try:
            wake_at = datetime.fromisoformat(entry["wake_at"])
        except Exception:
            continue  # malformed — drop (cleanup)
        if wake_at <= now:
            _fire(
                entry.get("name",             "Reminder"),
                entry.get("message",          ""),
                entry.get("notify_via",       "popup"),
                entry.get("blocking",         "false"),
                entry.get("blocking_duration","7"),
                entry.get("dismissable",      "true"),
            )
        else:
            pending.append(entry)

    SNOOZE_FILE.write_text(json.dumps(pending, indent=2))


def process_one_offs():
    if not REMINDERS_FILE.exists():
        return
    try:
        reminders = json.loads(REMINDERS_FILE.read_text())
    except Exception:
        return

    now, updated, changed = datetime.now(), [], False
    for r in reminders:
        if not (r.get("one_off") and r.get("enabled", True) and not r.get("fired")):
            updated.append(r)
            continue
        try:
            fire_at = datetime.fromisoformat(r["fire_at"])
        except Exception:
            updated.append(r)
            continue

        if fire_at <= now:
            changed = True
            notify_via = r.get("notify_via", ["popup"])
            _fire(
                r.get("name",             "Reminder"),
                r.get("message",          ""),
                notify_via,
                "true" if r.get("blocking") else "false",
                str(r.get("blocking_duration", 7)),
                "true" if r.get("dismissable", True) else "false",
                "true",
                r.get("id", ""),
            )
            if r.get("auto_cleanup", True):
                pass  # omit from updated → removes entry
            else:
                r["fired"] = True
                updated.append(r)
        else:
            updated.append(r)

    if changed:
        REMINDERS_FILE.write_text(json.dumps(updated, indent=2))


process_snooze_queue()
process_one_offs()
