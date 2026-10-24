#!/bin/sh
# Vercel build: the site uses the logo, illustrations and demo video from docs/.
set -e
cd "$(dirname "$0")/.."
mkdir -p site/assets
cp logo.svg docs/*.svg docs/demo.mp4 docs/demo-poster.jpg site/assets/
