#!/usr/bin/env python3
"""
Full-screen blocking notification with snooze / dismiss / follow-up.
Called by notify.sh — not meant to be run directly.

Args: TITLE MESSAGE NOTIFY_VIA BLOCKING BLOCKING_DURATION DISMISSABLE ONE_OFF REMINDER_ID
"""
import json
import sys
import urllib.parse
import uuid
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk

title             = sys.argv[1] if len(sys.argv) > 1 else "Reminder"
message           = sys.argv[2] if len(sys.argv) > 2 else ""
notify_via        = sys.argv[3] if len(sys.argv) > 3 else "popup"
blocking          = sys.argv[4] if len(sys.argv) > 4 else "true"
duration          = int(sys.argv[5]) if len(sys.argv) > 5 else 7
dismissable       = (sys.argv[6].lower() != "false") if len(sys.argv) > 6 else True
one_off           = (sys.argv[7].lower() == "true") if len(sys.argv) > 7 else False
reminder_id       = sys.argv[8] if len(sys.argv) > 8 else ""

SNOOZE_FILE = Path.home() / ".reminders-snooze.json"
UI_URL      = "http://localhost:8765"

# ── Window ────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-topmost", True)
root.configure(bg="black")
root.tk_setPalette(background="black", foreground="white",
                   activeBackground="#1e293b", activeForeground="white",
                   highlightBackground="black")
root.focus_force()

frame = tk.Frame(root, bg="black")
frame.place(relx=0.5, rely=0.5, anchor="center")

tk.Label(frame, text=title, bg="black", fg="white",
         font=("sans-serif", 28, "bold"), justify="center").pack(pady=(0, 20))

tk.Label(frame, text=message, bg="black", fg="#cccccc",
         font=("sans-serif", 18), wraplength=800, justify="center").pack()

tk.Label(frame, text="", bg="black").pack(pady=(32, 0))

countdown_var = tk.StringVar(value=f"closes in {duration}s")
tk.Label(frame, textvariable=countdown_var, bg="black", fg="#555555",
         font=("sans-serif", 13)).pack(pady=(8, 0))

# ── Snooze row ────────────────────────────────────────────────────────────────
snooze_row = tk.Frame(frame, bg="black")
snooze_row.pack(pady=(28, 0))

tk.Label(snooze_row, text="Snooze:", bg="black", fg="#666666",
         font=("sans-serif", 10)).pack(side="left", padx=(0, 10))

def write_snooze(mins):
    entries = []
    if SNOOZE_FILE.exists():
        try:
            entries = json.loads(SNOOZE_FILE.read_text())
        except Exception:
            pass
    entries.append({
        "id":                str(uuid.uuid4()),
        "name":              title,
        "message":           message,
        "notify_via":        notify_via,
        "blocking":          blocking,
        "blocking_duration": str(duration),
        "dismissable":       "true" if dismissable else "false",
        "one_off":           "false",
        "wake_at":           (datetime.now() + timedelta(minutes=mins)).isoformat(),
    })
    SNOOZE_FILE.write_text(json.dumps(entries, indent=2))
    root.destroy()

for label_text, mins in [("5 min", 5), ("10 min", 10), ("30 min", 30), ("1 hour", 60)]:
    tk.Button(snooze_row, text=label_text,
              bg="#1e293b", fg="white", activebackground="#6366f1", activeforeground="white",
              relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
              font=("sans-serif", 10, "bold"),
              command=lambda m=mins: write_snooze(m)).pack(side="left", padx=(0, 8))

# ── Dismiss button — top-right corner ────────────────────────────────────────
if dismissable:
    tk.Button(root, text="✕ Dismiss",
              bg="#1a1a1a", fg="#888888",
              activebackground="#334155", activeforeground="white",
              relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
              font=("sans-serif", 10),
              command=root.destroy).place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=20)

# ── Action row ────────────────────────────────────────────────────────────────
action_row = tk.Frame(frame, bg="black")
action_row.pack(pady=(14, 0))

if one_off:
    def follow_up():
        params = urllib.parse.urlencode({"follow_up": "1", "name": title, "message": message})
        webbrowser.open(f"{UI_URL}?{params}")
        root.destroy()

    tk.Button(action_row, text="Follow up →",
              bg="#6366f1", fg="white", activebackground="#4f46e5", activeforeground="white",
              relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
              font=("sans-serif", 10, "bold"),
              command=follow_up).pack(side="left", padx=(12, 0))

# ── Countdown ─────────────────────────────────────────────────────────────────
remaining = [duration]

def tick():
    remaining[0] -= 1
    countdown_var.set(f"closes in {remaining[0]}s")
    if remaining[0] <= 0:
        root.destroy()
        return
    root.after(1000, tick)

root.after(1000, tick)

if dismissable:
    root.bind("<Escape>", lambda _: root.destroy())

root.mainloop()
