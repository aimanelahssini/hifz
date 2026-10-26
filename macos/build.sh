#!/bin/bash
# Build the native macOS Hifz.app, install it to /Applications, and install the
# `quran` / `hifz` terminal commands that open it.
set -e
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"

echo "[hifz] build: checking tools"
if ! command -v xcodegen >/dev/null; then
    echo "[hifz] build: installing xcodegen via Homebrew"
    brew install xcodegen
fi

echo "[hifz] build: generating AppIcon"
swift tools/make_icon.swift "$(pwd)/Hifz/Assets.xcassets/AppIcon.appiconset"

echo "[hifz] build: exporting quran.json"
python3 tools/export_quran.py
echo "[hifz] build: bundling translations"
mkdir -p Hifz/Resources/trans
rsync -a --delete --include='*.txt' --exclude='*' \
    "$ROOT/hifz/data/trans/" Hifz/Resources/trans/

echo "[hifz] build: generating Xcode project"
xcodegen generate

echo "[hifz] build: xcodebuild Release"
xcodebuild \
    -project Hifz.xcodeproj \
    -scheme Hifz \
    -configuration Release \
    -derivedDataPath build \
    -destination "platform=macOS,arch=$(uname -m)" \
    ONLY_ACTIVE_ARCH=YES \
    CODE_SIGN_IDENTITY="-" \
    CODE_SIGNING_ALLOWED=YES \
    build

APP="build/Build/Products/Release/Hifz.app"
if [ ! -d "$APP" ]; then
    echo "[hifz] build: Hifz.app not found at $APP" >&2
    exit 1
fi

echo "[hifz] build: installing to /Applications"
rm -rf /Applications/Hifz.app
cp -R "$APP" /Applications/Hifz.app
# Prefer /Applications over the derived-data copy when using `open -a Hifz`.
LSREG=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
"$LSREG" -u "$APP" >/dev/null 2>&1 || true
"$LSREG" -u "${APP/Release/Debug}" >/dev/null 2>&1 || true
"$LSREG" -f -R -trusted /Applications/Hifz.app >/dev/null 2>&1 || true

# CLI: copy the Python package so `quran` / `hifz` work, and open the native app.
CLI_DIR="$HOME/Library/Application Support/Hifz/cli"
echo "[hifz] build: installing CLI to $CLI_DIR"
mkdir -p "$CLI_DIR"
rm -rf "$CLI_DIR/hifz" "$CLI_DIR/bin"
cp -R "$ROOT/hifz" "$CLI_DIR/hifz"
find "$CLI_DIR/hifz" -name __pycache__ -prune -exec rm -rf {} +
mkdir -p "$CLI_DIR/bin"
cat > "$CLI_DIR/bin/quran" <<'EOF'
#!/bin/sh
# Resolve this script even when invoked through a symlink.
SRC="$0"
while [ -L "$SRC" ]; do
    DIR="$(cd "$(dirname "$SRC")" && pwd)"
    SRC="$(readlink "$SRC")"
    case "$SRC" in /*) ;; *) SRC="$DIR/$SRC" ;; esac
done
HERE="$(cd "$(dirname "$SRC")/.." && pwd)"
export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m hifz.cli "$@"
EOF
cat > "$CLI_DIR/bin/hifz" <<'EOF'
#!/bin/sh
SRC="$0"
while [ -L "$SRC" ]; do
    DIR="$(cd "$(dirname "$SRC")" && pwd)"
    SRC="$(readlink "$SRC")"
    case "$SRC" in /*) ;; *) SRC="$DIR/$SRC" ;; esac
done
HERE="$(cd "$(dirname "$SRC")/.." && pwd)"
export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 -m hifz.cli --open "$@"
EOF
chmod +x "$CLI_DIR/bin/quran" "$CLI_DIR/bin/hifz"

# Prefer a directory already on PATH.
BIN=""
for d in "$HOME/.local/bin" /opt/homebrew/bin /usr/local/bin; do
    case ":$PATH:" in
        *":$d:"*) BIN="$d"; break ;;
    esac
done
if [ -z "$BIN" ]; then
    BIN="$HOME/.local/bin"
    mkdir -p "$BIN"
    echo "[hifz] build: created $BIN — add it to your PATH"
fi
mkdir -p "$BIN"
ln -sf "$CLI_DIR/bin/quran" "$BIN/quran"
ln -sf "$CLI_DIR/bin/hifz" "$BIN/hifz"

echo "[hifz] build: done"
echo "  App:  /Applications/Hifz.app"
echo "  CLI:  $BIN/quran  $BIN/hifz"
echo "Open with: open -a Hifz   or   quran 56"
