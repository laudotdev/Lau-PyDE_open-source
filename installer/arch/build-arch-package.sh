#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$ROOT/pyproject.toml")"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/lau-pyde-$VERSION"
cp -a "$ROOT"/{assets,core,ui,main.py,launcher.py,pyproject.toml,installer} "$STAGE/lau-pyde-$VERSION/"
cat > "$STAGE/lau-pyde-$VERSION/installer/lau-pyde-bin" <<'EOF'
#!/usr/bin/env bash
exec /usr/bin/python /usr/share/lau-pyde/launcher.py lau "$@"
EOF
chmod +x "$STAGE/lau-pyde-$VERSION/installer/lau-pyde-bin"
tar -C "$STAGE" -czf "$ROOT/installer/arch/lau-pyde-$VERSION.tar.gz" "lau-pyde-$VERSION"
cd "$ROOT/installer/arch"
makepkg -f

