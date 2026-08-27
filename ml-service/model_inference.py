#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Charge le modèle XGBoost entraîné par train_model.py (ml-service/model/) et
expose predict_probability(feature_dict) pour que les scripts d'import
(import_upcoming_matches.py, et plus tard import_real_data.py) puissent
l'utiliser à la place de la formule Elo brute.

Conçu pour ne JAMAIS faire planter le script appelant :
  - Si xgboost n'est pas installé -> MODEL_AVAILABLE = False.
  - Si le modèle n'a pas encore été entraîné (fichiers absents dans
    ml-service/model/, voir train_model.py) -> MODEL_AVAILABLE = False.
Dans les deux cas, le script appelant doit retomber sur la formule Elo
(hist.elo_win_probability) — voir son usage dans import_upcoming_matches.py.

Les features attendues sont EXACTEMENT celles définies dans
train_model.FEATURE_COLUMNS / train_model.build_feature_row (pas réimporté
depuis train_model.py pour éviter que cette dépendance elle-même dépende de
xgboost au niveau du module — voir sa propre garde d'import). build_feature_row
est donc dupliqué ici à l'identique ; si tu changes les features d'un côté,
change les deux (l'ordre exact des colonnes vit dans
ml-service/model/feature_columns.json, généré par train_model.py, donc les
deux restent forcément synchronisés sur l'ORDRE même si le code diverge).
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR / "model"

MODEL_AVAILABLE = False
MODEL_VERSION = None
_booster = None
_feature_columns = None

try:
    import xgboost as _xgb

    _model_path = MODEL_DIR / "tennis_model.json"
    _columns_path = MODEL_DIR / "feature_columns.json"
    _metadata_path = MODEL_DIR / "metadata.json"

    if _model_path.exists() and _columns_path.exists():
        _booster = _xgb.Booster()
        _booster.load_model(str(_model_path))
        _feature_columns = json.loads(_columns_path.read_text(encoding="utf-8"))
        MODEL_VERSION = "xgboost-v1-2026.08"
        if _metadata_path.exists():
            _meta = json.loads(_metadata_path.read_text(encoding="utf-8"))
            MODEL_VERSION = _meta.get("model_version", MODEL_VERSION)
        MODEL_AVAILABLE = True
except ImportError:
    pass  # xgboost non installé -> reste indisponible, jamais une erreur


def build_feature_row(rank1, rank2, elo1_overall, elo2_overall, elo1_surf, elo2_surf,
                       serve1, serve2, return1, return2, momentum1, momentum2,
                       form1, form2, rest1, rest2, h2h1, h2h2, hand_edge1, hand_edge2,
                       fatigue1, fatigue2, indoor1, indoor2, upset1, upset2, tour_is_wta=0):
    """Identique à train_model.build_feature_row — voir ce fichier pour le
    détail de chaque signal. "player1" est le joueur dont on veut connaître
    P(victoire) ; tous les écarts sont [player1 - player2].

    tour_is_wta : 1 si CE match est un match WTA, 0 si ATP (les deux joueurs
    d'un même match sont forcément du même circuit, donc c'est une info par
    match, pas par joueur — voir train_model.py, modèle combiné ATP+WTA).
    Défaut 0 (ATP) pour rester compatible avec un éventuel appelant qui
    n'aurait pas encore été mis à jour."""

    def diff_known(v1, v2, default=0.0):
        if v1 is None or v2 is None:
            return default, 0
        return v1 - v2, 1

    rank_diff, rank_known = diff_known(
        float(rank2) if rank2 is not None else None,
        float(rank1) if rank1 is not None else None,
    )
    momentum_diff, momentum_known = diff_known(momentum1, momentum2)
    form_diff, form_known = diff_known(form1, form2)
    rest_diff, rest_known = diff_known(rest1, rest2)
    hand_edge_diff, hand_edge_known = diff_known(hand_edge1, hand_edge2)
    fatigue_diff, fatigue_known = diff_known(fatigue2, fatigue1)
    indoor_diff, indoor_known = diff_known(indoor1, indoor2)
    upset_diff, upset_known = diff_known(upset1, upset2)
    h2h_known = 1 if (h2h1 + h2h2) > 0 else 0

    return {
        "rank_diff": rank_diff, "rank_known": rank_known,
        "elo_overall_diff": elo1_overall - elo2_overall,
        "elo_surface_diff": elo1_surf - elo2_surf,
        "serve_diff": serve1 - serve2,
        "return_diff": return1 - return2,
        "momentum_diff": momentum_diff, "momentum_known": momentum_known,
        "form_diff": form_diff, "form_known": form_known,
        "rest_diff": rest_diff, "rest_known": rest_known,
        "h2h_diff": h2h1 - h2h2, "h2h_known": h2h_known,
        "hand_edge_diff": hand_edge_diff, "hand_edge_known": hand_edge_known,
        "fatigue_diff": fatigue_diff, "fatigue_known": fatigue_known,
        "indoor_diff": indoor_diff, "indoor_known": indoor_known,
        "upset_diff": upset_diff, "upset_known": upset_known,
        "tour_is_wta": tour_is_wta,
    }


def predict_probability(feature_dict):
    """Renvoie P(player1 gagne), entre 0 et 1. N'appeler que si
    MODEL_AVAILABLE est True."""
    if not MODEL_AVAILABLE:
        raise RuntimeError(
            "model_inference.predict_probability() appelé alors que MODEL_AVAILABLE "
            "est False — vérifie MODEL_AVAILABLE avant d'appeler cette fonction."
        )
    vector = [[feature_dict[c] for c in _feature_columns]]
    dmatrix = _xgb.DMatrix(vector, feature_names=_feature_columns)
    return float(_booster.predict(dmatrix)[0])