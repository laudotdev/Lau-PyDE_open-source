#!/usr/bin/env bash
set -euo pipefail

APP_NAME="lau-pyde"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

printf '[1/5] checking Python and preparing install directories...\n'
command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3 is required." >&2; exit 1; }
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

printf '[2/5] copying Lau-PyDE application files...\n'
rm -rf "$APP_DIR/src"
mkdir -p "$APP_DIR/src"
cp -a "$PROJECT_ROOT"/{assets,core,ui,main.py,launcher.py,pyproject.toml} "$APP_DIR/src/"

printf '[3/5] creating the application virtual environment...\n'
if python3 -c 'import PySide6' >/dev/null 2>&1; then
    python3 -m venv --system-site-packages "$APP_DIR/venv"
    printf '[4/5] installing Lau-PyDE with system PySide6...\n'
    "$APP_DIR/venv/bin/python" -m pip install --no-deps "$APP_DIR/src"
else
    python3 -m venv "$APP_DIR/venv"
    printf '[4/5] installing Lau-PyDE and Python dependencies (this may take a few minutes)...\n'
    "$APP_DIR/venv/bin/python" -m pip install --progress-bar on "$APP_DIR/src"
fi

printf '[5/5] creating launcher and desktop integration...\n'
cat > "$BIN_DIR/lau-pyde" <<EOF
#!/usr/bin/env bash
exec "$APP_DIR/venv/bin/pyde" lau "\$@"
EOF
chmod +x "$BIN_DIR/lau-pyde"
cp "$PROJECT_ROOT/installer/linux/lau-pyde_logo.png" "$ICON_DIR/lau-pyde.png"
desktop_exec="$BIN_DIR/lau-pyde"
desktop_exec="${desktop_exec//\\/\\\\}"
desktop_exec="${desktop_exec//\"/\\\"}"
desktop_exec="${desktop_exec//%/%%}"
LAU_PYDE_EXEC="$desktop_exec" awk '
    /^Exec=/ {
        printf "Exec=\"%s\"\n", ENVIRON["LAU_PYDE_EXEC"]
        next
    }
    { print }
' "$PROJECT_ROOT/installer/linux/lau-pyde.desktop" > "$DESKTOP_DIR/lau-pyde.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
printf 'Installation complete. Ensure %s is on PATH, then launch with: lau-pyde\n' "$BIN_DIR"
