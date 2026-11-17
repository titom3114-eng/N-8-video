#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clipper.py : transforme des vidéos que tu as le droit d'utiliser (VOD de streamers qui
t'ont donné leur accord, rushs fournis par une campagne de clipping, clips envoyés par
ta communauté, tes propres captures) en clips TikTok 9:16 prêts à publier.

Commandes
  auto        repère les moments forts d'un long stream ET rend tous les clips + un TOP 5
  reperer     repère les moments forts (pics sonores) et écrit un fichier lot JSON modifiable
  lot         rend tous les clips et compilations décrits dans un fichier lot JSON
  clip        rend un seul clip
  couverture  fabrique une image de couverture 1080x1920

Dépendances : Python 3.9+, ffmpeg et ffprobe dans le PATH, Pillow, numpy.
Optionnel    : faster-whisper (sous-titres automatiques mot à mot).

Exemples
  python clipper.py auto vod/stream.mp4 --credit @nom_du_streamer --autorisation "DM du 18/11"
  python clipper.py reperer vod/stream.mp4 --credit @nom_du_streamer
  python clipper.py lot exports/stream_lot.json
  python clipper.py clip vod/stream.mp4 --debut 1:02:10 --fin 1:02:31 --hook "IL A PAS VU LE *CROCO*"
  python clipper.py couverture vod/stream.mp4 --temps 1:02:20 --titre "LE CROCO LE PLUS *FOU* DE GTA 6"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ICI = Path(__file__).resolve().parent
L, H = 1080, 1920
JAUNE = (255, 210, 63, 255)
BLANC = (255, 255, 255, 255)
NOIR = (0, 0, 0, 255)

DEFAUTS = {
    "pseudo": "@gta6zap",
    "credit": "",
    "cadre": "flou",          # flou = vidéo entière sur fond flouté ; plein = recadrage plein écran
    "zoom": 1.25,             # >= 1 ; 1.25 rogne un peu les côtés pour grossir l'action
    "decalage": 0.0,          # -1 (gauche) à 1 (droite) : position du recadrage
    "style": "contour",       # contour = texte blanc cerné de noir ; boite = texte noir sur bandeau blanc
    "fps": 0,                 # 0 = 60 i/s si la source est en 60, sinon 30
    "son_jeu": 1.0,           # volume du son d'origine (0 = muet)
    "musique": "",            # fichier audio facultatif mixé sous le son d'origine
    "volume_musique": 0.22,
    "cta": "ABONNE-TOI POUR LA SUITE",
    "sous_titres": False,
    "langue": "fr",
    "modele_whisper": "small",
    "rapide": False,          # rendu plus rapide et plus léger pour vérifier
    "police": "",
    "crf": 18,
    "sortie": "exports",
    "hooks_auto": True,
}

# Accroches utilisées quand un clip n'a pas d'accroche écrite (les *mots* passent en jaune).
HOOKS_AUTO = [
    "ATTENDS LA *FIN*...",
    "IL S'Y ATTENDAIT *PAS DU TOUT*",
    "LE MOMENT LE PLUS *FOU* DU STREAM",
    "PERSONNE N'A COMPRIS CE QUI S'EST *PASSÉ*",
    "GTA 6 EST TROP *RÉALISTE*",
    "LA POLICE DE GTA 6 NE *RIGOLE PAS*",
    "IL A PAS VU ÇA *ARRIVER*",
    "LE CHAT A *EXPLOSÉ*",
    "C'EST *LÉGAL* ÇA ?",
    "0 % DE CHANCE QUE ÇA *MARCHE*...",
    "LA PHYSIQUE DE GTA 6 EST *ABUSÉE*",
    "ROCKSTAR A PENSÉ À *TOUT*",
    "IL A *RAGE QUIT* EN DIRECT",
    "LE PIRE *TIMING* DE L'HISTOIRE",
    "REGARDE BIEN LE *PNJ*",
    "3... 2... 1... *CATASTROPHE*",
    "ON EN PARLE DE CE *BUG* ?",
    "TU L'AURAIS FAIT *TOI* ?",
    "LES ALLIGATORS DE LEONIDA SONT *FOUS*",
    "VICE CITY À *3 H DU MATIN*",
    "LE JEU LE PLUS *BEAU* DU MONDE ?",
    "IL A TOUT PERDU EN *10 SECONDES*",
    "QUI A ÉCRIT CE *PNJ* ?!",
    "JE CROIS QU'IL A *CASSÉ* LE JEU",
    "LA POURSUITE LA PLUS *LONGUE* DE GTA 6",
    "L'IA DE GTA 6 EST TROP *FORTE*",
    "ÇA DEVAIT PAS SE PASSER *COMME ÇA*",
    "LE DUO LE PLUS *NUL* DE LEONIDA",
    "IL A TROUVÉ UN *EASTER EGG*",
    "DIS-MOI QUE C'EST PAS *RÉEL*",
    "LE *FOU RIRE* QUI A TUÉ LE STREAM",
    "IL PENSAIT ÊTRE *DISCRET*...",
    "*5 ÉTOILES* EN 30 SECONDES",
    "CETTE VOITURE N'A *RIEN COMPRIS*",
    "C'EST PAS UN JEU, C'EST UN *FILM*",
    "REGARDE LE *RÉTRO*",
    "LA CHUTE LA PLUS *LONGUE* DE LEONIDA",
    "IL A VOULU FAIRE LE *MALIN*",
    "TU L'AS REGARDÉ *COMBIEN* DE FOIS ?",
    "LE CLIP QUE TOUT LE MONDE *PARTAGE*",
]


