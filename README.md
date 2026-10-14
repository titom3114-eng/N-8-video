# N+8 — Films de marque

Courts-métrages pour **N+8, Maison de parfums nocturne**.

## « Nuits » — film principal

La nuit, et surtout son odeur, à travers les villes. Une allumette s'enflamme, un cigare rougeoie :
*« Chaque nuit a son parfum. »* Puis, en plans courts montés sur le tempo :

- **Paris** — la tour scintille au-dessus des toits ; un bar, des bouteilles à contre-jour, le cognac
  qu'on verse, des silhouettes d'hommes en chapeau, la fumée des cigares à travers les stores.
  *Tabac, cognac, cuir, bois fumé.*
- **Rome** — le Colisée sous la bruine, les pavés mouillés, un encensoir qui se balance, la bergamote,
  un buste antique dans la fumée, une fontaine, des cierges.
  *Pierre mouillée, encens, bergamote, fumée.*
- **Oman** — dunes sous le croissant de lune, mosquée dorée, encensoir à oud, pétales de rose,
  lanterne ajourée, goutte d'ambre, poussière d'or.
  *Oud, rose, ambre.*
- **Les autres villes** défilent : London *night*, Madrid *noche*, Berlin *Nacht*, Lisboa *noite*,
  Amsterdam *nacht*, Stockholm *natt*, București *noapte*, Αθήνα *νύχτα* — le N toujours en or.
- **Finale** — toutes les nuits s'alignent, leurs N se rejoignent : *« Dans toutes les langues,
  la nuit s'écrit N+8. »* Le logo se révèle en or.

Le concept N+8 reste en filigrane : sur chaque carte de ville, la nuit s'écrit sous nos yeux
(*N + huit → nuit*, *N + otto → notte*, et *ليل* pour Oman).

| Fichier | Format | Usage |
|---|---|---|
| `output/N8_Nuits_16x9.mp4` | 1920×1080, 30 i/s, cadre cinéma 2.39:1 | site, YouTube, présentation, écran boutique |
| `output/N8_Nuits_9x16.mp4` | 1080×1920, 30 i/s | Instagram Reels, Stories, TikTok |
| `output/N8_Nuits_affiche_*.png` | image du logo final | miniature, couverture |
| `output/apercu/N8_Nuits_*_apercu-720p.mp4` | 720p, < 30 Mo | envoi rapide, validation |

Durée : 63 s. Tempo 96 BPM, coupes sur le temps. Son stéréo AAC normalisé à −14 LUFS (crête −1,5 dBTP).

**Direction artistique** : or, noir, gris, blanc ; toujours sombre. Silhouettes en contre-jour
liserées d'or, fumée, bokeh, profondeur de champ, grain argentique, cadre 2.39:1.
**Musique** : groove feutré (piano électrique, contrebasse, balais) à Paris ; chœur, cloches et pluie
à Rome ; percussions sur cadre, oud en mode hijaz et nappe sombre à Oman ; montée rythmique sur les
villes ; silence net, puis accord final sur le logo. Bruitages synchronisés : allumette, verre,
glaçon, briquet, pas sur la pierre, chaîne de l'encensoir, braises, goutte.

## « Nuits » en images réelles — prêt à lancer

Même film, monté plus vite (120 BPM, une coupe toutes les 0,5 à 1,5 s, 52 plans) avec de vraies vidéos
libres de droits, étalonnées or / noir / gris / blanc, grain et format cinéma, titres et logo par-dessus.

- Découpage plan par plan et mots-clés de recherche : `footage/edl.json`
- Récupération des vidéos : `scripts/footage/fetch.py` (Pexels avec clé `PEXELS_API_KEY`, ou Mixkit sans clé)
- Calque des titres : `src/reel.html` / `src/reel.js`
- Montage, étalonnage, recadrage 16:9 et 9:16 : `scripts/footage/assemble.py`
- Musique 120 BPM et bruitages : `scripts/soundtrack_reel.py`
- Tout d'un coup : `./scripts/build_reel.sh` → `output/N8_Nuits-Reel_16x9.mp4`, `output/N8_Nuits-Reel_9x16.mp4`

Accès réseau nécessaire dans l'environnement : `mixkit.co` et `assets.mixkit.co` (sans clé),
et/ou `api.pexels.com`, `videos.pexels.com`, `images.pexels.com` avec une clé gratuite Pexels
dans la variable `PEXELS_API_KEY`. Vos propres images peuvent remplacer n'importe quel plan :
`footage/override/<id>.mp4`. Les crédits des vidéos utilisées sont écrits dans `footage/CREDITS.md`.

## « La nuit » — première version

Néons bleu nuit sous la pluie : l'enseigne « N+8 » se transforme en *nuit, noche, night, notte…*
Fichiers : `output/N8_La-Nuit_*`.

## Refaire ou modifier les films

Prérequis : Node.js 18+ avec Playwright et Chromium, Python 3 avec numpy, ffmpeg (libx264, aac).

```bash
./scripts/build.sh            # « Nuits »
./scripts/build.sh la-nuit    # « La nuit »
```

Le script exporte la chronologie, synthétise la bande-son, rend chaque image des deux formats,
puis assemble les films, les aperçus et les affiches dans `output/`.

Aperçu en temps réel (sans le son) : `npx serve .` puis `http://localhost:3000/src/nuits.html`.

Points d'entrée pour les modifications :

- `src/nuits.js`, fonction `buildFilm()` : ordre des plans, durées en temps (1 temps = 0,625 s),
  notes olfactives affichées, cartes des villes (nom, coordonnées, formule de la nuit).
- `src/nuits.js`, objet `C` : palette ; chaque plan est une fonction `shot…` lisible séparément.
- `scripts/soundtrack_nuits.py` : accords, rythmes, riffs d'oud, niveaux des bruitages et ambiances.

## Arborescence

```
assets/                       logo fourni et logo détouré
src/nuits.html, nuits.js      film « Nuits »
src/index.html, film.js       film « La nuit »
src/logo/                     calques du logo (arche, N, +, 8, textes) + positions
src/fonts/                    polices (licence SIL Open Font License)
scripts/render.cjs            rendu image par image → vidéo master (build/)
scripts/soundtrack_nuits.py   bande-son de « Nuits »
scripts/soundtrack.py         bande-son de « La nuit » (et fonctions partagées)
scripts/mux.py                normalisation du son, encodage final et aperçus
scripts/build.sh              chaîne complète
output/                       films, aperçus et affiches
```
