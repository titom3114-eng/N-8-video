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
| `sols.html` | Parquet, stratifié, PVC, moquette : prestations, méthode, tableau « quel sol pour quelle pièce », FAQ |
| `entreprise.html` | Histoire familiale, chiffres clés, distinctions, valeurs, types de clients |
| `contact.html` | Formulaire de devis (le métier est pré-coché depuis chaque page), coordonnées, plan |
| `mentions-legales.html` | Mentions légales, données personnelles (RGPD), crédits photos |
| `merci.html`, `404.html` | Confirmation d'envoi du formulaire, page introuvable |

Points techniques : responsive (mobile, tablette, ordinateur), accessible (navigation au clavier, contrastes,
textes alternatifs), référencement local (balises, données structurées `HousePainter`, plan du site),
polices hébergées sur le site (aucun appel à Google), aucun cookie ni traceur, en-têtes de sécurité.

## Compléter les coordonnées

Le numéro de téléphone et l'adresse e-mail de l'entreprise ne sont pas publiés en ligne : ils sont à
renseigner dans `site.json`. Tant qu'un champ est vide, l'élément correspondant est masqué proprement.

```json
"telephone": "05 61 12 34 56",
"telephone_mobile": "06 12 34 56 78",
"email": "contact@votre-domaine.fr",
"horaires": "Du lundi au vendredi, 8 h – 12 h et 14 h – 18 h"
```

et, une fois le nom de domaine choisi :

```json
"url": "https://www.votre-domaine.fr"
```

Puis régénérez le site :

```bash
python3 build.py
```

Le téléphone apparaît alors dans l'en-tête, le menu mobile, chaque page métier, le pied de page et la
page contact ; l'adresse du site active le plan du site (`sitemap.xml`), les adresses canoniques et
l'image d'aperçu pour les réseaux sociaux.

La liste des communes de la zone d'intervention se modifie aussi dans `site.json`.

## Mettre le site en ligne

### Netlify (recommandé, gratuit)

1. Créez un compte sur [netlify.com](https://www.netlify.com).
2. Glissez-déposez le dossier `public/` sur [app.netlify.com/drop](https://app.netlify.com/drop).
3. Dans **Domain management**, reliez votre nom de domaine.
4. Les demandes de devis arrivent dans l'onglet **Forms** ; activez l'envoi par e-mail dans
   **Site configuration > Forms > Form notifications**.

Pour publier automatiquement depuis ce dépôt Git, indiquez `site-andres-peintures` comme
**Base directory** : le fichier `netlify.toml` fait le reste.

### Autre hébergeur (OVH, o2switch…)

1. Dans `site.json`, renseignez `"email"` et passez `"formulaire"` à `"courriel"` : le formulaire
   prépare alors la demande dans la messagerie du visiteur, sans serveur.
2. Remplacez les champs `hebergeur_nom`, `hebergeur_adresse` et `hebergeur_site` par ceux de votre
   hébergeur (ils apparaissent dans les mentions légales).
3. Lancez `python3 build.py`, puis envoyez le contenu de `public/` dans le dossier `www` de l'hébergement.

## Ajouter vos photos de chantiers

Les photos actuelles sont des illustrations libres de droits. Vos propres photos (avant/après, façades
primées, équipe au travail) renforceront encore la confiance :

```bash
pip install pillow
python3 outils/ajouter-photo.py photo-pargaminieres.jpg facade-ravalement
python3 build.py
```

Réutiliser un nom existant remplace la photo partout où elle apparaît. Pensez à adapter la mention
« Crédits photographiques » de `src/pages/mentions-legales.html` si toutes les photos deviennent les vôtres.

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
- Prix 2026 (Patrimoine Remarquable, 3 place Schuman ; Patrimoine Domestique, 11 rue des Lois) :
  La Dépêche du Midi, édition papier, article « Une société doublement primée pour ses façades ».

## Crédits photographiques

Photos [Pexels](https://www.pexels.com/license/) (usage commercial autorisé, sans attribution obligatoire) :

| Fichier | Photo Pexels |
|---|---|
| `salon-renove` | [36777534](https://www.pexels.com/photo/36777534/) |
| `peinture-rouleau` | [7218683](https://www.pexels.com/photo/7218683/) |
| `peinture-conseil-couleurs` | [8293669](https://www.pexels.com/photo/8293669/) |
| `peinture-papier-peint` | [5641766](https://www.pexels.com/photo/5641766/) |
| `facade-ravalement` | [38326993](https://www.pexels.com/photo/38326993/) |
| `toulouse-rue-briques` | [30753234](https://www.pexels.com/photo/30753234/) |
| `toulouse-capitole` | [30753238](https://www.pexels.com/photo/30753238/) |
| `toulouse-dome-grave` | [30753243](https://www.pexels.com/photo/30753243/) |
| `toulouse-balcon` | [30753239](https://www.pexels.com/photo/30753239/) |
| `platrerie-cloison` | [5493675](https://www.pexels.com/photo/5493675/) |
| `platrerie-plafond` | [6474129](https://www.pexels.com/photo/6474129/) |
| `sols-pose` | [4263067](https://www.pexels.com/photo/4263067/) |
| `sols-piece-lumineuse` | [7027997](https://www.pexels.com/photo/7027997/) |

Polices : Fraunces et Nunito Sans (licence SIL Open Font License), hébergées dans `src/static/fonts/`.