# --------------------------------------------------------------------------- outils


def stop(message):
    print(f"\nERREUR : {message}", file=sys.stderr)
    sys.exit(1)


def verifier_ffmpeg():
    for exe in ("ffmpeg", "ffprobe"):
        if not shutil.which(exe):
            stop(f"{exe} est introuvable. Installe ffmpeg (Windows : winget install Gyan.FFmpeg ; "
                 f"macOS : brew install ffmpeg ; Linux : sudo apt install ffmpeg), puis rouvre le terminal.")


def importer_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: F401
    except ImportError:
        stop("Pillow est introuvable. Installe-le : python -m pip install pillow numpy")


def parse_temps(valeur):
    """'83', '83.5', '1:23', '01:01:23.5' -> secondes (float)."""
    if valeur is None or valeur == "":
        return None
    if isinstance(valeur, (int, float)):
        return float(valeur)
    s = str(valeur).strip().replace(",", ".")
    parties = s.split(":")
    try:
        parties = [float(p) for p in parties]
    except ValueError:
        stop(f"Temps illisible : « {valeur} ». Écris par exemple 83, 1:23 ou 01:01:23.")
    total = 0.0
    for p in parties:
        total = total * 60 + p
    return total


def fmt_temps(t):
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:04.1f}"


def slug(texte, longueur=40):
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return (t[:longueur].strip("-")) or "clip"


def pair(x):
    return int(round(x / 2.0)) * 2


def sonder(src):
    p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                        "-show_format", str(src)], capture_output=True, text=True)
    if p.returncode != 0:
        stop(f"Impossible de lire « {src} » : {p.stderr.strip()[-300:]}")
    j = json.loads(p.stdout or "{}")
    video = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        stop(f"« {src} » ne contient pas de piste vidéo.")
    audio = any(s.get("codec_type") == "audio" for s in j.get("streams", []))
    try:
        num, den = (video.get("avg_frame_rate") or "30/1").split("/")
        fps = float(num) / float(den) if float(den) else 30.0
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    largeur, hauteur = int(video["width"]), int(video["height"])
    rotation = 0
    for sd in video.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = abs(int(sd["rotation"])) % 180
    if rotation == 90:
        largeur, hauteur = hauteur, largeur
    duree = float(j.get("format", {}).get("duration") or video.get("duration") or 0)
    hdr = video.get("color_transfer") in ("smpte2084", "arib-std-b67")
    return {"duree": duree, "l": largeur, "h": hauteur, "fps": fps, "audio": audio, "hdr": hdr}


