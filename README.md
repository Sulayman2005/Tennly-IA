# Tennly IA

Application d'analyse tennis par IA : Elo réel par surface + statistiques de jeu réelles (service, retour, forme, repos...) calculés sur l'historique ATP, expliqués simplement plutôt que cachés derrière une boîte noire.

## Architecture

```
veritennis/
├── backend/       Symfony 7 + API Platform — API REST/JSON-LD, auth JWT, paiement Stripe
├── frontend/      Vue 3 + Vite — SPA qui consomme l'API
└── ml-service/    Python — récupère les données ATP réelles et calcule les analyses IA
```

Le backend et le frontend communiquent en JSON-LD (API Platform). Le backend et le service Python ne se parlent jamais directement : le script Python écrit ses résultats dans la base MySQL (tables `player`, `tennis_match`, `prediction`), que Symfony se contente de lire. Ça permet de faire évoluer le calcul des analyses sans toucher à l'application web, et inversement.

Base de données : **MySQL**. Depuis le 29/08/2026, l'environnement local recommandé est **Docker** (voir `DOCKER.md`) : un conteneur unique PHP+Python (Apache, Symfony, ml-service) + un conteneur MySQL + un conteneur phpMyAdmin (`localhost:8080`), qui remplace WAMP. Le frontend Vue continue de tourner nativement (`npm run dev`), inchangé. Les instructions d'installation manuelle ci-dessous (sans Docker) restent valables si tu préfères repartir d'un environnement WAMP/PHP natif.

## Installation — backend

```bash
cd backend
composer install

# Base de données locale (WAMP, MySQL, root sans mot de passe par défaut) :
# crée la base "tennly" via phpMyAdmin, ou :
#   mysql -u root -e "CREATE DATABASE tennly CHARACTER SET utf8mb4;"
cp .env .env.local   # puis éditer APP_SECRET, JWT_PASSPHRASE, DATABASE_URL, clés Stripe

# Génération des clés JWT (lexik/jwt-authentication-bundle) :
mkdir -p config/jwt
openssl genpkey -out config/jwt/private.pem -aes256 -algorithm rsa -pkeyopt rsa_keygen_bits:4096
openssl pkey -in config/jwt/private.pem -out config/jwt/public.pem -pubout

# Migrations :
php bin/console doctrine:migrations:migrate

# Données de test optionnelles (joueur/match/analyse d'exemple + un compte
# abonné et un compte admin utilisables tels quels, voir plus bas) : importer
# backend/migrations/seed_dev_data.sql via phpMyAdmin.

php -S 127.0.0.1:8000 -t public
# API disponible sur http://127.0.0.1:8000/api (doc Swagger interactive à cette même adresse)
```

## Installation — frontend

```bash
cd frontend
npm install
npm run dev
# App disponible sur http://localhost:5173, le proxy Vite redirige /api vers http://127.0.0.1:8000
```

## Installation — récupération des données réelles

```bash
cd ml-service
python import_real_data.py
# Génère import_real_data.sql : à importer ensuite dans la base "tennly" via phpMyAdmin
```

Voir `ml-service/README.md` pour le détail de ce que fait le script.

## Ce qui fonctionne aujourd'hui

**Données réelles.** `import_real_data.py` télécharge de vrais joueurs et résultats de matchs ATP sur plusieurs années (dépôt public `Tennismylife/TML-Database`, gratuit, sans compte), rejoue tout l'historique chronologiquement pour calculer un vrai Elo par joueur et par surface (dur/terre battue/gazon), et calcule de vraies statistiques service/retour à partir des scores (aces, % de premier service, balles de break). S'y ajoutent cinq signaux supplémentaires quand l'échantillon est suffisant : dynamique du moment (tendance de l'Elo sur les 8 derniers matchs), habitude du jeu face à un gaucher/droitier, fatigue récente, habitude du jeu en intérieur, capacité à créer l'exploit contre plus fort classé. Aucune donnée n'est inventée : quand l'échantillon est trop petit, le facteur n'est simplement pas affiché plutôt que remplacé par une valeur neutre inventée.

