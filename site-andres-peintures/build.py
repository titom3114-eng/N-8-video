#!/usr/bin/env python3
"""Génère le site statique Andres Peintures dans public/.

    python3 build.py

Lit site.json (coordonnées, réglages), les gabarits de src/partials/ et les pages de src/pages/,
puis écrit des pages HTML complètes dans public/ avec les fichiers de src/static/.
Aucune dépendance : Python 3.8 ou plus récent suffit.

Syntaxe des gabarits :
  {{cle}}              valeur échappée          {{{cle}}}            valeur brute (HTML)
  {{#cle}}…{{/cle}}    bloc affiché si la valeur est renseignée
  {{^cle}}…{{/cle}}    bloc affiché si la valeur est vide
  {{> nom}}            insère src/partials/nom.html
  {{i:nom}}            icône du jeu src/partials/icones.svg
  {{img:nom|texte alternatif|sizes|eager}}   image src/static/img/nom-800.webp et nom-1600.webp
"""
import base64
import datetime
import hashlib
import html
import json
import re
import shutil
import struct
import sys
import urllib.parse
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SRC = RACINE / "src"
SORTIE = RACINE / "public"

METIERS = [
    {"id": "peinture", "nom": "Peinture", "detail": "Murs, plafonds, boiseries, volets", "icone": "rouleau"},
    {"id": "facade", "nom": "Façade", "detail": "Ravalement, enduits, brique, patrimoine", "icone": "facade"},
    {"id": "platrerie", "nom": "Plâtrerie", "detail": "Cloisons, doublages, faux plafonds", "icone": "cloison"},
    {"id": "sols", "nom": "Sols", "detail": "Parquet, stratifié, PVC, moquette", "icone": "sol"},
]
PAGES_NAV = ["peinture", "facade", "platrerie", "sols", "entreprise", "contact"]
SCRIPT_JS = 'document.documentElement.classList.add("js")'
APPEL_TITRE = "Un projet de peinture, de façade, de plâtrerie ou de sol ?"


class ErreurGabarit(Exception):
    pass


# --------------------------------------------------------------------------- outils
def telephone_lien(numero):
    chiffres = re.sub(r"[^\d+]", "", numero or "")
    if not chiffres:
        return ""
    if chiffres.startswith("0") and len(chiffres) == 10:
        chiffres = "+33" + chiffres[1:]
    return "tel:" + chiffres


def dimensions_webp(chemin):
    """Largeur et hauteur d'une image WebP (VP8, VP8L ou VP8X), sans bibliothèque externe."""
    donnees = chemin.read_bytes()[:40]
    if donnees[:4] != b"RIFF" or donnees[8:12] != b"WEBP":
        raise ValueError(f"{chemin} n'est pas une image WebP")
    bloc = donnees[12:16]
    if bloc == b"VP8X":
        largeur = 1 + int.from_bytes(donnees[24:27], "little")
        hauteur = 1 + int.from_bytes(donnees[27:30], "little")
    elif bloc == b"VP8 ":
        largeur, hauteur = struct.unpack("<HH", donnees[26:30])
        largeur &= 0x3FFF
        hauteur &= 0x3FFF
    elif bloc == b"VP8L":
        b = donnees[21:25]
        largeur = 1 + (((b[1] & 0x3F) << 8) | b[0])
        hauteur = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
    else:
        raise ValueError(f"Format WebP inconnu pour {chemin}")
    return largeur, hauteur


def annees_texte(annees):
    if annees % 5 == 0:
        return f"{annees} ans"
    return f"plus de {annees // 5 * 5} ans"


def lire_page(chemin):
    texte = chemin.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->\s*", texte, re.S)
    if not m:
        raise ErreurGabarit(f"{chemin.name} : en-tête <!-- … --> manquant")
    meta = {}
    for ligne in m.group(1).strip().splitlines():
        if ligne.strip():
            cle, _, valeur = ligne.partition(":")
            meta[cle.strip()] = valeur.strip()
    return meta, texte[m.end():]


