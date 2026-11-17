#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
automate.py : le pilote automatique de la chaîne.

À chaque lancement (idéalement tous les matins, tout seul via le planificateur de tâches) :
  1. récupère les nouvelles vidéos des boîtes de réception (« sources » : dossiers Google Drive des
     campagnes de clipping, liens fournis par des créateurs qui ont dit oui) ;
     en option, les clips Twitch des créateurs autorisés (twitch.actif) ;
  2. traite aussi les longues vidéos déposées dans a_traiter/ (VOD autorisées, tes captures) ;
  3. monte chaque clip en 9:16 (accroche, crédit, sous-titres si activés, appel à l'abonnement) ;
  4. fabrique la compilation TOP 5 du jour (plus d'1 min) ;
  5. écrit publications.csv / publications.txt : horaire, fichier, légende et hashtags ;
  6. si la publication automatique est activée (publication.auto.actif), programme chaque vidéo
     sur TikTok via Upload-Post : plus rien à faire à la main.

Premier lancement :  python automate.py --init
Lancement normal  :  python automate.py
Voir sans rien télécharger : python automate.py --essai
Autre configuration : python automate.py --config config.cloud.json  (ou variable GTA6ZAP_CONFIG)
Les clés peuvent venir de variables d'environnement : TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET,
UPLOAD_POST_API_KEY (c'est ainsi que les fournit GitHub Actions).
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import clipper  # noqa: E402
import publication  # noqa: E402
import sources as boites  # noqa: E402

CONFIG = ICI / (os.environ.get("GTA6ZAP_CONFIG") or "config.json")
EXEMPLE = ICI / "config.exemple.json"
ETAT = ICI / ".etat"
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".m4v", ".ts", ".flv"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def dire(msg=""):
    print(msg, flush=True)


# --------------------------------------------------------------------------- état


def lire_json(chemin, defaut):
    try:
        return json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defaut


def ecrire_json(chemin, donnees):
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    Path(chemin).write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")


def charger_config():
    if not CONFIG.exists():
        clipper.stop(f"{CONFIG.name} n'existe pas encore. Lance d'abord : python automate.py --init")
    try:
        c = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        clipper.stop(f"{CONFIG.name} n'est pas un JSON valide (ligne {e.lineno}, colonne {e.colno}) : {e.msg}")
    t = c.setdefault("twitch", {})
    if os.environ.get("TWITCH_CLIENT_ID"):
        t["client_id"] = os.environ["TWITCH_CLIENT_ID"].strip()
    if os.environ.get("TWITCH_CLIENT_SECRET"):
        t["client_secret"] = os.environ["TWITCH_CLIENT_SECRET"].strip()
    auto = c.setdefault("publication", {}).setdefault("auto", {})
    if os.environ.get("UPLOAD_POST_API_KEY"):
        auto["cle_api"] = os.environ["UPLOAD_POST_API_KEY"].strip()
    return c


def fuseau(config):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(config.get("fuseau") or "Europe/Paris")
    except Exception:
        clipper.stop("Fuseau horaire introuvable. Installe tzdata : python -m pip install tzdata")


def maintenant(config):
    """Heure locale du fuseau de la chaîne (Paris par défaut), sans fuseau attaché."""
    return datetime.now(fuseau(config)).replace(tzinfo=None)


# --------------------------------------------------------------------------- Twitch


class Twitch:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.jeton = None

    def _http(self, url, data=None, entetes=None):
        req = urllib.request.Request(url, data=data, headers=entetes or {}, method="POST" if data else "GET")
        for essai in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                corps = e.read().decode("utf-8", "replace")[:300]
                if e.code == 429 and essai < 2:
                    time.sleep(5)
                    continue
                if e.code in (400, 401, 403):
                    clipper.stop(f"Twitch refuse la requête ({e.code}) : {corps}\n"
                                 f"Vérifie client_id et client_secret dans config.json.")
                if essai == 2:
                    clipper.stop(f"Twitch ne répond pas correctement ({e.code}) : {corps}")
            except urllib.error.URLError as e:
                if essai == 2:
                    clipper.stop(f"Impossible de joindre Twitch : {e.reason}. Vérifie ta connexion.")
            time.sleep(2 * (essai + 1))

    def connecter(self):
        cache = lire_json(ETAT / "jeton_twitch.json", {})
        if cache.get("client_id") == self.client_id and cache.get("expire", 0) > time.time() + 3600:
            self.jeton = cache["jeton"]
            return
        donnees = urllib.parse.urlencode({"client_id": self.client_id, "client_secret": self.client_secret,
                                          "grant_type": "client_credentials"}).encode()
        r = self._http("https://id.twitch.tv/oauth2/token", data=donnees,
                       entetes={"Content-Type": "application/x-www-form-urlencoded"})
        self.jeton = r["access_token"]
        ecrire_json(ETAT / "jeton_twitch.json", {"client_id": self.client_id, "jeton": self.jeton,
                                                 "expire": time.time() + int(r.get("expires_in", 3600))})

    def get(self, chemin, params):
        url = f"https://api.twitch.tv/helix/{chemin}?{urllib.parse.urlencode(params, doseq=True)}"
        return self._http(url, entetes={"Client-Id": self.client_id, "Authorization": f"Bearer {self.jeton}"})

    def id_jeu(self, nom):
        r = self.get("games", {"name": nom})
        data = r.get("data", [])
        return data[0]["id"] if data else None

    def utilisateurs(self, logins):
        trouves = {}
        for i in range(0, len(logins), 100):
            r = self.get("users", {"login": logins[i:i + 100]})
            for u in r.get("data", []):
                trouves[u["login"].lower()] = u
        return trouves

    def clips(self, broadcaster_id, depuis, max_pages=3):
        tous, curseur = [], None
        for _ in range(max_pages):
            params = {"broadcaster_id": broadcaster_id, "started_at": depuis, "first": 100}
            if curseur:
                params["after"] = curseur
            r = self.get("clips", params)
            tous.extend(r.get("data", []))
            curseur = (r.get("pagination") or {}).get("cursor")
            if not curseur:
                break
        return tous


def telecharger(url, dossier, ident):
    """Télécharge un clip Twitch avec yt-dlp ; renvoie le chemin du fichier."""
    dossier.mkdir(parents=True, exist_ok=True)
    deja = [p for p in dossier.glob(f"{ident}.*") if p.suffix.lower() in VIDEO_EXT]
    if deja:
        return deja[0]
    try:
        import yt_dlp
    except ImportError:
        clipper.stop("yt-dlp est introuvable : python -m pip install -U yt-dlp")
    options = {"outtmpl": str(dossier / f"{ident}.%(ext)s"), "quiet": True, "no_warnings": True,
               "noprogress": True, "format": "best[ext=mp4]/best", "retries": 3}
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    fichiers = [p for p in dossier.glob(f"{ident}.*") if p.suffix.lower() in VIDEO_EXT]
    if not fichiers:
        raise RuntimeError(f"téléchargement vide pour {url}")
    return fichiers[0]


# --------------------------------------------------------------------------- accroches


GLYPHES_OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ !?.,'%:-+&#()")


def hook_depuis_titre(titre, titres_repetes):
    """Le titre donné au clip par le viewer est souvent la meilleure accroche."""
    if not titre or titre in titres_repetes:
        return ""
    if re.search(r"https?:|\||#|![A-Za-z]|🔴|\bjour \d|\bday \d", titre, flags=re.IGNORECASE):
        return ""
    t = titre.replace("’", "'").upper()
    t = "".join(ch for ch in t if ch in GLYPHES_OK)
    t = " ".join(t.split())
    if len(t) < 6 or len(t) > 60:
        return ""
    return t


def essayer(quoi, fonction, *args, **kwargs):
    """Un fichier qui pose problème ne doit pas arrêter toute la série."""
    try:
        return fonction(*args, **kwargs)
    except SystemExit as e:
        dire(f"  {quoi} ignoré (voir le message ci-dessus).")
    except Exception as e:  # noqa: BLE001
        dire(f"  {quoi} ignoré : {e}")
    return None


def hook_auto(etat):
    i = etat.get("hook_index", 0)
    etat["hook_index"] = i + 1
    return clipper.HOOKS_AUTO[(i * 7) % len(clipper.HOOKS_AUTO)]


def sans_etoiles(t):
    return (t or "").replace("*", "")


def phrase(t):
    t = sans_etoiles(t).strip()
    if not t:
        return ""
    t = t.lower()
    return t[0].upper() + t[1:]


# --------------------------------------------------------------------------- planning


def creneaux(horaires, depart, nombre):
    """Prochains créneaux de publication à partir de `depart`."""
    sortie = []
    jour = depart.date()
    while len(sortie) < nombre:
        for h in horaires:
            hh, mm = [int(x) for x in h.split(":")]
            moment = datetime(jour.year, jour.month, jour.day, hh, mm)
            if moment > depart + timedelta(minutes=20):
                sortie.append(moment)
                if len(sortie) >= nombre:
                    break
        jour += timedelta(days=1)
    return sortie


def legende(item, hashtags):
    lignes = []
    if item.get("commercial"):
        lignes.append("Collaboration commerciale")
    accroche = phrase(item["hook"])
    if accroche:
        lignes.append(accroche)
    if item.get("credits"):
        lignes.append("🎥 " + " · ".join(item["credits"]))
    lignes.append("Abonne-toi pour le meilleur de GTA 6 chaque jour")
    for ajout in item.get("legende_ajout") or []:
        if ajout and ajout not in lignes:
            lignes.append(ajout)
    lignes.append(" ".join(hashtags))
    return "\n".join(lignes)


# --------------------------------------------------------------------------- pipeline


def reglages_montage(config):
    m = dict(config.get("montage", {}))
    m["pseudo"] = config.get("pseudo", clipper.DEFAUTS["pseudo"])
    return clipper.reglages(m)


def recolte_sources(config, etat, essai=False):
    """Boîtes de réception : dossiers Google Drive des campagnes, liens de créateurs autorisés."""
    liste = [s for s in config.get("sources", []) or [] if s.get("actif", True) is not False]
    if not liste:
        dire("Boîtes de réception : aucune source dans la configuration.")
        return []
    reg = reglages_montage(config)
    vus = set(etat.get("fichiers_vus", []))
    budget = int(config.get("max_clips_par_lancement", 5))
    produits = []
    for s in liste:
        nom = s.get("nom") or (s.get("lien") or "source")[:40]
        if not str(s.get("autorisation", "")).strip():
            dire(f"Source « {nom} » ignorée : aucune autorisation notée (campagne rejointe ou accord écrit).")
            continue
        if len(produits) >= budget:
            dire(f"Source « {nom} » : quota du jour atteint, elle passera au prochain lancement.")
            continue
        cache = ETAT / "telechargements" / clipper.slug(nom, 30)
        try:
            fichiers = boites.nouveaux_fichiers(s, cache, vus, int(s.get("videos_par_jour", 3)))
        except boites.ErreurSource as e:
            dire(f"Source « {nom} » : {e}")
            continue
        except Exception as e:  # noqa: BLE001 - une source en panne ne bloque pas les autres
            dire(f"Source « {nom} » : erreur inattendue ({str(e)[:200]})")
            continue
        dire(f"Source « {nom} » : {len(fichiers)} nouvelle(s) vidéo(s).")
        if essai:
            for _, chemin, nom_fichier in fichiers:
                dire(f"  [essai] {nom_fichier}")
            continue
        credit = s.get("credit", "")
        ajout = s.get("legende_ajout", "")
        commun = {"credits": [credit] if credit else [], "credit": credit,
                  "commercial": bool(s.get("collaboration_commerciale", True)),
                  "legende_ajout": [ajout] if ajout else []}
        for ident, chemin, nom_fichier in fichiers:
            if len(produits) >= budget:
                break  # vidéo non marquée comme vue : elle sera reprise au prochain lancement
            vus.add(ident)
            info = essayer(nom_fichier, clipper.sonder, chemin)
            if info is None:
                continue
            if s.get("retouche", True) is False:
                sortie = config["_jour"] / f"src_{clipper.slug(nom, 16)}_{len(produits) + 1:02d}{chemin.suffix.lower()}"
                shutil.copy(chemin, sortie)
                dire(f"[{nom}] {sortie.name} (publiée telle quelle, sans retouche)")
                produits.append({"fichier": sortie, "duree": info["duree"], "hook": "", "poids": 1000.0,
                                 "source": chemin, "debut": 0.0, "fin": info["duree"],
                                 "origine": f"source:{nom}", **commun})
                continue
            if info["duree"] <= float(s.get("duree_max_clip", 75)) or not info["audio"]:
                moments = [{"debut": 0.0, "fin": info["duree"], "score": 10.0}]
            else:
                r = essayer(nom_fichier, clipper.reperer_moments, chemin, nombre=int(s.get("clips_par_video", 3)))
                moments = r[0] if r else []
            for m in sorted(moments, key=lambda m: m["score"], reverse=True):
                if len(produits) >= budget:
                    break
                hook = hook_auto(etat) if s.get("accroche", True) is not False else ""
                sortie = config["_jour"] / (f"src_{clipper.slug(nom, 16)}_{len(produits) + 1:02d}_"
                                            f"{clipper.slug(sans_etoiles(hook) or nom_fichier)}.mp4")
                dire(f"[{nom}] {sortie.name}  ({clipper.fmt_temps(m['debut'])} -> {clipper.fmt_temps(m['fin'])})")
                d = essayer(sortie.name, clipper.rendre, chemin, m["debut"], m["fin"], sortie,
                            dict(reg, credit=credit), hook=hook)
                if d is None:
                    continue
                produits.append({"fichier": sortie, "duree": d, "hook": hook, "poids": m["score"] * 100,
                                 "source": chemin, "debut": m["debut"], "fin": m["fin"],
                                 "origine": f"source:{nom}", **commun})
    etat["fichiers_vus"] = sorted(vus)[-20000:]
    return produits


def recolte_twitch(config, etat, essai):
    t = config.get("twitch", {}) or {}
    if t.get("actif") is False:
        return []
    if not t.get("client_id") or not t.get("client_secret"):
        dire("Twitch : client_id / client_secret vides dans config.json, étape ignorée.")
        return []
    createurs = []
    for c in config.get("createurs", []):
        login = (c.get("twitch") or "").strip().lower()
        if not login or c.get("actif", True) is False:
            continue
        if not str(c.get("autorisation", "")).strip():
            dire(f"Twitch : « {login} » ignoré, aucune autorisation notée dans config.json.")
            continue
        createurs.append({**c, "twitch": login})
    if not createurs:
        dire("Twitch : aucun créateur autorisé dans config.json, étape ignorée.")
        return []

    api = Twitch(t["client_id"], t["client_secret"])
    api.connecter()
    jeu_nom = t.get("jeu", "Grand Theft Auto VI")
    jeu = etat.get("jeux", {}).get(jeu_nom) or api.id_jeu(jeu_nom)
    if jeu:
        etat.setdefault("jeux", {})[jeu_nom] = jeu
    else:
        dire(f"Twitch : le jeu « {jeu_nom} » est introuvable, les clips ne sont pas filtrés par jeu.")
    comptes = api.utilisateurs([c["twitch"] for c in createurs])
    depuis = (datetime.now(timezone.utc) - timedelta(hours=float(t.get("heures", 24)))).strftime("%Y-%m-%dT%H:%M:%SZ")
    vus = set(etat.get("clips_vus", []))
    candidats = []
    for c in createurs:
        u = comptes.get(c["twitch"])
        if not u:
            dire(f"Twitch : compte « {c['twitch']} » introuvable.")
            continue
        clips = api.clips(u["id"], depuis)
        titres = [x.get("title", "") for x in clips]
        repetes = {x for x in titres if titres.count(x) >= 2}
        retenus = [x for x in clips
                   if (not jeu or x.get("game_id") == jeu)
                   and int(x.get("view_count", 0)) >= int(t.get("vues_min", 300))
                   and x["id"] not in vus
                   and (not t.get("langue") or x.get("language", t["langue"]) == t["langue"])]
        retenus.sort(key=lambda x: int(x.get("view_count", 0)), reverse=True)
        retenus = retenus[: int(t.get("clips_par_streamer", 3))]
        dire(f"Twitch : {u.get('display_name', c['twitch'])} : {len(clips)} clips sur la période, {len(retenus)} retenus.")
        for x in retenus:
            candidats.append({
                "type": "twitch", "id": x["id"], "url": x["url"], "vues": int(x.get("view_count", 0)),
                "titre": x.get("title", ""), "duree": float(x.get("duration", 0)),
                "credit": c.get("tiktok") or ("@" + u.get("login", c["twitch"])),
                "credit_texte": f"{u.get('display_name', c['twitch'])} (twitch.tv/{u.get('login', c['twitch'])})",
                "hook_titre": hook_depuis_titre(x.get("title", ""), repetes),
            })
    candidats.sort(key=lambda x: x["vues"], reverse=True)
    max_jour = int(config.get("max_clips_par_lancement", 5))
    candidats = candidats[:max_jour]
    if essai:
        for x in candidats:
            dire(f"  [essai] {x['vues']:>7} vues  {x['credit']:<22} {x['titre'][:60]}")
        return []

    produits = []
    reg = reglages_montage(config)
    dl = ETAT / "telechargements"
    for i, x in enumerate(candidats, start=1):
        try:
            fichier = telecharger(x["url"], dl, x["id"])
        except Exception as e:  # un clip supprimé ou privé ne doit pas bloquer les autres
            dire(f"  clip {x['id']} ignoré : {e}")
            continue
        hook = x["hook_titre"] if config.get("accroche_titre_twitch", True) and x["hook_titre"] else hook_auto(etat)
        o = dict(reg, credit=x["credit"])
        sortie = config["_jour"] / f"tw_{i:02d}_{clipper.slug(sans_etoiles(hook))}.mp4"
        dire(f"[Twitch {i}/{len(candidats)}] {sortie.name}  ({x['vues']} vues sur Twitch)")
        d = essayer(f"clip {x['id']}", clipper.rendre, fichier, 0.0, None, sortie, o, hook=hook)
        vus.add(x["id"])
        if d is None:
            continue
        produits.append({"fichier": sortie, "duree": d, "hook": hook, "poids": x["vues"],
                         "credits": [x["credit_texte"]], "source": fichier, "credit": x["credit"],
                         "origine": f"twitch:{x['id']}"})
    etat["clips_vus"] = sorted(vus)[-5000:]
    return produits


def recolte_dossier(config, etat):
    dossier = ICI / config.get("dossier_vod", "a_traiter")
    dossier.mkdir(parents=True, exist_ok=True)
    traites = dossier / "traites"
    fichiers = [p for p in dossier.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXT
                and traites not in p.parents]
    if not fichiers:
        dire(f"Dossier {dossier.name}/ : rien de nouveau.")
        return []
    autorises = {(c.get("twitch") or "").lower(): c for c in config.get("createurs", [])
                 if str(c.get("autorisation", "")).strip()}
    reg = reglages_montage(config)
    produits = []
    for f in sorted(fichiers):
        sous = f.parent.name.lower() if f.parent != dossier else ""
        if sous and sous not in autorises:
            dire(f"{f.name} : le dossier « {f.parent.name} » ne correspond à aucun créateur autorisé "
                 f"dans config.json, fichier ignoré.")
            continue
        c = autorises.get(sous, {})
        credit = c.get("tiktok") or (("@" + sous) if sous else "")
        info = essayer(f.name, clipper.sonder, f)
        if info is None:
            continue
        if info["duree"] <= 90 or not info["audio"]:
            moments = [{"debut": 0.0, "fin": info["duree"], "score": 10.0}]
        else:
            r = essayer(f.name, clipper.reperer_moments, f, nombre=int(config.get("clips_par_vod", 4)))
            moments = r[0] if r else []
        if not moments:
            dire(f"{f.name} : aucun moment fort détecté.")
        for i, m in enumerate(sorted(moments, key=lambda m: m["score"], reverse=True), start=1):
            hook = hook_auto(etat)
            sortie = config["_jour"] / f"vod_{clipper.slug(f.stem, 20)}_{i:02d}_{clipper.slug(sans_etoiles(hook))}.mp4"
            dire(f"[VOD {f.name} {i}/{len(moments)}] {sortie.name}")
            d = essayer(sortie.name, clipper.rendre, f, m["debut"], m["fin"], sortie, dict(reg, credit=credit),
                        hook=hook)
            if d is None:
                continue
            produits.append({"fichier": sortie, "duree": d, "hook": hook, "poids": m["score"] * 100,
                             "credits": [credit] if credit else [], "source": f, "credit": credit,
                             "debut": m["debut"], "fin": m["fin"], "origine": f"vod:{f.name}"})
        cible = traites / f.relative_to(dossier)
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(cible))
    return produits


def compilation_du_jour(config, produits):
    if not config.get("compilation_du_jour", True) or len(produits) < 5:
        return None
    meilleurs = sorted(produits, key=lambda p: p["poids"], reverse=True)[:7]
    segments, total = [], 0.0
    for p in meilleurs:
        fin = p.get("fin")
        if fin is None:
            fin = clipper.sonder(p["source"])["duree"]
        debut = max(p.get("debut", 0.0) or 0.0, fin - 16.0)
        segments.append({"p": p, "debut": debut, "fin": fin})
        total += fin - debut
        if len(segments) >= 5 and total >= 66:
            break
    if total < 61:
        return None
    segments.reverse()  # le meilleur en dernier
    n = len(segments)
    lot = {"sources": {}}
    comp = {"nom": f"top{n}_du_jour", "titre": f"TOP {n} DES MOMENTS LES PLUS *FOUS* DU JOUR",
            "classement": True, "segments": []}
    for i, s in enumerate(segments):
        alias = f"s{i}"
        lot["sources"][alias] = {"fichier": str(s["p"]["source"]), "credit": s["p"]["credit"], "autorisation": "oui"}
        comp["segments"].append({"source": alias, "debut": round(s["debut"], 2), "fin": round(s["fin"], 2), "label": ""})
    reglages = dict(config.get("montage", {}), pseudo=config.get("pseudo", clipper.DEFAUTS["pseudo"]))
    r = essayer("compilation du jour", clipper.rendre_compilation, lot, comp, reglages, ICI, config["_jour"])
    if r is None:
        return None
    sortie, d = r
    credits = []
    for s in segments:
        for c in s["p"]["credits"]:
            if c not in credits:
                credits.append(c)
    ajouts = []
    for s in segments:
        for x in s["p"].get("legende_ajout") or []:
            if x not in ajouts:
                ajouts.append(x)
    return {"fichier": sortie, "duree": d, "hook": comp["titre"], "poids": 10 ** 9, "credits": credits,
            "origine": "compilation", "commercial": any(s["p"].get("commercial") for s in segments),
            "legende_ajout": ajouts}


def ecrire_planning(config, produits, etat):
    pub = config.get("publication", {}) or {}
    horaires = pub.get("horaires") or ["12:00", "14:00", "17:00", "18:30", "20:30", "22:30"]
    jeux_hashtags = pub.get("hashtags") or [["#gta6", "#gtavi", "#gta6clips", "#gamingtiktok", "#gaming"]]
    file_attente = etat.get("file_attente_fin")
    depart = maintenant(config)
    if file_attente:
        try:
            depart = max(depart, datetime.fromisoformat(file_attente))
        except ValueError:
            pass
    # meilleurs créneaux du soir pour les meilleurs clips : on trie par poids puis on alterne
    tries = sorted(produits, key=lambda p: p["poids"], reverse=True)
    slots = creneaux(horaires, depart, len(tries))
    soir = sorted(range(len(slots)), key=lambda i: (slots[i].date(), -int(slots[i].hour >= 18), slots[i]))
    attribution = [None] * len(slots)
    for p, i in zip(tries, soir):
        attribution[i] = p
    lignes = []
    for i, (slot, p) in enumerate(zip(slots, attribution)):
        hashtags = jeux_hashtags[(etat.get("hashtag_index", 0) + i) % len(jeux_hashtags)]
        lignes.append({
            "date": slot.strftime("%Y-%m-%d"), "heure": slot.strftime("%H:%M"),
            "fichier": Path(p["fichier"]).name, "duree_s": f"{p['duree']:.0f}",
            "legende": legende(p, hashtags), "origine": p.get("origine", ""),
            "publication": "à programmer", "_quand": slot, "_chemin": Path(p["fichier"]),
        })
    etat["hashtag_index"] = etat.get("hashtag_index", 0) + len(lignes)
    if slots:
        etat["file_attente_fin"] = max(slots).isoformat()
        avance = (max(slots) - maintenant(config)).total_seconds() / 86400
        if avance > 3:
            dire(f"ATTENTION : la file de publication est pleine jusqu'au {max(slots):%d/%m %H:%M}. "
                 f"Baisse max_clips_par_lancement ou clips_par_vod, ou ajoute des horaires.")

    publier_auto(config, lignes)

    jour = config["_jour"]
    colonnes = ["date", "heure", "fichier", "duree_s", "legende", "origine", "publication"]
    with open(jour / "publications.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)
    manuelles = [l for l in lignes if not l["publication"].startswith("programmée")]
    with open(jour / "publications.txt", "w", encoding="utf-8") as f:
        auto = [l for l in lignes if l["publication"].startswith("programmée")]
        if auto:
            f.write(f"DÉJÀ PROGRAMMÉES AUTOMATIQUEMENT ({len(auto)})\n")
            for l in sorted(auto, key=lambda x: (x["date"], x["heure"])):
                f.write(f"[x] {l['date']} {l['heure']}  ->  {l['fichier']}  ({l['publication']})\n")
            f.write("\n")
        if manuelles:
            f.write("À PROGRAMMER (TikTok Studio sur ordinateur > Téléverser > Programmer)\n")
            f.write("Coche chaque ligne une fois programmée. Si une heure est déjà passée, publie la vidéo tout de suite.\n\n")
            for l in sorted(manuelles, key=lambda x: (x["date"], x["heure"])):
                note = "" if l["publication"] == "à programmer" else f"   [{l['publication']}]"
                f.write(f"[ ] {l['date']} {l['heure']}  ->  {l['fichier']}  ({l['duree_s']} s){note}\n")
                f.write("-" * 60 + "\n" + l["legende"] + "\n\n")
        f.write("Après publication : colle le lien de chaque vidéo dans ta campagne de clipping.\n")
    journal = ICI / "journal_publications.csv"
    neuf = not journal.exists()
    with open(journal, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if neuf:
            w.writerow(["genere_le", "date_prevue", "heure", "dossier", "fichier", "origine", "publication"])
        for l in lignes:
            w.writerow([maintenant(config).strftime("%Y-%m-%d %H:%M"), l["date"], l["heure"], jour.name,
                        l["fichier"], l["origine"], l["publication"]])
    return lignes


def publier_auto(config, lignes):
    """Programme chaque vidéo via Upload-Post si publication.auto.actif est vrai."""
    auto = (config.get("publication", {}) or {}).get("auto", {}) or {}
    if not auto.get("actif") or not lignes:
        return
    tz = fuseau(config)
    plateformes = auto.get("plateformes") or ["tiktok"]
    dire(f"\nPublication automatique ({', '.join(plateformes)}) via Upload-Post :")
    for l in sorted(lignes, key=lambda x: x["_quand"]):
        quand = l["_quand"].replace(tzinfo=tz)
        try:
            ident = publication.programmer(auto.get("cle_api", ""), auto.get("profil", ""), l["_chemin"],
                                           l["legende"], quand, plateformes)
            l["publication"] = f"programmée, tâche {ident}"
            dire(f"  OK      {l['date']} {l['heure']}  {l['fichier']}")
        except publication.ErreurPublication as e:
            l["publication"] = f"ÉCHEC : {e}"
            dire(f"  ÉCHEC   {l['date']} {l['heure']}  {l['fichier']} : {e}")


def init():
    if CONFIG.exists():
        dire(f"config.json existe déjà : {CONFIG}")
    else:
        shutil.copy(EXEMPLE, CONFIG)
        dire(f"config.json créé : {CONFIG}")
    for d in ("a_traiter", "a_publier"):
        (ICI / d).mkdir(exist_ok=True)
    dire("\nÀ remplir dans config.json :")
    dire("  1. twitch.client_id et twitch.client_secret (dev.twitch.tv > Your Console > Applications > Register).")
    dire("  2. createurs : un bloc par streamer qui t'a dit oui, avec la preuve dans « autorisation ».")
    dire("  3. pseudo : ton @ TikTok.")
    dire("Puis teste : python automate.py --essai")


def main():
    ap = argparse.ArgumentParser(description="Pilote automatique : récolte, montage et planning de publication.")
    ap.add_argument("--init", action="store_true", help="crée config.json et les dossiers")
    ap.add_argument("--essai", action="store_true", help="liste les clips Twitch qui seraient pris, sans rien télécharger")
    ap.add_argument("--sans-twitch", action="store_true")
    ap.add_argument("--sans-dossier", action="store_true")
    ap.add_argument("--config", help="fichier de configuration (défaut config.json)")
    a = ap.parse_args()
    global CONFIG
    if a.config:
        CONFIG = (Path.cwd() / a.config) if not Path(a.config).is_absolute() else Path(a.config)
        if not CONFIG.exists():
            CONFIG = ICI / a.config
    if a.init:
        init()
        return
    clipper.verifier_ffmpeg()
    clipper.importer_pillow()
    config = charger_config()
    etat = lire_json(ETAT / "etat.json", {})
    jour = ICI / config.get("dossier_sortie", "a_publier") / maintenant(config).strftime("%Y-%m-%d")
    jour.mkdir(parents=True, exist_ok=True)
    config["_jour"] = jour
    dire(f"=== Pilote automatique {maintenant(config):%d/%m/%Y %H:%M} ({config.get('fuseau') or 'Europe/Paris'}) ===")

    produits = []
    try:
        produits += recolte_sources(config, etat, a.essai)
        if not a.sans_twitch:
            produits += recolte_twitch(config, etat, a.essai)
        if a.essai:
            return
        if not a.sans_dossier:
            produits += recolte_dossier(config, etat)
        if not produits:
            dire("\nAucun nouveau clip aujourd'hui.")
            return
        compil = compilation_du_jour(config, produits)
        if compil:
            produits.append(compil)
        lignes = ecrire_planning(config, produits, etat)
    finally:
        config.pop("_jour", None)
        ecrire_json(ETAT / "etat.json", etat)

    dire(f"\n{len(produits)} vidéos prêtes dans {jour}")
    for l in sorted(lignes, key=lambda x: (x["date"], x["heure"])):
        dire(f"  {l['date']} {l['heure']}  {l['fichier']}  ({l['duree_s']} s)  {l['publication']}")
    echecs = [l for l in lignes if l["publication"].startswith("ÉCHEC")]
    restantes = [l for l in lignes if not l["publication"].startswith("programmée")]
    if not restantes:
        dire("\nTout est programmé automatiquement. Rien à faire.")
    else:
        dire(f"\n{len(restantes)} vidéo(s) à programmer à la main : voir {jour / 'publications.txt'}")
    if echecs:
        sys.exit(2)  # fait échouer l'exécution GitHub Actions : GitHub t'envoie un e-mail


if __name__ == "__main__":
    main()
