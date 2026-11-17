# -*- coding: utf-8 -*-
"""
sources.py : boîtes de réception du pilote. Récupère les vidéos que tu as le droit de publier :
  - "gdrive" : dossier Google Drive partagé par une campagne de clipping (ou par un créateur qui a dit
    oui). Le pilote liste le dossier chaque jour et ne télécharge que les nouvelles vidéos.
  - "liens"  : liste de liens directs (Dropbox, fichier Google Drive, lien .mp4, vidéo YouTube ou TikTok
    d'un créateur qui t'a donné son accord).

Chaque source doit porter une autorisation (campagne rejointe, accord écrit) : sans elle, le pilote
l'ignore.
"""

import hashlib
import re
import shutil
from pathlib import Path

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".m4v", ".ts", ".flv"}
HOTES_VIDEO = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com", "twitch.tv", "vimeo.com",
               "streamable.com", "kick.com")


class ErreurSource(Exception):
    pass


def _gdown():
    try:
        import gdown
        return gdown
    except ImportError as e:
        raise ErreurSource("gdown est introuvable : python -m pip install gdown") from e


def _empreinte(texte):
    return hashlib.sha1(texte.encode("utf-8")).hexdigest()[:16]


def _telecharger_lien(url, dest):
    """Télécharge un lien vers `dest` (sans extension imposée) ; renvoie le chemin final."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]+)", url)
    if m:
        cible = dest.with_suffix(".mp4")
        _gdown().download(id=m.group(1), output=str(cible), quiet=True)
        return cible
    if any(h in url for h in HOTES_VIDEO):
        try:
            import yt_dlp
        except ImportError as e:
            raise ErreurSource("yt-dlp est introuvable : python -m pip install -U yt-dlp") from e
        options = {"outtmpl": str(dest) + ".%(ext)s", "quiet": True, "no_warnings": True, "noprogress": True,
                   "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b", "merge_output_format": "mp4",
                   "retries": 3}
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        trouves = [p for p in dest.parent.glob(dest.name + ".*") if p.suffix.lower() in VIDEO_EXT]
        if not trouves:
            raise ErreurSource(f"rien n'a été téléchargé depuis {url}")
        return trouves[0]
    try:
        import requests
    except ImportError as e:
        raise ErreurSource("requests est introuvable : python -m pip install requests") from e
    if "dropbox.com" in url:
        url = re.sub(r"([?&])dl=0", r"\1dl=1", url)
        if "dl=1" not in url:
            url += ("&" if "?" in url else "?") + "dl=1"
    cible = dest.with_suffix(".mp4")
    with requests.get(url, stream=True, timeout=120, allow_redirects=True) as r:
        if r.status_code != 200:
            raise ErreurSource(f"HTTP {r.status_code} sur {url}")
        type_contenu = r.headers.get("content-type", "")
        if "text/html" in type_contenu:
            raise ErreurSource(f"{url} renvoie une page web, pas une vidéo : mets un lien de téléchargement direct")
        with open(cible, "wb") as f:
            shutil.copyfileobj(r.raw, f, length=1024 * 1024)
    return cible


def nouveaux_fichiers(source, cache, deja_vus, maximum):
    """Renvoie au plus `maximum` vidéos pas encore traitées : liste de (identifiant, chemin, nom)."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    type_source = (source.get("type") or "gdrive").lower()
    sortie = []

    if type_source == "gdrive":
        lien = source.get("lien", "")
        if "drive.google.com" not in lien:
            raise ErreurSource("le champ « lien » doit être l'adresse d'un dossier Google Drive partagé")
        gdown = _gdown()
        try:
            liste = gdown.download_folder(url=lien, output=str(cache), skip_download=True, quiet=True)
        except Exception as e:  # noqa: BLE001
            raise ErreurSource(f"dossier illisible ({str(e)[:160]}). Il doit être partagé en "
                               f"« Tous les utilisateurs disposant du lien ».") from e
        fichiers = sorted(liste or [], key=lambda f: str(getattr(f, "path", "")))
        for f in fichiers:
            nom = Path(str(f.path)).name
            if Path(nom).suffix.lower() not in VIDEO_EXT:
                continue
            ident = "gd_" + str(f.id)
            if ident in deja_vus:
                continue
            dest = cache / f"{ident}{Path(nom).suffix.lower()}"
            if not dest.exists():
                gdown.download(id=f.id, output=str(dest), quiet=True)
            if not dest.exists() or dest.stat().st_size == 0:
                raise ErreurSource(f"téléchargement vide pour « {nom} » (quota Google Drive atteint ? réessaie demain)")
            sortie.append((ident, dest, nom))
            if len(sortie) >= maximum:
                break
        return sortie

    if type_source == "liens":
        for url in source.get("liens", []) or []:
            url = str(url).strip()
            if not url:
                continue
            ident = "url_" + _empreinte(url)
            if ident in deja_vus:
                continue
            existants = [p for p in cache.glob(ident + ".*") if p.suffix.lower() in VIDEO_EXT]
            chemin = existants[0] if existants else _telecharger_lien(url, cache / ident)
            sortie.append((ident, chemin, url.rstrip("/").split("/")[-1].split("?")[0] or ident))
            if len(sortie) >= maximum:
                break
        return sortie

    raise ErreurSource(f"type de source inconnu « {type_source} » : utilise « gdrive » ou « liens »")
