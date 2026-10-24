#!/bin/bash
# Inside the test D-Bus session: for the demo, a private PipeWire (screen recording only: the
# "policy" profile of WirePlumber opens no audio or camera devices), then the headless shell.
if [ "$HIFZ_MODE" = demo ]; then
    pipewire > "$HIFZ_OUT/pipewire.log" 2>&1 &
    sleep 0.7
    wireplumber --profile=policy > "$HIFZ_OUT/wireplumber.log" 2>&1 &
    sleep 0.7
fi
exec gnome-shell --headless --wayland --virtual-monitor "${MONITOR:-1440x900}"
