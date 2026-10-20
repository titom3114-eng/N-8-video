# N+8 — Films de marque

Courts-métrages pour **N+8, Maison de parfums nocturne**.

## « Nuits » v7 — version actuelle : titrage Cinzel

La v6 (mêmes images, même son, mêmes durées, mêmes tailles et ombres), avec une police de titrage plus marquante :
**Cinzel**, des capitales romaines gravées — l'esthétique d'une affiche de cinéma, sombre et mystérieuse, qui rappelle
les inscriptions de Rome, l'encens, la nuit. Tout passe en capitales : *N + HUIT → NUIT*, *NIGHT*, *NACHT*, *ΝΥΧΤΑ*,
« CHAQUE NUIT A SON PARFUM. », « DANS TOUTES LES LANGUES, LA NUIT S'ÉCRIT N+8. ». Les grands mots sont en or dégradé
(clair en haut, profond en bas), le grec en Noto Serif Display, l'arabe (ليل) en Amiri gras. Polices sous licence
SIL Open Font License (usage commercial autorisé).

| Fichier | Format |
|---|---|
| `output/N8_Nuits-V7_16x9.mp4` | 1920×1080, 30 i/s, cadre 2.39:1, 55 s |
| `output/N8_Nuits-V7_9x16.mp4` | 1080×1920, 30 i/s, 55 s |
| `output/N8_Nuits-V7_affiche_*.png` | image du logo final |
| `output/apercu/N8_Nuits-V7_*_apercu-720p.mp4` | aperçus 720p |

Fabrication : `footage/edl_v7.json` (`"font": "cinzel"` active ce titrage dans `src/reel.js`), puis comme la v6 avec
`build/v7/` et `scripts/mux.py --film v7`.

## « Nuits » v6 : textes lisibles

Le film « Nuits » v5 (mêmes images, même musique, mêmes bruitages, sans voix), avec des écritures faites pour être lues,
en 16:9 comme en vertical :

- **Plus grandes et plus épaisses** — la formule des villes (*N + huit → nuit*) est 1,5 fois plus grande, les noms de
  ville et les coordonnées aussi ; les mots des capitales passent de 11 à 16 (paysage) et de 15 à 22 (vertical) ; la phrase
  d'ouverture et la phrase finale sont agrandies (en vertical, la phrase finale passe sur deux lignes). Le Bodoni est pris
  en graisse 500 : ses déliés, très fins, ne disparaissent plus dans l'image.
- **Détachées de l'image** — ombre portée sombre sous chaque texte, voile sombre derrière la carte de ville (moitié gauche
  en paysage, bande horizontale en vertical) : le texte reste net sur la tour Eiffel illuminée ou le lustre de Mascate.
- **Plus longtemps à l'écran** — la carte de ville reste 4,2 s au lieu de 3,5 s, *N + huit* reste lisible 1,1 s avant de
  glisser, et *nuit* tient ensuite 2 s ; « Chaque nuit a son parfum. » apparaît plus tôt (2,8 s au lieu de 2,1 s) ; chaque
  capitale reste 0,53 s au lieu de 0,35 s (le film passe de 53 à 55 s).
- **Plus haut en vertical** — la carte de ville est remontée, hors de la zone couverte par l'interface des réseaux sociaux.

| Fichier | Format |
|---|---|
| `output/N8_Nuits-V6_16x9.mp4` | 1920×1080, 30 i/s, cadre 2.39:1, 55 s |
| `output/N8_Nuits-V6_9x16.mp4` | 1080×1920, 30 i/s, 55 s |
| `output/N8_Nuits-V6_affiche_*.png` | image du logo final |
| `output/apercu/N8_Nuits-V6_*_apercu-720p.mp4` | aperçus 720p |

Fabrication : `footage/edl_lisible.json` (le montage, avec `"text": "lisible"` qui active ces réglages dans `src/reel.js`),
puis `scripts/sound_reel.py build/lisible/cues.json build/lisible/soundtrack.wav footage/edl_lisible.json`,
`scripts/footage/assemble.py --edl footage/edl_lisible.json` et `scripts/mux.py --film v6`. Crédits : ceux de « Nuits »
(`footage/CREDITS.md`, `footage/CREDITS_SON.md`).

