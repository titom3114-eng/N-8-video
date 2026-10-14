#!/usr/bin/env bash
# « Nuits » en images réelles, de bout en bout :
# vidéos libres de droits → chronologie → bande-son (musique Coverr + bruitages Mixkit) → calque titres
# → montage étalonné → films finaux.
#
# Prérequis réseau : videos.pexels.com (vidéos choisies, champ "src" de footage/edl.json), mixkit.co +
#                    assets.mixkit.co (bruitages), cdn.coverr.co (musique) ; recherche automatique Pexels facultative
#                    avec la variable PEXELS_API_KEY.
# Vos propres images : déposez footage/override/<id_du_plan>.mp4 (voir footage/edl.json).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/reel output
[ -f src/fonts/fonts.css ] || python3 scripts/fetch_fonts.py

python3 scripts/footage/fetch.py
node scripts/render.cjs --page reel.html --cues build/reel/cues.json
python3 scripts/sound_reel.py build/reel/cues.json build/reel/soundtrack.wav
rm -rf build/reel/ov_16x9 build/reel/ov_9x16
python3 scripts/footage/assemble.py --format 16x9 &
python3 scripts/footage/assemble.py --format 9x16 &
wait
python3 scripts/mux.py --film reel
echo "Terminé : output/N8_Nuits-Reel_*"
