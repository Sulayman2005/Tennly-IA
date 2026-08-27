#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calcule, à la demande, la probabilité de victoire du "joueur 1" face au
"joueur 2" avec le modèle XGBoost entraîné (voir train_model.py /
model_inference.py) — appelé en sous-processus par le backend Symfony
(ComparateurController / PlayerComparisonService) pour le comparateur de
joueurs (frontend/src/views/ComparateurView.vue), quand un utilisateur
abonné (ou l'admin) demande l'analyse complète entre deux joueurs choisis
librement.

Volontairement SANS accès réseau ni base de données : Symfony a déjà tout ce
qu'il faut en base (table player pour le classement/Elo, player_snapshot pour
le service/retour/forme/etc. — rafraîchie chaque jour par
import_upcoming_matches.py, voir son en-tête —, player_head_to_head pour le
face-à-face) et transmet ces valeurs ici en JSON sur l'entrée standard. Ce
script se contente d'appliquer le modèle déjà entraîné : jamais de
retéléchargement/rejeu d'historique ici, ce serait bien trop lent pour une
réponse HTTP (c'est exactement pour éviter ça que player_snapshot et
player_head_to_head existent — voir import_upcoming_matches.py).

Entrée (JSON sur stdin), toutes les clés requises (mettre `null` pour une
valeur inconnue plutôt que d'omettre la clé) :
  rank1, rank2                     — classement ATP/WTA (nombre ou null)
  elo_overall1, elo_overall2       — Elo global (nombre)
  elo_surface1, elo_surface2       — Elo de la surface choisie pour la
                                      comparaison (nombre)
  serve1, serve2                   — score service, 0-100 (nombre)
  return1, return2                 — score retour, 0-100 (nombre)
  momentum1, momentum2             — variation Elo récente (nombre ou null)
  form1, form2                     — taux de victoire récent, 0-1 (ou null)
  rest1, rest2                     — jours de repos (nombre ou null)
  h2h1, h2h2                       — victoires en face-à-face (nombre, 0 si inconnu)
  hand_edge1, hand_edge2           — taux de victoire face à la main de
                                      l'adversaire, 0-1 (ou null)
  fatigue1, fatigue2               — minutes jouées récemment (nombre ou null)
  indoor1, indoor2                 — taux de victoire en intérieur (ou null —
                                      non utilisé par ce comparateur générique,
                                      qui ne modélise pas de toit/pas de toit,
                                      voir PlayerComparisonService)
  upset1, upset2                   — taux de victoire en tant qu'outsider (ou null)
  tour_is_wta                      — 1 si les deux joueurs comparés sont du
                                      circuit WTA, 0 si ATP (modèle combiné
                                      ATP+WTA, voir train_model.py — c'est une
                                      info par PAIRE, pas par joueur, donc pas
                                      de suffixe 1/2 ici)

Sortie (JSON sur stdout, une seule ligne) :
  {"model_available": true, "model_version": "xgboost-v1-2026.08", "probability_player1": 0.63}
ou, si xgboost n'est pas installé ou si le modèle n'a pas encore été
entraîné (voir model_inference.MODEL_AVAILABLE) :
  {"model_available": false}
Dans ce 2e cas, Symfony retombe sur son propre calcul (formule Elo) — voir
PlayerComparisonService::analyser(), jamais d'erreur HTTP pour l'utilisateur.

Usage (depuis PHP, via Symfony\\Component\\Process\\Process) :
    echo '{"rank1": 5, ...}' | python predict_pair.py
"""

import json
import sys

import model_inference

REQUIRED_KEYS = [
    "rank1", "rank2", "elo_overall1", "elo_overall2", "elo_surface1", "elo_surface2",
    "serve1", "serve2", "return1", "return2", "momentum1", "momentum2",
    "form1", "form2", "rest1", "rest2", "h2h1", "h2h2", "hand_edge1", "hand_edge2",
    "fatigue1", "fatigue2", "indoor1", "indoor2", "upset1", "upset2", "tour_is_wta",
]


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"model_available": False, "error": f"JSON invalide en entrée : {e}"}))
        return

    missing = [k for k in REQUIRED_KEYS if k not in payload]
    if missing:
        print(json.dumps({
            "model_available": False,
            "error": f"Clé(s) manquante(s) dans l'entrée : {', '.join(missing)}",
        }))
        return

    if not model_inference.MODEL_AVAILABLE:
        print(json.dumps({"model_available": False}))
        return

    feature_dict = model_inference.build_feature_row(
        payload["rank1"], payload["rank2"],
        payload["elo_overall1"], payload["elo_overall2"],
        payload["elo_surface1"], payload["elo_surface2"],
        payload["serve1"], payload["serve2"],
        payload["return1"], payload["return2"],
        payload["momentum1"], payload["momentum2"],
        payload["form1"], payload["form2"],
        payload["rest1"], payload["rest2"],
        payload["h2h1"], payload["h2h2"],
        payload["hand_edge1"], payload["hand_edge2"],
        payload["fatigue1"], payload["fatigue2"],
        payload["indoor1"], payload["indoor2"],
        payload["upset1"], payload["upset2"],
        payload["tour_is_wta"],
    )
    proba = model_inference.predict_probability(feature_dict)
    print(json.dumps({
        "model_available": True,
        "model_version": model_inference.MODEL_VERSION,
        "probability_player1": proba,
    }))


if __name__ == "__main__":
    main()