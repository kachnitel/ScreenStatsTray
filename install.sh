#!/bin/bash
set -e
echo "Installing ScreenTrackerTray..."

INSTALL_WEB_FLAG=false
INSTALL_APPTRACK_FLAG=false
DEV_MODE=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --with-web|-w)
            INSTALL_WEB_FLAG=true
            ;;
        --with-app-tracker|-a)
            INSTALL_APPTRACK_FLAG=true
            ;;
        --dev)
            DEV_MODE=true
            ;;
    esac
done

# Directories
BIN="$HOME/.local/bin"
LIB_ROOT="$HOME/.local/lib"
LIB_PKG="$LIB_ROOT/screentray"
SYSTEMD_USER="$HOME/.config/systemd/user"
SERVICE_SRC="./systemd/user"

mkdir -p "$BIN"
mkdir -p "$LIB_ROOT"
mkdir -p "$SYSTEMD_USER"

# --- 1. Python Package Installation ---

if [[ "$DEV_MODE" == true ]]; then
    echo "Dev mode: creating symlink for 'screentray' package..."
    rm -rf "$LIB_PKG"
    ln -sfn "$(realpath screentray)" "$LIB_ROOT/screentray"
else
    echo "Installing 'screentray' package to $LIB_PKG..."
    rm -rf "$LIB_PKG"
    cp -r screentray "$LIB_ROOT/"
fi

# --- 2. Database Initialization ---
echo "Initializing/updating SQLite database..."
python3 -m screentray.db_init

# --- 3. Plugin Installation ---
# TODO:
echo "Checking for plugins..."


# --- 4. Wrapper Scripts ---
echo "Creating wrapper scripts in $BIN..."
cat > "$BIN/screentracker" <<'EOF'
#!/bin/bash
exec python3 -m screentray.tracker.main "$@"
EOF

cat > "$BIN/screentray" <<'EOF'
#!/bin/bash
exec python3 -m screentray.tray.main "$@"
EOF

chmod +x "$BIN/screentracker" "$BIN/screentray"

# --- 5. Systemd Service Files (Tracker & Tray) ---
echo "Installing core systemd service files..."
for svc in screentracker screentray; do
    if [[ ! -f "$SERVICE_SRC/$svc.service" ]]; then
        echo "Error: systemd service file not found at $SERVICE_SRC/$svc.service"
        exit 1
    fi

    if [[ "$DEV_MODE" == true ]]; then
        ln -sf "$(realpath "$SERVICE_SRC/$svc.service")" "$SYSTEMD_USER/$svc.service"
    else
        cp "$SERVICE_SRC/$svc.service" "$SYSTEMD_USER/"
    fi
done

# Reload and enable core services
systemctl --user daemon-reload
systemctl --user enable --now screentracker.service
systemctl --user enable --now screentray.service

sleep 1

if pgrep -f "python3 -m screentray.main" > /dev/null; then
    echo "Tray icon is running."
else
    echo "Warning: Tray icon process not detected. Check systemctl --user status screentray.service"
fi

echo "Tracker logs to ~/.local/share/screentracker.db"

echo
echo "✅ Installation complete."
