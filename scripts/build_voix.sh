#!/usr/bin/env bash
# « Huit voix » de bout en bout :
# voix (synthèse hors ligne + chuchotement) → vidéos libres de droits → chronologie → bande-son
# (voix, musique Coverr, bruitages Mixkit) → calque typographique → montage étalonné → films finaux.
#
# Prérequis : Python 3 avec numpy et piper-tts (pip install piper-tts), Node.js + Playwright, ffmpeg.
# Réseau : huggingface.co (modèles de voix, une fois), videos.pexels.com + images.pexels.com, assets.mixkit.co, cdn.coverr.co.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/voix output
[ -f src/fonts/fonts.css ] || python3 scripts/fetch_fonts.py

python3 scripts/voices.py
python3 scripts/footage/fetch.py --edl footage/edl_voix.json
node scripts/render.cjs --page reel.html --edl edl_voix --cues build/voix/cues.json
python3 scripts/sound_voix.py build/voix/cues.json build/voix/soundtrack.wav footage/edl_voix.json
rm -rf build/voix/ov_16x9 build/voix/ov_9x16
python3 scripts/footage/assemble.py --format 16x9 --edl footage/edl_voix.json &
python3 scripts/footage/assemble.py --format 9x16 --edl footage/edl_voix.json &
wait
python3 scripts/mux.py --film voix

# affiches : dernière image pleine du logo
for f in 16x9 9x16; do
  ffmpeg -y -v error -sseof -1.8 -i "output/N8_Huit-Voix_$f.mp4" -frames:v 1 "output/N8_Huit-Voix_affiche_$f.png"
done
echo "Terminé : output/N8_Huit-Voix_*"
