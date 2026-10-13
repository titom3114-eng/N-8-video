# N+8 — « La nuit »

Court-métrage de marque pour **N+8, Maison de parfums nocturne**.

Le film ne présente pas le concept, il le fait **découvrir** : la nuit tombe sur une ville,
une enseigne énigmatique « N+8 » s'allume sur un toit… puis, de rue en rue, de pays en pays,
le « 8 » grésille et devient *huit*, *ocho*, *eight*, *otto*… et les lettres glissent pour écrire
**nuit, noche, night, notte, Nacht, noite, nacht, natt, noapte, νύχτα**.
Une seule phrase, à la fin : *« Dans toutes les langues, la nuit s'écrit N+8. »* — puis l'arche du logo se trace.

## Les films

| Fichier | Format | Usage |
|---|---|---|
| `output/N8_La-Nuit_16x9.mp4` | 1920×1080, 30 i/s, cadre cinéma 2.39:1 | site, YouTube, présentation, écran boutique |
| `output/N8_La-Nuit_9x16.mp4` | 1080×1920, 30 i/s | Instagram Reels, Stories, TikTok |
| `output/N8_affiche_16x9.png` / `output/N8_affiche_9x16.png` | image fixe du logo final | miniature, couverture |
| `output/apercu/*_apercu-720p.mp4` | 720p, < 30 Mo | envoi rapide par messagerie, validation |

Durée : 63 s. Son stéréo AAC 256 kb/s normalisé à −14 LUFS (crête −1,5 dBTP).

## Découpage

| Temps | Plan | Ce qu'on voit / entend |
|---|---|---|
| 0:00 – 0:10 | **La nuit tombe** | Ville au crépuscule au bord de l'eau, le ciel s'éteint, les fenêtres s'allument. Sur un toit, une enseigne grésille : « N+8 ». La caméra plonge vers elle. Vent, rumeur de ville, la pluie arrive. |
| 0:10 – 0:20 | **Français** | Mur de béton sous la pluie, sol mouillé. « N+8 »… le 8 s'éteint, *huit* s'allume lettre à lettre, le *h* meurt dans une gerbe d'étincelles, les lettres glissent : **nuit**. Des phares balaient le mur. |
| 0:20 – 0:26 | **Español** | Contre-plongée, balcon en fer forgé, réverbère dans la brume : *ocho* → **noche**. |
| 0:26 – 0:32 | **English** | Derrière une vitre ruisselante, mise au point sur l'enseigne : *eight* → **night**. |
| 0:32 – 0:38 | **Italiano** | D'abord le reflet à l'envers dans l'eau noire d'un canal, puis la caméra se lève : *otto* → **notte**. |
| 0:38 – 0:45 | **Montage** | Coupes rapides au rythme d'un battement : **Nacht** (métal), **noite** (réverbère), **nacht** (reflet), **natt** (neige), **noapte** (vitre), **νύχτα** (pierre). Montée de tension… |
| 0:45 – 0:51 | **Silence** | Noir. Seul « N », puis « + », puis « 8 » s'allument. *Dans toutes les langues, la nuit s'écrit N+8.* |
| 0:51 – 1:03 | **Logo** | L'arche se trace en lumière autour de N+8, *MAISON DE PARFUMS — NOCTURNE* apparaît, accord final, fondu au noir. |

## Direction artistique

- **Palette** : noir, gris, bleu nuit très foncé uniquement. Les lettres sont en verre gris bleuté,
  leur halo bleu nuit éclaire le béton, la brique, la pierre et la pluie.
- **Image** : format cinéma 2.39:1 (version 16:9), grain argentique, vignettage, brouillard, reflets
  ondulants, caméra à l'épaule, mises au point, coupes franches.
- **Typographie** : Didone (Bodoni Moda, GFS Didot pour le grec), en écho au N+8 du logo.
- **Logo** : le logo fourni (`assets/logo-n8-original.png`) a été détouré en calques
  (`src/logo/` : arche, N, +, 8, deux lignes de texte) et adapté au fond noir : tracé gris
  argenté et halo bleu nuit, révélé élément par élément.
- **Son** : pluie (claire ou étouffée derrière la vitre), vent, clapotis, grésillement et bourdonnement
  des enseignes, étincelles, voiture qui passe, impacts aux coupes, pulsation cardiaque pendant le montage,
  nappe sombre en ré mineur, vrai silence avant la révélation, accord final sur le logo.

## Refaire ou modifier le film

Prérequis : Node.js 18+ avec Playwright et Chromium, Python 3 avec numpy, ffmpeg (libx264, aac).

```bash
./scripts/build.sh
```

Le script exporte la chronologie, synthétise la bande-son, rend chaque image des deux formats,
puis assemble les films et les affiches dans `output/`.

Aperçu en temps réel (sans le son) : servir le dossier et ouvrir `src/index.html`, par exemple
`npx serve .` puis `http://localhost:3000/src/index.html`.

Points d'entrée pour les modifications, tous dans `src/film.js` :

- `buildFilm()` : ordre des plans, durées, langues (`def: { eight, night, map }`), décors, météo, caméra.
- `COL` : palette (halo, verre des lettres, logo).
- `sceneFinale()` : la phrase de fin et le minutage de la révélation du logo.
- `scripts/soundtrack.py` : niveaux, accords et sons de chaque événement.

## Arborescence

```
assets/logo-n8-original.png   logo fourni
assets/logo-n8-mask.png       logo détouré (transparent)
src/index.html, src/film.js   le film (rendu image par image dans un canvas)
src/logo/                     calques du logo + positions (parts.json)
src/fonts/                    polices (licence SIL Open Font License)
scripts/render.cjs            rendu des images → vidéo master (build/)
scripts/soundtrack.py         bande-son synchronisée
scripts/mux.py                normalisation du son + encodage final
scripts/build.sh              chaîne complète
scripts/fetch_fonts.py        téléchargement des polices
output/                       films et affiches finaux
```
