#!/bin/bash
set -e
echo "Installing ScreenTrackerTray..."

# Directories
BIN="$HOME/.local/bin"
LIB="$HOME/.local/lib/screentray"
SYSTEMD_USER="$HOME/.config/systemd/user"

mkdir -p "$BIN"
mkdir -p "$LIB"
mkdir -p "$SYSTEMD_USER"

# Copy Python package
cp -r screentray/* "$LIB/"

# Wrapper scripts using -m to support relative imports
cat > "$BIN/screentracker" <<'EOF'
#!/bin/bash
python3 "$HOME/.local/lib/screentray/screentracker.py" "$@"
EOF

cat > "$BIN/screentray" <<'EOF'
#!/bin/bash
python3 -m screentray.main "$@"
EOF

chmod +x "$BIN/screentracker" "$BIN/screentray"

# Copy systemd service files
cp systemd/user/screentracker.service "$SYSTEMD_USER/"
cp systemd/user/screentray.service "$SYSTEMD_USER/"

# Copy screenstats
cp ./screenstats.sh "$BIN/screenstats"
chmod +x "$BIN/screenstats"

# Reload and enable services
systemctl --user daemon-reload
systemctl --user enable --now screentracker.service
systemctl --user enable --now screentray.service

# Wait a moment
sleep 1

# Check if tray is running
if pgrep -f "python3 -m screentray.main" > /dev/null; then
    echo "Tray icon is running."
else
    echo "Warning: Tray icon process not detected."
    echo "You may need to check your DISPLAY/XAUTHORITY environment or run 'screentray' manually."
fi

echo "Installation complete!"
echo "Tracker logs to ~/.local/share/screentracker.db"
echo "Use 'screenstats' to view usage summaries."
