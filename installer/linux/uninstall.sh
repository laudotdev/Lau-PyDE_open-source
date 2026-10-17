#!/usr/bin/env bash
set -euo pipefail
APP_NAME="lau-pyde"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"
rm -rf "$APP_DIR"
rm -f "$BIN_DIR/lau-pyde" "$DESKTOP_DIR/lau-pyde.desktop" "$ICON_DIR/lau-pyde.png"
echo "Lau-PyDE uninstalled."

