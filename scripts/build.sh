#!/usr/bin/env bash
# Construit un film N+8 de bout en bout :
# chronologie → bande-son → rendu image par image (16:9 et 9:16) → films finaux, aperçus et affiches.
#
#   ./scripts/build.sh            # « Nuits »  (Paris, Rome, Oman…)  → output/N8_Nuits_*
#   ./scripts/build.sh la-nuit    # « La nuit » (version néons)       → output/N8_La-Nuit_*
set -euo pipefail
cd "$(dirname "$0")/.."
FILM="${1:-nuits}"

[ -f src/fonts/fonts.css ] || python3 scripts/fetch_fonts.py

if [ "$FILM" = "nuits" ]; then
  B=build/nuits; PAGE=nuits.html; SND=scripts/soundtrack_nuits.py; NAME=N8_Nuits; POSTER=58.5
else
  B=build; PAGE=index.html; SND=scripts/soundtrack.py; NAME=N8_La-Nuit; POSTER=58.5
fi
mkdir -p "$B" output

node scripts/render.cjs --page "$PAGE" --cues "$B/cues.json"
python3 "$SND" "$B/cues.json" "$B/soundtrack.wav"

node scripts/render.cjs --page "$PAGE" --format 16x9 --out "$B/video_16x9.mp4" &
node scripts/render.cjs --page "$PAGE" --format 9x16 --out "$B/video_9x16.mp4" &
wait

python3 scripts/mux.py --film "$FILM"

node scripts/render.cjs --page "$PAGE" --format 16x9 --snap "$POSTER" --out "$B/poster"
node scripts/render.cjs --page "$PAGE" --format 9x16 --snap "$POSTER" --out "$B/poster"
cp "$B/poster/16x9_0${POSTER}0.png" "output/${NAME}_affiche_16x9.png"
cp "$B/poster/9x16_0${POSTER}0.png" "output/${NAME}_affiche_9x16.png"
echo "Terminé : output/"
