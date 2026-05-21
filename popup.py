#!/usr/bin/env python3
"""
Positioned notification popup with snooze / dismiss / follow-up.
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
import platform
import tkinter as tk

title             = sys.argv[1] if len(sys.argv) > 1 else "Reminder"
message           = sys.argv[2] if len(sys.argv) > 2 else ""
notify_via        = sys.argv[3] if len(sys.argv) > 3 else "popup"
blocking          = sys.argv[4] if len(sys.argv) > 4 else "false"
blocking_duration = sys.argv[5] if len(sys.argv) > 5 else "7"
dismissable       = sys.argv[6] if len(sys.argv) > 6 else "true"
one_off           = (sys.argv[7].lower() == "true") if len(sys.argv) > 7 else False
reminder_id       = sys.argv[8] if len(sys.argv) > 8 else ""

AUTO_CLOSE  = 30
SNOOZE_FILE = Path.home() / ".reminders-snooze.json"
UI_URL      = "http://localhost:8765"

# ── Window ────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title(title)
root.resizable(False, False)
root.attributes("-topmost", True)

WIN_W, WIN_H = 360, 185
root.update_idletasks()
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
bottom_offset = 76 if platform.system() == 'Darwin' else 56
root.geometry(f"{WIN_W}x{WIN_H}+{sw - WIN_W - 20}+{sh - WIN_H - bottom_offset}")

BG     = "#1e293b"
BG2    = "#0f172a"
ACCENT = "#6366f1"
FG     = "#f1f5f9"
MUTED  = "#94a3b8"
BTN_SM = {"relief": "flat", "bd": 0, "padx": 8, "pady": 4, "cursor": "hand2",
           "font": ("sans-serif", 8, "bold")}

root.configure(bg=BG)
tk.Frame(root, bg=ACCENT, height=3).pack(fill="x")

body = tk.Frame(root, bg=BG, padx=16, pady=10)
body.pack(fill="both", expand=True)

tk.Label(body, text=f"⏰  {title}", bg=BG, fg=FG,
         font=("sans-serif", 11, "bold"), anchor="w").pack(fill="x")

tk.Label(body, text=message, bg=BG, fg=MUTED,
         font=("sans-serif", 10), anchor="w",
         wraplength=326, justify="left").pack(fill="x", pady=(3, 10))

# ── Snooze row ────────────────────────────────────────────────────────────────
snooze_row = tk.Frame(body, bg=BG)
snooze_row.pack(fill="x", pady=(0, 6))

tk.Label(snooze_row, text="Snooze:", bg=BG, fg=MUTED,
         font=("sans-serif", 8)).pack(side="left", padx=(0, 6))

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
        "blocking_duration": blocking_duration,
        "dismissable":       dismissable,
        "one_off":           "false",
        "wake_at":           (datetime.now() + timedelta(minutes=mins)).isoformat(),
    })
    SNOOZE_FILE.write_text(json.dumps(entries, indent=2))
    root.destroy()

for label_text, mins in [("5m", 5), ("10m", 10), ("30m", 30), ("1h", 60)]:
    tk.Button(snooze_row, text=label_text,
              bg="#2d3f55", fg=FG, activebackground=ACCENT, activeforeground="#fff",
              **BTN_SM, command=lambda m=mins: write_snooze(m)).pack(side="left", padx=(0, 4))

# ── Action row ────────────────────────────────────────────────────────────────
action_row = tk.Frame(body, bg=BG)
action_row.pack(fill="x")

tk.Button(action_row, text="Dismiss",
          bg=BG2, fg=MUTED, activebackground="#1e293b", activeforeground=FG,
          relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
          font=("sans-serif", 9),
          command=root.destroy).pack(side="left")

if one_off:
    def follow_up():
        params = urllib.parse.urlencode({"follow_up": "1", "name": title, "message": message})
        webbrowser.open(f"{UI_URL}?{params}")
        root.destroy()

    tk.Button(action_row, text="Follow up →",
              bg=ACCENT, fg="#fff", activebackground="#4f46e5", activeforeground="#fff",
              relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
              font=("sans-serif", 9, "bold"),
              command=follow_up).pack(side="left", padx=(8, 0))

# ── Countdown ─────────────────────────────────────────────────────────────────
countdown = tk.StringVar(value=f"auto-closes in {AUTO_CLOSE}s")
tk.Label(body, textvariable=countdown, bg=BG, fg=MUTED,
         font=("sans-serif", 8), anchor="e").pack(fill="x", pady=(6, 0))

remaining = [AUTO_CLOSE]

def tick():
    remaining[0] -= 1
    if remaining[0] <= 0:
        root.destroy()
        return
    countdown.set(f"auto-closes in {remaining[0]}s")
    root.after(1000, tick)

root.after(1000, tick)
root.mainloop()
