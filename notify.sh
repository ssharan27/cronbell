#!/bin/bash
TITLE="${1:-Reminder}"
MESSAGE="${2:-You have a reminder!}"
NOTIFY_VIA="${3:-popup}"
BLOCKING="${4:-false}"
BLOCKING_DURATION="${5:-7}"
DISMISSABLE="${6:-true}"
ONE_OFF="${7:-false}"
REMINDER_ID="${8:-}"

USER_ID=$(id -u)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve DISPLAY from running user processes if not set
if [ -z "$DISPLAY" ]; then
    for pid in $(pgrep -u "$USER_ID" 2>/dev/null | head -30); do
        d=$(cat /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | grep '^DISPLAY=' | head -1 | cut -d= -f2-)
        if [ -n "$d" ]; then
            export DISPLAY="$d"
            break
        fi
    done
    export DISPLAY="${DISPLAY:-:0}"
fi

if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${USER_ID}/bus"
fi

if [[ "$BLOCKING" == "true" ]]; then
    # Full-screen takeover — skips desktop/popup
    python3 "$SCRIPT_DIR/blocker.py" "$TITLE" "$MESSAGE" "$NOTIFY_VIA" "$BLOCKING" "$BLOCKING_DURATION" "$DISMISSABLE" "$ONE_OFF" "$REMINDER_ID" &
else
    # System tray notification
    if [[ "$NOTIFY_VIA" == *"desktop"* ]] && command -v notify-send &>/dev/null; then
        notify-send --urgency=normal --icon=appointment-new "$TITLE" "$MESSAGE" 2>/dev/null || true
    fi
    # Positioned popup with snooze + dismiss (bottom-right)
    if [[ "$NOTIFY_VIA" == *"popup"* ]]; then
        python3 "$SCRIPT_DIR/popup.py" "$TITLE" "$MESSAGE" "$NOTIFY_VIA" "$BLOCKING" "$BLOCKING_DURATION" "$DISMISSABLE" "$ONE_OFF" "$REMINDER_ID" &
    fi
fi
