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

echo "Tracker logs to ~/.local/share/screentracker.db"
echo "Use 'screenstats' to view usage summaries."

echo
read -p "Do you want to install the optional ScreenStats Web interface? [y/N]: " INSTALL_WEB

if [[ "$INSTALL_WEB" =~ ^[Yy]$ ]]; then
    echo "Checking for Flask dependency..."
    if ! python3 -c "import flask" 2>/dev/null; then
        echo "Flask not found. Please install it first:"
        echo "  pip install flask"
        echo "Aborting web interface installation."
        exit 0
    fi

    echo "Installing ScreenStats Web interface..."

    # Copy app files (if exist)
    cp screentray/web/screenstats_web.py "$LIB/"
    cp screentray/web/web_static_index.html "$LIB/"

    # Find an available port (starting at 5050)
    PORT=5050
    while ss -tuln | grep -q ":$PORT "; do
        PORT=$((PORT + 1))
    done
    echo "Using port $PORT for the web interface."

    # Create launcher script
    cat > "$BIN/screenstats-web" <<EOF
#!/bin/bash
python3 "$HOME/.local/lib/screentray/web/screenstats_web.py" --port $PORT "$@"
EOF
    chmod +x "$BIN/screenstats-web"

    # Copy systemd service file
    cp systemd/user/screenstats-web.service "$SYSTEMD_USER/"

    # Enable the service
    systemctl --user daemon-reload
    systemctl --user enable --now screenstats-web.service

    echo
    echo "✅ ScreenStats Web interface installed and running."
    echo "Access it at: http://127.0.0.1:$PORT"
    echo "Use 'systemctl --user status screenstats-web.service' for logs."
else
    echo "Skipping web interface installation."
fi

echo
echo "Installation complete!"
