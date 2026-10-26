#!/bin/bash
# Install Hifz for the current user on any common Linux distro.
# Works with apt (Debian/Ubuntu), dnf (Fedora), pacman (Arch) and zypper (openSUSE).
# The GNOME Shell extension (always-on-top corner) is installed only when GNOME is present.
set -e
cd "$(dirname "$0")"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN="$HOME/.local/bin"
UUID=hifz@aimanelahssini
APP=io.github.aimanelahssini.Hifz

echo "[hifz] install: starting"

have_python_mod() {
    python3 -c "$1" >/dev/null 2>&1
}

need_gtk=0
need_gst_good=0
need_gst_bad=0
have_python_mod "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); from gi.repository import Gtk, Adw" \
    || need_gtk=1
have_python_mod "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst; Gst.init(None); assert Gst.ElementFactory.find('mpg123audiodec') or Gst.ElementFactory.find('avdec_mp3')" \
    || need_gst_good=1
have_python_mod "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst; Gst.init(None); assert Gst.ElementFactory.find('pitch')" \
    || need_gst_bad=1

install_pkgs() {
    local pkgs=("$@")
    [ ${#pkgs[@]} -eq 0 ] && return 0
    echo "[hifz] install: need packages: ${pkgs[*]}"
    if command -v dnf >/dev/null; then
        pkexec dnf install -y "${pkgs[@]}"
    elif command -v apt-get >/dev/null; then
        pkexec bash -c "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y ${pkgs[*]}"
    elif command -v pacman >/dev/null; then
        pkexec pacman -Sy --noconfirm --needed "${pkgs[@]}"
    elif command -v zypper >/dev/null; then
        pkexec zypper --non-interactive install -y "${pkgs[@]}"
    else
        echo "[hifz] install: no supported package manager (dnf/apt/pacman/zypper)." >&2
        echo "Please install GTK 4, libadwaita, PyGObject and GStreamer (good + bad) yourself, then re-run." >&2
        return 1
    fi
}

if [ "$need_gtk$need_gst_good$need_gst_bad" != "000" ]; then
    pkgs=()
    if command -v dnf >/dev/null; then
        [ "$need_gtk" = 1 ] && pkgs+=(python3-gobject gtk4 libadwaita)
        [ "$need_gst_good" = 1 ] && pkgs+=(gstreamer1-plugins-good)
        [ "$need_gst_bad" = 1 ] && pkgs+=(gstreamer1-plugins-bad-free)
    elif command -v apt-get >/dev/null; then
        [ "$need_gtk" = 1 ] && pkgs+=(python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libgtk-4-1 libadwaita-1-0)
        [ "$need_gst_good" = 1 ] && pkgs+=(gstreamer1.0-plugins-good gir1.2-gstreamer-1.0)
        [ "$need_gst_bad" = 1 ] && pkgs+=(gstreamer1.0-plugins-bad)
    elif command -v pacman >/dev/null; then
        [ "$need_gtk" = 1 ] && pkgs+=(python-gobject gtk4 libadwaita)
        [ "$need_gst_good" = 1 ] && pkgs+=(gst-plugins-good)
        [ "$need_gst_bad" = 1 ] && pkgs+=(gst-plugins-bad)
    elif command -v zypper >/dev/null; then
        [ "$need_gtk" = 1 ] && pkgs+=(python3-gobject typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 libgtk-4-1 libadwaita-1-0)
        [ "$need_gst_good" = 1 ] && pkgs+=(gstreamer-plugins-good)
        [ "$need_gst_bad" = 1 ] && pkgs+=(gstreamer-plugins-bad)
    fi
    install_pkgs "${pkgs[@]}" || exit 1
fi

# Re-check after install.
if ! have_python_mod "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); from gi.repository import Gtk, Adw"; then
    echo "[hifz] install: GTK 4 / libadwaita / PyGObject still missing." >&2
    exit 1
fi
echo "[hifz] install: dependencies ok"

# The app itself.
rm -rf "$DATA/hifz/hifz"
mkdir -p "$DATA/hifz" "$BIN"
cp -r hifz "$DATA/hifz/"
find "$DATA/hifz" -name __pycache__ -prune -exec rm -rf {} +
cp -r bin "$DATA/hifz/"
ln -sf "$DATA/hifz/bin/quran" "$BIN/quran"
ln -sf "$DATA/hifz/bin/hifz" "$BIN/hifz"
install -Dm644 "data/$APP.desktop" "$DATA/applications/$APP.desktop"
mkdir -p "$DATA/dbus-1/services"
printf '[D-BUS Service]\nName=%s\nExec=%s --gapplication-service\n' "$APP" "$DATA/hifz/bin/hifz-service" \
    > "$DATA/dbus-1/services/$APP.service"
dbus-send --session --type=method_call --dest=org.freedesktop.DBus /org/freedesktop/DBus \
    org.freedesktop.DBus.ReloadConfig 2>/dev/null || true
install -Dm644 "data/$APP.svg" "$DATA/icons/hicolor/scalable/apps/$APP.svg"
gtk-update-icon-cache -q -t "$DATA/icons/hicolor" 2>/dev/null || true
echo "[hifz] install: app + commands"

# GNOME Shell extension (pins the card top-right on Wayland). Skip on other desktops.
is_gnome=0
if [ "${XDG_CURRENT_DESKTOP-}" != "${XDG_CURRENT_DESKTOP#*GNOME}" ] \
    || [ "${XDG_CURRENT_DESKTOP-}" != "${XDG_CURRENT_DESKTOP#*gnome}" ] \
    || command -v gnome-shell >/dev/null 2>&1; then
    is_gnome=1
fi
if [ "$is_gnome" = 1 ] && [ -d "extension/$UUID" ]; then
    mkdir -p "$DATA/gnome-shell/extensions"
    rm -rf "$DATA/gnome-shell/extensions/$UUID"
    cp -r "extension/$UUID" "$DATA/gnome-shell/extensions/"
    if command -v gsettings >/dev/null && gsettings list-schemas 2>/dev/null | grep -qx org.gnome.shell; then
        python3 - "$UUID" <<'PY' || true
import ast, subprocess, sys
try:
    cur = subprocess.check_output(['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'], text=True)
except subprocess.CalledProcessError:
    sys.exit(0)
l = ast.literal_eval(cur.replace('@as ', ''))
if sys.argv[1] not in l:
    l.append(sys.argv[1])
    subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', str(l)], check=False)
PY
        echo "[hifz] install: GNOME extension enabled"
    else
        echo "[hifz] install: GNOME extension copied (enable it from Extensions after login)"
    fi
else
    echo "[hifz] install: no GNOME Shell — skipping corner-pin extension (app still runs)"
fi

# Evening reminder via systemd --user when available.
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
if command -v systemctl >/dev/null && [ -d data/systemd ]; then
    mkdir -p "$UNITS"
    first_time=1
    [ -f "$UNITS/hifz-reminder.timer" ] && first_time=0
    cp data/systemd/hifz-reminder.service data/systemd/hifz-reminder.timer "$UNITS/"
    systemctl --user daemon-reload 2>/dev/null || true
    [ $first_time = 1 ] && systemctl --user enable --now hifz-reminder.timer 2>/dev/null || true
    echo "[hifz] install: reminder timer"
fi

case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "[hifz] install: add $BIN to your PATH to use the 'quran' / 'hifz' commands" ;;
esac

echo
echo "Installed. Open Hifz from your app menu, or type:  quran"
if [ "$is_gnome" = 1 ]; then
    if ! gnome-extensions info "$UUID" 2>/dev/null | grep -q 'State: ACTIVE'; then
        echo "On GNOME: log out and back in once so the extension can pin the card top-right."
    fi
else
    echo "On this desktop the card opens as a normal window (place it where you like)."
fi
