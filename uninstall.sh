#!/bin/bash
set -e
echo "Uninstalling ScreenTrackerTray..."

# Service file names
SERVICES="screentracker.service screentray.service screenstats-web.service"
BINS="screentracker screentray"

# Stop and disable systemd services
echo "Stopping and disabling systemd services..."
systemctl --user stop $SERVICES || true
systemctl --user disable $SERVICES || true

# Remove wrapper scripts
echo "Removing wrapper scripts..."
for bin in $BINS; do
    rm -f ~/.local/bin/$bin
done

# Remove Python package (the symlink or the copied directory)
echo "Removing Python package..."
# Remove the symlink if in dev mode, or the directory otherwise
rm -rf ~/.local/lib/screentray

# Remove systemd service files
echo "Removing systemd files..."
for svc in $SERVICES; do
    rm -f ~/.config/systemd/user/$svc
done

# Reload systemd
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Optionally remove the database
read -p "Do you want to remove all tracked data (~/.local/share/screentracker.db)? [y/N] " remove_db
if [[ "$remove_db" =~ ^[Yy]$ ]]; then
    rm -f ~/.local/share/screentracker.db
    echo "Database removed."
else
    echo "Database kept."
fi

echo "✅ ScreenTrackerTray uninstalled successfully."
