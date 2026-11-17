# -*- coding: utf-8 -*-
"""
publication.py : programmation automatique des vidéos sur TikTok (et, en option, YouTube Shorts,
Instagram Reels...) par l'API d'Upload-Post, service partenaire de l'API officielle de TikTok.

Pourquoi un intermédiaire : TikTok n'autorise la publication par API qu'aux applications qu'il a
auditées ; une application maison non auditée ne peut publier qu'en privé. Upload-Post est audité :
tu y relies ton compte TikTok une fois (connexion officielle TikTok), puis ce module lui envoie les
vidéos avec leur légende et leur heure de publication.

Requête : POST https://api.upload-post.com/api/upload (multipart)
  en-tête  Authorization: Apikey <clé>
  champs   user (profil Upload-Post), platform[] (tiktok...), title (légende), video (fichier),
           scheduled_date (ISO 8601, ici en UTC avec le suffixe Z)
"""

import time
from datetime import timezone
from pathlib import Path

API = "https://api.upload-post.com/api/upload"


class ErreurPublication(Exception):
    pass


def programmer(cle, profil, fichier, legende, quand_utc, plateformes, delai_s=600):
    """Envoie une vidéo et la programme. Renvoie l'identifiant de la tâche (job_id) ou 'ok'."""
    try:
        import requests
    except ImportError as e:
        raise ErreurPublication("le module requests manque : python -m pip install requests") from e
    if not cle:
        raise ErreurPublication("clé API Upload-Post absente (variable UPLOAD_POST_API_KEY ou config)")
    if not profil:
        raise ErreurPublication("profil Upload-Post absent (publication.auto.profil dans la config)")
    quand = quand_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    champs = [("user", profil), ("title", legende), ("scheduled_date", quand)]
    champs += [("platform[]", p) for p in plateformes]
    derniere = ""
    for essai in range(3):
        try:
            with open(fichier, "rb") as f:
                r = requests.post(API, headers={"Authorization": f"Apikey {cle}"}, data=champs,
                                  files={"video": (Path(fichier).name, f, "video/mp4")}, timeout=delai_s)
        except requests.RequestException as e:
            derniere = f"réseau : {e}"
            time.sleep(15 * (essai + 1))
            continue
        if r.status_code in (200, 201, 202):
            try:
                corps = r.json()
            except ValueError:
                corps = {}
            if isinstance(corps, dict) and corps.get("success") is False:
                raise ErreurPublication(f"refus d'Upload-Post : {str(corps)[:300]}")
            if isinstance(corps, dict):
                return str(corps.get("job_id") or corps.get("request_id") or corps.get("id") or "ok")
            return "ok"
        derniere = f"HTTP {r.status_code} : {r.text[:300]}"
        if r.status_code in (401, 403):
            raise ErreurPublication(f"clé API refusée ({derniere}). Vérifie UPLOAD_POST_API_KEY.")
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(30 * (essai + 1))
            continue
        raise ErreurPublication(derniere)
    raise ErreurPublication(derniere or "échec après 3 essais")
