#!/usr/bin/env python3
"""Prépare une photo pour le site : crée nom-800.webp et nom-1600.webp dans src/static/img/.
(« 1600 » désigne la version grand format : une photo plus étroite garde sa largeur d'origine.)

    python3 outils/ajouter-photo.py ma-photo.jpg facade-ravalement

Le second argument est le nom de l'image utilisé dans les pages ({{img:facade-ravalement|…}}).
Réutiliser un nom existant remplace la photo partout où elle apparaît. Nécessite Pillow
(pip install pillow). Relancez ensuite « python3 build.py ».
"""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow est nécessaire : pip install pillow")

if len(sys.argv) != 3:
    sys.exit(__doc__)

source, nom = Path(sys.argv[1]), sys.argv[2].strip().lower()
dossier = Path(__file__).resolve().parent.parent / "src" / "static" / "img"
image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
if image.width < 1600:
    print(f"Info : la photo fait {image.width} px de large (1600 px conseillés) ; elle n'est pas agrandie.")
for format_nom, qualite in ((1600, 74), (800, 76)):
    largeur = min(format_nom, image.width)
    hauteur = round(image.height * largeur / image.width)
    copie = image.resize((largeur, hauteur), Image.LANCZOS)
    cible = dossier / f"{nom}-{format_nom}.webp"
    copie.save(cible, quality=qualite, method=6)
    print(f"{cible.relative_to(dossier.parent.parent.parent)} : {largeur}×{hauteur}")
