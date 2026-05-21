#!/usr/bin/env python3
"""
Reminders Manager — local crontab-backed reminder UI.
Usage: python3 reminders.py [port]   (default port: 8765)
Then open http://localhost:8765
"""
import http.server
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
DATA_FILE = Path.home() / ".reminders.json"
NOTIFY_SCRIPT   = str(Path(__file__).parent.resolve() / "notify.sh")
SNOOZE_CHECKER  = str(Path(__file__).parent.resolve() / "snooze_checker.py")
CRON_START = "# REMINDERS_MANAGER_START"
CRON_END   = "# REMINDERS_MANAGER_END"

# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

def load():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            return []
    return []

def save(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))
    sync_crontab(data)

def sync_crontab(reminders):
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    # Strip our managed block
    lines, skip = [], False
    for line in existing.splitlines():
        if line.strip() == CRON_START:
            skip = True
        elif line.strip() == CRON_END:
            skip = False
        elif not skip:
            lines.append(line)

    # Trim trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()

    # Re-add managed block
    lines.append("")
    lines.append(CRON_START)
    for r in reminders:
        if r.get("enabled", True) and not r.get("one_off"):
            name        = r["name"].replace('"', '\\"')
            msg         = r["message"].replace('"', '\\"')
            via         = ",".join(r.get("notify_via", ["popup"]))
            blocking    = "true" if r.get("blocking") else "false"
            duration    = str(r.get("blocking_duration", 7))
            dismissable = "true" if r.get("dismissable", True) else "false"
            lines.append(f'{r["cron"]} {NOTIFY_SCRIPT} "{name}" "{msg}" "{via}" "{blocking}" "{duration}" "{dismissable}" "false" "{r["id"]}"')
    lines.append(f"* * * * * python3 {SNOOZE_CHECKER} >> /dev/null 2>&1")
    lines.append(CRON_END)
    lines.append("")

    subprocess.run(["crontab", "-"], input="\n".join(lines), text=True, check=True)

# ---------------------------------------------------------------------------
# Embedded UI
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reminders</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:           #f0f2f5;
  --surface:      #ffffff;
  --surface2:     #f8f9fa;
  --border:       #e2e8f0;
  --accent:       #6366f1;
  --accent-hover: #4f46e5;
  --text:         #1e293b;
  --muted:        #64748b;
  --danger:       #ef4444;
  --radius:       12px;
  --shadow:       0 1px 3px rgba(0,0,0,.10), 0 1px 2px rgba(0,0,0,.06);
  --shadow-lg:    0 10px 15px -3px rgba(0,0,0,.10), 0 4px 6px -2px rgba(0,0,0,.05);
}

