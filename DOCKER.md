# Lancer Tennly IA avec Docker (à la place de WAMP)

Ce Docker remplace uniquement la partie que WAMP gérait : Apache + PHP +
MySQL (+ maintenant Python, pour ml-service). Le frontend Vue continuait déjà
de tourner en dehors de WAMP via `npm run dev` — ça ne change pas, tu gardes
exactement la même habitude pour le frontend.

## ⚠️ Avant de commencer : deux pièges à éviter

1. **Arrête WAMP complètement** avant de lancer Docker. WAMP et Docker vont
   tous les deux essayer d'utiliser les ports 3306 (MySQL) et potentiellement
   80/8000 — s'ils tournent en même temps, l'un des deux échouera à démarrer
   ou les deux se marcheront dessus silencieusement. Ferme WAMP dans la barre
   des tâches avant `docker compose up`.

2. **La base MySQL de Docker part VIDE** — ce n'est pas ta base WAMP actuelle
   avec tous tes vrais joueurs/matchs importés et ton modèle entraîné, c'est
   une toute nouvelle base MySQL. Tu as deux options :

   - **Option A (recommandée, rapide)** — migrer tes vraies données : dans
     phpMyAdmin de WAMP, onglet **Exporter** sur la base `tennly` (format SQL,
     export rapide), ça te donne un fichier `.sql`. Une fois Docker lancé
     (étapes ci-dessous), va sur `http://localhost:8080` (le phpMyAdmin de
     Docker), crée une base `tennly` si elle n'existe pas déjà, puis onglet
     **Importer** ce même fichier `.sql`. Tu retrouves toutes tes données
     réelles (joueurs, matchs, modèle) sans rien réimporter.
   - **Option B (plus long)** — repartir de zéro et relancer les scripts
     `ml-service/import_real_data.py` / `import_upcoming_matches.py` contre
     la nouvelle base Docker, puis `train_model.py` pour ré-entraîner le
     modèle. À éviter sauf si tu veux repartir propre.

## Premier lancement

Dans un terminal, à la racine du projet (là où se trouvent `Dockerfile` et
`docker-compose.yml`) :

```bash
docker compose build
docker compose up -d
```

Ça démarre trois conteneurs : `app` (Apache+PHP+Python, sur le port 8000,
comme avant), `db` (MySQL, port 3306) et `phpmyadmin` (port 8080).

Puis, toujours dans ce terminal :

```bash
# Installe les dépendances PHP (équivalent de ce que tu faisais avec WAMP)
# -w /var/www/html/backend : composer.json est dans backend/, pas à la
# racine /var/www/html (WORKDIR par défaut du conteneur) — sans ce -w,
# Composer répond "could not find a composer.json file in /var/www/html".
docker compose exec -w /var/www/html/backend app composer install

# Génère les clés JWT — nécessaire une seule fois, elles n'existent pas
# encore dans ce nouveau conteneur (config/jwt/ est dans .gitignore, comme
# avant avec WAMP). Même remarque : -w pour se placer dans backend/.
docker compose exec -w /var/www/html/backend app php bin/console lexik:jwt:generate-keypair

# Si tu as choisi l'option A ci-dessus (import du .sql), tu n'as PAS besoin
# de relancer les migrations : la structure vient avec les données importées.
# Si tu es en option B (base vide), lance les migrations existantes :
docker compose exec -w /var/www/html/backend app php bin/console doctrine:migrations:migrate
```

Le backend est maintenant sur `http://127.0.0.1:8000`, exactement comme avec
`php -S 127.0.0.1:8000 -t public`.

Le frontend, comme toujours, se lance à part (pas de changement) :

```bash
cd frontend
npm run dev
```

## Usage au quotidien

```bash
docker compose up -d      # démarrer (silencieux, en arrière-plan)
docker compose down       # arrêter (les données restent dans le volume db_data)
docker compose logs -f app   # voir les erreurs PHP en direct (équivalent du terminal WAMP)
docker compose exec -w /var/www/html/backend app vendor/bin/phpunit   # lancer les tests PHPUnit
docker compose exec -w /var/www/html/backend app php bin/console ...  # n'importe quelle commande Symfony
```

`docker compose down -v` supprime aussi le volume MySQL (vraie remise à
zéro) — à utiliser seulement si tu veux vraiment repartir de rien.

## Pour créer/re-créer le compte admin

Même procédure que ce qu'on a fait avec WAMP, juste en passant par le
conteneur :

```bash
docker compose exec -w /var/www/html/backend app php bin/console security:hash-password
```

Puis colle le hash obtenu dans la table `app_user` via phpMyAdmin
(`http://localhost:8080`), onglet **SQL** (pas le formulaire d'édition en
ligne, qui avait ajouté un `\r\n` parasite la dernière fois).

## Tâche planifiée Windows (calendrier des matchs à venir)

Si tu as mis en place la tâche planifiée décrite dans
`ml-service/AUTOMATISATION.md` (import quotidien du calendrier des matchs à
venir), elle se connectait à la base MySQL de WAMP. Depuis le passage à
Docker, mets à jour `DATABASE_URL` dans `ml-service/.env.local` avec le
mot de passe Docker (`root_dev_only` au lieu d'un mot de passe vide) —
voir le détail dans `ml-service/AUTOMATISATION.md`. Le conteneur `db` doit
être démarré (`docker compose up -d`) au moment où la tâche s'exécute,
comme WAMP devait l'être avant.

## Si un conteneur ne démarre pas

`docker compose logs app` (ou `db`) affiche l'erreur exacte — envoie-la moi
telle quelle, comme pour les erreurs qu'on a débuggées cette session.