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
mkdir -p build/reel build/teaser output
[ -f src/fonts/fonts.css ] || python3 scripts/fetch_fonts.py

python3 scripts/footage/fetch.py
node scripts/render.cjs --page reel.html --cues build/reel/cues.json
python3 scripts/sound_reel.py build/reel/cues.json build/reel/soundtrack.wav
rm -rf build/reel/ov_16x9 build/reel/ov_9x16
python3 scripts/footage/assemble.py --format 16x9 &
python3 scripts/footage/assemble.py --format 9x16 &
wait
python3 scripts/mux.py --film reel

# version courte (≈ 16 s) pour la publicité et les réseaux : mêmes plans, autre montage (footage/edl_teaser.json)
node scripts/render.cjs --page reel.html --edl edl_teaser --cues build/teaser/cues.json
python3 scripts/sound_reel.py build/teaser/cues.json build/teaser/soundtrack.wav footage/edl_teaser.json
rm -rf build/teaser/ov_16x9 build/teaser/ov_9x16
python3 scripts/footage/assemble.py --format 16x9 --edl footage/edl_teaser.json &
python3 scripts/footage/assemble.py --format 9x16 --edl footage/edl_teaser.json &
wait
python3 scripts/mux.py --film teaser

# affiches : dernière image pleine du logo
for f in 16x9 9x16; do
  ffmpeg -y -v error -sseof -1.6 -i "output/N8_Nuits-Reel_$f.mp4" -frames:v 1 "output/N8_Nuits-Reel_affiche_$f.png"
done
echo "Terminé : output/N8_Nuits-Reel_*, output/N8_Nuits-Teaser_*"
