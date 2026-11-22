#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$ROOT/pyproject.toml")"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
printf '[1/3] preparing Lau-PyDE %s source files...\n' "$VERSION"
mkdir -p "$STAGE/lau-pyde-$VERSION"
cp -a "$ROOT"/{assets,core,ui,main.py,launcher.py,pyproject.toml} "$STAGE/lau-pyde-$VERSION/"
mkdir -p "$STAGE/lau-pyde-$VERSION/installer"
cp -a "$ROOT/installer/linux" "$STAGE/lau-pyde-$VERSION/installer/"
cat > "$STAGE/lau-pyde-$VERSION/installer/lau-pyde-bin" <<'EOF'
#!/usr/bin/env bash
exec /usr/bin/python /usr/share/lau-pyde/launcher.py lau "$@"
EOF
chmod +x "$STAGE/lau-pyde-$VERSION/installer/lau-pyde-bin"
printf '[2/3] creating Arch source archive...\n'
tar -C "$STAGE" -czf "$ROOT/installer/arch/lau-pyde-$VERSION.tar.gz" "lau-pyde-$VERSION"
cd "$ROOT/installer/arch"
printf '[3/3] building Arch package (makepkg will show build progress)...\n'
makepkg -f
printf 'Build complete: %s/installer/arch/lau-pyde-%s-1-any.pkg.tar.zst\n' "$ROOT" "$VERSION"
