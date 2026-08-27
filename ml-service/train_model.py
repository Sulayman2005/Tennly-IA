#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entraîne un VRAI modèle de machine learning (XGBoost) pour prédire la
probabilité de victoire dans un match de tennis ATP OU WTA, à partir de
l'historique réel des deux circuits COMBINÉS (un seul modèle, avec le
circuit lui-même comme simple feature supplémentaire — voir tour_is_wta
dans build_feature_row/FEATURE_COLUMNS) — remplace la formule "Elo + stats"
par un modèle qui apprend lui-même à pondérer chaque signal, au lieu
d'utiliser des poids choisis à la main (voir cahier des charges section
4.4.3 : "entraînement XGBoost/LightGBM, reste à faire").

Ce script NE MODIFIE RIEN dans import_real_data.py ni
import_upcoming_matches.py, et n'écrit rien dans la base — il se contente
d'entraîner un modèle et de l'enregistrer sur disque
(ml-service/model/tennis_model.json). Le brancher dans les deux scripts
d'import est une étape séparée, volontairement faite APRÈS avoir vérifié
ici que le modèle est vraiment meilleur que la formule actuelle.

Ce que ce script fait, dans l'ordre :
  1. Télécharge un historique ATP plus large que les scripts d'import
     (TRAIN_HIST_YEARS_BACK années, voir plus bas) — un modèle entraîné a
     besoin de plus de matière que ce qu'affichent réellement les scripts
     d'import (qui, eux, se limitent volontairement à un petit nombre de
     matchs "à afficher").
  2. Rejoue TOUT cet historique chronologiquement et calcule, pour CHAQUE
     match, les mêmes signaux que la formule Elo+stats actuelle (Elo
     global + par surface, service/retour, forme, repos, face-à-face,
     dynamique du moment, habitude gaucher/droitier, fatigue, habitude en
     intérieur, capacité à créer l'exploit) — mais toujours tels qu'ils
     étaient connus AVANT ce match précis, jamais après (même règle
     anti-fuite que import_real_data.py).
  3. Transforme chaque match en DEUX lignes d'entraînement symétriques
     (joueur1=vainqueur avec étiquette 1, ET joueur1=perdant avec étiquette
     0, tous les écarts de signaux inversés) — pour que le modèle apprenne
     une vraie relation symétrique entre "l'écart de signaux" et "qui
     gagne", plutôt que d'apprendre un biais lié à l'ordre gagnant/perdant.
  4. Sépare les données dans le temps (les matchs les plus récents servent
     de test, jamais vus à l'entraînement) — plus honnête qu'un tirage
     aléatoire pour évaluer un modèle destiné à prédire des matchs futurs.
  5. Entraîne un classifieur XGBoost, puis compare ses résultats sur le jeu
     de test à la formule Elo actuelle (hist.elo_win_probability) sur
     EXACTEMENT les mêmes matchs — précision, log loss, score de Brier.
  6. Enregistre le modèle entraîné + l'ordre des colonnes de features dans
     ml-service/model/, avec un fichier de métadonnées (date
     d'entraînement, taille des jeux train/test, métriques obtenues) —
     jamais de "fais-moi confiance", toujours une trace vérifiable.

Dépendance supplémentaire : xgboost.
    pip install xgboost

Usage :
    cd ml-service
    python train_model.py
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

try:
    import xgboost as xgb
except ImportError:
    raise SystemExit(
        "Le module 'xgboost' est requis pour entraîner le modèle.\n"
        "Installe-le avec : pip install xgboost\n"
    )

# Fonctions PURES (téléchargement de l'historique, Elo, stats service/retour)
# réutilisées directement depuis import_real_data.py — jamais recopiées, pour
# être certain d'utiliser EXACTEMENT les mêmes formules que la production.
import import_real_data as hist

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR / "model"

# Plus large que HIST_YEARS_BACK des scripts d'import (3) : un modèle
# entraîné a besoin de bien plus de matière que ce qu'on affiche réellement
# dans l'app.
TRAIN_HIST_YEARS_BACK = 8

# Part des matchs (les plus récents, triés par date) mise de côté comme
# jeu de test — jamais utilisée à l'entraînement.
TEST_FRACTION = 0.15

N_MOMENTUM_MATCHES = hist.N_MOMENTUM_MATCHES
FATIGUE_WINDOW_DAYS = hist.FATIGUE_WINDOW_DAYS
TML_SURFACE_ELO_KEY = {"Hard": "hard", "Clay": "clay", "Grass": "grass"}

MODEL_VERSION = "xgboost-v1-2026.08"


# ---------------------------------------------------------------------------
# Mêmes fonctions de signaux "avant ce match" que import_upcoming_matches.py
# (recopiées ici pour la même raison : ce script doit pouvoir tourner seul,
# sans dépendre d'un autre script qui a lui-même une dépendance — pymysql —
# sans rapport avec l'entraînement).
# ---------------------------------------------------------------------------

def build_matches_by_player(all_matches):
    idx = {}
    for m in all_matches:
        idx.setdefault(m["winner_id"], []).append(m)
        idx.setdefault(m["loser_id"], []).append(m)
    return idx


def recent_form(matches_by_player, pid, before_date):
    played = [m for m in matches_by_player.get(pid, []) if m.get("tourney_date", "0") < before_date]
    if not played:
        return None
    wins = sum(1 for m in played if m["winner_id"] == pid)
    return wins / len(played)


def days_rest(matches_by_player, pid, before_date):
    prior = [m["tourney_date"] for m in matches_by_player.get(pid, []) if m.get("tourney_date", "0") < before_date]
    if not prior:
        return None
    try:
        last = max(prior)
        d1 = datetime.strptime(str(int(float(last))), "%Y%m%d")
        d2 = datetime.strptime(str(int(float(before_date))), "%Y%m%d")
        return max((d2 - d1).days, 0)
    except (ValueError, TypeError):
        return None


def head_to_head(matches_by_player, pid_a, pid_b, before_date):
    wins_a = wins_b = 0
    for m in matches_by_player.get(pid_a, []):
        if m.get("tourney_date", "0") >= before_date:
            continue
        if {m["winner_id"], m["loser_id"]} == {pid_a, pid_b}:
            if m["winner_id"] == pid_a:
                wins_a += 1
            else:
                wins_b += 1
    return wins_a, wins_b


def hand_matchup_rate(matches_by_player, pid, opponent_hand, before_date):
    wins = total = 0
    for m in matches_by_player.get(pid, []):
        if m.get("tourney_date", "0") >= before_date:
            continue
        is_winner = m["winner_id"] == pid
        opp_hand = (m.get("loser_hand") if is_winner else m.get("winner_hand")) or ""
        if opp_hand[:1] != opponent_hand:
            continue
        total += 1
        wins += 1 if is_winner else 0
    if total < 3:
        return None
    return wins / total


def recent_minutes_played(matches_by_player, pid, before_date, window_days=FATIGUE_WINDOW_DAYS):
    try:
        before_dt = datetime.strptime(str(int(float(before_date))), "%Y%m%d")
    except (ValueError, TypeError):
        return None
    cutoff = (before_dt - timedelta(days=window_days)).strftime("%Y%m%d")
    total, found = 0.0, False
    for m in matches_by_player.get(pid, []):
        d = m.get("tourney_date", "0")
        if cutoff <= d < before_date:
            minutes = hist.to_num(m.get("minutes"))
            if minutes:
                total += minutes
                found = True
    return total if found else None


def indoor_win_rate(matches_by_player, pid, before_date):
    wins = total = 0
    for m in matches_by_player.get(pid, []):
        if m.get("tourney_date", "0") >= before_date:
            continue
        if hist.to_num(m.get("indoor")) != 1:
            continue
        total += 1
        wins += 1 if m["winner_id"] == pid else 0
    if total < 3:
        return None
    return wins / total


def upset_rate(matches_by_player, pid, before_date):
    wins = total = 0
    for m in matches_by_player.get(pid, []):
        if m.get("tourney_date", "0") >= before_date:
            continue
        is_winner = m["winner_id"] == pid
        own_rank = hist.to_num(m.get("winner_rank") if is_winner else m.get("loser_rank"))
        opp_rank = hist.to_num(m.get("loser_rank") if is_winner else m.get("winner_rank"))
        if own_rank is None or opp_rank is None or own_rank <= opp_rank:
            continue
        total += 1
        wins += 1 if is_winner else 0
    if total < 3:
        return None
    return wins / total


def momentum_for(elo_history, pid):
    h = elo_history.get(pid) or []
    if len(h) < N_MOMENTUM_MATCHES:
        return None
    return h[-1] - h[-N_MOMENTUM_MATCHES]


# ---------------------------------------------------------------------------
# Colonnes de features, dans un ordre FIXE — le même ordre doit être utilisé
# à l'inférence (une fois ce modèle branché dans les scripts d'import), sinon
# le modèle recevrait des colonnes dans le désordre. L'ordre est enregistré
# dans model/feature_columns.json pour que le code d'inférence n'ait jamais
# à le redeviner.
# ---------------------------------------------------------------------------
FEATURE_COLUMNS = [
    "rank_diff", "rank_known",
    "elo_overall_diff",
    "elo_surface_diff",
    "serve_diff",
    "return_diff",
    "momentum_diff", "momentum_known",
    "form_diff", "form_known",
    "rest_diff", "rest_known",
    "h2h_diff", "h2h_known",
    "hand_edge_diff", "hand_edge_known",
    "fatigue_diff", "fatigue_known",
    "indoor_diff", "indoor_known",
    "upset_diff", "upset_known",
    "tour_is_wta",
]


def build_feature_row(rank1, rank2, elo1_overall, elo2_overall, elo1_surf, elo2_surf,
                       serve1, serve2, return1, return2, momentum1, momentum2,
                       form1, form2, rest1, rest2, h2h1, h2h2, hand_edge1, hand_edge2,
                       fatigue1, fatigue2, indoor1, indoor2, upset1, upset2, tour_is_wta=0):
    """Construit un vecteur de features [player1 - player2] avec un indicateur
    "known" pour chaque signal qui peut manquer — un modèle à base d'arbres
    apprend mieux en distinguant explicitement "aucun avantage mesuré" de
    "signal manquant", ce qu'une simple formule linéaire ne fait pas."""

    def diff_known(v1, v2, default=0.0):
        if v1 is None or v2 is None:
            return default, 0
        return v1 - v2, 1

    rank_diff, rank_known = diff_known(
        float(rank2) if rank2 is not None else None,
        float(rank1) if rank1 is not None else None,
    )  # positif = player1 mieux classé (rang plus petit)

    momentum_diff, momentum_known = diff_known(momentum1, momentum2)
    form_diff, form_known = diff_known(form1, form2)
    rest_diff, rest_known = diff_known(rest1, rest2)
    hand_edge_diff, hand_edge_known = diff_known(hand_edge1, hand_edge2)
    # fatigue : moins de minutes jouées récemment = plus reposé = avantage
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


def generate_training_rows(all_matches, tour_is_wta=0):
    """Rejoue l'historique chronologiquement, comme simulate_history dans
    import_real_data.py — sauf qu'ici on capture un exemple d'entraînement
    pour CHAQUE match (pas seulement un petit sous-ensemble "à afficher").

    `tour_is_wta` s'applique à TOUS les matchs passés en argument : appeler
    cette fonction séparément pour les matchs ATP (tour_is_wta=0) et les
    matchs WTA (tour_is_wta=1) — jamais un mélange des deux dans un seul
    appel, exactement comme process_tour dans import_real_data.py : les
    états Elo/serve/return de cette fonction sont locaux à l'appel, donc un
    joueur ATP et une joueuse WTA qui partageraient par coïncidence le même
    id brut ne se marchent jamais dessus tant qu'on ne fait pas UN appel par
    circuit."""
    elo, serve_running, return_running, elo_history = {}, {}, {}, {}
    matches_by_player = {}

    def ensure(pid, rank_hint):
        if pid not in elo:
            e = hist.bootstrap_elo(rank_hint)
            elo[pid] = {"overall": e, "hard": e, "clay": e, "grass": e}
            serve_running[pid] = hist.new_serve_running()
            return_running[pid] = hist.new_return_running()
            elo_history[pid] = []
            matches_by_player[pid] = []

    ordered = sorted(
        all_matches,
        key=lambda m: (m.get("tourney_date", "0"), hist.to_num(m.get("match_num")) or 0),
    )

    rows = []
    for m in ordered:
        wid, lid = m["winner_id"], m["loser_id"]
        ensure(wid, m.get("winner_rank"))
        ensure(lid, m.get("loser_rank"))
        before_date = m.get("tourney_date", "0")
        surf_key = TML_SURFACE_ELO_KEY.get(m.get("surface", ""))

        elo_w, elo_l = elo[wid], elo[lid]
        elo_w_surf = elo_w[surf_key] if surf_key else elo_w["overall"]
        elo_l_surf = elo_l[surf_key] if surf_key else elo_l["overall"]
        serve_w = hist.serve_score(serve_running[wid])
        serve_l = hist.serve_score(serve_running[lid])
        return_w = hist.return_score(return_running[wid])
        return_l = hist.return_score(return_running[lid])
        form_w = recent_form(matches_by_player, wid, before_date)
        form_l = recent_form(matches_by_player, lid, before_date)
        rest_w = days_rest(matches_by_player, wid, before_date)
        rest_l = days_rest(matches_by_player, lid, before_date)
        h2h_w, h2h_l = head_to_head(matches_by_player, wid, lid, before_date)
        momentum_w = momentum_for(elo_history, wid)
        momentum_l = momentum_for(elo_history, lid)
        fatigue_w = recent_minutes_played(matches_by_player, wid, before_date)
        fatigue_l = recent_minutes_played(matches_by_player, lid, before_date)
        upset_w = upset_rate(matches_by_player, wid, before_date)
        upset_l = upset_rate(matches_by_player, lid, before_date)

        hand_w, hand_l = (m.get("winner_hand") or "")[:1], (m.get("loser_hand") or "")[:1]
        hand_edge_w = hand_edge_l = None
        if hand_w in ("L", "R") and hand_l in ("L", "R") and hand_w != hand_l:
            hand_edge_w = hand_matchup_rate(matches_by_player, wid, hand_l, before_date)
            hand_edge_l = hand_matchup_rate(matches_by_player, lid, hand_w, before_date)

        is_indoor = hist.to_num(m.get("indoor")) == 1
        indoor_w = indoor_win_rate(matches_by_player, wid, before_date) if is_indoor else None
        indoor_l = indoor_win_rate(matches_by_player, lid, before_date) if is_indoor else None

        rank_w, rank_l = hist.to_num(m.get("winner_rank")), hist.to_num(m.get("loser_rank"))

        # Ligne 1 : player1 = vainqueur -> étiquette 1
        rows.append((
            before_date,
            build_feature_row(
                rank_w, rank_l, elo_w["overall"], elo_l["overall"], elo_w_surf, elo_l_surf,
                serve_w, serve_l, return_w, return_l, momentum_w, momentum_l,
                form_w, form_l, rest_w, rest_l, h2h_w, h2h_l, hand_edge_w, hand_edge_l,
                fatigue_w, fatigue_l, indoor_w, indoor_l, upset_w, upset_l, tour_is_wta,
            ),
            1,
        ))
        # Ligne 2 (miroir) : player1 = perdant -> étiquette 0. Évite que le
        # modèle apprenne un biais lié à l'ordre gagnant/perdant plutôt qu'à
        # l'écart réel de signaux.
        rows.append((
            before_date,
            build_feature_row(
                rank_l, rank_w, elo_l["overall"], elo_w["overall"], elo_l_surf, elo_w_surf,
                serve_l, serve_w, return_l, return_w, momentum_l, momentum_w,
                form_l, form_w, rest_l, rest_w, h2h_l, h2h_w, hand_edge_l, hand_edge_w,
                fatigue_l, fatigue_w, indoor_l, indoor_w, upset_l, upset_w, tour_is_wta,
            ),
            0,
        ))

        # -- mise à jour de l'état, APRÈS avoir capturé les features "avant" --
        new_ow, new_ol = hist.apply_elo_update(elo[wid]["overall"], elo[lid]["overall"], hist.ELO_K_OVERALL)
        elo[wid]["overall"], elo[lid]["overall"] = new_ow, new_ol
        if surf_key:
            new_sw, new_sl = hist.apply_elo_update(elo[wid][surf_key], elo[lid][surf_key], hist.ELO_K_SURFACE)
            elo[wid][surf_key], elo[lid][surf_key] = new_sw, new_sl
        hist.update_serve_running(serve_running[wid], m, "w")
        hist.update_serve_running(serve_running[lid], m, "l")
        hist.update_return_running(return_running[wid], m, "l")
        hist.update_return_running(return_running[lid], m, "w")
        elo_history[wid].append(elo[wid]["overall"])
        elo_history[lid].append(elo[lid]["overall"])
        matches_by_player[wid].append(m)
        matches_by_player[lid].append(m)

    return rows


# ---------------------------------------------------------------------------
# Métriques (implémentées à la main pour ne pas ajouter scikit-learn comme
# dépendance juste pour 3 formules simples)
# ---------------------------------------------------------------------------

def accuracy(y_true, y_pred_proba):
    correct = sum(1 for yt, yp in zip(y_true, y_pred_proba) if (float(yp) >= 0.5) == bool(yt))
    # float(...) : xgboost renvoie des probabilités en numpy.float32, que le
    # module json standard ne sait pas sérialiser tel quel (voir metadata.json
    # plus bas) — on force un float Python natif dès le calcul des métriques.
    return float(correct / len(y_true))


def log_loss(y_true, y_pred_proba, eps=1e-15):
    total = 0.0
    for yt, yp in zip(y_true, y_pred_proba):
        p = min(max(float(yp), eps), 1 - eps)
        total += -(yt * math.log(p) + (1 - yt) * math.log(1 - p))
    return float(total / len(y_true))


def brier_score(y_true, y_pred_proba):
    return float(sum((float(yp) - yt) ** 2 for yt, yp in zip(y_true, y_pred_proba)) / len(y_true))


def main():
    print(f"1/4 — Téléchargement de {TRAIN_HIST_YEARS_BACK} ans d'historique réel ATP + WTA…")
    this_year = datetime.now().year

    atp_matches = hist.fetch_history(this_year, TRAIN_HIST_YEARS_BACK)
    atp_matches = [m for m in atp_matches if hist.is_usable_match(m)]
    print(f"  ATP : {len(atp_matches)} matchs exploitables")

    wta_matches = hist.fetch_wta_history(this_year, TRAIN_HIST_YEARS_BACK)
    wta_matches = [m for m in wta_matches if hist.is_usable_match(m)]
    print(f"  WTA : {len(wta_matches)} matchs exploitables")

    if not atp_matches and not wta_matches:
        raise SystemExit("Impossible de récupérer le moindre match (ATP ET WTA), abandon.")

    print("2/4 — Rejeu chronologique et calcul des features 'avant chaque match', "
          "circuit par circuit (modèle combiné, tour_is_wta comme feature — voir "
          "generate_training_rows) puis fusion…")
    rows = []
    if atp_matches:
        rows.extend(generate_training_rows(atp_matches, tour_is_wta=0))
    if wta_matches:
        rows.extend(generate_training_rows(wta_matches, tour_is_wta=1))
    rows.sort(key=lambda r: r[0])  # ordre chronologique global, ATP et WTA mélangés par date
    print(f"  {len(rows)} exemples d'entraînement générés ({len(rows) // 2} matchs x 2, symétrisés, ATP+WTA combinés)")

    split_index = int(len(rows) * (1 - TEST_FRACTION))
    train_rows, test_rows = rows[:split_index], rows[split_index:]
    print(f"  Découpage temporel : {len(train_rows)} exemples d'entraînement, "
          f"{len(test_rows)} exemples de test (les plus récents, jamais vus à l'entraînement)")

    X_train = [[r[1][c] for c in FEATURE_COLUMNS] for r in train_rows]
    y_train = [r[2] for r in train_rows]
    X_test = [[r[1][c] for c in FEATURE_COLUMNS] for r in test_rows]
    y_test = [r[2] for r in test_rows]

    print("3/4 — Entraînement du modèle XGBoost…")
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    model_proba = model.predict_proba(X_test)[:, 1]
    # Comparaison honnête : la formule Elo actuelle (surface si connue, sinon
    # globale), sur EXACTEMENT les mêmes matchs de test. hist.elo_win_probability
    # ne dépend que de l'écart elo_a - elo_b (1/(1+10^(-diff/400))), donc le
    # recalculer à partir de elo_surface_diff (déjà dans le vecteur de
    # features) donne exactement le même résultat que l'appeler avec les
    # deux Elo bruts.
    baseline_proba = []
    for r in test_rows:
        feat = r[1]
        # elo_surface_diff = elo1_surf - elo2_surf ; on n'a pas gardé les valeurs
        # absolues dans le vecteur de features (volontaire : seul l'écart compte
        # pour le modèle), donc on les recalcule ici à partir d'un Elo de
        # référence neutre — équivalent car elo_win_probability ne dépend que
        # de l'écart (1/(1+10^(-diff/400))).
        baseline_proba.append(1.0 / (1.0 + 10 ** (-feat["elo_surface_diff"] / 400.0)))

    print("4/4 — Évaluation sur le jeu de test (jamais vu à l'entraînement)…")
    print(f"\n{'Métrique':<22}{'Modèle XGBoost':>18}{'Formule Elo actuelle':>22}")
    print(f"{'Précision':<22}{accuracy(y_test, model_proba):>18.4f}{accuracy(y_test, baseline_proba):>22.4f}")
    print(f"{'Log loss (plus bas = mieux)':<22}{log_loss(y_test, model_proba):>18.4f}{log_loss(y_test, baseline_proba):>22.4f}")
    print(f"{'Score de Brier (plus bas = mieux)':<22}{brier_score(y_test, model_proba):>18.4f}{brier_score(y_test, baseline_proba):>22.4f}")

    better = log_loss(y_test, model_proba) < log_loss(y_test, baseline_proba)
    print(f"\n{'=> Le modèle XGBoost est MEILLEUR que la formule Elo actuelle sur ce test.' if better else '=> Le modèle XGBoost n_EST PAS meilleur que la formule Elo actuelle ici — ne pas le brancher en production tel quel, revoir les features/hyperparamètres.'}")

    MODEL_DIR.mkdir(exist_ok=True)
    model.save_model(str(MODEL_DIR / "tennis_model.json"))
    (MODEL_DIR / "feature_columns.json").write_text(
        json.dumps(FEATURE_COLUMNS, indent=2), encoding="utf-8"
    )
    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now().isoformat(),
        "hist_years_back": TRAIN_HIST_YEARS_BACK,
        "n_train": len(train_rows),
        "n_test": len(test_rows),
        "metrics": {
            "model": {
                "accuracy": accuracy(y_test, model_proba),
                "log_loss": log_loss(y_test, model_proba),
                "brier_score": brier_score(y_test, model_proba),
            },
            "elo_baseline": {
                "accuracy": accuracy(y_test, baseline_proba),
                "log_loss": log_loss(y_test, baseline_proba),
                "brier_score": brier_score(y_test, baseline_proba),
            },
        },
        "better_than_baseline": better,
    }
    (MODEL_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nModèle enregistré dans {MODEL_DIR}/ (tennis_model.json, feature_columns.json, metadata.json)")


if __name__ == "__main__":
    main()