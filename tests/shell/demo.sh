#!/bin/bash
# Records the demo video: tests/shell/demo.sh [OUT_DIR]  ->  docs/demo.mp4
# The screen comes from a throwaway headless GNOME Shell; the recitation (Mishary Alafasy,
# everyayah.com) is laid over it afterwards from the log of what the app played and when.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="${1:-$(mktemp -d)}"
mkdir -p "$OUT"
# Wallpaper: the same colours as the illustrations.
magick -size 2560x1440 -define gradient:direction=southeast gradient:'#1e2a4a-#3b6e6a' \
    \( -size 2560x1440 radial-gradient:'#f6d98b40-#00000000' -geometry +900-500 \) -composite \
    "$OUT/wall.png"
cat > "$OUT/state.json" <<'JSON'
{"surah": 56, "speed": 1.0, "auto": false, "surahs": {"56": {"line": 0, "finished": 3, "finishes": []}}}
JSON
MODE=demo BG="$OUT/wall.png" STATE_JSON="$OUT/state.json" MONITOR=2560x1440 TIMEOUT=240 \
    "$HERE/run.sh" "$OUT"
python3 "$HERE/make_video.py" "$OUT" "$REPO/docs/demo.mp4"
