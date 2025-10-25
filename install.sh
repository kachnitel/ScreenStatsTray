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
LIB_ROOT="$HOME/.local/lib"
LIB_PKG="$LIB_ROOT/screentray" # This is the full path to the package directory
SYSTEMD_USER="$HOME/.config/systemd/user"
SERVICE_SRC="./systemd/user" # Source directory for service files

mkdir -p "$BIN"
mkdir -p "$LIB_ROOT" # Ensure LIB_ROOT exists
mkdir -p "$SYSTEMD_USER"

# --- 1. Python Package Installation ---

if [[ "$DEV_MODE" == true ]]; then
    echo "Dev mode: creating symlink for 'screentray' package..."

    # **FIXED LOGIC:**
    # 1. Remove the old directory or symlink first.
    # 2. Create the symlink directly in LIB_ROOT.
    rm -rf "$LIB_PKG"
    ln -sfn "$(realpath screentray)" "$LIB_ROOT/screentray"

else
    echo "Installing 'screentray' package to $LIB_PKG..."
    # Ensure target is empty before copying
    rm -rf "$LIB_PKG"
    cp -r screentray "$LIB_ROOT/"
fi

# --- 2. Database Initialization ---
echo "Initializing/updating SQLite database..."
# Run this using the installed/symlinked package
python3 -m screentray.db_init

# --- 3. Wrapper Scripts ---
# Simple wrappers to execute the module
echo "Creating wrapper scripts in $BIN..."
cat > "$BIN/screentracker" <<'EOF'
#!/bin/bash
exec python3 -m screentray.screentracker "$@"
EOF

cat > "$BIN/screentray" <<'EOF'
#!/bin/bash
exec python3 -m screentray.main "$@"
EOF

chmod +x "$BIN/screentracker" "$BIN/screentray"

# --- 4. Systemd Service Files (Tracker & Tray) ---
echo "Installing core systemd service files..."
for svc in screentracker screentray; do
    if [[ ! -f "$SERVICE_SRC/$svc.service" ]]; then
        echo "Error: systemd service file not found at $SERVICE_SRC/$svc.service"
        echo "Please ensure all service files are correctly placed."
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

# Wait a moment
sleep 1

# Check if tray is running
if pgrep -f "python3 -m screentray.main" > /dev/null; then
    echo "Tray icon is running."
else
    echo "Warning: Tray icon process not detected. Check systemctl --user status screentray.service"
fi

echo "Tracker logs to ~/.local/share/screentracker.db"

# --- 5. Optional Web Interface ---
if [[ "$INSTALL_WEB_FLAG" == true ]]; then
    INSTALL_WEB="y"
else
    echo
    read -p "Do you want to install the optional ScreenStats Web interface? [y/N]: " INSTALL_WEB
fi

if [[ "$INSTALL_WEB" =~ ^[Yy]$ ]]; then
    WEB_SVC="screenstats-web"
    echo "Checking for Flask dependency..."
    if ! python3 -c "import flask" 2>/dev/null; then
        echo "❌ Flask not found. Install with:"
        echo "  pip install flask"
        echo "Aborting web interface installation."
        # We don't exit the script, just skip web install
    else
        echo "✅ Flask found."

        # Copy or symlink systemd service file
        if [[ ! -f "$SERVICE_SRC/$WEB_SVC.service" ]]; then
            echo "Error: Web service file not found at $SERVICE_SRC/$WEB_SVC.service"
        else
            if [[ "$DEV_MODE" == true ]]; then
                ln -sf "$(realpath "$SERVICE_SRC/$WEB_SVC.service")" "$SYSTEMD_USER/"
            else
                cp "$SERVICE_SRC/$WEB_SVC.service" "$SYSTEMD_USER/"
            fi

            # Enable the service
            systemctl --user daemon-reload
            systemctl --user enable --now $WEB_SVC.service

            echo
            echo "✅ Web UI service enabled. Check logs: systemctl --user status $WEB_SVC.service"
            echo "It runs at port 5050 by default, see the service file for details."
        fi
    fi
else
    echo "Skipping web interface installation."
fi

echo
echo "✅ Installation complete."
