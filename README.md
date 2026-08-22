# Tennly IA — scaffolding technique

Point de départ du code, en suivant le cahier des charges (section 4.5 :
Symfony + Vue.js + PostgreSQL, service Python séparé pour le data/ML).

## Important : à propos de ce scaffolding

Ce code a été **écrit à la main**, fichier par fichier, dans un environnement
cloud qui n'a pas accès à Packagist ni au registre npm — il n'a donc pas pu
être installé (`composer install` / `npm install`) ni lancé pour un test de
bout en bout automatisé ici. En revanche :

- Chaque fichier PHP a été vérifié avec `php -l` (aucune erreur de syntaxe).
- Chaque fichier `.vue`/`.js` a été vérifié avec `node --check` sur son
  contenu `<script>` (aucune erreur de syntaxe).
- **Le schéma de base de données a été réellement créé et testé** contre une
  instance PostgreSQL 16 locale, avec des données réalistes insérées et
  requêtées avec succès (voir `backend/migrations/seed_dev_data.sql`) — donc
  le modèle de données (tables, clés étrangères, colonnes JSON, énumérations)
  est validé, pas seulement écrit sur la foi de la documentation Doctrine.

Une fois `composer install` et `npm install` lancés sur une machine avec un
accès internet normal, il restera probablement quelques ajustements mineurs
à faire (versions exactes de paquets, génération des clés JWT) mais la
structure, les entités, la sécurité et les vues sont un vrai point de départ,
pas une maquette.

**Sur les contraintes de version dans `composer.json`/`package.json`** : elles
ont été écrites de mémoire, sans pouvoir interroger Packagist/npm pour
vérifier les numéros exacts. Un premier problème de ce genre est déjà apparu
et a été corrigé (`doctrine/doctrine-fixtures-bundle` retiré : la contrainte
`^1.5` ne correspondait à aucune version publiée, et le paquet n'était de
toute façon pas utilisé — les données de test passent par
`migrations/seed_dev_data.sql`). Si `composer install`/`npm install`
bloquent encore sur un autre paquet avec un message "Your requirements
could not be resolved...", le plus simple est de me renvoyer le message
d'erreur pour que j'ajuste la contrainte, ou de relâcher toi-même la ligne
concernée (par exemple `"^3.4"` → `"*"` le temps de l'installation, à
resserrer ensuite sur la version réellement installée).

## Architecture (rappel section 4.5 du cahier des charges)

```
veritennis/
├── backend/       Symfony 7 + API Platform — API REST, auth JWT, back-office
├── frontend/       Vue 3 + Vite — SPA consommant l'API
└── ml-service/     Python (à construire) — pipeline data/ML, écrit dans la même base
```

Le backend et le frontend communiquent en JSON-LD/Hydra (API Platform).
Le backend et le service Python communiquent uniquement via PostgreSQL.

## Installation — backend

```bash
cd backend
composer install

# Base de données locale (déjà créée dans cette session, à refaire ailleurs) :
#   sudo -u postgres psql -c "CREATE USER veritennis WITH PASSWORD 'veritennis' CREATEDB;"
#   sudo -u postgres psql -c "CREATE DATABASE veritennis OWNER veritennis;"
cp .env .env.local   # puis éditer APP_SECRET, JWT_PASSPHRASE, clés Stripe

# Génération des clés JWT (lexik/jwt-authentication-bundle) :
mkdir -p config/jwt
openssl genpkey -out config/jwt/private.pem -aes256 -algorithm rsa -pkeyopt rsa_keygen_bits:4096
openssl pkey -in config/jwt/private.pem -out config/jwt/public.pem -pubout

# Migrations (le schéma a déjà été validé manuellement, voir migrations/seed_dev_data.sql) :
php bin/console doctrine:migrations:migrate

# Données de test (formules, joueurs, un match + son pronostic) :
psql "postgresql://veritennis:veritennis@127.0.0.1:5432/veritennis" -f migrations/seed_dev_data.sql

php -S 127.0.0.1:8000 -t public
# API disponible sur http://127.0.0.1:8000/api, docs sur /api/docs
```

## Installation — frontend

