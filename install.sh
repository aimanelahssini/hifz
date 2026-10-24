#!/bin/bash
# Install Hifz for the current user: the app, the `quran` and `hifz` commands, the app icon
# and the GNOME Shell extension that keeps the window in the top-right corner.
#   git clone https://github.com/aimanelahssini/hifz && cd hifz && ./install.sh
set -e
cd "$(dirname "$0")"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN="$HOME/.local/bin"
UUID=hifz@aimanelahssini
APP=io.github.aimanelahssini.Hifz

# What it needs: GTK 4, libadwaita and GStreamer (good for MP3 and scaletempo, bad for the
# soundtouch "pitch" element that changes speed without changing the voice).
missing=()
python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')" 2>/dev/null \
    || missing+=(python3-gobject gtk4 libadwaita)
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); \
assert Gst.ElementFactory.find('mpg123audiodec') or Gst.ElementFactory.find('avdec_mp3')" 2>/dev/null \
    || missing+=(gstreamer1-plugins-good)
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); \
assert Gst.ElementFactory.find('pitch')" 2>/dev/null || missing+=(gstreamer1-plugins-bad-free)
if [ ${#missing[@]} -gt 0 ]; then
    if command -v dnf >/dev/null; then
        echo "Installing ${missing[*]}"
        pkexec dnf install -y "${missing[@]}"
    else
        echo "Please install: GTK 4, libadwaita, PyGObject and GStreamer good + bad plugins." >&2
        exit 1
    fi
fi

# The app itself.
rm -rf "$DATA/hifz/hifz"
mkdir -p "$DATA/hifz" "$BIN"
cp -r hifz "$DATA/hifz/"
find "$DATA/hifz" -name __pycache__ -prune -exec rm -rf {} +
cp -r bin "$DATA/hifz/"
ln -sf "$DATA/hifz/bin/quran" "$BIN/quran"
ln -sf "$DATA/hifz/bin/hifz" "$BIN/hifz"
install -Dm644 "data/$APP.desktop" "$DATA/applications/$APP.desktop"
# D-Bus can start Hifz for GNOME (a click on the reminder while Hifz is closed).
mkdir -p "$DATA/dbus-1/services"
printf '[D-BUS Service]\nName=%s\nExec=%s --gapplication-service\n' "$APP" "$DATA/hifz/bin/hifz-service" \
    > "$DATA/dbus-1/services/$APP.service"
dbus-send --session --type=method_call --dest=org.freedesktop.DBus /org/freedesktop/DBus \
    org.freedesktop.DBus.ReloadConfig 2>/dev/null || true
install -Dm644 "data/$APP.svg" "$DATA/icons/hicolor/scalable/apps/$APP.svg"
gtk-update-icon-cache -q -t "$DATA/icons/hicolor" 2>/dev/null || true

# The extension. Only add it to GNOME's enabled list: `gnome-extensions enable` can rewrite
# the list from the running shell's view and drop other extensions.
mkdir -p "$DATA/gnome-shell/extensions"
rm -rf "$DATA/gnome-shell/extensions/$UUID"
cp -r "extension/$UUID" "$DATA/gnome-shell/extensions/"
python3 - "$UUID" <<'PY'
import ast, subprocess, sys
cur = subprocess.check_output(['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'], text=True)
l = ast.literal_eval(cur.replace('@as ', ''))
if sys.argv[1] not in l:
    l.append(sys.argv[1])
subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', str(l)], check=True)
PY

# The evening reminder: a notification at 22:00 every day to recite Al-Wâqi'a.
# Turn it off from the right-click menu, or: systemctl --user disable --now hifz-reminder.timer
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNITS"
first_time=1
[ -f "$UNITS/hifz-reminder.timer" ] && first_time=0
cp data/systemd/hifz-reminder.service data/systemd/hifz-reminder.timer "$UNITS/"
systemctl --user daemon-reload 2>/dev/null || true
[ $first_time = 1 ] && systemctl --user enable --now hifz-reminder.timer 2>/dev/null || true

echo "Installed. Type 'quran' in a terminal to start."
if ! gnome-extensions info "$UUID" 2>/dev/null | grep -q 'State: ACTIVE'; then
    echo "Log out and back in once so GNOME loads the extension that pins the window top-right."
fi