# --------------------------------------------------------------------------- moteur de gabarits
class Gabarits:
    def __init__(self):
        self.partiels = {p.stem: p.read_text(encoding="utf-8") for p in (SRC / "partials").glob("*.html")}
        sprite = (SRC / "partials" / "icones.svg").read_text(encoding="utf-8")
        self.icones = set(re.findall(r'<symbol id="i-([\w-]+)"', sprite))
        self.sprite = sprite.strip()
        self.images = {}
        for p in (SRC / "static" / "img").glob("*-1600.webp"):
            self.images[p.name[: -len("-1600.webp")]] = dimensions_webp(p)

    def icone(self, nom):
        if nom not in self.icones:
            raise ErreurGabarit(f"icône inconnue : {nom}")
        return f'<svg class="icone" aria-hidden="true"><use href="#i-{nom}"/></svg>'

    def image(self, arguments):
        parties = arguments.split("|")
        nom = parties[0].strip()
        alt = parties[1].strip() if len(parties) > 1 else ""
        sizes = parties[2].strip() if len(parties) > 2 and parties[2].strip() else "100vw"
        prioritaire = len(parties) > 3 and parties[3].strip() == "eager"
        if nom not in self.images:
            raise ErreurGabarit(f"image inconnue : {nom} (attendu : src/static/img/{nom}-1600.webp)")
        largeur, hauteur = self.images[nom]
        chargement = 'fetchpriority="high"' if prioritaire else 'loading="lazy"'
        return (
            f'<img src="img/{nom}-1600.webp" srcset="img/{nom}-800.webp 800w, img/{nom}-1600.webp 1600w" '
            f'sizes="{html.escape(sizes)}" width="{largeur}" height="{hauteur}" alt="{html.escape(alt)}" '
            f'{chargement} decoding="async">'
        )

    def rendre(self, texte, ctx, profondeur=0):
        if profondeur > 10:
            raise ErreurGabarit("inclusions trop profondes")
        # Inclusions
        texte = re.sub(
            r"\{\{>\s*([\w-]+)\s*\}\}",
            lambda m: self.rendre(self._partiel(m.group(1)), ctx, profondeur + 1),
            texte,
        )
        # Blocs conditionnels, du plus intérieur au plus extérieur
        motif = re.compile(r"\{\{([#^])([\w]+)\}\}((?:(?!\{\{[#^]\2\}\}).)*?)\{\{/\2\}\}", re.S)
        while True:
            nouveau = motif.sub(lambda m: self._bloc(m, ctx), texte)
            if nouveau == texte:
                break
            texte = nouveau
        texte = re.sub(r"\{\{i:([\w-]+)\}\}", lambda m: self.icone(m.group(1)), texte)
        texte = re.sub(r"\{\{img:([^}]+)\}\}", lambda m: self.image(m.group(1)), texte)
        texte = re.sub(r"\{\{\{\s*([\w]+)\s*\}\}\}", lambda m: str(self._valeur(m.group(1), ctx)), texte)
        texte = re.sub(r"\{\{\s*([\w]+)\s*\}\}", lambda m: html.escape(str(self._valeur(m.group(1), ctx))), texte)
        reste = re.search(r"\{\{.*?\}\}", texte)
        if reste:
            raise ErreurGabarit(f"balise non résolue : {reste.group(0)}")
        return texte

    def _partiel(self, nom):
        if nom not in self.partiels:
            raise ErreurGabarit(f"gabarit inconnu : {nom}")
        return self.partiels[nom]

    @staticmethod
    def _valeur(cle, ctx):
        if cle not in ctx:
            raise ErreurGabarit(f"valeur inconnue : {cle}")
        valeur = ctx[cle]
        return "" if valeur is None else valeur

    def _bloc(self, m, ctx):
        signe, cle, contenu = m.groups()
        actif = bool(self._valeur(cle, ctx))
        return contenu if actif == (signe == "#") else ""


