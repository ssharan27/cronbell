#!/bin/bash
set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="reminders"
SERVICE_DEST="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

echo "Installing Reminders service..."
echo "  Source : $INSTALL_DIR"

# Ensure systemd user directory exists
mkdir -p "$HOME/.config/systemd/user"

# Write service file with resolved path
sed "s|INSTALL_DIR|${INSTALL_DIR}|g" "$INSTALL_DIR/reminders.service" > "$SERVICE_DEST"

chmod +x "$INSTALL_DIR/notify.sh"

# Reload, enable, start
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