## « Nuits » avec la voix

Le film « Nuits » en images réelles (même montage, mêmes images, même musique), avec **une seule voix de femme, chuchotée** —
celle de « Huit voix » qui souffle *« La nuit a une odeur »* — qui dit « la nuit » dans la langue de chaque ville au moment
où le mot s'écrit à l'écran :

- **Paris** — *« Nuit. »* quand N + huit devient nuit ; **Roma** — *« Notte. »* ; **Oman** — *« Layl. »* (ليل).
- **Les capitales** — un mot par ville, sur chaque plan : *night, noche, Nacht, noite, nacht, natt, noapte, νύχτα*.
  Ces plans durent un peu plus que dans « Nuits » (0,53 s au lieu de 0,35 s) pour que chaque mot soit dit en entier.
- **La fin** — dans le silence : *« La nuit s'écrit… N plus huit. »* — « huit » tombe sur l'impact du logo,
  et la musique revient.

Même voix pour toutes les langues (Kokoro-82M, voix « ff_siwis », licence Apache 2.0) : pour les langues étrangères, on lui
donne la prononciation en alphabet phonétique. Même chuchotement que dans « Huit voix » : on garde les formants de la voix,
on remplace la vibration des cordes vocales par un souffle, avec une part de voix (45 à 75 %) pour que le souffle reste humain.
Pour chaque mot, de nombreuses variantes (prononciation, débit, dosage) sont essayées ; une reconnaissance vocale à l'aveugle
garde la plus chuchotée de celles qui sont comprises (`build/voices/nuits_chuchote/choix.json`). Le néerlandais *nacht* se dit
comme l'allemand *Nacht* : c'est une autre prise du même mot. La musique s'efface de 9 dB sous chaque mot.

| Fichier | Format |
|---|---|
| `output/N8_Nuits-Voix_16x9.mp4` | 1920×1080, 30 i/s, cadre 2.39:1, 55 s |
| `output/N8_Nuits-Voix_9x16.mp4` | 1080×1920, 30 i/s, 55 s |
| `output/N8_Nuits-Voix_affiche_*.png` | image du logo final |
| `output/apercu/N8_Nuits-Voix_*_apercu-720p.mp4` | aperçus 720p |

Fabrication : `footage/edl_nuits_voix.json` (le montage), `footage/voix_nuits.json` (quel mot sur quel plan, à quel
instant), `scripts/voice_chuchote.py` (la voix, mot par mot), puis
`scripts/sound_reel.py build/nuits_voix/cues.json build/nuits_voix/soundtrack.wav footage/edl_nuits_voix.json --voices footage/voix_nuits.json`
et `scripts/mux.py --film nuits-voix`.
Crédits : `footage/CREDITS.md` (images) et `footage/CREDITS_SON_NUITS_VOIX.md` (son et voix, attribution SIWIS CC BY 4.0).

## « Huit voix » — la nuit chuchote son nom

Un film tout autre : typographique, sonore, intime. Dans huit langues, la nuit s'écrit N + huit — et chaque langue a
sa voix, qui chuchote le mot à l'oreille au moment où il s'écrit.

- **Ouverture** — noir, une inspiration, le « pschit » d'un vaporisateur : une brume d'or apparaît.
  Une voix de femme, tout bas : *« La nuit a une odeur. »*
