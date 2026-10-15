# Site internet — Andres Peintures (SARL ANDRES PASCAL)

Site vitrine de l'entreprise familiale de peinture, façade, plâtrerie et sols à Toulouse, fondée en 1994.
Chaleureux, rassurant et organisé autour des quatre métiers.

**Le site prêt à mettre en ligne se trouve dans `public/`.** Pour le voir tout de suite, ouvrez
`public/index.html` dans un navigateur.

## Ce que contient le site

| Page | Contenu |
|---|---|
| `index.html` | Accueil : les 4 métiers, les 3 premiers prix de la Ville de Toulouse, les engagements, les étapes d'un chantier, la zone d'intervention, une FAQ |
| `peinture.html` | Peinture intérieure et extérieure : prestations, méthode, choix des finitions, conseil couleurs, FAQ |
| `facade.html` | Ravalement et patrimoine : prestations, chantier primé du 59 rue Pargaminières, méthode, réglementation toulousaine, FAQ |
| `platrerie.html` | Cloisons, doublages, plafonds : prestations, méthode, tableau des plaques, FAQ |
| `sols.html` | Parquets en point de Hongrie et bâtons rompus (photos et schémas de pose), parquet et stratifié, sols souples (PVC, vinyle, linoléum, Marmoleum, moquette), méthode, tableau « quel sol pour quelle pièce », FAQ |
| `entreprise.html` | Histoire familiale, chiffres clés, distinctions, valeurs, types de clients |
| `contact.html` | Formulaire de devis (le métier est pré-coché depuis chaque page), coordonnées, plan |
| `mentions-legales.html` | Mentions légales, données personnelles (RGPD), crédits photos |
| `merci.html`, `404.html` | Confirmation d'envoi du formulaire, page introuvable |

Points techniques : responsive (mobile, tablette, ordinateur), accessible (navigation au clavier, contrastes,
textes alternatifs), référencement local (balises, données structurées `HousePainter`, plan du site),
polices hébergées sur le site (aucun appel à Google), aucun cookie ni traceur, en-têtes de sécurité.

## Coordonnées et réglages

Toutes les coordonnées sont dans `site.json` :

```json
"telephone": "06 07 08 38 23",
"telephone_2": "07 85 53 97 07",
"email": "andres.peinture@wanadoo.fr",
"email_2": "andrestom.pro@gmail.com",
"horaires": ""
```

Le premier numéro est mis en avant (en-tête, boutons « Appeler », menu mobile) ; le second figure sur la
page contact, dans le pied de page et les mentions légales. Les numéros peuvent être saisis avec ou
sans espaces. Un champ laissé vide (`""`) est masqué proprement, par exemple les horaires :

```json
"horaires": "Du lundi au vendredi, 8 h – 12 h et 14 h – 18 h"
```

Une fois le nom de domaine choisi, renseignez-le pour activer le plan du site (`sitemap.xml`),
les adresses canoniques et l'image d'aperçu pour les réseaux sociaux :

```json
"url": "https://www.votre-domaine.fr"
```

Après chaque modification, régénérez le site :

```bash
python3 build.py
```

La liste des communes de la zone d'intervention se modifie aussi dans `site.json`.

## Mettre le site en ligne

### Netlify (recommandé, gratuit)

