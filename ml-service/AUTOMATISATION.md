# Automatiser le calendrier des matchs à venir

Ce guide explique comment faire tourner `import_upcoming_matches.py` tout
seul, une fois par jour, sans que tu aies besoin d'ouvrir VS Code ni
phpMyAdmin.

**Rappel important** : seul `import_upcoming_matches.py` doit être
automatisé. `import_real_data.py` efface et reconstruit toute la base à
chaque exécution — ne jamais le mettre sur une planification automatique
tel quel (voir son en-tête).

## Avant de commencer

1. Assure-toi que le fichier `ml-service/.env.local` existe bien avec ta
   clé LiveTennisAPI et ton `DATABASE_URL` (voir l'en-tête de
   `import_upcoming_matches.py`).
2. Assure-toi que `pip install pymysql` a bien été fait.
3. **WAMP doit être démarré** au moment où la tâche s'exécute (l'icône WAMP
   doit être verte) — sinon le script échouera avec un message clair dans
   le journal (voir plus bas). Si ton PC redémarre souvent, pense à
   configurer WAMP pour démarrer automatiquement avec Windows (raccourci
   WAMP dans le dossier "Démarrage" de Windows), sinon la tâche planifiée
   ne pourra pas se connecter à la base tant que tu n'as pas relancé WAMP
   toi-même.

## Étape 1 — Teste le fichier .bat fourni

Un fichier `run_import_upcoming.bat` est déjà présent dans `ml-service/` —
il lance le script et écrit tout ce qui se passe dans `ml-service/logs/auto_run.log`.

Double-clique dessus une fois, manuellement, pour vérifier que ça fonctionne.
Une fenêtre noire s'ouvre puis se ferme toute seule — c'est normal. Ouvre
ensuite `ml-service/logs/auto_run.log` pour voir ce qui s'est passé.

## Étape 2 — Crée la tâche planifiée Windows

1. Ouvre le menu Démarrer, tape **"Planificateur de tâches"** et ouvre-le.
2. Dans le panneau de droite, clique sur **"Créer une tâche de base…"**.
3. Nom : `Tennly - Calendrier des matchs à venir` → Suivant.
4. Déclencheur : **"Tous les jours"** → Suivant → choisis une heure (par
   exemple 09:00, un moment où ton PC est généralement allumé et WAMP
   démarré) → Suivant.
5. Action : **"Démarrer un programme"** → Suivant.
6. Dans "Programme/script", clique sur **Parcourir…** et sélectionne le
   fichier `run_import_upcoming.bat` dans ton dossier `ml-service`.
   Laisse "Ajouter des arguments" et "Démarrer dans" vides (le .bat gère
   ça tout seul).
7. Suivant → **Terminer**.

## Étape 3 — Vérifie que ça fonctionne

Tu peux forcer un test immédiat sans attendre le lendemain :
1. Dans le Planificateur de tâches, trouve ta tâche dans la liste
   (onglet "Bibliothèque du Planificateur de tâches").
2. Clic droit dessus → **"Exécuter"**.
3. Regarde le fichier `ml-service/logs/auto_run.log` : tu dois y voir la
   même progression (1/5, 2/5…) que quand tu lances le script toi-même.

## Ce qui se passe ensuite

Chaque jour, à l'heure choisie :
- Le script récupère les nouveaux matchs à venir et les écrit **directement**
  dans ta base (plus besoin de phpMyAdmin).
- Un fichier `.sql` horodaté est gardé dans `ml-service/logs/` à chaque
  exécution — une trace lisible de ce qui a été ajouté, même si tu ne l'as
  pas relu avant.
- Un match déjà importé une fois n'est jamais réimporté en double, tant
  qu'il n'a pas encore eu lieu.
- Si un jour il n'y a rien de nouveau (tous les matchs à venir sont déjà en
  base), le script le signale simplement dans le journal et ne touche à
  rien.

## Si ça ne marche pas

Ouvre `ml-service/logs/auto_run.log` et regarde le dernier bloc (le plus
bas dans le fichier) :
- **"Impossible de se connecter à MySQL"** → WAMP n'était pas démarré à ce
  moment-là.
- **"LiveTennisAPI a renvoyé une erreur 401"** → ta clé API dans
  `.env.local` est invalide ou expirée.
- **"Fichier manquant : .env.local"** → le fichier `.env.local` n'existe
  pas au bon endroit (doit être directement dans `ml-service/`).

Colle-moi le contenu du journal si tu bloques, je t'aiderai à corriger.