```bash
cd frontend
npm install
npm run dev
# App disponible sur http://localhost:5173, proxy /api vers http://127.0.0.1:8000
```

## Ce qui est déjà en place

- **Entités** (`backend/src/Entity/`) : `User`, `Plan`, `Subscription`,
  `Player`, `TennisMatch`, `Prediction`, `RefreshToken`.
- **Sécurité** : JWT (lexik) + refresh token (gesdinet), rôles `ROLE_USER` /
  `ROLE_ADMIN`. Le paywall (section 3.2.1) est implémenté via les groupes de
  sérialisation API Platform : les champs d'aperçu (favori, probabilité,
  confiance) sont publics et embarqués directement dans `GET
  /api/tennis_matches` (groupe `match:read`, y compris le joueur favori et le
  match lui-même — pas de simples IRI à résoudre à la main côté frontend),
  les champs détaillés (radar, explication, cote de marché) n'apparaissent
  que sur `GET /api/predictions/{id}`, une opération qui exige
  `user.hasActiveSubscription()`.
- **`GET /api/me`** (`CurrentUserProvider`) : renvoie toujours l'utilisateur
  du token courant (jamais un id arbitraire) avec son statut d'abonnement
  (`hasActiveSubscription()`, groupe `user:read`) — c'est ce que
  `frontend/src/stores/auth.js` appelle pour savoir si la popup paywall doit
  s'afficher, y compris après un rafraîchissement de page.
- **Abonnements** (`Subscription`) : la collection `GET /api/subscriptions`
  est filtrée par `CurrentUserSubscriptionExtension`
  (`backend/src/Doctrine/`) pour ne renvoyer que les abonnements de
  l'utilisateur courant (sauf `ROLE_ADMIN`) — sans cette extension,
  n'importe quel compte connecté aurait pu lister les abonnements de tous
  les autres utilisateurs.
- **Inscription** (`POST /api/register`, `UserRegistrationProcessor`) :
  n'est déclenchée que depuis l'écran de connexion en mode inscription,
  lui-même atteint uniquement depuis une formule choisie dans la popup
  paywall (jamais de bouton d'inscription libre — section 3.9). Si un
  `planCode` est transmis, une session Stripe Checkout est créée
  immédiatement après la création du compte.
- **Paiement** : `StripeCheckoutService` (création de session, avec le code
  de la formule transmis dans les métadonnées Stripe) + `StripeWebhookController`
  (confirmation `checkout.session.completed` → abonnement `active`, formule
  retrouvée via ces mêmes métadonnées plutôt qu'un paramètre de requête qui
  n'existe pas au moment où le webhook est appelé).
- **Frontend** : les 4 écrans du parcours principal (Accueil, Matchs,
  Fiche match, Connexion/Inscription), avec la même logique de bandeau de
  formule sélectionnée que `mockups/connexion.html`, la jauge de probabilité
  et le radar comparatif en SVG (mêmes calculs que les maquettes), et un
  état d'authentification (`stores/auth.js`) rechargé au démarrage de l'app
  via `GET /api/me`.

Ce backend a été relu par une passe de revue de code indépendante (5
incohérences trouvées : groupes de sérialisation Player/Prediction,
IDOR sur les abonnements, métadonnées Stripe manquantes, `/api/me`
manquant) — les 5 corrections ci-dessus en sont le résultat. Cette revue a
porté sur la cohérence du code (syntaxe, groupes, sécurité déclarée,
correspondance frontend/backend) ; elle ne remplace pas un test de bout en
bout réel, qui reste à faire une fois `composer install`/`npm install`
lancés (voir section suivante).

## Ce qu'il reste à faire

- Le service `ml-service/` (voir son propre README) : c'est lui qui doit
  peupler `player`, `tennis_match` et `prediction` avec de vraies données.
- Le back-office admin (section 3.7) : pas encore de contre-partie Vue —
  les maquettes `admin.html` / `admin-analyse-match.html` sont la référence
  visuelle une fois qu'on l'attaque.
- Tests automatisés (PHPUnit côté Symfony, Vitest côté Vue).
- CI/CD, configuration de production (section 4.6).
