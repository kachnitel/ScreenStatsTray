#!/bin/bash
set -e
echo "Uninstalling ScreenTrackerTray..."

# stop and disable services
systemctl --user stop screentracker.service screentray.service
systemctl --user disable screentracker.service screentray.service

# remove wrapper scripts
rm -f ~/.local/bin/screentracker
rm -f ~/.local/bin/screentray

# remove Python package
rm -rf ~/.local/lib/screentray

# remove systemd service files
rm -f ~/.config/systemd/user/screentracker.service
rm -f ~/.config/systemd/user/screentray.service

# reload systemd
systemctl --user daemon-reload

# optional: remove database
read -p "Do you want to remove all tracked data (~/.local/share/screentracker.db)? [y/N] " remove_db
if [[ "$remove_db" =~ ^[Yy]$ ]]; then
    rm -f ~/.local/share/screentracker.db
    echo "Database removed."
else
    echo "Database kept."
fi

echo "ScreenTrackerTray uninstalled successfully."
