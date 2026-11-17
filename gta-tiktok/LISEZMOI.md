# GTA 6 ZAP : le pilote automatique de la chaîne TikTok

Chaîne TikTok française de clips GTA VI (sortie le jeudi 19 novembre 2026 sur PS5 et Xbox Series).
Ce dossier fait tout le travail de production :

1. **Récolte** chaque matin les clips Twitch GTA VI les plus vus des dernières 24 h, uniquement chez les
   streamers qui t'ont donné leur accord.
2. **Découpe** aussi les longs streams que tu déposes dans `a_traiter/` (VOD fournies par une campagne de
   clipping, rushs autorisés, tes propres parties) : il repère tout seul les moments forts.
3. **Monte** chaque clip en vertical 1080×1920 : accroche en gros avec un mot en jaune, crédit du créateur,
   ton @, appel à s'abonner à la fin, son normalisé à −14 LUFS, sous-titres mot à mot en option.
4. **Assemble** le TOP 5 du jour (plus d'une minute, le format qui compte pour Creator Rewards).
5. **Prépare** `publications.txt` : pour chaque vidéo, l'heure de publication, la légende et les hashtags à
   copier-coller.

6. **Programme** lui-même chaque vidéo sur TikTok via Upload-Post (mode 100 % automatique ci-dessous).

---

## Mode 100 % automatique (recommandé) : rien à faire au quotidien

Le pilote tourne chaque matin à 5 h 30 sur les serveurs de GitHub (ton ordinateur peut rester éteint) et
programme les vidéos sur TikTok via **Upload-Post**, un service partenaire de l'API officielle de TikTok.
C'est la seule voie automatique qui ne met pas le compte en danger : TikTok n'autorise la publication par
API qu'aux applications qu'il a auditées, et un robot qui clique à ta place sur TikTok fait bannir le compte.

### Une seule fois (30 minutes)

1. **Upload-Post** (upload-post.com) : crée un compte, crée un profil nommé `gta6zap`, connecte ton compte
   TikTok à ce profil (fenêtre de connexion officielle TikTok), puis copie ta clé API. Le forfait gratuit
   est limité en nombre d'envois par mois : à 6 vidéos par jour (environ 180 par mois), il faut un forfait
   payant, vérifie le tarif du moment sur leur site.
2. **Twitch** : crée tes clés comme indiqué en 2.1.
3. **Secrets GitHub** : sur github.com, dans ce dépôt → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**. Crée ces trois secrets (nom exact, puis la valeur) :
   - `TWITCH_CLIENT_ID`
   - `TWITCH_CLIENT_SECRET`
   - `UPLOAD_POST_API_KEY`

   Les clés ne se tapent jamais dans un fichier du dépôt ni dans une conversation.
4. **Créateurs autorisés** : ajoute-les dans `gta-tiktok/config.cloud.json` (bloc `"createurs"`, même
   format qu'en 2.2). Sur github.com, ouvre le fichier et clique sur le crayon pour le modifier, ou demande
   à Claude de le faire.
5. Si ton profil Upload-Post ne s'appelle pas `gta6zap`, change `publication.auto.profil` dans
   `config.cloud.json`.
6. **Activation** : `.github/workflows/gta6zap.yml` doit se trouver sur la branche par défaut du dépôt.
   Ensuite : onglet **Actions** → **GTA 6 Zap - pilote quotidien** → **Run workflow**, coche
   « Essai à blanc » pour vérifier les clés et la liste des clips retenus, puis relance sans cocher.

### Ensuite, chaque jour, tout seul

- 5 h 30 : récolte des clips, montage, TOP du jour, programmation des 6 vidéos entre 12 h et 22 h 30
  (les meilleures le soir).
- Les vidéos du jour restent téléchargeables 7 jours : onglet **Actions** → l'exécution → **Artifacts**.
- Si un envoi échoue (clé expirée, vidéo refusée), l'exécution passe en rouge et **GitHub t'envoie un
  e-mail**. La vidéo concernée figure dans `publications.txt` de l'artefact, prête à publier à la main.
- La mémoire du pilote (clips déjà traités, file de publication) est conservée d'un jour à l'autre.

Ce qui reste à toi : coller les liens de tes vidéos dans tes campagnes de clipping, si tu en fais
(2 minutes par jour), et contacter de nouveaux streamers le dimanche.

### Coût

- GitHub Actions : gratuit dans la limite de 2 000 minutes par mois pour un dépôt privé (illimité pour un
  dépôt public). Une exécution prend 15 à 25 minutes, soit 450 à 750 minutes par mois.
- Upload-Post : selon le forfait choisi.

### Autres plateformes

Les mêmes vidéos peuvent partir sur YouTube Shorts et Instagram Reels : connecte ces comptes au même profil
Upload-Post et mets `"plateformes": ["tiktok", "youtube", "instagram"]` dans `config.cloud.json`.
Cette option n'a pas été testée en conditions réelles : fais d'abord un essai sur une journée.

### Publication automatique depuis ton propre PC

Si tu préfères garder le pilote sur ton ordinateur : dans `config.json`, mets `publication.auto.actif` à
`true`, renseigne `publication.auto.profil`, et fournis la clé dans la variable d'environnement
`UPLOAD_POST_API_KEY` (Windows : `setx UPLOAD_POST_API_KEY "ta_clé"` puis rouvre le terminal).

---

## 1. Installation (une fois, 15 minutes)

### Windows

1. Installe Python 3.12 depuis le Microsoft Store (cherche « Python 3.12 »), ou sur python.org en cochant
   « Add python.exe to PATH ».
2. Ouvre « Terminal » (ou « Invite de commandes ») et installe ffmpeg :
   ```
   winget install Gyan.FFmpeg
   ```
3. Ferme puis rouvre le terminal, va dans le dossier `gta-tiktok` et installe les dépendances :
   ```
   cd chemin\vers\gta-tiktok
   python -m pip install -r requirements.txt
   ```

### macOS

```
brew install python ffmpeg
cd chemin/vers/gta-tiktok
python3 -m pip install -r requirements.txt
```

Vérification : `ffmpeg -version` et `python automate.py --help` doivent répondre sans erreur.

`faster-whisper` (sous-titres automatiques) télécharge un modèle de reconnaissance vocale d'environ 500 Mo
au premier usage. Sans carte graphique NVIDIA, compte 20 à 40 secondes de calcul par clip.

---

## 2. Configuration (une fois, 20 minutes)

```
python automate.py --init
```

Cela crée `config.json` (jamais envoyé sur GitHub : il contient tes clés) et les dossiers `a_traiter/` et
`a_publier/`. Ouvre `config.json` avec le Bloc-notes et remplis trois choses.

### 2.1 Les clés Twitch (gratuites)

1. Va sur https://dev.twitch.tv/console/apps et connecte-toi avec ton compte Twitch (active la double
   authentification si Twitch la demande).
2. « Register Your Application » :
   - Name : `gta6zap-clips` (n'importe quel nom unique) ;
   - OAuth Redirect URLs : `http://localhost` ;
   - Category : `Application Integration` ;
   - Client Type : `Confidential`.
3. Ouvre l'application créée : copie le **Client ID**, clique **New Secret** et copie le **Client Secret**.
4. Colle-les dans `config.json` :
   ```json
   "twitch": {
     "client_id": "ton_client_id",
     "client_secret": "ton_client_secret",
   ```

### 2.2 Les créateurs qui t'ont dit oui

Pour chaque streamer qui accepte (message type dans l'onglet « Kit » du QG), ajoute un bloc dans
`"createurs"` en recopiant `createur.exemple.json` :

```json
"createurs": [
  {
    "twitch": "login_twitch_du_streamer",
    "tiktok": "@son_compte_tiktok",
    "autorisation": "Accord écrit par DM Instagram le 18/11/2026, capture enregistrée dans preuves/",
    "actif": true
  }
]
```

- `twitch` : le nom dans l'adresse de sa chaîne (twitch.tv/**login**).
- `tiktok` : son @ TikTok s'il en a un (affiché « CLIP : @... » sur la vidéo). Vide = son nom Twitch.
- `autorisation` : la preuve de son accord. **Un créateur sans autorisation notée est ignoré.** Garde les
  captures d'écran dans un dossier `preuves/` : en cas de signalement pour droits d'auteur, c'est ce qui te
  protège.
- `actif: false` met un créateur en pause sans le supprimer.

### 2.3 Ton pseudo

`"pseudo": "@gta6zap"` : remplace par ton @ TikTok exact.

### 2.4 Test à blanc

```
python automate.py --essai
```

Affiche les clips qui seraient récupérés, sans rien télécharger.

---

## 3. Le lancement automatique chaque matin

Le pilote met 1 à 2 minutes par clip. Programme-le à 6 h : tout est prêt quand tu te lèves.
L'ordinateur doit être allumé (ou en veille, réveil autorisé) à cette heure-là.

### Windows

Dans le dossier `gta-tiktok`, ouvre l'Invite de commandes (cmd) et colle :

```
schtasks /Create /SC DAILY /ST 06:00 /TN "GTA6 Zap" /TR "\"%cd%\lancer.bat\""
```

Si ton terminal est PowerShell (l'invite commence par `PS`), tape d'abord `cmd` puis Entrée, puis colle la
commande ci-dessus.

Pour que la tâche rattrape un matin où le PC était éteint : Planificateur de tâches → « GTA6 Zap » →
Propriétés → Paramètres → coche « Exécuter la tâche dès que possible si un démarrage planifié est manqué ».
Les comptes rendus vont dans `journaux/`.

### macOS / Linux

Dans le dossier `gta-tiktok` :

```
(crontab -l 2>/dev/null; echo "0 6 * * * \"$(pwd)/lancer.sh\"") | crontab -
```

---

## 4. Ta routine si la publication automatique est désactivée (environ 12 minutes par jour)

1. Ouvre `a_publier/<date du jour>/publications.txt`.
2. Sur ordinateur, va sur TikTok Studio (tiktok.com/tiktokstudio) → **Téléverser**. Pour chaque ligne :
   dépose la vidéo, colle la légende, choisis **Programmer** et règle l'heure indiquée. Si l'heure est passée,
   publie tout de suite.
3. Une fois publiées, colle les liens TikTok dans ta ou tes campagnes de clipping (c'est ce qui déclenche
   le paiement).
4. Le dimanche : reporte les vues, abonnés et gains de la semaine dans l'onglet « Stats » du QG.

Tu peux aussi déposer à tout moment une longue vidéo dans `a_traiter/` :

- `a_traiter/<login_twitch>/fichier.mp4` : VOD d'un créateur autorisé (le nom du sous-dossier doit être
  son login Twitch présent dans `config.json`) ;
- `a_traiter/fichier.mp4` (à la racine) : tes propres captures ou des rushs fournis par une campagne ;
- un sous-dossier qui ne correspond à aucun créateur autorisé est ignoré.

Les fichiers traités sont rangés dans `a_traiter/traites/`.

---

## 5. Réglages utiles (`config.json`)

| Réglage | Défaut | Effet |
|---|---|---|
| `max_clips_par_lancement` | 5 | clips Twitch montés par jour (+ le TOP 5 = 6 vidéos) |
| `clips_par_vod` | 4 | moments gardés par long stream déposé dans `a_traiter/` |
| `twitch.vues_min` | 300 | un clip Twitch moins vu que ça est ignoré |
| `twitch.clips_par_streamer` | 3 | maximum par créateur et par jour |
| `twitch.heures` | 24 | période de recherche (mets 6 le soir de la sortie) |
| `twitch.langue` | `fr` | langue des clips ; `""` pour toutes |
| `accroche_titre_twitch` | true | reprend le titre donné au clip par le viewer s'il fait une bonne accroche |
| `montage.sous_titres` | false | `true` = sous-titres mot à mot (faster-whisper) |
| `montage.cadre` | `flou` | `plein` = recadrage plein écran (perd les côtés) |
| `montage.zoom` | 1.25 | grossit l'action (1 = image entière) |
| `montage.style` | `contour` | `boite` = texte noir sur bandeau blanc |
| `montage.cta` | `ABONNE-TOI POUR LA SUITE` | texte des 2 dernières secondes, `""` pour aucun |
| `publication.horaires` | 12:00 → 22:30 | créneaux proposés ; les meilleurs clips vont le soir |
| `publication.hashtags` | 4 jeux | utilisés à tour de rôle |

Le pilote garde en mémoire (`.etat/`) les clips déjà traités : un clip n'est jamais monté deux fois.
S'il produit plus de vidéos que de créneaux, il les décale aux jours suivants et te prévient quand la file
dépasse trois jours.

---

## 6. Outil manuel : `clipper.py`

Pour un passage précis, sans passer par le pilote :

```
# un clip entre 1:02:10 et 1:02:31, le mot entre étoiles passe en jaune
python clipper.py clip vod.mp4 --debut 1:02:10 --fin 1:02:31 --hook "IL A PAS VU LE *CROCO*" --credit @streamer

# repérer les moments forts d'un stream et écrire un fichier lot modifiable
python clipper.py reperer vod.mp4 --credit @streamer --autorisation "DM du 18/11"
python clipper.py lot exports/vod_lot.json

# tout d'un coup : repérage + clips + TOP 5
python clipper.py auto vod.mp4 --credit @streamer --autorisation "DM du 18/11" --sous-titres

# image de couverture
python clipper.py couverture vod.mp4 --temps 1:02:20 --titre "LE CROCO LE PLUS *FOU* DE GTA 6"
```

`--rapide` fait un rendu deux à trois fois plus rapide pour vérifier avant le rendu final.
`python clipper.py clip --help` liste tous les réglages.

### Format d'un fichier lot

```json
{
  "reglages": { "pseudo": "@gta6zap", "sortie": "exports", "sous_titres": false },
  "sources": {
    "stream_19nov": {
      "fichier": "a_traiter/stream_19-11.mp4",
      "credit": "@streamer",
      "autorisation": "Accord écrit par DM le 18/11/2026"
    }
  },
  "clips": [
    { "source": "stream_19nov", "debut": "01:12:30", "fin": "01:12:52", "hook": "IL A PAS VU LE *CROCO*" }
  ],
  "compilations": [
    {
      "nom": "top3_police",
      "titre": "TOP 3 DES POURSUITES LES PLUS *FOLLES*",
      "classement": true,
      "segments": [
        { "source": "stream_19nov", "debut": "00:41:02", "fin": "00:41:20", "label": "LE PONT" },
        { "source": "stream_19nov", "debut": "01:55:40", "fin": "01:55:58", "label": "LE MARAIS" },
        { "source": "stream_19nov", "debut": "02:30:11", "fin": "02:30:33", "label": "LA PLAGE" }
      ]
    }
  ]
}
```

Un clip sans `hook` reçoit une accroche automatique (40 accroches dans `clipper.py`, `HOOKS_AUTO`).
Le classement d'une compilation va du dernier au premier : mets le meilleur segment en dernier.

---

## 7. Les règles qui protègent la chaîne

- **Uniquement des contenus autorisés.** Republier les clips d'un créateur sans son accord, c'est des
  signalements pour droits d'auteur, des vidéos supprimées et, au bout de quelques-uns, un compte banni.
  Les campagnes de clipping et les streamers qui acceptent te donnent tout le contenu dont tu as besoin.
- **Toujours créditer** : sur la vidéo (automatique) et dans la légende (automatique).
- **Musique des radios du jeu** : elle est sous licence. Si TikTok coupe le son d'une vidéo, refais-la avec
  `--son-jeu 0 --musique` et un son libre de droits.
- **Rien d'avant la sortie ni de fuite** : Take-Two fait retirer systématiquement ces contenus.
- **Pas de nudité, de gore poussé ni de gros plans de drogue** : même dans un jeu, TikTok retire ou cesse de
  recommander ces vidéos.
- **Pas d'apparence officielle** : pas de logo Rockstar en photo de profil, « compte fan non officiel » dans
  la bio.

---

## 8. Fichiers

| Fichier | Rôle |
|---|---|
| `automate.py` | pilote automatique (récolte Twitch, dossier `a_traiter/`, montage, TOP 5, planning, publication) |
| `publication.py` | programmation automatique sur TikTok via l'API Upload-Post |
| `config.cloud.json` | configuration utilisée par GitHub Actions (sans aucune clé : elles sont dans les secrets) |
| `../.github/workflows/gta6zap.yml` | exécution quotidienne à 5 h 30 sur GitHub Actions |
| `clipper.py` | moteur de montage et commandes manuelles |
| `config.exemple.json` | modèle de configuration copié par `--init` |
| `createur.exemple.json` | bloc à recopier pour chaque créateur autorisé |
| `lancer.bat` / `lancer.sh` | lancement quotidien (Windows / macOS-Linux) |
| `requirements.txt` | dépendances Python |
| `polices/Anton-Regular.ttf` | police des accroches (licence SIL OFL, usage commercial autorisé) |
| `identite/avatar.png` | photo de profil du compte (1080×1080) |
| `qg/qg-gta6zap.html` | source du tableau de bord en ligne (plan, calendrier, stats, revenus, kit) |
| `a_publier/<date>/` | vidéos prêtes + `publications.txt` + `publications.csv` (créé à l'usage) |
| `journal_publications.csv` | historique de tout ce qui a été produit (créé à l'usage) |
