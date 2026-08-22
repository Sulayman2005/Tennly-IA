# Tennly IA — service data / ML (Python)

Ce dossier est un placeholder : le pipeline de collecte de données et le
modèle prédictif (cahier des charges sections 4.2, 4.3, 4.4) forment un
service **séparé** de l'application Symfony/Vue, volontairement découplé
(voir section 4.5 du cahier des charges).

## Pourquoi un service séparé

- Python reste le langage le plus adapté pour l'entraînement et l'exécution
  du modèle (pandas, scikit-learn, XGBoost/LightGBM).
- Il communique avec l'application Symfony **uniquement via la base de
  données MySQL partagée** : il écrit dans les tables `player`,
  `tennis_match` et `prediction`, que Symfony/API Platform se contente de
  lire. Aucun appel réseau direct entre les deux services.
- Cela permet de faire évoluer le modèle (ré-entraînement, nouvelles
  features) sans jamais toucher à l'application web, et inversement.

## Ce qui est fait ici pour l'instant

- `import_real_data.py` (v2) : télécharge de vrais joueurs ATP et de vrais
  résultats de matchs sur plusieurs années (source gratuite, sans compte —
  dépôt public `Tennismylife/TML-Database`, voir cahier des charges section
  4.2), rejoue tout cet historique chronologiquement pour calculer un Elo
  réel par joueur ET par surface (dur/terre battue/gazon), et calcule de
  vrais scores service/retour à partir des statistiques de jeu du CSV
  (aces, % de service, balles de break). Génère un fichier SQL à importer
  via phpMyAdmin, pour remplacer les données figées de `seed_dev_data.sql`.
  Voir l'en-tête du script pour le détail complet et ses limites assumées
  (matchs récents déjà joués, pas un calendrier à venir ; probabilités
  calculées avec Elo + stats réelles, pas encore un modèle entraîné).

## Ce qui reste à construire ici

1. Une vraie source de matchs À VENIR (calendrier du jour) : nécessite une
   API avec inscription gratuite (ex. RapidAPI "Tennis Live Data") —
   `Tennismylife/TML-Database` ne fournit que des résultats déjà joués, et
   Flashscore n'a pas d'API publique gratuite exploitable. Décidé comme non
   prioritaire pour l'instant (session du 22/08).
2. Entraînement du modèle (Elo + régression logistique en référence, puis
   gradient boosting - XGBoost/LightGBM - en modèle principal, cf. 4.4.3).
   Choix assumé pour l'instant : rester sur Elo par surface + vraies stats
   service/retour (v2 du script) plutôt qu'un modèle entraîné non validé.
3. Tâche planifiée (cron / Celery / Airflow) pour le ré-entraînement
   périodique et le recalcul quotidien des stats joueurs (section 4.4.4) —
   pour l'instant le script se relance manuellement.

Fait depuis la première version : calcul de l'Elo par surface sur
l'historique multi-années (plus une simple estimation de départ), et
statistiques réelles de service/retour par joueur (plus de valeur neutre
70/70 inventée).

Fait en v3 (session du 22/08, "toutes les données gratuites possibles avant
de regarder une source payante") : exploitation des colonnes du CSV
jusque-là ignorées, ajoutées comme facteurs d'explication supplémentaires
quand l'échantillon est suffisant et l'écart notable — dynamique du moment
(tendance Elo sur les 8 derniers matchs), habitude du jeu face à un
gaucher/droitier, fatigue récente (minutes réellement jouées sur les 10
jours précédents), habitude du jeu en intérieur, et capacité à créer
l'exploit contre plus fort classé. Volontairement pas ajoutés : âge et
taille des joueurs (signal jugé trop faible/générique sans un modèle
statistique validé derrière).

Piste explorée mais non exploitée : les dépôts `ATP-Rankings-Tables` et
`TML-Rankings-Database` du même auteur (classements hebdomadaires plus
précis) — repérés mais pas vérifiés de façon fiable, à investiguer
manuellement avant d'y construire quoi que ce soit dessus.

## Format attendu pour `explanation_factors` et `radar_profile`

```json
// explanation_factors
[
  { "label": "Elo surface", "favors": "A", "impactPoints": 9, "tone": "ok" },
  { "label": "Face-à-face", "favors": "B", "impactPoints": -2, "tone": "warn" }
]

// radar_profile (valeurs normalisées 0-100, [joueurA, joueurB])
{
  "eloSurface": [85, 72],
  "forme": [80, 68],
  "service": [78, 73],
  "retour": [70, 74],
  "repos": [90, 60],
  "h2h": [55, 62]
}
```