# --------------------------------------------------------------------------- contexte
def contexte_global(config):
    ent, coord, zone, site = config["entreprise"], config["coordonnees"], config["zone_intervention"], config["site"]
    aujourd_hui = datetime.date.today()
    annees = aujourd_hui.year - int(ent["annee_creation"])
    adresse_complete = f'{coord["adresse_rue"]}, {coord["code_postal"]} {coord["ville"]}'
    url = site.get("url", "").strip().rstrip("/")
    email = coord.get("email", "").strip()
    lat, lon = float(coord["latitude"]), float(coord["longitude"])
    mode_formulaire = site.get("formulaire", "netlify").strip()
    if mode_formulaire == "courriel" and not email:
        print("Attention : formulaire « courriel » demandé sans adresse e-mail, retour au mode « netlify ».")
        mode_formulaire = "netlify"
    if mode_formulaire == "courriel":
        form_attributs = f'method="post" action="merci.html" data-courriel="{html.escape(email)}"'
    else:
        form_attributs = 'name="devis" method="post" action="merci.html" data-netlify="true" netlify-honeypot="site_web"'
    texte_annees = annees_texte(annees)
    ctx = {
        "raison_sociale": ent["raison_sociale"],
        "nom_commercial": ent["nom_commercial"],
        "gerant": ent["gerant"],
        "annee_creation": str(ent["annee_creation"]),
        "forme_juridique": ent["forme_juridique"],
        "capital": ent["capital"],
        "siren": ent["siren"],
        "siret": ent["siret"],
        "rcs": ent["rcs"],
        "tva": ent["tva"],
        "naf": ent["naf"],
        "adresse_rue": coord["adresse_rue"],
        "code_postal": coord["code_postal"],
        "ville": coord["ville"],
        "quartier": coord["quartier"],
        "adresse_complete": adresse_complete,
        "tel": coord.get("telephone", "").strip(),
        "tel_lien": telephone_lien(coord.get("telephone", "")),
        "tel_mobile": coord.get("telephone_mobile", "").strip(),
        "tel_mobile_lien": telephone_lien(coord.get("telephone_mobile", "")),
        "email": email,
        "email_lien": f"mailto:{email}" if email else "",
        "horaires": coord.get("horaires", "").strip(),
        "zone_resume": zone["resume"],
        "communes_li": "\n        ".join(f"<li>{html.escape(c)}</li>" for c in zone["communes"]),
        "communes_options": "\n              ".join(f'<option value="{html.escape(c)}">' for c in zone["communes"]),
        "annee": str(aujourd_hui.year),
        "annees_experience": texte_annees,
        "annees_experience_titre": texte_annees[:1].upper() + texte_annees[1:],
        "url": url,
        "hebergeur_nom": site["hebergeur_nom"],
        "hebergeur_adresse": site["hebergeur_adresse"],
        "hebergeur_site": site["hebergeur_site"],
        "form_attributs": form_attributs,
        "form_netlify": mode_formulaire == "netlify",
        "lien_itineraire": "https://www.google.com/maps/search/?api=1&query="
        + urllib.parse.quote_plus(f'{ent["raison_sociale"]} {adresse_complete}'),
        "osm_embed": "https://www.openstreetmap.org/export/embed.html?"
        + urllib.parse.urlencode(
            {"bbox": f"{lon - 0.012:.5f},{lat - 0.006:.5f},{lon + 0.012:.5f},{lat + 0.006:.5f}", "layer": "mapnik", "marker": f"{lat},{lon}"}
        ),
        "script_js": SCRIPT_JS,
    }
    return ctx


def json_ld(donnees):
    return '<script type="application/ld+json">' + json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


