# Handoff — cronbell

## Project

Local cron-backed desktop reminder manager. Web UI at `http://localhost:8765`, served by a systemd user service. Reminders are stored in `~/.reminders.json` and synced to crontab on every save. One-off reminders and snooze entries live in `~/.reminders-snooze.json` and are processed every minute by `snooze_checker.py`.

**Repo:** `git@github.com:ssharan27/cronbell.git`  
**Working directory:** `/home/fadmvlhr3/Desktop/playground/notifier/`  
**Service:** `systemctl --user [start|stop|restart|status] reminders`

---

## Current live reminders (as of handoff)

| Name | Schedule | Type |
|------|----------|------|
| Water | Every 30 min | Blocking, non-dismissable, 4s |
| Walk | Every 90 min | Popup |
| Eyes | Every 20 min | Blocking, dismissable, 10s |
| ESOPs Expiry | Daily at 11:00 | Popup |

---

## Architecture

```
reminders.py         HTTP server (port 8765) + embedded HTML/CSS/JS UI
notify.sh            Dispatcher called by cron — routes to popup.py or blocker.py
popup.py             Bottom-right tkinter popup (snooze, dismiss, follow-up)
blocker.py           Full-screen black takeover (snooze, dismiss, follow-up)
snooze_checker.py    Runs every minute via cron:
                       - fires overdue snooze entries from ~/.reminders-snooze.json
                       - fires due one-off reminders from ~/.reminders.json
                       - cleans up fired entries
install.sh           Writes systemd user service and starts it
reminders.service    systemd unit template (INSTALL_DIR replaced by install.sh)
```

### notify.sh arg contract (8 args)
```
$1 TITLE
$2 MESSAGE
$3 NOTIFY_VIA        comma-separated: "popup", "desktop", or "popup,desktop"
$4 BLOCKING          "true" | "false"
$5 BLOCKING_DURATION seconds (integer)
$6 DISMISSABLE       "true" | "false"
$7 ONE_OFF           "true" | "false"
$8 REMINDER_ID       UUID string (used for follow-up URL)
```

### Reminder JSON schema (`~/.reminders.json`)
```json
{
  "id":                "uuid",
  "name":              "string",
  "message":           "string",
  "cron":              "cron expression | null (one-offs)",
  "schedule_label":    "human-readable string",
  "notify_via":        ["popup"] | ["desktop"] | ["popup","desktop"],
  "blocking":          false,
  "blocking_duration": 7,
  "dismissable":       true,
  "one_off":           false,
  "fire_at":           "ISO datetime | null",
  "auto_cleanup":      true,
  "enabled":           true,
  "created_at":        "ISO datetime",
  "fired":             false   // set when one_off + auto_cleanup=false
}
```

### Crontab line format
```
{cron} notify.sh "{name}" "{message}" "{via}" "{blocking}" "{duration}" "{dismissable}" "false" "{id}"
* * * * * python3 {SNOOZE_CHECKER} >> /dev/null 2>&1
```

---

## What was in progress when interrupted

**Task: Simplify the creation UI**

Two changes were requested:
1. **Merge Daily / Weekdays / Weekly into a single "Days" tab** with toggleable day pills (Mon Tue Wed Thu Fri Sat Sun). Default = Mon–Fri selected.
2. **Replace all `<input type="time">` with an AM/PM time picker** — Hour (1–12 select) + Minute (5-min increments select) + AM/PM toggle buttons.

### Progress at interruption
- ✅ **CSS added** — `.day-group`, `.day-pill`, `.day-pill.on`, `.time-picker`, `.ampm-toggle`, `.ampm-btn`, dark mode overrides
- ❌ **HTML not updated** — segment buttons still show 6 tabs (Interval/Daily/Weekdays/Weekly/Custom/Once); s-daily, s-weekdays, s-weekly panels still exist; no s-days panel yet; s-once still uses `<input type="time">`
- ❌ **JS not updated** — buildCron, setSched, populateSchedule still reference the old tab names

### What still needs to be done

#### 1. HTML — replace schedule segment buttons
Replace the 6-button seg-group with 4 buttons:
```html
Interval | Days | Once | Custom
```

#### 2. HTML — remove old panels, add new Days panel
Remove `<div id="s-daily">`, `<div id="s-weekdays">`, `<div id="s-weekly">`.

Add `<div id="s-days">`:
```
Day pills row: [Mon] [Tue] [Wed] [Thu] [Fri] [Sat] [Sun]   (Mon–Fri active by default)
Time row:      At  [hour ▾] : [min ▾]  [AM] [PM]
```

#### 3. HTML — update Once panel
Replace `<input type="time" id="f-once-time">` with the same AM/PM picker component (prefix `once`).

#### 4. JS helper functions to add
```js
// Toggle a day pill on/off
function toggleDay(btn) { btn.classList.toggle('on'); updatePreview(); }

// Set active/inactive state of day pills
function setSelectedDays(days) { /* toggle .on on each .day-pill by data-day */ }

// Read selected day numbers from pills
function getSelectedDays() { /* returns array of strings e.g. ['1','2','3','4','5'] */ }

// Set AM/PM picker values
function setTimePicker(prefix, h24, m) { /* sets hour select, min select, AM/PM button */ }

// Read AM/PM picker values → returns [hour24, minute]
function getTimePicker(prefix) { /* reads hour, min, am/pm → converts to 24h */ }

// Build human-readable label from days + time
function buildDayLabel(days, h24, m) { /* "Weekdays at 9:30 AM", "Mon, Wed, Fri at 2:00 PM", etc. */ }
```

#### 5. JS — update buildCron
Replace `daily`, `weekdays`, `weekly` cases with one `days` case:
```js
case 'days': {
  const days = getSelectedDays();
  const [h, m] = getTimePicker('days');
  const dayStr = days.length === 7 ? '*' : days.sort((a,b)=>a-b).join(',');
  return [`${m} ${h} * * ${dayStr}`, buildDayLabel(days, h, m)];
}
```

#### 6. JS — update setSched
Update the list of panel IDs from `['interval','daily','weekdays','weekly','custom','once']` to `['interval','days','custom','once']`.

#### 7. JS — update populateSchedule
Replace `daily`, `weekdays`, `weekly` regex branches with one `days` branch:
```js
// Match: "M H * * DAY_SPEC" where DAY_SPEC is *, 1-5, 0, 1,2,3 etc.
const daysMatch = cron.match(/^(\d+) (\d+) \* \* ([\d,*-]+)$/);
if (daysMatch) {
  setSched('days');
  setTimePicker('days', +daysMatch[2], +daysMatch[1]);
  const spec = daysMatch[3];
  const activeDays = spec === '*' ? ['0','1','2','3','4','5','6']
    : spec === '1-5' ? ['1','2','3','4','5']
    : spec.split(',');
  setSelectedDays(activeDays);
}
```

Also update the `once` branch to call `setTimePicker('once', h, m)` from `r.fire_at`.

#### 8. JS — update openModal defaults
Change the "new reminder" default from `setSched('interval')` block to also reset the Days picker to Mon–Fri when switching to 'days'.

---

## Docs
- `README.md` — GitHub landing page
- `GETTING_STARTED.md` — first-time user guide
- `docs/reference.md` — full technical reference

## Roadmap
- **v2** — phone push notifications via ntfy.sh, cross-device sync
