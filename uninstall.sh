#!/bin/bash
set -e
echo "Uninstalling ScreenTrackerTray..."

# Stop and disable systemd services
systemctl --user stop screentracker.service screentray.service screenstats-web.service
systemctl --user disable screentracker.service screentray.service screenstats-web.service

# Remove wrapper scripts
rm -f ~/.local/bin/screentracker
rm -f ~/.local/bin/screentray

# Remove Python package
rm -rf ~/.local/lib/screentray

# Remove systemd service files
rm -f ~/.config/systemd/user/screentracker.service
rm -f ~/.config/systemd/user/screentray.service
rm -f ~/.config/systemd/user/screenstats-web.service

# Reload systemd
systemctl --user daemon-reload

# Optionally remove the database
read -p "Do you want to remove all tracked data (~/.local/share/screentracker.db)? [y/N] " remove_db
if [[ "$remove_db" =~ ^[Yy]$ ]]; then
    rm -f ~/.local/share/screentracker.db
    echo "Database removed."
else
    echo "Database kept."
fi

echo "ScreenTrackerTray uninstalled successfully."