def jsonld_entreprise(config, ctx):
    ent, coord, zone = config["entreprise"], config["coordonnees"], config["zone_intervention"]
    donnees = {
        "@context": "https://schema.org",
        "@type": "HousePainter",
        "name": ent["nom_commercial"],
        "legalName": ent["raison_sociale"],
        "foundingDate": str(ent["annee_creation"]),
        "founder": {"@type": "Person", "name": ent["gerant"]},
        "address": {
            "@type": "PostalAddress",
            "streetAddress": coord["adresse_rue"],
            "postalCode": coord["code_postal"],
            "addressLocality": coord["ville"],
            "addressCountry": "FR",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": coord["latitude"], "longitude": coord["longitude"]},
        "areaServed": [{"@type": "City", "name": c} for c in zone["communes"]],
        "vatID": ent["tva"],
        "knowsAbout": ["Peinture intérieure", "Peinture extérieure", "Ravalement de façade", "Plâtrerie", "Revêtements de sols"],
        "award": [
            "1er Prix Restauration du Patrimoine Remarquable, Ville de Toulouse (2026)",
            "1er Prix Restauration du Patrimoine Domestique, Ville de Toulouse (2026)",
            "1er prix de la plus belle rénovation de devanture commerciale 2024, Ville de Toulouse (2025)",
        ],
    }
    if ctx["tel"]:
        donnees["telephone"] = ctx["tel_lien"].replace("tel:", "")
    if ctx["email"]:
        donnees["email"] = ctx["email"]
    if ctx["url"]:
        donnees["url"] = ctx["url"] + "/"
        donnees["logo"] = ctx["url"] + "/img/logo-andres-peintures.png"
        donnees["image"] = ctx["url"] + "/img/og-image.jpg"
    return json_ld(donnees)


def fil_ariane(meta, ctx, gab):
    if not meta.get("fil"):
        return "", ""
    elements = [("Accueil", "index.html")]
    for morceau in meta["fil"].split(";"):
        libelle, _, lien = morceau.strip().partition("|")
        elements.append((libelle.strip(), lien.strip()))
    lis = []
    for i, (libelle, lien) in enumerate(elements):
        if i == len(elements) - 1:
            lis.append(f'<li><span aria-current="page">{html.escape(libelle)}</span></li>')
        else:
            lis.append(f'<li><a href="{lien}">{html.escape(libelle)}</a></li>')
    nav = '<nav class="fil-ariane" aria-label="Fil d\'Ariane"><ol>' + "".join(lis) + "</ol></nav>"
    ld = ""
    if ctx["url"]:
        items = []
        for i, (libelle, lien) in enumerate(elements, start=1):
            item = {"@type": "ListItem", "position": i, "name": libelle}
            if i < len(elements):
                item["item"] = ctx["url"] + "/" + ("" if lien == "index.html" else lien)
            items.append(item)
        ld = json_ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})
    return nav, ld


def tuiles_metiers(gab, exclure=None):
    morceaux = []
    for m in METIERS:
        if m["id"] == exclure:
            continue
        morceaux.append(
            f'<li class="teinte-{m["id"]}"><a class="tuile" href="{m["id"]}.html">'
            f'<span class="tuile__icone">{gab.icone(m["icone"])}</span>'
            f'<span><span class="tuile__nom">{m["nom"]}</span><span class="tuile__detail">{m["detail"]}</span></span></a></li>'
        )
    return "\n      ".join(morceaux)