1. Créez un compte sur [netlify.com](https://www.netlify.com).
2. Glissez-déposez le dossier `public/` sur [app.netlify.com/drop](https://app.netlify.com/drop).
3. Dans **Domain management**, reliez votre nom de domaine.
4. Les demandes de devis arrivent dans l'onglet **Forms** ; activez l'envoi par e-mail dans
   **Site configuration > Forms > Form notifications** (ajoutez une notification pour
   andres.peinture@wanadoo.fr et une pour andrestom.pro@gmail.com).

Pour publier automatiquement depuis ce dépôt Git, indiquez `site-andres-peintures` comme
**Base directory** : le fichier `netlify.toml` fait le reste.

### Autre hébergeur (OVH, o2switch…)

1. Dans `site.json`, passez `"formulaire"` à `"courriel"` : le formulaire prépare alors la demande
   dans la messagerie du visiteur, adressée au premier e-mail (`"email"`), sans serveur.
2. Remplacez les champs `hebergeur_nom`, `hebergeur_adresse` et `hebergeur_site` par ceux de votre
   hébergeur (ils apparaissent dans les mentions légales).
3. Lancez `python3 build.py`, puis envoyez le contenu de `public/` dans le dossier `www` de l'hébergement.

## Ajouter vos photos de chantiers

Les façades primées du 11 rue des Lois (`facade-rue-des-lois`) et du 3 place Robert-Schuman
(`facade-place-schuman`) sont des photos de l'entreprise : la première illustre la carte « Façade » de
l'accueil et le haut de la page Façade, la seconde le haut de la page Entreprise et l'encadré du prix
sur la page Façade ; les deux figurent côte à côte dans la section des prix de l'accueil. Le séjour
rénové (`chantier-peinture-sols`, peinture et parquet en bâtons rompus) illustre le haut de l'accueil
et l'encadré « Chantier terminé » des pages Peinture et Sols. Les autres
photos sont des illustrations libres de droits. D'autres photos de vos chantiers (rue Pargaminières,
avant/après, parquets posés, équipe au travail) renforceront encore la confiance :

```bash
pip install pillow
python3 outils/ajouter-photo.py photo-pargaminieres.jpg peinture-rouleau
python3 build.py
```

Réutiliser un nom existant remplace la photo partout où elle apparaît ; une photo de moins de 1600 px
de large n'est pas agrandie. Pensez à adapter la mention « Crédits photographiques » de
`src/pages/mentions-legales.html` quand vous remplacez des photos d'illustration par les vôtres.

## Modifier les textes

- Pages : `src/pages/*.html` (en-tête `titre` et `description` pour Google en haut de chaque fichier).
- Éléments communs : `src/partials/` (en-tête, menu, pied de page, bloc d'appel, prix).
- Styles : `src/static/css/style.css` ; interactions : `src/static/js/main.js`.

Après chaque modification : `python3 build.py`. Ne modifiez pas `public/` directement, il est régénéré.

## Sources des informations

- Identité légale (SIREN 397 838 426, siège, création en 1994, gérant, capital, TVA) :
  [annuaire-entreprises.data.gouv.fr](https://annuaire-entreprises.data.gouv.fr/entreprise/397838426)
  et registre du commerce.
- Prix 2025 (plus belle rénovation de devanture commerciale 2024, 59 rue Pargaminières) :
  [La Dépêche du Midi, 17 juin 2025](https://www.ladepeche.fr/2025/06/17/plus-belle-renovation-12766794.php).
- Prix 2026 (Patrimoine Remarquable, 3 place Robert-Schuman ; Patrimoine Domestique, 11 rue des Lois) :
  La Dépêche du Midi, édition papier, article « Une société doublement primée pour ses façades ».

## Crédits photographiques

`facade-rue-des-lois`, `facade-place-schuman` et `chantier-peinture-sols` : photos de la SARL ANDRES
PASCAL (chantiers réalisés par l'entreprise).

Photos [Pexels](https://www.pexels.com/license/) (usage commercial autorisé, sans attribution obligatoire) :

| Fichier | Photo Pexels |
|---|---|
| `peinture-rouleau` | [7218683](https://www.pexels.com/photo/7218683/) |
| `peinture-conseil-couleurs` | [8293669](https://www.pexels.com/photo/8293669/) |
| `peinture-papier-peint` | [5641766](https://www.pexels.com/photo/5641766/) |
| `toulouse-rue-briques` | [30753234](https://www.pexels.com/photo/30753234/) |
| `toulouse-capitole` | [30753238](https://www.pexels.com/photo/30753238/) |
| `toulouse-dome-grave` | [30753243](https://www.pexels.com/photo/30753243/) |
| `platrerie-cloison` | [5493675](https://www.pexels.com/photo/5493675/) |
| `platrerie-plafond` | [6474129](https://www.pexels.com/photo/6474129/) |
| `sols-pose` | [4263067](https://www.pexels.com/photo/4263067/) |
| `sols-point-de-hongrie` | [7587872](https://www.pexels.com/photo/7587872/) |
| `sols-point-de-hongrie-salle` | [8143700](https://www.pexels.com/photo/8143700/) |
| `sols-point-de-hongrie-detail` | [6856821](https://www.pexels.com/photo/6856821/) |
| `sols-point-de-hongrie-sejour` | [16922964](https://www.pexels.com/photo/16922964/) |
| `sols-batons-rompus` | [4409365](https://www.pexels.com/photo/4409365/) |
| `sols-batons-rompus-detail` | [15066939](https://www.pexels.com/photo/15066939/) |
| `sols-batons-rompus-ancien` | [35822328](https://www.pexels.com/photo/35822328/) |

Polices : Fraunces et Nunito Sans (licence SIL Open Font License), hébergées dans `src/static/fonts/`.
