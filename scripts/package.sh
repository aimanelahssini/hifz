#!/bin/bash
# Build downloadable installers for the landing page into site/downloads/.
#   Mac:   Hifz-macOS.dmg   (drag Hifz → Applications)
#          Hifz-macOS.zip   (fallback)
#   Linux: Hifz-linux.tar.gz
#          Hifz-linux-installer.sh  (self-extracting installer)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/site/downloads"
VERSION="$(python3 -c "import sys; sys.path.insert(0,'$ROOT'); from hifz import VERSION; print(VERSION)")"
mkdir -p "$OUT"

echo "[hifz] package: version $VERSION"

# ---------- macOS ----------
if [[ "$(uname)" == Darwin ]]; then
    APP="$ROOT/macos/build/Build/Products/Release/Hifz.app"
    if [ ! -d "$APP" ]; then
        echo "[hifz] package: building macOS app first"
        "$ROOT/macos/build.sh"
    fi
    [ -d "$ROOT/macos/build/Build/Products/Release/Hifz.app" ] \
        && APP="$ROOT/macos/build/Build/Products/Release/Hifz.app"
    [ -d "$APP" ] || APP="/Applications/Hifz.app"
    [ -d "$APP" ] || { echo "[hifz] package: no Hifz.app found" >&2; exit 1; }

    STAGE=$(mktemp -d)
    cp -R "$APP" "$STAGE/Hifz.app"
    # Clear quarantine so first open is smoother when the DMG is signed later;
    # unsigned builds still need right-click → Open the first time.
    xattr -cr "$STAGE/Hifz.app" 2>/dev/null || true

    cat > "$STAGE/Install.txt" <<EOF
Hifz $VERSION for macOS

1. Drag Hifz into Applications.
2. Open it from Applications (or Spotlight).
3. If macOS blocks it the first time: right-click Hifz → Open.
EOF

    ZIP="$OUT/Hifz-macOS.zip"
    rm -f "$ZIP"
    (cd "$STAGE" && zip -qry "$ZIP" Hifz.app Install.txt)
    echo "[hifz] package: wrote $ZIP ($(du -h "$ZIP" | cut -f1))"

    DMG="$OUT/Hifz-macOS.dmg"
    rm -f "$DMG" "$OUT/.rw.Hifz-macOS.dmg" 2>/dev/null || true
    DMG_STAGE=$(mktemp -d)
    cp -R "$STAGE/Hifz.app" "$DMG_STAGE/Hifz.app"
    if command -v create-dmg >/dev/null; then
        create-dmg \
            --volname "Hifz $VERSION" \
            --volicon "$ROOT/macos/Hifz/Assets.xcassets/AppIcon.appiconset/icon_512.png" \
            --window-pos 200 120 \
            --window-size 620 400 \
            --icon-size 100 \
            --icon "Hifz.app" 150 180 \
            --hide-extension "Hifz.app" \
            --app-drop-link 450 180 \
            --text-size 12 \
            "$DMG" \
            "$DMG_STAGE" || {
                # create-dmg sometimes leaves a valid DMG even with a non-zero exit (Finder blessing).
                [ -f "$DMG" ] || hdiutil create -volname "Hifz $VERSION" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG"
            }
    else
        # Fallback without create-dmg: plain compressed disk image + Applications link.
        ln -s /Applications "$DMG_STAGE/Applications"
        hdiutil create -volname "Hifz $VERSION" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG"
    fi
    rm -rf "$STAGE" "$DMG_STAGE"
    echo "[hifz] package: wrote $DMG ($(du -h "$DMG" | cut -f1))"
else
    for f in Hifz-macOS.dmg Hifz-macOS.zip; do
        if [ -f "$OUT/$f" ]; then
            echo "[hifz] package: keeping existing $f (not on Darwin)"
        else
            echo "[hifz] package: skip $f (not on Darwin)"
        fi
    done
fi

# ---------- Linux tarball ----------
STAGE_PARENT=$(mktemp -d)
STAGE="$STAGE_PARENT/hifz"
mkdir -p "$STAGE"
cp -R "$ROOT/hifz" "$ROOT/bin" "$ROOT/data" "$ROOT/extension" "$STAGE/"
cp "$ROOT/install.sh" "$ROOT/uninstall.sh" "$ROOT/LICENSE" "$ROOT/logo.svg" "$STAGE/"
chmod +x "$STAGE/install.sh" "$STAGE/uninstall.sh" "$STAGE/bin/"*
find "$STAGE" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.DS_Store' -delete 2>/dev/null || true

TAR="$OUT/Hifz-linux.tar.gz"
rm -f "$TAR"
tar -C "$STAGE_PARENT" -czf "$TAR" hifz
echo "[hifz] package: wrote $TAR ($(du -h "$TAR" | cut -f1))"

# Self-extracting installer: one file to download and run.
INSTALLER="$OUT/Hifz-linux-installer.sh"
rm -f "$INSTALLER"
{
    cat <<EOF
#!/bin/bash
# Hifz $VERSION — self-extracting installer for Linux (apt / dnf / pacman / zypper).
set -e
echo "[hifz] installer: Hifz $VERSION"
TMP=\$(mktemp -d)
trap 'rm -rf "\$TMP"' EXIT
ARCHIVE_LINE=\$(awk '/^__HIFZ_ARCHIVE__/ {print NR + 1; exit 0}' "\$0")
tail -n +"\$ARCHIVE_LINE" "\$0" | tar -xz -C "\$TMP"
cd "\$TMP/hifz"
exec bash ./install.sh
__HIFZ_ARCHIVE__
EOF
    cat "$TAR"
} > "$INSTALLER"
chmod +x "$INSTALLER"
echo "[hifz] package: wrote $INSTALLER ($(du -h "$INSTALLER" | cut -f1))"

rm -rf "$STAGE_PARENT"

# Manifest for the site (sizes + version).
python3 - <<PY
import json, os
out = "$OUT"
man = {"version": "$VERSION", "files": {}}
for name in ("Hifz-macOS.dmg", "Hifz-macOS.zip", "Hifz-linux-installer.sh", "Hifz-linux.tar.gz"):
    path = os.path.join(out, name)
    if os.path.isfile(path):
        man["files"][name] = {"bytes": os.path.getsize(path)}
with open(os.path.join(out, "manifest.json"), "w") as f:
    json.dump(man, f, indent=2)
print("[hifz] package: wrote manifest.json")
PY