**Backend.** Entités `User`, `Plan`, `Subscription`, `Player`, `TennisMatch`, `Prediction`, `RefreshToken`. Sécurité par JWT (lexik) + refresh token (gesdinet). Le paywall est géré via les groupes de sérialisation API Platform : l'aperçu (favori pressenti, probabilité, confiance) est public sur `GET /api/tennis_matches`, l'analyse complète (radar, facteurs d'explication détaillés, cote de marché) n'apparaît que sur `GET /api/predictions/{id}`, réservé aux abonnés. `GET /api/me` renvoie l'utilisateur courant avec son statut d'abonnement. Paiement Stripe (mode test) : création de session Checkout à l'inscription si une formule est choisie, webhook qui active l'abonnement à la confirmation du paiement.

**Frontend.** Les 4 écrans du parcours principal (Accueil, Matchs, Fiche match, Connexion/Inscription). La page d'accueil a été redesignée dans un style Apple avec un moment "terre battue" mis en avant, en s'inspirant de l'organisation de Visifoot. La fiche match affiche le radar comparatif et les facteurs d'explication (y compris les 5 nouveaux signaux quand ils sont pertinents pour le match affiché).

**Back-office admin** (section 3.7). Contrepartie Vue des maquettes `admin.html` / `admin-analyse-match.html`, branchée sur le vrai backend Symfony — aucune donnée fictive :

- `GET /api/admin/dashboard` (nouvelle ressource non-Doctrine, `AdminDashboardProvider`, sécurité `ROLE_ADMIN`) calcule en direct : répartition des abonnements actifs par formule, MRR (mensualisé selon la périodicité de chaque formule), taux de réussite du modèle global et par surface (comparaison `Prediction::favoritePlayer` / `TennisMatch::winner` sur les matchs réellement terminés), nombre d'analyses calculées et de matchs à venir. Un agrégat non calculable (aucun match terminé, par exemple) renvoie `null` plutôt qu'une valeur inventée.
- Page **Modèle IA** : liste des matchs (filtrable par surface/statut/tournoi, filtres déjà supportés par `TennisMatch`) → fiche d'analyse par match (gauge de probabilité, radar comparatif, tornado des facteurs d'explication, cote de marché/value bet), avec une vue "après match" (score réel, analyse IA vs résultat) quand le match est terminé.
- Page **Abonnés** : liste réelle des abonnements (`GET /api/subscriptions`, qui renvoie déjà toute la collection à un admin grâce à `CurrentUserSubscriptionExtension`) avec email, formule, statut, fin de période.
- Un compte `ROLE_ADMIN` (`admin@tennly.local` / `admin1234` dans `seed_dev_data.sql`) voit apparaître le lien "Back-office" dans le header et peut accéder à `/admin/*` ; ces routes sont gardées côté client (`router/index.js`) mais la sécurité réelle reste `is_granted('ROLE_ADMIN')` côté API.
- Volontairement absent : onglet "Contenu" (aucune entité de contenu éditorial n'existe encore, affiché en placeholder plutôt que fabriqué), supervision live du pipeline d'ingestion et calendrier des tournois (aucune source de données réelle pour l'instant, voir plus bas) — pas de widget avec un contenu inventé pour "faire joli".

## Ce qui fonctionne depuis le 29/08/2026 (déploiement local + CI/CD)

- **Environnement Docker** : remplace WAMP en local — voir `DOCKER.md`. Backend (Symfony) + ml-service (Python) dans un même conteneur (le premier appelle le second en sous-processus via un chemin relatif, donc les deux doivent partager le même système de fichiers), + conteneur MySQL, + phpMyAdmin. Vraies données migrées (239 joueurs, 157 matchs/analyses).
- **Tests automatisés** : PHPUnit côté Symfony, Vitest côté Vue.
- **CI/CD** (`.github/workflows/ci.yml`) : lance les tests à chaque push/PR, construit l'image Docker à chaque push/PR (détection immédiate si le Dockerfile casse), et publie l'image sur GitHub Container Registry (ghcr.io) à chaque push sur `main` — premier pas vers le déploiement continu, en attendant de choisir un hébergeur (voir plus bas).
- **Calendrier des matchs à venir** : `ml-service/import_upcoming_matches.py` récupère le vrai calendrier ATP et WTA via LiveTennisAPI (compte gratuit avec clé API) et l'écrit directement en base, sans jamais effacer l'existant. Automatisable en tâche planifiée Windows quotidienne — voir `ml-service/AUTOMATISATION.md` (et sa note importante sur le mot de passe MySQL à mettre à jour depuis le passage à Docker).
- **Comparateur ATP/WTA** : le badge de circuit (ATP/WTA) et le libellé de classement s'affichent désormais correctement pour les deux circuits (`Player::tour`, `PlayerComparisonService`).

## Ce qui reste à faire

- **Stats de la page d'accueil** : les chiffres mis en avant (67,8 % de réussite, 12 480 matchs analysés, +4,1 % de value, 0,19 de score de Brier) sont pour l'instant des valeurs fixes codées dans `HomeView.vue` (`TODO` explicite dans le fichier), en attendant un vrai endpoint `/api/stats` qui les calculerait depuis les vraies données — ce qui contredit pour l'instant le principe "aucune donnée inventée" appliqué partout ailleurs sur le site. À trancher : construire l'endpoint réel, ou remplacer temporairement ces chiffres par un état "à venir" plutôt que des valeurs inventées.
- **Modèle entraîné** : les analyses reposent aujourd'hui sur une formule (Elo + statistiques réelles), pas encore sur un modèle de machine learning entraîné (XGBoost/LightGBM). `ml-service/train_model.py` existe et sait entraîner/sauvegarder un modèle (`ml-service/model/tennis_model.json`), et `model_inference.py` sait déjà s'en servir s'il est présent (repli automatique sur la formule sinon) — mais le brancher réellement dans les scripts d'import est une étape volontairement séparée, pas encore faite.
- **Design des autres pages** : le nouveau style (terre battue, palette Apple) n'est appliqué qu'à la page d'accueil et au back-office admin (qui réutilise les tokens existants). Les autres pages (Connexion, Matchs, Fiche match...) gardent l'ancien style — c'est la prochaine étape, une fois le déploiement/back validés.
- **Contenu éditorial admin** : la section 3.7 prévoit un onglet "Contenu" — pas d'entité ni de CRUD pour l'instant, faute de contenu éditorial réel à gérer dans le projet.
- **Hébergement en ligne** : le projet tourne désormais dans des conteneurs Docker en local (voir `DOCKER.md`) et l'image est déjà publiée sur GitHub Container Registry à chaque push sur `main`, mais l'hébergeur qui ferait tourner ces conteneurs en ligne (et le nom de domaine) n'est pas encore choisi.