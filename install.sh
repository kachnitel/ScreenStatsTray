#!/bin/bash
set -e
echo "Installing ScreenTrackerTray..."

INSTALL_WEB_FLAG=false
DEV_MODE=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --with-web|-w)
            INSTALL_WEB_FLAG=true
            ;;
        --dev)
            DEV_MODE=true
            ;;
    esac
done

# Directories
BIN="$HOME/.local/bin"
LIB="$HOME/.local/lib/screentray"
SYSTEMD_USER="$HOME/.config/systemd/user"

mkdir -p "$BIN"
mkdir -p "$LIB"
mkdir -p "$SYSTEMD_USER"

# Copy or symlink Python package
if [[ "$DEV_MODE" == true ]]; then
    echo "Dev mode: creating symlinks to current directory..."
    find screentray -type f | while read -r f; do
        dest="$LIB/${f#screentray/}"
        mkdir -p "$(dirname "$dest")"
        ln -sf "$(realpath "$f")" "$dest"
    done
else
    echo "Installing to {$LIB}..."
    cp -r screentray/* "$LIB/"
fi

# --- Initialize/Update SQLite database ---
echo "Initializing/updating SQLite database..."
python3 -m screentray.db_init

# Wrapper scripts using -m to support relative imports
cat > "$BIN/screentracker" <<'EOF'
#!/bin/bash
python3 -m screentray.screentracker "$@"
EOF

cat > "$BIN/screentray" <<'EOF'
#!/bin/bash
python3 -m screentray.main "$@"
EOF

chmod +x "$BIN/screentracker" "$BIN/screentray"

# Copy or symlink systemd service files
for svc in screentracker screentray; do
    if [[ "$DEV_MODE" == true ]]; then
        ln -sf "$(realpath systemd/user/$svc.service)" "$SYSTEMD_USER/$svc.service"
    else
        cp systemd/user/$svc.service "$SYSTEMD_USER/"
    fi
done

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

# --- Optional Web Interface ---
if [[ "$INSTALL_WEB_FLAG" == true ]]; then
    INSTALL_WEB="y"
else
    echo
    read -p "Do you want to install the optional ScreenStats Web interface? [y/N]: " INSTALL_WEB
fi

if [[ "$INSTALL_WEB" =~ ^[Yy]$ ]]; then
    echo "Checking for Flask dependency..."
    if ! python3 -c "import flask" 2>/dev/null; then
        echo "❌ Flask not found. Install with:"
        echo "  pip install flask"
        echo "Aborting web interface installation."
        exit 1
    fi

    echo "Installing ScreenStats Web interface..."

    if [[ "$DEV_MODE" == true ]]; then
        ln -sf "$(realpath screentray/web/screenstats_web.py)" "$LIB/"
        ln -sf "$(realpath screentray/web/web_static_index.html)" "$LIB/"
    else
        cp screentray/web/screenstats_web.py "$LIB/"
        cp screentray/web/web_static_index.html "$LIB/"
    fi

    # Find an available port (starting at 5050)
    PORT=5050
    while ss -tuln | grep -q ":$PORT "; do
        PORT=$((PORT + 1))
    done
    echo "Using port $PORT"

    # Create launcher script
    cat > "$BIN/screenstats-web" <<EOF
#!/bin/bash
python3 "$HOME/.local/lib/screentray/web/screenstats_web.py" --port $PORT "$@"
EOF
    chmod +x "$BIN/screenstats-web"

    # Copy or symlink systemd service file
    if [[ "$DEV_MODE" == true ]]; then
        ln -sf "$(realpath systemd/user/screenstats-web.service)" "$SYSTEMD_USER/"
    else
        cp systemd/user/screenstats-web.service "$SYSTEMD_USER/"
    fi

    # Enable the service
    systemctl --user daemon-reload
    systemctl --user enable --now screenstats-web.service

    echo
    echo "✅ Web UI running at: http://127.0.0.1:$PORT"
    echo "Check logs: systemctl --user status screenstats-web.service"
else
    echo "Skipping web interface installation."
fi

echo
echo "✅ Installation complete."
