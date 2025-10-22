#!/bin/bash
set -e
echo "Installing ScreenTrackerTray..."

# directories
BIN="$HOME/.local/bin"
LIB="$HOME/.local/lib/screentray"
SYSTEMD_USER="$HOME/.config/systemd/user"

mkdir -p "$BIN"
mkdir -p "$LIB"
mkdir -p "$SYSTEMD_USER"

# copy Python package
cp -r screentray/* "$LIB/"

# wrapper scripts using -m to support relative imports
cat > "$BIN/screentracker" <<'EOF'
#!/bin/bash
python3 "$HOME/.local/lib/screentray/screentracker.py" "$@"
EOF

cat > "$BIN/screentray" <<'EOF'
#!/bin/bash
python3 -m screentray.main "$@"
EOF

chmod +x "$BIN/screentracker" "$BIN/screentray"

# copy systemd services
cp systemd/user/screentracker.service "$SYSTEMD_USER/"

# Update tray service to use python -m
cat > "$SYSTEMD_USER/screentray.service" <<'EOF'
[Unit]
Description=ScreenTracker Tray App
After=graphical-session.target plasma-workspace.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -m screentray.main
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# reload systemd, enable + start services
systemctl --user daemon-reload
systemctl --user enable --now screentracker.service
systemctl --user enable --now screentray.service

echo "Installation complete!"
echo "Tracker logs to ~/.local/share/screentracker.db"
echo "Tray icon is running; click to view stats."