[data-theme="dark"] {
  --bg:           #0f172a;
  --surface:      #1e293b;
  --surface2:     #263548;
  --border:       #334155;
  --accent-hover: #818cf8;
  --text:         #f1f5f9;
  --muted:        #94a3b8;
  --danger:       #f87171;
  color-scheme: dark;
}
[data-theme="dark"] .badge-accent    { background: #312e81; color: #a5b4fc; }
[data-theme="dark"] .badge-blocking  { background: #450a0a; color: #fca5a5; }
[data-theme="dark"] .badge-once      { background: #422006; color: #fde047; }
[data-theme="dark"] .check-pill.on   { background: #312e81; color: #a5b4fc; border-color: var(--accent); }
[data-theme="dark"] .toast           { background: #f1f5f9; color: #0f172a; }
[data-theme="dark"] .seg-btn.active  { background: var(--surface2); }
[data-theme="dark"] .overlay         { background: rgba(0,0,0,.65); }
[data-theme="dark"] input[type=date],
[data-theme="dark"] input[type=time] { color-scheme: dark; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  transition: background .2s, color .2s;
}

.app { max-width: 720px; margin: 0 auto; padding: 36px 16px; }

/* ── Header ── */
header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
}
header h1  { font-size: 1.75rem; font-weight: 700; }
header p   { color: var(--muted); font-size: .875rem; margin-top: 3px; }

/* ── Buttons ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: .875rem;
  font-weight: 500;
  transition: background .15s, box-shadow .15s;
}
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-ghost   { background: transparent; color: var(--muted); border: 1px solid var(--border); }
.btn-ghost:hover { background: var(--surface2); color: var(--text); }

/* ── Empty state ── */
.empty { text-align: center; padding: 72px 24px; color: var(--muted); }
.empty-icon { font-size: 3rem; margin-bottom: 14px; }
.empty h3   { font-size: 1.125rem; font-weight: 600; color: var(--text); margin-bottom: 6px; }

/* ── Cards ── */
.reminder-list { display: flex; flex-direction: column; gap: 12px; }

.card {
  background: var(--surface);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  padding: 12px 16px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  box-shadow: var(--shadow);
  transition: box-shadow .15s, opacity .2s;
}
.card:hover { box-shadow: var(--shadow-lg); }
.card.disabled { opacity: .5; }

.card-stripe {
  width: 4px;
  border-radius: 4px;
  background: var(--accent);
  align-self: stretch;
  flex-shrink: 0;
}
.card.disabled .card-stripe { background: var(--muted); }

.card-body   { flex: 1; min-width: 0; }
.card-name   { font-size: 1rem; font-weight: 600; margin-bottom: 3px; }
.card-msg    { font-size: .8125rem; color: var(--muted); margin-bottom: 8px;
               white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-meta   { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: .75rem;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 99px;
}
.badge-accent    { background: #ede9fe; color: #7c3aed; }
.badge-muted     { background: var(--surface2); color: var(--muted); }
.badge-blocking  { background: #fee2e2; color: #991b1b; }
.badge-once      { background: #fef9c3; color: #854d0e; }
.badge-fired     { background: var(--surface2); color: var(--muted); text-decoration: line-through; }

.card-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* ── Toggle ── */
.toggle { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-track {
  position: absolute;
  inset: 0;
  background: var(--border);
  border-radius: 22px;
  cursor: pointer;
  transition: background .2s;
}
.toggle-track::before {
  content: '';
  position: absolute;
  height: 16px; width: 16px;
  left: 3px; top: 3px;
  background: #fff;
  border-radius: 50%;
  transition: transform .2s;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.toggle input:checked + .toggle-track { background: var(--accent); }
.toggle input:checked + .toggle-track::before { transform: translateX(18px); }

/* ── Icon buttons ── */
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px; height: 32px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: transparent;
  cursor: pointer;
  color: var(--muted);
  transition: all .15s;
  font-size: .875rem;
}
.icon-btn:hover           { background: var(--surface2); color: var(--text); }
.icon-btn.del:hover       { background: #fef2f2; color: var(--danger); border-color: #fecaca; }

/* ── Modal ── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
  backdrop-filter: blur(2px);
}
.overlay.hidden { display: none; }

.modal {
  background: var(--surface);
  border-radius: 16px;
  padding: 28px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.modal-header h2 { font-size: 1.25rem; font-weight: 700; }

.close-btn {
  width: 30px; height: 30px;
  border-radius: 6px;
  border: none;
  background: var(--surface2);
  cursor: pointer;
  font-size: 1rem;
  color: var(--muted);
  display: flex; align-items: center; justify-content: center;
  transition: background .15s;
}
.close-btn:hover { background: var(--border); }

/* ── Form ── */
.form-group { margin-bottom: 18px; }
label { display: block; font-size: .875rem; font-weight: 500; margin-bottom: 6px; }
label .req { color: var(--danger); margin-left: 2px; }

input[type=text], textarea, select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: .9375rem;
  font-family: inherit;
  color: var(--text);
  background: var(--surface);
  outline: none;
  transition: border-color .15s, box-shadow .15s;
}
input[type=text]:focus, textarea:focus, select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(99,102,241,.15);
}
textarea { resize: vertical; min-height: 72px; }

/* ── Schedule type segments ── */
.seg-group {
  display: flex;
  background: var(--surface2);
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
  margin-bottom: 16px;
}
.seg-btn {
  flex: 1;
  padding: 7px 4px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: .8rem;
  font-weight: 500;
  color: var(--muted);
  transition: all .15s;
  white-space: nowrap;
}
.seg-btn.active { background: var(--surface); color: var(--text); box-shadow: var(--shadow); }

.sched-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
.sched-row .form-group { flex: 1; min-width: 100px; margin-bottom: 0; }

.cron-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding: 10px 12px;
  background: var(--surface2);
  border-radius: 8px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: .875rem;
  color: var(--muted);
}
.cron-preview b { color: var(--text); font-weight: 600; }

.form-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
}

/* ── Toast ── */
.toast {
  position: fixed;
  bottom: 24px; right: 24px;
  padding: 12px 18px;
  background: #1e293b;
  color: #fff;
  border-radius: 8px;
  font-size: .875rem;
  box-shadow: var(--shadow-lg);
  z-index: 200;
  transition: opacity .3s, transform .3s;
}
.toast.hidden { opacity: 0; transform: translateY(16px); pointer-events: none; }

/* ── Notify-via pills ── */
.check-group { display: flex; gap: 10px; flex-wrap: wrap; }
.check-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: .875rem;
  font-weight: 500;
  color: var(--muted);
  background: var(--surface2);
  user-select: none;
  transition: all .15s;
}
.check-pill input { display: none; }
.check-pill.on { border-color: var(--accent); background: #ede9fe; color: var(--accent); }

/* ── Day pills ── */
.day-group { display: flex; gap: 6px; flex-wrap: wrap; }
.day-pill {
  padding: 6px 11px;
  border-radius: 6px;
  border: 1.5px solid var(--border);
  background: var(--surface2);
  color: var(--muted);
  font-size: .8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
  user-select: none;
}
.day-pill.on { border-color: var(--accent); background: #ede9fe; color: var(--accent); }
[data-theme="dark"] .day-pill.on { background: #312e81; color: #a5b4fc; }

/* ── AM/PM time picker ── */
.time-picker { display: flex; align-items: center; gap: 4px; }
.time-picker select { width: auto; padding: 9px 8px; }
.time-colon { font-weight: 700; color: var(--muted); padding: 0 2px; }
.ampm-toggle {
  display: flex;
  border: 1px solid var(--border);
  border-radius: 7px;
  overflow: hidden;
  margin-left: 4px;
}
.ampm-btn {
  padding: 8px 11px;
  border: none;
  background: var(--surface2);
  color: var(--muted);
  font-size: .8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
}
.ampm-btn.active { background: var(--accent); color: #fff; }

/* ── Tag suggestions ── */
.tag-suggestions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; min-height: 0; }
.tag-suggestion {
  padding: 3px 10px;
  border: 1.5px solid var(--border);
  border-radius: 99px;
  font-size: .75rem;
  font-weight: 500;
  color: var(--text);
  background: var(--surface2);
  cursor: pointer;
  transition: all .15s;
  user-select: none;
}
.tag-suggestion:hover { border-color: var(--accent); color: var(--accent); background: #ede9fe; }
[data-theme="dark"] .tag-suggestion:hover { background: #312e81; color: #a5b4fc; border-color: var(--accent); }

/* ── Tag input (modal) ── */
.tag-input-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: text;
  min-height: 42px;
  transition: border-color .15s, box-shadow .15s;
}
.tag-input-wrap:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(99,102,241,.15);
}
.tag-pill-input {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px 3px 10px;
  background: #ede9fe;
  color: #7c3aed;
  border-radius: 99px;
  font-size: .75rem;
  font-weight: 500;
}
[data-theme="dark"] .tag-pill-input { background: #312e81; color: #a5b4fc; }
.tag-pill-remove { line-height: 1; cursor: pointer; opacity: .55; font-size: .65rem; }
.tag-pill-remove:hover { opacity: 1; }
.tag-text-input {
  border: none; outline: none; background: transparent;
  font-size: .875rem; color: var(--text); font-family: inherit;
  min-width: 80px; flex: 1; padding: 2px 4px;
}
.tag-text-input::placeholder { color: var(--muted); }

/* ── Group headers (list) ── */
.group-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0 8px;
  margin: 8px 0 6px;
  background: var(--bg);
  backdrop-filter: blur(8px);
  cursor: pointer;
  user-select: none;
}
.group-header:first-child { margin-top: 0; }
.group-label {
  font-size: .7rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .07em;
  color: var(--muted); white-space: nowrap;
}
.group-count {
  font-size: .7rem; font-weight: 600;
  padding: 1px 7px; background: var(--surface2);
  color: var(--muted); border-radius: 99px;
}
.group-line  { flex: 1; height: 1px; background: var(--border); }
.group-chevron { font-size: .65rem; color: var(--muted); transition: transform .2s; }
.group-chevron.collapsed { transform: rotate(-90deg); }

.hidden { display: none !important; }
</style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <h1>Reminders</h1>
      <p>Manage your crontab-backed notifications</p>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <button class="icon-btn" id="theme-btn" onclick="toggleTheme()" title="Toggle theme" style="font-size:1rem">🌙</button>
      <button class="btn btn-primary" onclick="openModal()">+ New Reminder</button>
    </div>
  </header>
  <div id="list"></div>
</div>

<!-- Modal -->
<div class="overlay hidden" id="overlay" onclick="overlayClick(event)">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <div class="modal-header">
      <h2 id="modal-title">New Reminder</h2>
      <button class="close-btn" onclick="closeModal()" aria-label="Close">✕</button>
    </div>
    <form onsubmit="saveReminder(event)" novalidate>
      <div class="form-group">
        <label for="f-name">Name <span class="req" aria-label="required">*</span></label>
        <input type="text" id="f-name" placeholder="e.g. Daily Stand-up" required>
      </div>
      <div class="form-group">
        <label for="f-message">Message <span class="req" aria-label="required">*</span></label>
        <textarea id="f-message" placeholder="e.g. Time for stand-up!" required></textarea>
      </div>

      <div class="form-group">
        <label>Tags <span style="color:var(--muted);font-weight:400;font-size:.8rem">(optional, press Enter or ,)</span></label>
        <div class="tag-input-wrap" id="tag-input-wrap" onclick="document.getElementById('tag-text-input').focus()">
          <input type="text" id="tag-text-input" class="tag-text-input" placeholder="e.g. health, work"
                 onkeydown="tagKeydown(event)" oninput="tagInputHandler(event)">
        </div>
        <div id="tag-suggestions" class="tag-suggestions"></div>
      </div>

      <div class="form-group">
        <label>Schedule</label>
        <div class="seg-group" role="tablist">
          <button type="button" class="seg-btn active" data-t="interval" onclick="setSched('interval')">Interval</button>
          <button type="button" class="seg-btn"        data-t="days"     onclick="setSched('days')">Days</button>
          <button type="button" class="seg-btn"        data-t="once"     onclick="setSched('once')">Once</button>
          <button type="button" class="seg-btn"        data-t="custom"   onclick="setSched('custom')">Custom</button>
        </div>

        <!-- Interval -->
        <div id="s-interval" class="sched-row">
          <div class="form-group">
            <label for="f-ival">Every</label>
            <input type="text" id="f-ival" value="30" style="width:80px" oninput="updatePreview()">
          </div>
          <div class="form-group">
            <label for="f-iunit">Unit</label>
            <select id="f-iunit" onchange="updatePreview()">
              <option value="min">minutes</option>
              <option value="hr">hours</option>
            </select>
          </div>
        </div>

        <!-- Days -->
        <div id="s-days" class="hidden">
          <div class="form-group" style="margin-bottom:12px">
            <label>Days</label>
            <div class="day-group">
              <button type="button" class="day-pill on" data-day="1" onclick="toggleDay(this)">Mon</button>
              <button type="button" class="day-pill on" data-day="2" onclick="toggleDay(this)">Tue</button>
              <button type="button" class="day-pill on" data-day="3" onclick="toggleDay(this)">Wed</button>
              <button type="button" class="day-pill on" data-day="4" onclick="toggleDay(this)">Thu</button>
              <button type="button" class="day-pill on" data-day="5" onclick="toggleDay(this)">Fri</button>
              <button type="button" class="day-pill"    data-day="6" onclick="toggleDay(this)">Sat</button>
              <button type="button" class="day-pill"    data-day="0" onclick="toggleDay(this)">Sun</button>
            </div>
          </div>
          <div class="form-group" style="margin-bottom:0">
            <label>At</label>
            <div class="time-picker">
              <select id="days-hour" onchange="updatePreview()">
                <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                <option value="7">7</option><option value="8">8</option><option value="9" selected>9</option>
                <option value="10">10</option><option value="11">11</option><option value="12">12</option>
              </select>
              <span class="time-colon">:</span>
              <select id="days-min" onchange="updatePreview()">
                <option value="0" selected>00</option><option value="5">05</option><option value="10">10</option>
                <option value="15">15</option><option value="20">20</option><option value="25">25</option>
                <option value="30">30</option><option value="35">35</option><option value="40">40</option>
                <option value="45">45</option><option value="50">50</option><option value="55">55</option>
              </select>
              <div class="ampm-toggle">
                <button type="button" class="ampm-btn active" id="days-am" onclick="setAmPm('days','am')">AM</button>
                <button type="button" class="ampm-btn"        id="days-pm" onclick="setAmPm('days','pm')">PM</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Custom cron -->
        <div id="s-custom" class="hidden">
          <input type="text" id="f-cron" placeholder="e.g. */30 9-17 * * 1-5" oninput="updatePreview()">
          <small style="display:block;margin-top:6px;color:var(--muted);font-size:.8rem">
            Format: minute&nbsp; hour&nbsp; day&nbsp; month&nbsp; weekday
          </small>
        </div>

        <!-- Once -->
        <div id="s-once" class="sched-row hidden">
          <div class="form-group" style="flex:2;min-width:140px;margin-bottom:0">
            <label for="f-once-date">Date</label>
            <input type="date" id="f-once-date" oninput="updatePreview()">
          </div>
          <div class="form-group" style="flex:1;min-width:120px;margin-bottom:0">
            <label>Time</label>
            <div class="time-picker">
              <select id="once-hour" onchange="updatePreview()">
                <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                <option value="4">4</option><option value="5">5</option><option value="6">6</option>
                <option value="7">7</option><option value="8">8</option><option value="9" selected>9</option>
                <option value="10">10</option><option value="11">11</option><option value="12">12</option>
              </select>
              <span class="time-colon">:</span>
              <select id="once-min" onchange="updatePreview()">
                <option value="0" selected>00</option><option value="5">05</option><option value="10">10</option>
                <option value="15">15</option><option value="20">20</option><option value="25">25</option>
                <option value="30">30</option><option value="35">35</option><option value="40">40</option>
                <option value="45">45</option><option value="50">50</option><option value="55">55</option>
              </select>
              <div class="ampm-toggle">
                <button type="button" class="ampm-btn active" id="once-am" onclick="setAmPm('once','am')">AM</button>
                <button type="button" class="ampm-btn"        id="once-pm" onclick="setAmPm('once','pm')">PM</button>
              </div>
            </div>
          </div>
        </div>
        <!-- Auto cleanup (only shown for once) -->
        <div id="s-auto-cleanup" class="hidden" style="margin-top:12px">
          <label class="check-pill on" id="pill-auto-cleanup">
            <input type="checkbox" id="f-auto-cleanup" checked onchange="togglePill(this)">
            &#128465; Remove after firing
          </label>
        </div>

        <div class="cron-preview">
          <span>cron:</span>&nbsp;<b id="cron-val">*/30 * * * *</b>
        </div>
      </div>

      <div class="form-group">
        <label>Notify via</label>
        <div class="check-group" id="notify-group">
          <label class="check-pill" id="pill-desktop">
            <input type="checkbox" value="desktop" onchange="togglePill(this)">
            &#128438; Desktop
          </label>
          <label class="check-pill on" id="pill-popup">
            <input type="checkbox" value="popup" checked onchange="togglePill(this)">
            &#128172; Popup
          </label>
        </div>
      </div>

      <div class="form-group">
        <label>Behaviour</label>
        <label class="check-pill" id="pill-blocking" style="margin-bottom:12px">
          <input type="checkbox" id="f-blocking" value="blocking" onchange="togglePill(this); toggleBlockingFields(this.checked)">
          &#128683; Blocking (full-screen takeover)
        </label>
        <div id="blocking-fields" class="hidden" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
          <div class="form-group" style="flex:1;min-width:100px;margin-bottom:0">
            <label for="f-bduration">Duration (s)</label>
            <input type="text" id="f-bduration" value="7" style="width:80px">
          </div>
          <div class="form-group" style="flex:1;min-width:140px;margin-bottom:0">
            <label>Dismissable</label>
            <label class="check-pill on" id="pill-dismissable">
              <input type="checkbox" id="f-dismissable" checked onchange="togglePill(this)">
              Allow early dismiss
            </label>
          </div>
        </div>
      </div>

      <div class="form-footer">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="button" class="btn btn-ghost" onclick="previewReminder()">&#128064; Preview</button>
        <button type="submit" class="btn btn-primary" id="submit-btn">Add Reminder</button>
      </div>
    </form>
  </div>
</div>

<!-- Toast -->
<div class="toast hidden" id="toast" role="status" aria-live="polite"></div>

<script>
'use strict';

let reminders    = [];
let editingId    = null;
let schedType    = 'interval';
let currentTags  = [];
let collapseState = {};
try { collapseState = JSON.parse(localStorage.getItem('cronbell-collapse') || '{}'); } catch(_) {}

// ── API ──────────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch(path, opts);
  if (res.status === 204) return null;
  return res.json();
}

// ── Render ───────────────────────────────────────────────────────────────────

function toggleGroup(key) {
  collapseState[key] = !collapseState[key];
  try { localStorage.setItem('cronbell-collapse', JSON.stringify(collapseState)); } catch(_) {}
  render();
}

function render() {
  const el = document.getElementById('list');
  if (!reminders.length) {
    el.innerHTML = `
      <div class="empty">
        <div class="empty-icon">⏰</div>
        <h3>No reminders yet</h3>
        <p>Click "New Reminder" to create your first one.</p>
      </div>`;
    return;
  }

  const hasAnyTags = reminders.some(r => r.tags && r.tags.length);
  if (!hasAnyTags) {
    el.innerHTML = `<div class="reminder-list">${reminders.map(cardHTML).join('')}</div>`;
    return;
  }

  // Group by first tag; untagged → key ''
  const groups = {};
  reminders.forEach(r => {
    const key = (r.tags && r.tags.length) ? r.tags[0] : '';
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
  });

  const tagKeys = Object.keys(groups).filter(k => k).sort();
  if (groups['']) tagKeys.push('');

  let html = '<div class="reminder-list">';
  tagKeys.forEach(key => {
    const items     = groups[key];
    const label     = key || 'General';
    const colKey    = key || '__general__';
    const collapsed = !!collapseState[colKey];
    html += `
      <div class="group-header" data-key="${esc(colKey)}" onclick="toggleGroup(this.dataset.key)">
        <span class="group-label">${esc(label)}</span>
        <span class="group-count">${items.length}</span>
        <span class="group-line"></span>
        <span class="group-chevron${collapsed ? ' collapsed' : ''}">▾</span>
      </div>`;
    if (!collapsed) items.forEach(r => { html += cardHTML(r); });
  });
  html += '</div>';
  el.innerHTML = html;
}

function cardHTML(r) {
  const tagBadges = (r.tags || []).map(t =>
    `<span class="badge badge-muted">&#35;${esc(t)}</span>`
  ).join('');
  return `
  <div class="card${r.enabled ? '' : ' disabled'}" id="card-${r.id}">
    <div class="card-stripe" style="${r.blocking ? 'background:#ef4444' : ''}"></div>
    <div class="card-body">
      <div class="card-name">${esc(r.name)}</div>
      <div class="card-msg">${esc(r.message)}</div>
      <div class="card-meta">
        ${r.one_off
          ? `<span class="badge badge-once">&#128197; ${esc(r.schedule_label)}</span>`
          : `<span class="badge badge-accent">&#9200; ${esc(r.schedule_label)}</span>`}
        ${r.blocking ? `<span class="badge badge-blocking">&#128683; ${r.blocking_duration || 7}s</span>` : `<span class="badge badge-muted">${notifyViaLabel(r.notify_via || ['popup'])}</span>`}
        ${r.fired ? `<span class="badge badge-fired">Fired</span>` : `<span class="badge badge-muted">${r.enabled ? 'Active' : 'Paused'}</span>`}
        ${tagBadges}
      </div>
    </div>
    <div class="card-actions">
      <label class="toggle" title="${r.enabled ? 'Pause' : 'Enable'}">
        <input type="checkbox" ${r.enabled ? 'checked' : ''} onchange="onToggle('${r.id}', this.checked)">
        <div class="toggle-track"></div>
      </label>
      <button class="icon-btn" title="Edit"   onclick="openEdit('${r.id}')">&#9998;</button>
      <button class="icon-btn del" title="Delete" onclick="onDelete('${r.id}')">&#128465;</button>
    </div>
  </div>`;
}

// ── Tags ──────────────────────────────────────────────────────────────────────

function renderTagPills() {
  const wrap  = document.getElementById('tag-input-wrap');
  const input = document.getElementById('tag-text-input');
  wrap.querySelectorAll('.tag-pill-input').forEach(p => p.remove());
  currentTags.forEach((tag, i) => {
    const pill = document.createElement('span');
    pill.className = 'tag-pill-input';
    pill.innerHTML = `${esc(tag)}<span class="tag-pill-remove" onclick="removeTag(${i})">&#10005;</span>`;
    wrap.insertBefore(pill, input);
  });
}

function updateTagSuggestions() {
  const el = document.getElementById('tag-suggestions');
  if (!el) return;
  const typed    = (document.getElementById('tag-text-input').value || '').toLowerCase();
  const allTags  = [...new Set(reminders.flatMap(r => r.tags || []))];
  const filtered = allTags.filter(t => !currentTags.includes(t) && (!typed || t.includes(typed)));
  el.innerHTML   = filtered.map(t =>
    `<span class="tag-suggestion" onclick="selectSuggestion('${esc(t)}')">${esc(t)}</span>`
  ).join('');
}

function selectSuggestion(tag) {
  document.getElementById('tag-text-input').value = '';
  addTag(tag);
}

function addTag(raw) {
  const tag = raw.trim().toLowerCase().replace(/[,#\s]+/g, '-').replace(/^-|-$/g, '');
  if (!tag || currentTags.includes(tag)) return;
  currentTags.push(tag);
  renderTagPills();
  updateTagSuggestions();
}

function removeTag(i) {
  currentTags.splice(i, 1);
  renderTagPills();
  updateTagSuggestions();
}

function tagKeydown(e) {
  const input = e.target;
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    if (input.value.trim()) { addTag(input.value); input.value = ''; }
  } else if (e.key === 'Backspace' && !input.value && currentTags.length) {
    removeTag(currentTags.length - 1);
  }
}

function tagInputHandler(e) {
  if (e.target.value.includes(',')) {
    e.target.value.split(',').forEach(p => addTag(p));
    e.target.value = '';
  } else {
    updateTagSuggestions();
  }
}

function getTags()     { return [...currentTags]; }
function setTags(tags) { currentTags = [...(tags || [])]; renderTagPills(); updateTagSuggestions(); }

// ── Notify-via helpers ───────────────────────────────────────────────────────

function togglePill(cb) {
  cb.closest('.check-pill').classList.toggle('on', cb.checked);
}

function getNotifyVia() {
  return [...document.querySelectorAll('#notify-group input:checked')].map(x => x.value);
}

function setNotifyVia(via = ['popup']) {
  document.querySelectorAll('#notify-group input').forEach(cb => {
    cb.checked = via.includes(cb.value);
    cb.closest('.check-pill').classList.toggle('on', cb.checked);
  });
}

function toggleBlockingFields(show) {
  const el = document.getElementById('blocking-fields');
  el.classList.toggle('hidden', !show);
  if (show) el.style.display = 'flex'; else el.style.display = '';
}

function notifyViaLabel(via = []) {
  const icons = { desktop: '&#128438;', popup: '&#128172;' };
  return via.map(v => icons[v] || v).join(' ') || '&#128172;';
}

function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Schedule helpers ──────────────────────────────────────────────────────────

function p2(n) { return String(n).padStart(2, '0'); }

function toggleDay(btn) { btn.classList.toggle('on'); updatePreview(); }

function setSelectedDays(days) {
  document.querySelectorAll('#s-days .day-pill').forEach(p => {
    p.classList.toggle('on', days.includes(p.dataset.day));
  });
}

function getSelectedDays() {
  return [...document.querySelectorAll('#s-days .day-pill.on')].map(p => p.dataset.day);
}

function setAmPm(prefix, val) {
  document.getElementById(`${prefix}-am`).classList.toggle('active', val === 'am');
  document.getElementById(`${prefix}-pm`).classList.toggle('active', val === 'pm');
  updatePreview();
}

function setTimePicker(prefix, h24, m) {
  const ispm = h24 >= 12;
  let h12 = h24 % 12;
  if (h12 === 0) h12 = 12;
  const mRounded = Math.round(m / 5) * 5 % 60;
  document.getElementById(`${prefix}-hour`).value = String(h12);
  document.getElementById(`${prefix}-min`).value  = String(mRounded);
  setAmPm(prefix, ispm ? 'pm' : 'am');
}

function getTimePicker(prefix) {
  const h12  = parseInt(document.getElementById(`${prefix}-hour`).value) || 9;
  const m    = parseInt(document.getElementById(`${prefix}-min`).value)  || 0;
  const ispm = document.getElementById(`${prefix}-pm`).classList.contains('active');
  const h24  = h12 % 12 + (ispm ? 12 : 0);
  return [h24, m];
}

function buildDayLabel(days, h24, m) {
  const ispm  = h24 >= 12;
  let   h12   = h24 % 12;
  if (h12 === 0) h12 = 12;
  const time  = `${h12}:${p2(m)} ${ispm ? 'PM' : 'AM'}`;
  const names = {0:'Sun', 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat'};
  const sorted = [...days].map(Number).sort((a, b) => a - b);
  if (sorted.length === 7) return `Daily at ${time}`;
  if (sorted.length === 5 && sorted.join(',') === '1,2,3,4,5') return `Weekdays at ${time}`;
  if (sorted.length === 1) return `${names[sorted[0]]}s at ${time}`;
  return sorted.map(d => names[d]).join(', ') + ` at ${time}`;
}

function buildCron() {
  switch (schedType) {
    case 'interval': {
      const val  = Math.max(1, parseInt(document.getElementById('f-ival').value) || 1);
      const unit = document.getElementById('f-iunit').value;
      if (unit === 'min') return [`*/${val} * * * *`, `Every ${val} min${val>1?'s':''}`];
      return [`0 */${val} * * *`, `Every ${val} hour${val>1?'s':''}`];
    }
    case 'days': {
      const days = getSelectedDays();
      if (!days.length) return ['* * * * *', 'Days — pick at least one'];
      const [h, m] = getTimePicker('days');
      const sorted = [...days].map(Number).sort((a, b) => a - b);
      const dayStr = sorted.length === 7 ? '*' : sorted.join(',');
      return [`${m} ${h} * * ${dayStr}`, buildDayLabel(days, h, m)];
    }
    case 'custom': {
      const c = (document.getElementById('f-cron').value.trim()) || '* * * * *';
      return [c, `Custom: ${c}`];
    }
    case 'once': {
      const d = document.getElementById('f-once-date').value;
      if (!d) return [null, 'Once — pick a date'];
      const [h, m] = getTimePicker('once');
      const dt  = new Date(`${d}T${p2(h)}:${p2(m)}`);
      const fmt = dt.toLocaleDateString('en-GB', {day:'numeric', month:'short', year:'numeric'});
      const ispm = h >= 12;
      let   h12  = h % 12; if (h12 === 0) h12 = 12;
      return [null, `Once on ${fmt} at ${h12}:${p2(m)} ${ispm ? 'PM' : 'AM'}`];
    }
  }
}

function getFireAt() {
  const d = document.getElementById('f-once-date').value;
  if (!d) return null;
  const [h, m] = getTimePicker('once');
  return `${d}T${p2(h)}:${p2(m)}:00`;
}

function updatePreview() {
  const [cron, label] = buildCron();
  document.getElementById('cron-val').textContent = schedType === 'once' ? label : (cron || '');
}

function setSched(type) {
  schedType = type;
  ['interval','days','custom','once'].forEach(t => {
    document.getElementById(`s-${t}`).classList.toggle('hidden', t !== type);
  });
  document.getElementById('s-auto-cleanup').classList.toggle('hidden', type !== 'once');
  document.querySelectorAll('.seg-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.t === type);
  });
  updatePreview();
}

function populateSchedule(cron, r = null) {
  if (r && r.one_off) {
    setSched('once');
    if (r.fire_at) {
      document.getElementById('f-once-date').value = r.fire_at.substring(0, 10);
      setTimePicker('once', parseInt(r.fire_at.substring(11, 13)), parseInt(r.fire_at.substring(14, 16)));
    }
    const ac = r.auto_cleanup !== false;
    document.getElementById('f-auto-cleanup').checked = ac;
    document.getElementById('pill-auto-cleanup').classList.toggle('on', ac);
    updatePreview();
    return;
  }

  const iMin      = cron.match(/^\*\/(\d+) \* \* \* \*$/);
  const iHr       = cron.match(/^0 \*\/(\d+) \* \* \*$/);
  const daysMatch = cron.match(/^(\d+) (\d+) \* \* ([\d,*-]+)$/);

  if (iMin) {
    setSched('interval');
    document.getElementById('f-ival').value  = iMin[1];
    document.getElementById('f-iunit').value = 'min';
  } else if (iHr) {
    setSched('interval');
    document.getElementById('f-ival').value  = iHr[1];
    document.getElementById('f-iunit').value = 'hr';
  } else if (daysMatch) {
    setSched('days');
    setTimePicker('days', +daysMatch[2], +daysMatch[1]);
    const spec       = daysMatch[3];
    const activeDays = spec === '*'   ? ['0','1','2','3','4','5','6']
                     : spec === '1-5' ? ['1','2','3','4','5']
                     : spec.split(',');
    setSelectedDays(activeDays);
  } else {
    setSched('custom');
    document.getElementById('f-cron').value = cron;
  }

  updatePreview();
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(r = null, prefill = null) {
  editingId = r ? r.id : null;
  document.getElementById('modal-title').textContent = r ? 'Edit Reminder' : 'New Reminder';
  document.getElementById('submit-btn').textContent  = r ? 'Save Changes'  : 'Add Reminder';
  document.getElementById('f-name').value    = r ? r.name    : (prefill ? prefill.name    : '');
  document.getElementById('f-message').value = r ? r.message : (prefill ? prefill.message : '');

  setTags(r ? (r.tags || []) : []);
  if (r) { populateSchedule(r.cron, r); }
  else   { setSched('interval'); document.getElementById('f-ival').value='30'; document.getElementById('f-iunit').value='min'; setSelectedDays(['1','2','3','4','5']); updatePreview(); }
  setNotifyVia(r ? (r.notify_via || ['popup']) : ['popup']);

  const blocking = r ? !!r.blocking : false;
  const dismissable = r ? (r.dismissable !== false) : true;
  document.getElementById('f-blocking').checked = blocking;
  document.getElementById('pill-blocking').classList.toggle('on', blocking);
  toggleBlockingFields(blocking);
  document.getElementById('f-bduration').value = r ? (r.blocking_duration || 7) : 7;
  document.getElementById('f-dismissable').checked = dismissable;
  document.getElementById('pill-dismissable').classList.toggle('on', dismissable);

  document.getElementById('overlay').classList.remove('hidden');
  document.getElementById('f-name').focus();
}

function openEdit(id) {
  const r = reminders.find(x => x.id === id);
  if (r) openModal(r);
}

function closeModal() {
  document.getElementById('overlay').classList.add('hidden');
  editingId = null;
}

function overlayClick(e) {
  if (e.target === document.getElementById('overlay')) closeModal();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── CRUD ──────────────────────────────────────────────────────────────────────

async function previewReminder() {
  const via = getNotifyVia();
  await api('POST', '/api/preview', {
    name:              document.getElementById('f-name').value.trim()    || 'Preview',
    message:           document.getElementById('f-message').value.trim() || 'Preview notification',
    notify_via:        via.length ? via : ['popup'],
    blocking:          document.getElementById('f-blocking').checked,
    blocking_duration: parseInt(document.getElementById('f-bduration').value) || 7,
    dismissable:       document.getElementById('f-dismissable').checked,
  });
  toast('Preview fired');
}

async function saveReminder(e) {
  e.preventDefault();
  const [cron, schedule_label] = buildCron();
  const isOnce = schedType === 'once';
  const data = {
    name:              document.getElementById('f-name').value.trim(),
    message:           document.getElementById('f-message').value.trim(),
    cron:              isOnce ? null : cron,
    schedule_label,
    notify_via:        getNotifyVia(),
    blocking:          document.getElementById('f-blocking').checked,
    blocking_duration: parseInt(document.getElementById('f-bduration').value) || 7,
    dismissable:       document.getElementById('f-dismissable').checked,
    one_off:           isOnce,
    fire_at:           isOnce ? getFireAt() : null,
    auto_cleanup:      isOnce ? document.getElementById('f-auto-cleanup').checked : false,
    tags:              getTags(),
    enabled: true,
  };
  if (!data.name || !data.message) return;

  if (editingId) {
    await api('PUT', `/api/reminders/${editingId}`, data);
    toast('Reminder updated');
  } else {
    await api('POST', '/api/reminders', data);
    toast('Reminder created');
  }
  closeModal();
  fetchAll();
}

async function onDelete(id) {
  if (!confirm('Delete this reminder?')) return;
  await api('DELETE', `/api/reminders/${id}`);
  toast('Reminder deleted');
  fetchAll();
}

async function onToggle(id, enabled) {
  await api('PUT', `/api/reminders/${id}`, { enabled });
  const r = reminders.find(x => x.id === id);
  if (r) r.enabled = enabled;
  render();
  toast(enabled ? 'Reminder enabled' : 'Reminder paused');
}

// ── Toast ─────────────────────────────────────────────────────────────────────

let toastTimer;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 2800);
}

// ── Theme ─────────────────────────────────────────────────────────────────────

function initTheme() {
  const saved = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  document.getElementById('theme-btn').textContent = saved === 'dark' ? '☀' : '🌙';
}

function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  document.getElementById('theme-btn').textContent = next === 'dark' ? '☀' : '🌙';
}

// ── Boot ──────────────────────────────────────────────────────────────────────
let followUpHandled = false;

initTheme();

async function fetchAll() {
  reminders = await api('GET', '/api/reminders');
  render();
  if (!followUpHandled) {
    followUpHandled = true;
    const p = new URLSearchParams(location.search);
    if (p.get('follow_up')) {
      openModal(null, { name: p.get('name') || '', message: p.get('message') || '' });
    }
  }
}

fetchAll();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # suppress access logs

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/reminders":
            self.send_json(load())
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/reminders":
            data = load()
            r = self.read_json()
            r["id"]         = str(uuid.uuid4())
            r["created_at"] = datetime.now().isoformat()
            r.setdefault("enabled", True)
            data.append(r)
            save(data)
            self.send_json(r, 201)
        elif path == "/api/preview":
            r           = self.read_json()
            name        = r.get("name") or "Preview"
            msg         = r.get("message") or "Preview notification"
            via         = ",".join(r.get("notify_via") or ["popup"])
            blocking    = "true" if r.get("blocking") else "false"
            duration    = str(r.get("blocking_duration") or 7)
            dismissable = "true" if r.get("dismissable", True) else "false"
            subprocess.Popen(
                [NOTIFY_SCRIPT, name, msg, via, blocking, duration, dismissable, "false", ""],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.send_json({"ok": True})
        else:
            self.send_response(404); self.end_headers()

    def do_PUT(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        # api / reminders / <id>
        if len(parts) == 3 and parts[:2] == ["api", "reminders"]:
            rid  = parts[2]
            data = load()
            updates = self.read_json()
            for r in data:
                if r["id"] == rid:
                    r.update(updates)
                    save(data)
                    self.send_json(r)
                    return
            self.send_response(404); self.end_headers()
        else:
            self.send_response(404); self.end_headers()

    def do_DELETE(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "reminders"]:
            rid  = parts[2]
            data = [r for r in load() if r["id"] != rid]
            save(data)
            self.send_response(204); self.end_headers()
        else:
            self.send_response(404); self.end_headers()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(NOTIFY_SCRIPT):
        print(f"Warning: notify.sh not found at {NOTIFY_SCRIPT}", file=sys.stderr)
    else:
        os.chmod(NOTIFY_SCRIPT, 0o755)

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Reminders running → http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
