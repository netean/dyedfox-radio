#!/usr/bin/env bash
set -euo pipefail

APP=dyedfox-radio
DEST_LIB=/usr/lib/$APP
DEST_BIN=/usr/bin/$APP
DEST_DESKTOP=/usr/share/applications/$APP.desktop
DEST_ICON_PNG=/usr/share/icons/hicolor/256x256/apps/$APP.png
DEST_ICON_SVG=/usr/share/icons/hicolor/scalable/apps/$APP-tray.svg
DEST_LICENSE=/usr/share/licenses/$APP/LICENSE

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- helpers -----------------------------------------------------------------

info()  { echo "  $*"; }
warn()  { echo "  WARNING: $*" >&2; }
die()   { echo "  ERROR: $*" >&2; exit 1; }

check_cmd() { command -v "$1" &>/dev/null; }

# --- uninstall ---------------------------------------------------------------

if [[ "${1:-}" == "uninstall" ]]; then
    echo "Uninstalling $APP..."
    sudo rm -rf "$DEST_LIB"
    sudo rm -f  "$DEST_BIN" "$DEST_DESKTOP" "$DEST_ICON_PNG" "$DEST_ICON_SVG"
    sudo rm -rf "/usr/share/licenses/$APP"
    check_cmd update-desktop-database && sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    check_cmd gtk-update-icon-cache   && sudo gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
    echo "Done."
    exit 0
fi

# --- preflight ---------------------------------------------------------------

echo "Installing $APP..."

[[ $EUID -ne 0 ]] || die "Do not run as root — the script will call sudo where needed."

check_cmd python3 || die "python3 not found."
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" \
    || die "Python 3.10 or newer required."

check_cmd pip3 || die "pip3 not found. Install python3-pip for your distro."

# Warn about system-level deps that pip can't provide
python3 -c "import dbus" 2>/dev/null \
    || warn "python-dbus not found. Install: python3-dbus (Debian/Ubuntu/Fedora)"
python3 -c "import gobject" 2>/dev/null \
    || warn "python-gobject not found. Install: python3-gi (Debian/Ubuntu) or python3-gobject (Fedora)"

# Check GStreamer
python3 -c "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst" 2>/dev/null \
    || warn "GStreamer not found. Install: gstreamer1.0-plugins-base python3-gi (Debian/Ubuntu) or gstreamer1-plugins-base python3-gobject (Fedora)"

# --- pip dependencies --------------------------------------------------------

info "Installing Python dependencies..."
pip3 install --user -r "$SRC_DIR/requirements.txt"

# --- copy files --------------------------------------------------------------

info "Copying application files..."
sudo install -dm755 "$DEST_LIB"
sudo cp -r "$SRC_DIR"/api "$SRC_DIR"/data "$SRC_DIR"/player \
           "$SRC_DIR"/tray "$SRC_DIR"/ui "$SRC_DIR"/assets \
           "$SRC_DIR"/main.py "$DEST_LIB/"

info "Installing icons..."
sudo install -Dm644 "$SRC_DIR/assets/icons/$APP.png"      "$DEST_ICON_PNG"
sudo install -Dm644 "$SRC_DIR/assets/icons/$APP-tray.svg" "$DEST_ICON_SVG"

info "Installing desktop entry..."
sudo install -Dm644 "$SRC_DIR/$APP.desktop" "$DEST_DESKTOP"

info "Installing license..."
sudo install -Dm644 "$SRC_DIR/LICENSE" "$DEST_LICENSE"

info "Creating launcher..."
sudo tee "$DEST_BIN" > /dev/null << 'LAUNCHER'
#!/bin/sh
exec python3 /usr/lib/dyedfox-radio/main.py "$@"
LAUNCHER
sudo chmod 755 "$DEST_BIN"

# --- post-install ------------------------------------------------------------

check_cmd update-desktop-database && sudo update-desktop-database /usr/share/applications 2>/dev/null || true
check_cmd gtk-update-icon-cache   && sudo gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true

echo "Done. Run '$APP' to start."
