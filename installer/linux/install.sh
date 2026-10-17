#!/usr/bin/env bash
set -euo pipefail

APP_NAME="lau-pyde"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3 is required." >&2; exit 1; }
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$APP_DIR/src"
mkdir -p "$APP_DIR/src"
cp -a "$PROJECT_ROOT"/{assets,core,ui,main.py,launcher.py,pyproject.toml} "$APP_DIR/src/"
if python3 -c 'import PySide6' >/dev/null 2>&1; then
    python3 -m venv --system-site-packages "$APP_DIR/venv"
    "$APP_DIR/venv/bin/python" -m pip install --no-deps "$APP_DIR/src" >/dev/null
else
    python3 -m venv "$APP_DIR/venv"
    "$APP_DIR/venv/bin/python" -m pip install "$APP_DIR/src" >/dev/null
fi

cat > "$BIN_DIR/lau-pyde" <<EOF
#!/usr/bin/env bash
exec "$APP_DIR/venv/bin/pyde" lau "\$@"
EOF
chmod +x "$BIN_DIR/lau-pyde"
cp "$PROJECT_ROOT/installer/linux/lau-pyde_logo.png" "$ICON_DIR/lau-pyde.png"
cp "$PROJECT_ROOT/installer/linux/lau-pyde.desktop" "$DESKTOP_DIR/lau-pyde.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
echo "Lau-PyDE installed. Ensure $BIN_DIR is on PATH, then launch with: lau-pyde"