- **Huit chapitres**, de plus en plus courts (le cœur accélère) : sur un fond de fumée, un battement de cœur, le N
  en or ; *N + huit* glisse et devient *nuit* — au même instant, la voix chuchote « Nuit ». Puis le mot devient une
  fenêtre : la ville apparaît à travers ses lettres, la caméra traverse la première lettre et l'on entre dans la nuit
  de la ville, son ambiance et son odeur, qui a un bruit.
  1. **Paris** — *nuit* : la tour scintille ; fumée d'un cigare dans le noir (souffle), cognac versé. Rumeur feutrée d'un bar.
  2. **Roma** — *notte* : le Colisée ; un encensoir qui se balance, un cierge qu'on allume. Pluie fine sur la pierre.
  3. **Madrid** — *noche* : la Gran Vía ; une orange pressée. Grillons d'une nuit d'été.
  4. **London** — *night* : Big Ben ; la pluie sur le pavé, des talons qui passent.
  5. **Lisboa** — *noite* : le pont sur le Tage, les reflets du fleuve. Un tram, le fleuve.
  6. **București** — *noapte* (N + opt) : l'Arc de triomphe ; une rose qui brûle. Vent sourd.
  7. **Berlin** — *Nacht* : N + acht = Nacht, lettre pour lettre ; la tour de télévision, fumée froide. Une rame de U-Bahn entre en station.
  8. **Amsterdam** — *nacht* : les maisons sur le canal ; pétales sur l'eau. Un vélo, l'eau des canaux.
- **Le chœur** — les huit mots s'enchaînent en fenêtres sur leurs villes, puis huit odeurs en éclairs (allumette,
  fumée, encens, orange, pluie, miel, rose, braises). Les huit voix se superposent en nuée, de partout, le cœur
  s'emballe, tous les N se rassemblent en un seul… coupure nette : **silence**.
- **La révélation** — dans le silence, la voix : *« Dans toutes les langues, la nuit s'écrit… N plus huit. »*
  Sur « plus », le + apparaît ; sur « huit », le 8 — le logo frappe, l'arche se trace, la musique revient.
  *« Maison de parfums nocturne. »* — les deux lignes du logo s'écrivent avec la voix.

Durée : 39 s. Tempo 110 BPM. Son stéréo AAC normalisé à −14 LUFS (crête −1,5 dBTP). Sans le son (réseaux sociaux),
le film se comprend aussi : la formule s'écrit à l'écran et la dernière phrase apparaît en sous-titre.

| Fichier | Format | Usage |
|---|---|---|
| `output/N8_Huit-Voix_16x9.mp4` | 1920×1080, 30 i/s, cadre cinéma 2.39:1 | site, YouTube, présentation, écran boutique |
| `output/N8_Huit-Voix_9x16.mp4` | 1080×1920, 30 i/s | Instagram Reels, Stories, TikTok |
| `output/N8_Huit-Voix_affiche_*.png` | image du logo final | miniature, couverture |
| `output/apercu/N8_Huit-Voix_*_apercu-720p.mp4` | 720p | envoi rapide, validation |

**Voix** — synthèse vocale neuronale hors ligne **Kokoro-82M** (poids Apache 2.0, entraîné uniquement sur des données
libres ou sans droits), huit timbres différents (femmes et hommes), puis chuchotées par traitement du signal : on garde
les formants de la voix et on remplace la vibration des cordes vocales par un souffle, en laissant le N voisé pour qu'il
reste net. L'allemand, le néerlandais et le roumain sont dictés à Kokoro en alphabet phonétique. Chaque mot et chaque
phrase ont été vérifiés par reconnaissance vocale automatique, à l'aveugle : tous sont compris. Aucune voix de personne
réelle n'est imitée. Les voix « Piper » essayées en route ont été écartées : la plupart sont dérivées de modèles entraînés
sur des données à usage non commercial. Pour une diffusion télévisée, des comédiens peuvent remplacer ces voix en
gardant exactement le même montage (`build/voices/out/<nom>.wav`, mêmes noms de fichiers).

**Musique** — « Cinematic Visions » (Coverr) : sa partie dépouillée sous les chuchotements, l'entrée de la basse sur le
chœur, silence, puis la partie pleine qui revient sur le logo. **Bruitages et ambiances** — Mixkit.

**Droits** — images : Pexels License (vidéos et photos) ; musique : Coverr License ; bruitages : Mixkit Sound Effects
Free License ; voix : Kokoro (Apache 2.0) ; la voix française provient du corpus SIWIS (CC BY 4.0 : attribution dans
`footage/CREDITS_SON_VOIX.md`). Détail : `footage/CREDITS_VOIX.md` (images) et `footage/CREDITS_SON_VOIX.md` (son).

