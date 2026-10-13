#!/usr/bin/env bash
# Construit le film N+8 « La nuit » de bout en bout :
# chronologie → bande-son → rendu image par image (16:9 et 9:16) → films finaux + affiches.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build output

[ -f src/fonts/fonts.css ] || python3 scripts/fetch_fonts.py

node scripts/render.cjs --cues build/cues.json
python3 scripts/soundtrack.py build/cues.json build/soundtrack.wav

node scripts/render.cjs --format 16x9 --out build/video_16x9.mp4 &
node scripts/render.cjs --format 9x16 --out build/video_9x16.mp4 &
wait

python3 scripts/mux.py

# Affiches (image du logo final)
node scripts/render.cjs --format 16x9 --snap 58.5 --out build/poster
node scripts/render.cjs --format 9x16 --snap 58.5 --out build/poster
cp build/poster/16x9_058.50.png output/N8_affiche_16x9.png
cp build/poster/9x16_058.50.png output/N8_affiche_9x16.png
echo "Terminé : output/"
