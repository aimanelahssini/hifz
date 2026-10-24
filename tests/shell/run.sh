#!/bin/bash
# Runs Hifz and its extension with a test driver in a throwaway headless GNOME Shell.
# Settings, progress and the audio cache go to a temp folder, never to the real ones, and
# the audio goes to a fakesink, so nothing is heard.
#   tests/shell/run.sh [OUT_DIR]        results.txt and screenshots land in OUT_DIR
# MODE=demo records the frames for the demo video instead of running the checks.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
T="$(mktemp -d)"
OUT="${1:-$T/out}"
rm -f "$OUT/app.log" "$OUT/results.txt" 2>/dev/null || true
mkdir -p "$T"/{home,config/glib-2.0/settings,data/gnome-shell/extensions,state,cache,rt} "$OUT"
chmod 700 "$T/rt"
cp -r "$REPO/extension/hifz@aimanelahssini" "$HERE/hifz-test@tests" "$T/data/gnome-shell/extensions/"
# Reuse downloaded recitations between runs so tests don't hammer the server.
mkdir -p "$HOME/.cache/hifz-tests" && ln -s "$HOME/.cache/hifz-tests" "$T/cache/hifz"
cat > "$T/config/glib-2.0/settings/keyfile" <<KEY
[org/gnome/shell]
enabled-extensions=['hifz@aimanelahssini', 'hifz-test@tests']
disable-user-extensions=false
welcome-dialog-last-shown-version='999'

[org/gnome/desktop/interface]
color-scheme='prefer-dark'
enable-hot-corners=false
${BG:+
[org/gnome/desktop/background]
picture-uri='file://$BG'
picture-uri-dark='file://$BG'
picture-options='zoom'}
KEY
# A neutral prompt for the terminal in the demo (no user or host name).
printf '%s\n' "PS1='\$ '" 'PROMPT_COMMAND=' 'unset PROMPT_COMMAND' > "$T/home/.bashrc"
cp "$T/home/.bashrc" "$T/home/.bash_profile"
rm -f "$OUT/play.log"
if [ -n "$STATE_JSON" ]; then mkdir -p "$T/state/hifz"; cp "$STATE_JSON" "$T/state/hifz/progress.json"; fi
dconf dump / > "$T/dconf-before.txt"
env -u WAYLAND_DISPLAY -u DISPLAY -u DBUS_SESSION_BUS_ADDRESS \
    HOME="$T/home" XDG_CONFIG_HOME="$T/config" XDG_DATA_HOME="$T/data" XDG_STATE_HOME="$T/state" \
    XDG_CACHE_HOME="$T/cache" XDG_RUNTIME_DIR="$T/rt" GSETTINGS_BACKEND=keyfile \
    HIFZ_AUDIO_SINK="fakesink sync=true" HIFZ_REPO="$REPO" HIFZ_OUT="$OUT" HIFZ_MODE="${MODE:-check}" \
    PATH="$REPO/bin:$PATH" MONITOR="${MONITOR:-1440x900}" HIFZ_PLAYLOG="$OUT/play.log" \
    dbus-run-session -- timeout "${TIMEOUT:-300}" "$HERE/session.sh" > "$OUT/shell.log" 2>&1 || true
dconf dump / > "$T/dconf-after.txt"
if diff "$T/dconf-before.txt" "$T/dconf-after.txt" | grep -qiE 'hifz|enabled-extensions'; then
    echo "REAL DCONF CHANGED"
else
    echo "real dconf: no Hifz changes"
fi
cp "$T/state/hifz/progress.json" "$OUT/progress.json" 2>/dev/null || true
grep -E 'JS ERROR|TypeError|ReferenceError|Traceback' "$OUT/shell.log" | head -5 || true
cat "$OUT/results.txt" 2>/dev/null
rm -rf "$T"