Fabrication : `./scripts/build_voix.sh` (voix → vidéos → chronologie → bande-son → calque → montage → films).

- Voix : `scripts/voices.py` (textes, timbres, dosage du chuchotement) — `pip install kokoro-onnx` ; les modèles sont
  téléchargés au premier lancement.
- Montage : `footage/edl_voix.json` (même syntaxe que le film principal ; `"formula"` : la nuit qui s'écrit,
  `"window"` : le mot-fenêtre et le zoom à travers la lettre, `"render": "gather"` puis `"logo"` : la révélation ;
  bruitages `"vo"` : la voix, son fichier, son panoramique).
- Calque typographique : `src/reel.js` (fonctions `formulaCard`, `windowWord`, `gather`, `logoVoice`).
- Bande-son : `scripts/sound_voix.py` (voix, nuée du chœur, cœur, ambiances par ville, coupure, musique).

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

## « Nuits » en images réelles

Le film principal en vraies vidéos de nuit : 71 plans en 53 s, coupés sur le tempo de la musique
(85,3 BPM : surtout des demi-temps de 0,35 s, quelques plans d'un temps et demi), étalonnés or / noir / gris /
blanc, grain et format cinéma. Aucun ingrédient n'est écrit : chaque ville déroule trois matières, chacune avec
un plan « héros » un peu plus long et, quand c'est possible, le geste de sentir, souligné par une inspiration.
La carte de chaque ville (*N + huit → nuit*) reste 3,5 s, le temps de lire le jeu de lettres.

Mise en scène : ouverture sur le noir et une inspiration, l'allumette s'enflamme d'emblée ; chaque ville a sa
température d'image (Paris ambre-tabac, Rome pierre argentée, Oman ambre profond) ; une brume dorée passe devant
les plans où l'on sent (tabac, écorce d'orange, pétales) ; un bref fondu au noir ferme chaque ville ;
après la salve des capitales, la musique s'arrête net : les mots se rassemblent dans le silence, puis le logo frappe
et le piano revient.

- **Ouverture** — une allumette craque dans le noir, une braise, *« Chaque nuit a son parfum. »*
- **Paris** — tour Eiffel, Arc de Triomphe, le bar. *Tabac* : feuilles dorées, briquet, cigare, fumée soufflée,
  cendre. *Cognac* : versé, verre de cristal, glaçon. *Cuir* : capitonné noir, saxophone.
- **Rome** — Colisée, pont Saint-Ange, pluie. *Encens* : rayons dans l'église, encensoir, chœur, cierges, cloche.
  *Agrumes* : écorce en spirale, orange pressée, citrons qui plongent. *Pierre mouillée* : pluie sur le pavé, fontaine.
- **Oman** — ciel étoilé, lustre de la mosquée Sultan Qaboos, mosquée, chameau, dunes. *Oud* : copeaux qui
  brûlent, bois fumant tenu à la main, encensoir, braises. *Rose* : silhouette qui respire une fleur, rose en
  flammes, coupe de pétales. *Ambre* : goutte d'huile, miel, or.
- **Les capitales** en éclair (London *night*, Madrid *noche*, Berlin *Nacht*…), puis le logo doré et
  *« Dans toutes les langues, la nuit s'écrit N+8. »*

