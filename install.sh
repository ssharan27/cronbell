#!/bin/bash
set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS="$(uname -s)"

chmod +x "$INSTALL_DIR/notify.sh"

if [[ "$OS" == "Darwin" ]]; then
    PYTHON3="$(which python3)"
    PLIST_SRC="$INSTALL_DIR/com.user.reminders.plist"
    PLIST_DEST="$HOME/Library/LaunchAgents/com.user.reminders.plist"

    mkdir -p "$HOME/Library/LaunchAgents"
    sed -e "s|INSTALL_DIR|${INSTALL_DIR}|g" \
        -e "s|PYTHON3|${PYTHON3}|g" \
        "$PLIST_SRC" > "$PLIST_DEST"

    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    launchctl load -w "$PLIST_DEST"

    echo ""
    echo "Done. Reminders is running at http://localhost:8765"
    echo ""
    echo "Useful commands:"
    echo "  launchctl list | grep reminders          # check status"
    echo "  launchctl stop  com.user.reminders        # stop"
    echo "  launchctl start com.user.reminders        # start"
    echo "  tail -f /tmp/reminders.log               # live logs"
    echo ""
    echo "To uninstall:"
    echo "  launchctl unload $PLIST_DEST"
    echo "  rm $PLIST_DEST"
else
    SERVICE_NAME="reminders"
    SERVICE_DEST="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

    echo "Installing Reminders service..."
    echo "  Source : $INSTALL_DIR"

    mkdir -p "$HOME/.config/systemd/user"
    sed "s|INSTALL_DIR|${INSTALL_DIR}|g" "$INSTALL_DIR/reminders.service" > "$SERVICE_DEST"

    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user restart "$SERVICE_NAME"

    echo ""
    echo "Done. Reminders is running at http://localhost:8765"
    echo ""
    echo "Useful commands:"
    echo "  systemctl --user status $SERVICE_NAME     # check status"
    echo "  systemctl --user stop   $SERVICE_NAME     # stop"
    echo "  systemctl --user start  $SERVICE_NAME     # start"
    echo "  journalctl --user -u    $SERVICE_NAME -f  # live logs"
    echo ""
    echo "To uninstall:"
    echo "  systemctl --user disable --now $SERVICE_NAME"
    echo "  rm $SERVICE_DEST"
fi
