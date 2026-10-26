#!/bin/sh
# Vercel / local site build: assets, localized pages, downloadable packages.
set -e
cd "$(dirname "$0")/.."
mkdir -p site/assets site/downloads
cp logo.svg docs/*.svg docs/demo.mp4 docs/demo-poster.jpg site/assets/ 2>/dev/null || true
chmod +x scripts/package.sh scripts/build-site.py
./scripts/package.sh || echo "[hifz] site: packaging skipped or partial — downloads may be incomplete"
python3 scripts/build-site.py