**Son** : musique « Disturbing Night » (Coverr) montée sur la grille du film — raccords sur les mesures,
passage dans sa partie calme à l'arrivée du logo ; ambiances réelles par lieu (rue de Paris puis rumeur du bar,
pluie légère à Rome, vent du désert à Oman, discrets) ; un seul bruitage réel par matière, jamais répété
(allumette, molette du briquet, souffle de fumée, cendre, versement, glaçon, cloche, chœur, cierge, jus pressé,
plongeon des citrons, gouttes, eau, rafale, braises, flamme, goutte d'ambre) ; impact grave à l'entrée de chaque
ville ; réverbération propre à chaque lieu ; la musique s'efface légèrement sous chaque bruitage.

| Fichier | Format | Usage |
|---|---|---|
| `output/N8_Nuits-Reel_16x9.mp4` | 1920×1080, 30 i/s, cadre cinéma 2.39:1 | site, YouTube, présentation, écran boutique |
| `output/N8_Nuits-Reel_9x16.mp4` | 1080×1920, 30 i/s | Instagram Reels, Stories, TikTok |
| `output/N8_Nuits-Teaser_16x9.mp4`, `output/N8_Nuits-Teaser_9x16.mp4` | 16 s, mêmes formats | publicité, Reels, TikTok, stories |
| `output/N8_Nuits-Reel_affiche_*.png` | image du logo final | miniature, couverture |
| `output/apercu/N8_Nuits-*_apercu-720p.mp4` | 720p, < 30 Mo | envoi rapide, validation |

**Droits** — images : Pexels License (vidéos et photos) et Mixkit Stock Video Free License ;
musique : Coverr License ; bruitages : Mixkit Sound Effects Free License. Toutes autorisent l'usage commercial
et publicitaire sans attribution (les bruitages aussi en télévision et radio). Aucune vidéo payante, générée par IA
ou sous licence restreinte. Détail : `footage/CREDITS.md` (images) et `footage/CREDITS_SON.md` (son).
Les fichiers de musique et de bruitages ne sont pas versionnés (redistribution seule interdite) : le script
les retélécharge. La musique utilisée est la version MP3 publique de Coverr ; si vous téléchargez l'original
WAV depuis coverr.co, déposez-le en `footage/music/disturbing-night.wav`, il sera pris automatiquement.
Comme pour toute banque d'images, les marques ou monuments visibles ne sont pas « libérés » par la licence ;
aucun logo de marque n'apparaît dans les plans retenus.

- Découpage plan par plan : `footage/edl.json` — durée en temps, vidéo (`"src"` : `p:<id>` Pexels, `c:<id>` Coverr,
  `m:<id>` Mixkit, ou `"use"` : même vidéo qu'un autre plan), point d'entrée (`"in"`, en secondes), mouvement,
  cadrage serré (`"zoom"`), étalonnage, cadrage vertical (`"focus_v"`), bruitages (`"sfx"`), cartes des villes ;
  `"music"` : piste, temps de départ et raccords.
- Recherche et choix des vidéos : `scripts/footage/pexels.py` (fichiers Pexels sans clé d'API à partir
  des identifiants listés dans `footage/pexels/*.json`), `scripts/footage/coverr_index.py`,
  `scripts/footage/mixkit_index.py`, puis `scripts/footage/shortlist.py` (planches de vignettes par plan).
- Téléchargement des vidéos : `scripts/footage/fetch.py` (4K quand elle existe, pour un recadrage vertical net).
- Effets sonores : `scripts/footage/mixkit_sfx.py` (index et téléchargement).
- Calque des titres : `src/reel.html` / `src/reel.js`
- Montage, étalonnage, recadrage 16:9 et 9:16 : `scripts/footage/assemble.py`
- Bande-son (musique, ambiances, bruitages, réverbérations, mixage) : `scripts/sound_reel.py`
- Version courte : `footage/edl_teaser.json` (même syntaxe ; `assemble.py --edl`, `render.cjs --edl`,
  `sound_reel.py … footage/edl_teaser.json`, `mux.py --film teaser`).
- Tout d'un coup : `./scripts/build_reel.sh` → film, version courte et affiches dans `output/`

Accès réseau nécessaire : `videos.pexels.com`, `assets.mixkit.co`, `cdn.coverr.co`. Vos propres images peuvent
remplacer n'importe quel plan : déposez `footage/override/<id>.mp4` (prioritaire sur la vidéo choisie).

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
scripts/voices.py             voix de « Huit voix » (synthèse + chuchotement)
scripts/sound_voix.py         bande-son de « Huit voix »
scripts/build_voix.sh         « Huit voix » de bout en bout
scripts/soundtrack_nuits.py   bande-son de « Nuits »
scripts/soundtrack.py         bande-son de « La nuit » (et fonctions partagées)
scripts/mux.py                normalisation du son, encodage final et aperçus
scripts/build.sh              chaîne complète
output/                       films, aperçus et affiches
```
