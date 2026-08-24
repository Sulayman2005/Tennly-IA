# Tennly IA

Application de pronostics tennis : Elo réel par surface + statistiques de jeu réelles (service, retour, forme, repos...) calculés sur l'historique ATP, expliqués simplement plutôt que cachés derrière une boîte noire.

## Architecture

```
veritennis/
├── backend/       Symfony 7 + API Platform — API REST/JSON-LD, auth JWT, paiement Stripe
├── frontend/      Vue 3 + Vite — SPA qui consomme l'API
└── ml-service/    Python — récupère les données ATP réelles et calcule les pronostics
```

Le backend et le frontend communiquent en JSON-LD (API Platform). Le backend et le service Python ne se parlent jamais directement : le script Python écrit ses résultats dans la base MySQL (tables `player`, `tennis_match`, `prediction`), que Symfony se contente de lire. Ça permet de faire évoluer le calcul des pronostics sans toucher à l'application web, et inversement.

Base de données : **MySQL**, via WAMP en local (phpMyAdmin pour l'administrer).

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

## Ce qui reste à faire

- **Calendrier de matchs à venir** : le script actuel ne récupère que des matchs déjà joués (l'historique sert à calculer l'Elo). Un vrai calendrier du jour nécessiterait une API externe payante ou avec inscription — pas fait pour l'instant, volontairement.
- **Modèle entraîné** : les pronostics reposent aujourd'hui sur une formule (Elo + statistiques réelles), pas encore sur un modèle de machine learning entraîné (XGBoost/LightGBM) — choix assumé pour privilégier une base fiable avant d'ajouter de la complexité.
- **Design des autres pages** : le nouveau style (terre battue, palette Apple) n'est appliqué qu'à la page d'accueil. Connexion et back-office admin gardent l'ancien style.
- **Back-office admin** (section 3.7 du cahier des charges) : pas encore de contrepartie Vue — les maquettes `admin.html` / `admin-analyse-match.html` servent de référence visuelle.
- **Tests automatisés** (PHPUnit côté Symfony, Vitest côté Vue) et **CI/CD**.
- **Hébergement en ligne** : le projet tourne pour l'instant uniquement en local (WAMP + serveur PHP intégré + Vite dev server). Pas encore déployé.