# --------------------------------------------------------------------------- construction
def construire():
    config = json.loads((RACINE / "site.json").read_text(encoding="utf-8"))
    gab = Gabarits()
    ctx_global = contexte_global(config)

    if SORTIE.exists():
        shutil.rmtree(SORTIE)
    shutil.copytree(SRC / "static", SORTIE)

    empreinte = hashlib.sha256()
    for fichier in sorted((SORTIE / "css").glob("*")) + sorted((SORTIE / "js").glob("*")):
        empreinte.update(fichier.read_bytes())
    ctx_global["version"] = empreinte.hexdigest()[:10]

    pages = sorted((SRC / "pages").glob("*.html"))
    plan = []
    for chemin in pages:
        meta, corps = lire_page(chemin)
        page_id = meta.get("page", chemin.stem)
        ctx = dict(ctx_global)
        ctx["titre"] = meta["titre"]
        ctx["description"] = meta["description"]
        ctx["robots"] = meta.get("robots", "")
        ctx["appel_titre"] = meta.get("appel_titre", APPEL_TITRE)
        ctx["appel_lien"] = f'contact.html?metier={meta["teinte"]}#devis' if meta.get("teinte") else "contact.html"
        nom_sortie = chemin.name
        indexable = ctx["robots"] != "noindex"
        ctx["canonique"] = (ctx["url"] + "/" + ("" if nom_sortie == "index.html" else nom_sortie)) if ctx["url"] and indexable else ""
        for p in PAGES_NAV:
            ctx[f"actif_{p}"] = ' aria-current="page"' if p == page_id else ""
        ctx["fil_ariane"], ld_fil = fil_ariane(meta, ctx, gab)
        ld = jsonld_entreprise(config, ctx) if meta.get("jsonld_entreprise") == "oui" else ""
        ctx["jsonld"] = "\n".join(x for x in (ld, ld_fil) if x)
        ctx["autres_metiers"] = tuiles_metiers(gab, exclure=page_id)
        ctx["tous_metiers"] = tuiles_metiers(gab)

        tete = gab.rendre(gab.partiels["head"], ctx)
        if page_id == "introuvable":
            tete = tete.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<base href="/">', 1)
        document = (
            '<!doctype html>\n<html lang="fr">\n<head>\n'
            + tete.strip()
            + "\n</head>\n<body>\n"
            + gab.sprite
            + "\n"
            + gab.rendre(gab.partiels["entete"], ctx).strip()
            + '\n<main id="contenu">\n'
            + gab.rendre(corps, ctx).strip()
            + "\n</main>\n"
            + gab.rendre(gab.partiels["pied"], ctx).strip()
            + "\n</body>\n</html>\n"
        )
        (SORTIE / nom_sortie).write_text(document, encoding="utf-8")
        if indexable:
            plan.append(nom_sortie)
        print(f"  {nom_sortie}")

    # Fichiers annexes
    url = ctx_global["url"]
    robots = "User-agent: *\nAllow: /\n"
    if url:
        robots += f"\nSitemap: {url}/sitemap.xml\n"
        aujourd_hui = datetime.date.today().isoformat()
        priorites = {"index.html": "1.0", "contact.html": "0.9"}
        entrees = "".join(
            f"  <url><loc>{url}/{'' if p == 'index.html' else p}</loc><lastmod>{aujourd_hui}</lastmod>"
            f"<priority>{priorites.get(p, '0.8' if p.replace('.html', '') in [m['id'] for m in METIERS] else '0.5')}</priority></url>\n"
            for p in sorted(plan, key=lambda n: (n != "index.html", n))
        )
        (SORTIE / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + entrees
            + "</urlset>\n",
            encoding="utf-8",
        )
    (SORTIE / "robots.txt").write_text(robots, encoding="utf-8")

    manifeste = {
        "name": "Andres Peintures",
        "short_name": "Andres",
        "start_url": "index.html",
        "display": "browser",
        "background_color": "#fbf7ef",
        "theme_color": "#16214f",
        "icons": [
            {"src": "img/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "img/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    (SORTIE / "site.webmanifest").write_text(json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")

    empreinte_script = base64.b64encode(hashlib.sha256(SCRIPT_JS.encode()).digest()).decode()
    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'sha256-{empreinte_script}'; "
        "style-src 'self'; img-src 'self' data:; font-src 'self'; "
        "frame-src https://www.openstreetmap.org; connect-src 'self'; "
        "form-action 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'"
    )
    (SORTIE / "_headers").write_text(
        "/*\n"
        f"  Content-Security-Policy: {csp}\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()\n"
        "/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/css/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/js/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/img/*\n  Cache-Control: public, max-age=2592000\n",
        encoding="utf-8",
    )

    manquants = [c for c, v in (("telephone", ctx_global["tel"]), ("email", ctx_global["email"]), ("url", url)) if not v]
    print(f"Site généré dans {SORTIE.relative_to(RACINE)}/ ({len(pages)} pages).")
    if manquants:
        print("À compléter dans site.json pour enrichir le site : " + ", ".join(manquants) + ".")


if __name__ == "__main__":
    try:
        construire()
    except (ErreurGabarit, KeyError, ValueError) as erreur:
        sys.exit(f"Erreur : {erreur}")
