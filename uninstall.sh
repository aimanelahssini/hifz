#!/bin/bash
# Remove Hifz. Your progress (~/.local/state/hifz) is kept unless you pass --all.
set -e
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
UUID=hifz@aimanelahssini
APP=io.github.aimanelahssini.Hifz
python3 - "$UUID" <<'PY'
import ast, subprocess, sys
cur = subprocess.check_output(['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'], text=True)
l = ast.literal_eval(cur.replace('@as ', ''))
if sys.argv[1] in l:
    l.remove(sys.argv[1])
    subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', str(l)], check=True)
PY
systemctl --user disable --now hifz-reminder.timer 2>/dev/null || true
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
rm -f "$UNITS/hifz-reminder.timer" "$UNITS/hifz-reminder.service" "$DATA/dbus-1/services/$APP.service"
systemctl --user daemon-reload 2>/dev/null || true
rm -rf "$DATA/gnome-shell/extensions/$UUID" "$DATA/hifz" "$DATA/applications/$APP.desktop" \
    "$DATA/icons/hicolor/scalable/apps/$APP.svg" "${XDG_CACHE_HOME:-$HOME/.cache}/hifz"
rm -f "$HOME/.local/bin/quran" "$HOME/.local/bin/hifz"
if [ "$1" = "--all" ]; then
    rm -rf "${XDG_STATE_HOME:-$HOME/.local/state}/hifz"
    echo "Hifz and your progress are removed."
else
    echo "Hifz is removed. Your progress is still in ${XDG_STATE_HOME:-$HOME/.local/state}/hifz."
fi