def trouver_police(chemin=""):
    candidats = [
        chemin,
        str(ICI / "polices" / "Anton-Regular.ttf"),
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for c in candidats:
        if c and Path(c).is_file():
            return str(Path(c).resolve())
    stop("Aucune police trouvée. Garde le dossier polices/ à côté de clipper.py ou passe --police chemin.ttf")


def resoudre(chemin, base=None):
    """Cherche un fichier tel quel, puis relativement au dossier du fichier lot."""
    p = Path(chemin).expanduser()
    if p.is_file():
        return p.resolve()
    if base is not None:
        q = (Path(base) / chemin).expanduser()
        if q.is_file():
            return q.resolve()
    stop(f"Fichier introuvable : « {chemin} »")


def lancer(cmd, cwd=None, quoi="ffmpeg"):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        fin = "\n".join(p.stderr.strip().splitlines()[-25:])
        stop(f"{quoi} a échoué :\n{fin}")
    return p


# --------------------------------------------------------------------------- textes (Pillow)


def jetons(texte):
    """'IL A PAS VU LE *CROCO*' -> [('IL', False), ..., ('CROCO', True)]"""
    sortie = []
    accent = False
    for morceau in re.split(r"(\*)", texte or ""):
        if morceau == "*":
            accent = not accent
            continue
        for mot in morceau.split():
            sortie.append((mot, accent))
    return sortie


def envelopper(mots, police, largeur_max):
    lignes, ligne = [], []
    for mot in mots:
        essai = " ".join(m for m, _ in ligne + [mot])
        if ligne and police.getlength(essai) > largeur_max:
            lignes.append(ligne)
            ligne = [mot]
        else:
            ligne.append(mot)
    if ligne:
        lignes.append(ligne)
    return lignes


def bloc_texte(img, texte, centre_y, taille, police_chemin, style="contour", max_lignes=3,
               largeur_max=960, couleur=BLANC, accent=JAUNE, opacite=255):
    """Dessine un bloc de texte centré horizontalement autour de centre_y. Renvoie (haut, bas)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    mots = jetons(texte)
    if not mots:
        return centre_y, centre_y
    t = taille
    while True:
        f = ImageFont.truetype(police_chemin, t)
        lignes = envelopper(mots, f, largeur_max)
        if len(lignes) <= max_lignes or t <= 34:
            break
        t -= 4
    asc, desc = f.getmetrics()
    hauteur_ligne = int((asc + desc) * 1.0)
    total = hauteur_ligne * len(lignes)
    y0 = int(centre_y - total / 2)
    espace = f.getlength(" ")
    contour = max(3, int(t * 0.085))

    placements = []
    for i, ligne in enumerate(lignes):
        largeur = f.getlength(" ".join(m for m, _ in ligne))
        x = (L - largeur) / 2
        y = y0 + i * hauteur_ligne
        placements.append((x, y, largeur, ligne))

    def a(c):
        return (c[0], c[1], c[2], int(c[3] * opacite / 255))

    if style == "boite":
        fond = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(fond)
        marge = int(t * 0.24)
        for x, y, largeur, _ in placements:
            d.rounded_rectangle([x - marge, y - int(marge * 0.15), x + largeur + marge,
                                 y + hauteur_ligne + int(marge * 0.15)], radius=marge, fill=a(BLANC))
        img.alpha_composite(fond)
        d = ImageDraw.Draw(img)
        for x, y, _, ligne in placements:
            cx = x
            for mot, acc in ligne:
                d.text((cx, y), mot, font=f, fill=a((214, 40, 110, 255)) if acc else a(NOIR))
                cx += f.getlength(mot) + espace
    else:
        ombre = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ombre)
        for x, y, _, ligne in placements:
            od.text((x + 5, y + 8), " ".join(m for m, _ in ligne), font=f, fill=(0, 0, 0, int(160 * opacite / 255)),
                    stroke_width=contour, stroke_fill=(0, 0, 0, int(160 * opacite / 255)))
        img.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(9)))
        d = ImageDraw.Draw(img)
        for x, y, _, ligne in placements:
            cx = x
            for mot, acc in ligne:
                d.text((cx, y), mot, font=f, fill=a(accent if acc else couleur),
                       stroke_width=contour, stroke_fill=a(NOIR))
                cx += f.getlength(mot) + espace
    return y0, y0 + total


def disposition(info, cadre, zoom):
    """Renvoie (cadre_effectif, haut_video, bas_video) dans l'image 1080x1920."""
    portrait = info["l"] / max(1, info["h"]) < 1.0
    if cadre == "plein" or portrait:
        return "plein", 0, H
    fg_l = pair(L * zoom)
    fg_h = pair(fg_l * info["h"] / info["l"])
    fg_h = min(fg_h, H)
    haut = (H - fg_h) // 2
    return "flou", haut, haut + fg_h


def positions(cadre, haut, bas):
    if cadre == "plein":
        return {"hook": 400, "titre": 300, "rang": 560, "signature": 1395, "cta": 1290, "st": 1150}
    hook = max(250, min(420, haut // 2 + 40))
    return {
        "hook": hook,
        "titre": max(215, haut // 2 - 60),
        "rang": max(430, haut - 110),
        "signature": min(bas + 44, 1440),
        "cta": min(bas + 150, 1500),
        "st": bas - 120,
    }


def calque_principal(chemin, police, style, pos, hook="", signature="", titre="", rang_texte=""):
    from PIL import Image
    img = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    if titre:
        bloc_texte(img, titre, pos["titre"], 78, police, style="contour", max_lignes=2)
    if rang_texte:
        bloc_texte(img, rang_texte, pos["rang"], 88, police, style=style, max_lignes=2)
    if hook:
        bloc_texte(img, hook, pos["hook"], 96, police, style=style, max_lignes=3)
    if signature:
        bloc_texte(img, signature, pos["signature"], 40, police, style="contour", max_lignes=1,
                   largeur_max=1000, opacite=215)
    img.save(chemin)


def calque_cta(chemin, police, pos, texte):
    from PIL import Image
    img = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    bloc_texte(img, texte, pos["cta"], 62, police, style="boite", max_lignes=2, largeur_max=900)
    img.save(chemin)


# --------------------------------------------------------------------------- sous-titres


def nom_police(police):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(police, 40).getname()[0]
    except Exception:
        return "Arial"


def mots_whisper(src, debut, duree, langue, modele, dossier):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        stop("Les sous-titres demandent faster-whisper : python -m pip install faster-whisper "
             "(ou relance sans --sous-titres).")
    wav = Path(dossier) / "voix.wav"
    lancer(["ffmpeg", "-y", "-v", "error", "-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", str(src),
            "-vn", "-ac", "1", "-ar", "16000", str(wav)], quoi="extraction audio")
    if not hasattr(mots_whisper, "_modeles"):
        mots_whisper._modeles = {}
    if modele not in mots_whisper._modeles:
        print(f"   chargement du modèle de transcription « {modele} » (une seule fois)...")
        mots_whisper._modeles[modele] = WhisperModel(modele, device="auto", compute_type="int8")
    segments, _ = mots_whisper._modeles[modele].transcribe(str(wav), language=langue or None,
                                                          word_timestamps=True, vad_filter=True)
    mots = []
    for seg in segments:
        for w in (seg.words or []):
            texte = (w.word or "").strip()
            if texte:
                mots.append({"debut": float(w.start), "fin": float(w.end), "mot": texte})
    return mots


def temps_ass(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def ecrire_ass(mots, chemin, police_nom, y, duree):
    """Sous-titres façon TikTok : 3 mots maximum à l'écran, mot prononcé en jaune."""
    groupes, g = [], []
    for w in mots:
        if g and (len(g) >= 3 or w["debut"] - g[0]["debut"] > 1.4 or w["debut"] - g[-1]["fin"] > 0.6):
            groupes.append(g)
            g = []
        g.append(w)
    if g:
        groupes.append(g)

    def propre(x):
        return x.replace("{", "(").replace("}", ")").replace("\\", "/").upper()

    lignes = []
    for gi, groupe in enumerate(groupes):
        fin_groupe = groupe[-1]["fin"] + 0.25
        if gi + 1 < len(groupes):
            fin_groupe = min(fin_groupe, groupes[gi + 1][0]["debut"])
        fin_groupe = min(fin_groupe, duree)
        for i, w in enumerate(groupe):
            debut = w["debut"]
            fin = groupe[i + 1]["debut"] if i + 1 < len(groupe) else fin_groupe
            if fin - debut < 0.04:
                continue
            parties = []
            for j, x in enumerate(groupe):
                if j == i:
                    parties.append("{\\c&H3FD2FF&}" + propre(x["mot"]) + "{\\c&HFFFFFF&}")
                else:
                    parties.append(propre(x["mot"]))
            texte = " ".join(parties)
            lignes.append(f"Dialogue: 0,{temps_ass(debut)},{temps_ass(fin)},TT,,0,0,0,,"
                          f"{{\\an5\\pos(540,{y})}}{texte}")
    entete = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: TT,{police_nom},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,6,3,"
        "5,60,60,0,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    Path(chemin).write_text(entete + "\n".join(lignes) + "\n", encoding="utf-8")
    return len(lignes)


# --------------------------------------------------------------------------- rendu


def filtre_cadrage(info, cadre, zoom, decalage, fps=None):
    pre = ""
    if info["hdr"]:
        pre += ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
    if fps:
        pre += f"fps={fps},"
    d = max(-1.0, min(1.0, float(decalage)))
    if cadre == "plein":
        h_cible = pair(H * zoom)
        return (f"[0:v]{pre}scale=-2:{h_cible}:flags=lanczos,"
                f"scale='max(iw,{L})':-2,"
                f"crop={L}:{H}:(iw-{L})/2*(1+{d}):(ih-{H})/2,setsar=1[base]")
    fg_l = pair(L * zoom)
    return (f"[0:v]{pre}split=2[a][b];"
            f"[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10:3,"
            f"scale={L}:{H},eq=brightness=-0.09:saturation=1.2[fond];"
            f"[b]scale={fg_l}:-2:flags=lanczos,crop={L}:'min(ih,{H})':(iw-{L})/2*(1+{d}):(ih-min(ih\\,{H}))/2[avant];"
            f"[fond][avant]overlay=(W-w)/2:(H-h)/2,setsar=1[base]")


def rendre(src, debut, fin, sortie, o, hook="", titre="", rang_texte="", fps_force=None, avec_cta=True):
    """Rend un clip 9:16. `o` = réglages fusionnés (DEFAUTS + lot + clip)."""
    importer_pillow()
    src = Path(src).expanduser().resolve()
    info = sonder(src)
    if fin is None:
        fin = info["duree"]
    debut = max(0.0, debut or 0.0)
    if info["duree"] and fin > info["duree"] + 0.5:
        print(f"   attention : fin {fmt_temps(fin)} au-delà de la vidéo ({fmt_temps(info['duree'])}), coupée.")
        fin = info["duree"]
    duree = fin - debut
    if duree <= 0.5:
        stop(f"Clip trop court ou mal défini ({fmt_temps(debut)} -> {fmt_temps(fin)}).")

    zoom = max(1.0, float(o["zoom"]))
    cadre, haut, bas = disposition(info, o["cadre"], zoom)
    pos = positions(cadre, haut, bas)
    fps = fps_force or int(o["fps"]) or (60 if info["fps"] >= 50 else 30)
    police = trouver_police(o.get("police", ""))
    rapide = bool(o.get("rapide"))

    signature = o["pseudo"] or ""
    if o.get("credit"):
        signature = f"{signature}  ·  CLIP : {o['credit']}" if signature else f"CLIP : {o['credit']}"

    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="clipper_") as tmp:
        calque_principal(Path(tmp) / "calque.png", police, o["style"], pos, hook=hook, signature=signature,
                         titre=titre, rang_texte=rang_texte)
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", str(src),
               "-loop", "1", "-framerate", str(fps), "-t", f"{duree:.3f}", "-i", "calque.png"]
        idx = 2
        idx_cta = None
        if avec_cta and o.get("cta") and duree >= 6:
            calque_cta(Path(tmp) / "cta.png", police, pos, o["cta"])
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{duree:.3f}", "-i", "cta.png"]
            idx_cta = idx
            idx += 1
        idx_mus = None
        if o.get("musique"):
            cmd += ["-stream_loop", "-1", "-i", str(resoudre(o["musique"]))]
            idx_mus = idx
            idx += 1

        graphe = [filtre_cadrage(info, cadre, zoom, o["decalage"], fps)]
        courant = "base"
        if o.get("sous_titres"):
            mots = mots_whisper(src, debut, duree, o.get("langue", "fr"), o.get("modele_whisper", "small"), tmp)
            if mots:
                shutil.copy(police, Path(tmp) / Path(police).name)
                n = ecrire_ass(mots, Path(tmp) / "st.ass", nom_police(police), pos["st"], duree)
                if n:
                    graphe.append(f"[{courant}]subtitles=st.ass:fontsdir=.[st]")
                    courant = "st"
            else:
                print("   aucun mot détecté : clip rendu sans sous-titres.")
        graphe.append(f"[{courant}][1:v]overlay=0:0:format=auto[v1]")
        courant = "v1"
        if idx_cta is not None:
            graphe.append(f"[{courant}][{idx_cta}:v]overlay=0:0:format=auto:"
                          f"enable='gte(t,{max(0.0, duree - 2.2):.2f})'[v2]")
            courant = "v2"
        graphe.append(f"[{courant}]format=yuv420p[v]")

        vol = float(o.get("son_jeu", 1.0))
        if info["audio"] and vol > 0:
            graphe.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol}[ja]")
        else:
            graphe.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{duree:.3f}[ja]")
        audio = "ja"
        if idx_mus is not None:
            graphe.append(f"[{idx_mus}:a]atrim=0:{duree:.3f},aresample=48000,aformat=channel_layouts=stereo,"
                          f"volume={float(o.get('volume_musique', 0.22))}[mu]")
            graphe.append("[ja][mu]amix=inputs=2:duration=first:dropout_transition=0[mix]")
            audio = "mix"
        graphe.append(f"[{audio}]afade=t=in:d=0.04,afade=t=out:st={max(0.0, duree - 0.12):.3f}:d=0.12,"
                      f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")

        cmd += ["-filter_complex", ";".join(graphe), "-map", "[v]", "-map", "[a]",
                "-t", f"{duree:.3f}", "-r", str(fps),
                "-c:v", "libx264", "-preset", "veryfast" if rapide else "medium",
                "-crf", "24" if rapide else str(int(o.get("crf", 18))),
                "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", str(fps * 2),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
                str(sortie.resolve())]
        lancer(cmd, cwd=tmp, quoi=f"le rendu de {sortie.name}")
    return duree


def etiquette_duree(d):
    if d > 60:
        return "plus d'1 min"
    if d <= 15:
        return "format boucle"
    return "format court"


# --------------------------------------------------------------------------- repérage


def reperer_moments(src, nombre=12, avant=12.0, apres=6.0, ecart=30.0, ignorer_debut=None, ignorer_fin=20.0):
    """Moments forts = pics de volume au-dessus du niveau ambiant (cris, rires, explosions, crashs)."""
    try:
        import numpy as np
    except ImportError:
        stop("numpy est introuvable : python -m pip install numpy")
    info = sonder(src)
    if not info["audio"]:
        stop("Cette vidéo n'a pas de son : le repérage automatique se base sur l'audio.")
    duree = info["duree"]
    if ignorer_debut is None:
        ignorer_debut = 180.0 if duree > 1800 else 0.0

    print(f"Analyse du son de « {Path(src).name} » ({fmt_temps(duree)})...")
    taux, pas_s = 8000, 0.5
    pas = int(taux * pas_s)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(taux),
                             "-f", "s16le", "-"], stdout=subprocess.PIPE)
    niveaux = []
    reste = b""
    while True:
        bloc = proc.stdout.read(pas * 2 * 240)
        if not bloc:
            break
        bloc = reste + bloc
        n = len(bloc) // (pas * 2)
        if n:
            x = np.frombuffer(bloc[: n * pas * 2], dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt((x.reshape(n, pas) ** 2).mean(axis=1)) + 1e-5
            niveaux.extend((20 * np.log10(rms)).tolist())
        reste = bloc[n * pas * 2:]
    proc.wait()
    db = np.array(niveaux, dtype=np.float32)
    if len(db) < 20:
        stop("Vidéo trop courte pour repérer des moments.")

    k = 121  # 60 s de contexte
    marge = k // 2
    from numpy.lib.stride_tricks import sliding_window_view
    fond = np.median(sliding_window_view(np.pad(db, (marge, marge), mode="edge"), k), axis=1)
    brut = db - fond
    lisse = np.convolve(brut, np.ones(3) / 3, mode="same")  # pic soutenu sur ~1,5 s
    score = 0.6 * lisse + 0.4 * brut

    t = np.arange(len(score)) * pas_s
    valide = (t >= ignorer_debut) & (t <= duree - ignorer_fin)
    ordre = [i for i in np.argsort(score)[::-1] if valide[i]]
    choisis = []
    for i in ordre:
        if score[i] < 4.0:
            break
        ti = float(t[i])
        if all(abs(ti - c["pic"]) >= ecart for c in choisis):
            choisis.append({"pic": ti, "score": float(score[i])})
        if len(choisis) >= nombre:
            break
    for c in choisis:
        c["debut"] = max(0.0, c["pic"] - avant)
        c["fin"] = min(duree, c["pic"] + apres)
    return sorted(choisis, key=lambda c: c["pic"]), info


def nom_source(src):
    return slug(Path(src).stem, 30) or "source"


def ecrire_lot(src, moments, credit, autorisation, chemin, hooks_auto=True, compil=True):
    alias = nom_source(src)
    clips = []
    for i, m in enumerate(moments):
        clips.append({
            "source": alias,
            "debut": fmt_temps(m["debut"]),
            "fin": fmt_temps(m["fin"]),
            "hook": HOOKS_AUTO[(i * 7 + len(alias)) % len(HOOKS_AUTO)] if hooks_auto else "",
            "score": round(m["score"], 1),
        })
    lot = {
        "reglages": {"pseudo": DEFAUTS["pseudo"], "sortie": str(Path(chemin).parent), "sous_titres": False,
                     "hooks_auto": bool(hooks_auto)},
        "sources": {alias: {"fichier": str(Path(src)), "credit": credit or "", "autorisation": autorisation or ""}},
        "clips": clips,
        "compilations": [],
    }
    if compil and len(moments) >= 5:
        top = sorted(moments, key=lambda m: m["score"])[-5:]  # 5e meilleur en premier, le meilleur à la fin
        lot["compilations"].append({
            "nom": f"top5_{alias}",
            "titre": "TOP 5 DES MOMENTS LES PLUS *FOUS* DU STREAM",
            "classement": True,
            "segments": [{"source": alias, "debut": fmt_temps(m["debut"]), "fin": fmt_temps(m["fin"]), "label": ""}
                         for m in top],
        })
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    Path(chemin).write_text(json.dumps(lot, ensure_ascii=False, indent=2), encoding="utf-8")
    return lot


# --------------------------------------------------------------------------- lot


def reglages(*couches):
    o = dict(DEFAUTS)
    for c in couches:
        for k, v in (c or {}).items():
            if v is not None and k in DEFAUTS:
                o[k] = v
    return o


def source_de(lot, ref, base):
    sources = lot.get("sources", {}) or {}
    if ref in sources:
        s = sources[ref]
        return resoudre(s["fichier"], base), s.get("credit", ""), s.get("autorisation", "")
    return resoudre(ref, base), "", ""


def executer_lot(chemin_lot, seulement=None):
    verifier_ffmpeg()
    chemin_lot = Path(chemin_lot).resolve()
    try:
        lot = json.loads(chemin_lot.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        stop(f"Le fichier lot n'est pas un JSON valide (ligne {e.lineno}, colonne {e.colno}) : {e.msg}")
    base = chemin_lot.parent
    g = lot.get("reglages", {}) or {}
    dossier = Path(g.get("sortie") or DEFAUTS["sortie"])
    if not dossier.is_absolute():
        dossier = (Path.cwd() / dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    for alias, s in (lot.get("sources", {}) or {}).items():
        if not str(s.get("autorisation", "")).strip():
            print(f"ATTENTION : aucune autorisation notée pour la source « {alias} ». "
                  f"Ne publie que si tu as l'accord du créateur ou d'une campagne de clipping.")

    rendus = []
    if seulement in (None, "clips"):
        for i, c in enumerate(lot.get("clips", []) or [], start=1):
            src, credit, _ = source_de(lot, c["source"], base)
            o = reglages(g, {"credit": credit}, c)
            hook = c.get("hook", "")
            if not hook and o.get("hooks_auto"):
                hook = HOOKS_AUTO[(i * 7) % len(HOOKS_AUTO)]
            nom = c.get("nom") or f"{i:02d}_{slug(hook.replace('*', '') or Path(src).stem)}"
            sortie = dossier / f"{nom}.mp4"
            print(f"[{i}/{len(lot.get('clips', []))}] {sortie.name}  ({c.get('debut')} -> {c.get('fin')})")
            d = rendre(src, parse_temps(c.get("debut")), parse_temps(c.get("fin")), sortie, o, hook=hook)
            rendus.append((sortie, d))

    if seulement in (None, "compilations"):
        for comp in lot.get("compilations", []) or []:
            rendus.append(rendre_compilation(lot, comp, g, base, dossier))

    print("\nTerminé :")
    for sortie, d in rendus:
        print(f"  {sortie}  {d:5.1f} s  ({etiquette_duree(d)})")
    return rendus


def rendre_compilation(lot, comp, g, base, dossier):
    segments = comp.get("segments", []) or []
    if not segments:
        stop(f"La compilation « {comp.get('nom')} » n'a aucun segment.")
    nom = comp.get("nom") or slug(comp.get("titre", "compilation"))
    sortie = dossier / f"{nom}.mp4"
    premier, _, _ = source_de(lot, segments[0]["source"], base)
    o0 = reglages(g, {"zoom": 1.0}, comp)
    fps = int(o0["fps"]) or (60 if sonder(premier)["fps"] >= 50 else 30)
    total = 0.0
    print(f"Compilation {sortie.name} ({len(segments)} segments)")
    with tempfile.TemporaryDirectory(prefix="compil_") as tmp:
        morceaux = []
        n = len(segments)
        for i, s in enumerate(segments):
            src, credit, _ = source_de(lot, s["source"], base)
            o = reglages(g, {"zoom": 1.0, "credit": credit}, comp, s)
            rang = n - i
            label = s.get("label", "")
            if comp.get("classement", True):
                rang_texte = f"*#{rang}* {label}".strip()
            else:
                rang_texte = label
            morceau = Path(tmp) / f"seg{i:02d}.mp4"
            print(f"   segment {i + 1}/{n} ({s.get('debut')} -> {s.get('fin')})")
            total += rendre(src, parse_temps(s.get("debut")), parse_temps(s.get("fin")), morceau, o,
                            titre=comp.get("titre", ""), rang_texte=rang_texte, fps_force=fps,
                            avec_cta=(i == n - 1))
            morceaux.append(morceau)
        liste = Path(tmp) / "liste.txt"
        liste.write_text("".join(f"file '{m.name}'\n" for m in morceaux), encoding="utf-8")
        lancer(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "liste.txt",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(sortie.resolve())],
               cwd=tmp, quoi="l'assemblage de la compilation")
    if total < 61:
        print(f"   attention : {total:.1f} s. Ajoute des segments pour passer 61 s "
              f"(durée minimale du programme Creator Rewards).")
    return sortie, total


# --------------------------------------------------------------------------- couverture


def couverture(src, temps, titre, sortie, o):
    importer_pillow()
    from PIL import Image
    verifier_ffmpeg()
    info = sonder(src)
    zoom = max(1.0, float(o["zoom"]))
    cadre, haut, bas = disposition(info, o["cadre"], zoom)
    police = trouver_police(o.get("police", ""))
    with tempfile.TemporaryDirectory(prefix="couv_") as tmp:
        image = Path(tmp) / "image.png"
        lancer(["ffmpeg", "-y", "-v", "error", "-ss", f"{temps:.3f}", "-i", str(src), "-frames:v", "1",
                "-filter_complex", filtre_cadrage(info, cadre, zoom, o["decalage"]), "-map", "[base]", str(image)],
               quoi="l'extraction de l'image")
        img = Image.open(image).convert("RGBA")
        degrade = Image.new("L", (1, 900))
        degrade.putdata([int(170 * (1 - y / 900) ** 1.4) for y in range(900)])
        voile = Image.new("RGBA", (L, H), (0, 0, 0, 0))
        voile.paste(Image.new("RGBA", (L, 900), (0, 0, 0, 255)), (0, 0), degrade.resize((L, 900)))
        img.alpha_composite(voile)
        bloc_texte(img, titre, 470, 132, police, style="contour", max_lignes=4, largeur_max=980)
        if o.get("pseudo"):
            bloc_texte(img, o["pseudo"], 1400, 44, police, style="contour", max_lignes=1, opacite=220)
        Path(sortie).parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(sortie, quality=95)
    print(f"Couverture : {sortie}")


# --------------------------------------------------------------------------- interface


def ajouter_reglages(p):
    p.add_argument("--pseudo", help=f"ton @ affiché sous la vidéo (défaut {DEFAUTS['pseudo']})")
    p.add_argument("--credit", help="@ du créateur clippé, affiché « CLIP : @... »")
    p.add_argument("--cadre", choices=["flou", "plein"], help="flou (défaut) ou plein écran")
    p.add_argument("--zoom", type=float, help="1 à 2 (défaut 1.25)")
    p.add_argument("--decalage", type=float, help="-1 gauche à 1 droite (défaut 0)")
    p.add_argument("--style", choices=["contour", "boite"], help="style des accroches")
    p.add_argument("--fps", type=int, help="30 ou 60 (défaut : comme la source)")
    p.add_argument("--son-jeu", dest="son_jeu", type=float, help="volume du son d'origine, 0 = muet")
    p.add_argument("--musique", help="fichier audio mixé sous le son d'origine")
    p.add_argument("--volume-musique", dest="volume_musique", type=float)
    p.add_argument("--cta", help="texte affiché les 2 dernières secondes ('' pour aucun)")
    p.add_argument("--sous-titres", dest="sous_titres", action="store_true", default=None,
                   help="sous-titres automatiques (faster-whisper)")
    p.add_argument("--langue", help="langue parlée pour les sous-titres (défaut fr)")
    p.add_argument("--modele-whisper", dest="modele_whisper", help="tiny, base, small (défaut), medium")
    p.add_argument("--rapide", action="store_true", default=None, help="rendu rapide pour vérifier")
    p.add_argument("--police", help="police .ttf/.otf à utiliser")
    p.add_argument("--sortie", help="dossier de sortie (défaut exports)")


def depuis_args(a):
    return {k: getattr(a, k) for k in DEFAUTS if hasattr(a, k) and getattr(a, k) is not None}


def main():
    ap = argparse.ArgumentParser(description="Clips TikTok 9:16 à partir de vidéos autorisées.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="commande", required=True)

    p = sub.add_parser("auto", help="repérage + rendu de tous les clips + TOP 5")
    p.add_argument("source")
    p.add_argument("--nombre", type=int, default=12, help="nombre de clips (défaut 12)")
    p.add_argument("--avant", type=float, default=12.0, help="secondes gardées avant le pic (défaut 12)")
    p.add_argument("--apres", type=float, default=6.0, help="secondes gardées après le pic (défaut 6)")
    p.add_argument("--autorisation", default="", help="preuve d'accord (ex. « DM Instagram du 18/11/2026 »)")
    p.add_argument("--sans-compil", action="store_true", help="ne pas fabriquer le TOP 5")
    p.add_argument("--sans-hooks", action="store_true", help="pas d'accroche automatique")
    ajouter_reglages(p)

    p = sub.add_parser("reperer", help="repère les moments forts et écrit un fichier lot JSON")
    p.add_argument("source")
    p.add_argument("--nombre", type=int, default=12)
    p.add_argument("--avant", type=float, default=12.0)
    p.add_argument("--apres", type=float, default=6.0)
    p.add_argument("--ecart", type=float, default=30.0, help="écart minimal entre deux moments (s)")
    p.add_argument("--credit", default="")
    p.add_argument("--autorisation", default="")
    p.add_argument("--lot", help="chemin du fichier lot à écrire (défaut exports/<source>_lot.json)")
    p.add_argument("--sans-hooks", action="store_true")

    p = sub.add_parser("lot", help="rend un fichier lot JSON")
    p.add_argument("fichier")
    p.add_argument("--seulement", choices=["clips", "compilations"])

    p = sub.add_parser("clip", help="rend un seul clip")
    p.add_argument("source")
    p.add_argument("--debut", required=True)
    p.add_argument("--fin", required=True)
    p.add_argument("--hook", default="", help="accroche ; *mot* = mot en jaune")
    p.add_argument("--nom", help="nom du fichier de sortie sans extension")
    ajouter_reglages(p)

    p = sub.add_parser("couverture", help="image de couverture 1080x1920")
    p.add_argument("source")
    p.add_argument("--temps", required=True)
    p.add_argument("--titre", required=True)
    p.add_argument("--fichier", default="", help="chemin du PNG (défaut exports/couverture_<titre>.png)")
    ajouter_reglages(p)

    a = ap.parse_args()
    verifier_ffmpeg()

    if a.commande == "lot":
        executer_lot(a.fichier, a.seulement)
        return

    if a.commande in ("reperer", "auto"):
        src = resoudre(a.source)
        moments, info = reperer_moments(src, nombre=a.nombre, avant=a.avant, apres=a.apres,
                                        ecart=getattr(a, "ecart", 30.0))
        if not moments:
            stop("Aucun moment fort détecté (son trop uniforme). Choisis les passages à la main avec la commande clip.")
        dossier = Path(getattr(a, "sortie", None) or DEFAUTS["sortie"])
        chemin_lot = Path(getattr(a, "lot", None) or dossier / f"{nom_source(src)}_lot.json")
        lot = ecrire_lot(src, moments, a.credit or "", a.autorisation, chemin_lot,
                         hooks_auto=not a.sans_hooks, compil=not getattr(a, "sans_compil", False))
        if a.commande == "auto":
            lot["reglages"].update(depuis_args(a))
            lot["reglages"]["sortie"] = str(dossier)
            chemin_lot.write_text(json.dumps(lot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{len(moments)} moments repérés :")
        for i, (m, c) in enumerate(zip(moments, lot["clips"]), start=1):
            print(f"  {i:2d}. {fmt_temps(m['debut'])} -> {fmt_temps(m['fin'])}   pic +{m['score']:.1f} dB   "
                  f"{c['hook'].replace('*', '')}")
        print(f"\nFichier lot : {chemin_lot}")
        if not a.autorisation:
            print("ATTENTION : note la preuve d'accord du créateur dans le champ « autorisation » du fichier lot.")
        if a.commande == "reperer":
            print("Vérifie ou modifie les temps et accroches, puis lance : "
                  f"python clipper.py lot \"{chemin_lot}\"")
            return
        executer_lot(chemin_lot)
        return

    o = reglages(depuis_args(a))
    src = resoudre(a.source)
    if a.commande == "clip":
        dossier = Path(o["sortie"])
        nom = a.nom or slug(a.hook.replace("*", "") or Path(src).stem)
        sortie = dossier / f"{nom}.mp4"
        d = rendre(src, parse_temps(a.debut), parse_temps(a.fin), sortie, o, hook=a.hook)
        print(f"Clip : {sortie}  {d:.1f} s  ({etiquette_duree(d)})")
    elif a.commande == "couverture":
        sortie = a.fichier or str(Path(o["sortie"]) / f"couverture_{slug(a.titre.replace('*', ''))}.png")
        couverture(src, parse_temps(a.temps), a.titre, sortie, o)


if __name__ == "__main__":
    main()
