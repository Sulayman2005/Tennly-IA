#!/usr/bin/env python3
"""
Import des vrais joueurs ATP + vrais résultats de matchs récents (cahier des
charges section 4.2 : sources de données) pour remplacer les 2 joueurs / 1
match figés dans seed_dev_data.sql par un jeu de données réel.

Source : le dépôt public Tennismylife/TML-Database (github.com/Tennismylife/
TML-Database), déjà cité comme "TennisMyLife" en section 4.2 du cahier des
charges. Gratuit, pas de compte à créer, mis à jour régulièrement (bien plus
récent que les dépôts historiques de Jeff Sackmann, qui ne sont plus
accessibles sous leur ancien nom au moment où ce script est écrit).

Ce que ce script fait réellement (v2 — enrichi avec plusieurs années
d'historique, suite à un appel avec un pronosticeur sur ce qui compte
vraiment pour un pronostic) :
  - télécharge PLUSIEURS années de résultats (saison en cours + HIST_YEARS_BACK
    précédentes, un CSV par année, ex. 2026.csv, 2025.csv, 2024.csv…) depuis
    ce dépôt, pour avoir un vrai historique et pas juste un instantané ;
  - rejoue chronologiquement TOUT cet historique pour calculer un Elo réel
    par joueur ET par surface (dur/terre battue/gazon), qui évolue match
    après match (pas juste une estimation de départ à partir du classement,
    même si le classement sert de point de départ à la toute première
    apparition d'un joueur) ;
  - calcule aussi, à partir des vraies statistiques de jeu présentes dans
    le CSV (aces, % de premier service, points gagnés au 1er/2e service,
    balles de break sauvées/converties), un vrai score "service" ET un vrai
    score "retour" par joueur — plus de valeur neutre inventée ;
  - calcule la forme récente, le repos et le face-à-face sur TOUT
    l'historique récupéré (pas seulement les quelques matchs finalement
    affichés), avec la même précaution anti-fuite que la version précédente
    (on ne regarde jamais un match pour prédire ce même match) ;
  - (v3) exploite aussi les autres colonnes du CSV jusque-là ignorées, pour
    ajouter — uniquement quand l'échantillon est suffisant et l'écart
    notable — des facteurs d'explication supplémentaires, toujours dérivés
    de données réelles :
      * dynamique du moment (variation de l'Elo sur les 8 derniers matchs,
        différent du taux de victoire brut "forme") ;
      * habitude du jeu face à un gaucher/droitier (colonne winner_hand/
        loser_hand), quand les deux joueurs du match n'ont pas la même main ;
      * fatigue récente (minutes réellement jouées sur les 10 jours
        précédents, colonne `minutes`) ;
      * habitude du jeu en intérieur (colonne `indoor`), quand ce match est
        lui-même en intérieur ;
      * capacité à créer l'exploit contre plus fort classé (taux de
        victoire historique quand le joueur était l'outsider au classement).
    Volontairement PAS ajoutés : l'âge et la taille des joueurs — le lien
    avec la performance est trop faible/générique pour en faire un vrai
    signal sans un modèle statistique validé, plutôt que d'injecter du bruit
    juste pour "utiliser toutes les colonnes".
  - garde les N joueurs les mieux classés et les matchs qui les opposent
    entre eux (priorité aux plus récents, avec les plus grands tournois en
    départage), et génère un fichier SQL (import_real_data.sql) prêt à
    importer dans phpMyAdmin, comme seed_dev_data.sql.

Ce que ce script NE fait PAS (limite honnête, à lire avant de considérer que
« l'IA prédit les vrais matchs ») :
  - il n'y a pas de calendrier des matchs À VENIR gratuit sans compte (les
    fédérations ATP/WTA n'exposent pas ça publiquement, et Flashscore n'a pas
    d'API publique gratuite exploitable) : les matchs importés ici sont donc
    des matchs RÉCENTS DÉJÀ JOUÉS (statut "finished" ou "walkover"), pas le
    programme du jour. Pour de vrais matchs à venir en direct, il faudra
    passer par une API avec inscription gratuite (ex. RapidAPI "Tennis Live
    Data") — étape suivante, décidée comme non prioritaire pour l'instant.
  - les probabilités et le radar comparatif restent calculés avec une formule
    Elo + stats réelles (pas un modèle entraîné : le vrai entraînement
    XGBoost/LightGBM, cf. section 4.4.3, reste à faire — choix assumé pour
    avoir quelque chose de solide rapidement plutôt qu'un modèle non validé).

Usage :
    cd ml-service
    python import_real_data.py
    # -> écrit import_real_data.sql à côté de ce script

Puis, comme pour seed_dev_data.sql : phpMyAdmin -> base "tennly" (ou ton nom
de base) -> onglet Importer -> choisir import_real_data.sql -> Importer.

Aucune dépendance à installer : uniquement la bibliothèque standard Python.
"""

import csv
import io
import json
import math
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta

TOP_N_PLAYERS = 40
MAX_MATCHES = 30
HIST_YEARS_BACK = 3  # + année en cours = 4 années récupérées au total
BASE_URL = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master"
OUTPUT_FILE = "import_real_data.sql"

ELO_K_OVERALL = 24
ELO_K_SURFACE = 32

SURFACE_MAP = {
    "Hard": "dur",
    "Clay": "terre_battue",
    "Grass": "gazon",
    "Carpet": "indoor",
}

# Seules ces 3 surfaces ont une colonne Elo dédiée dans le schéma
# (elo_hard / elo_clay / elo_grass) — "Carpet" ne met à jour que l'Elo global.
SURFACE_ELO_KEY = {
    "Hard": "hard",
    "Clay": "clay",
    "Grass": "grass",
}

ROUND_MAP = {
    "F": "Finale",
    "SF": "Demi-finale",
    "QF": "Quart de finale",
    "R16": "8e de finale",
    "R32": "3e tour",
    "R64": "2e tour",
    "R128": "1er tour",
    "RR": "Round robin",
    "BR": "Petite finale",
}

# Utilisé uniquement pour départager deux matchs de la même date lors de la
# sélection finale (priorité aux plus grands tournois — donnée réelle du CSV,
# pas une invention) : G=Grand Chelem, M=Masters 1000, F=Masters/Tour Finals,
# D=Coupe Davis/United Cup, A=autre tournoi du circuit.
TOURNEY_LEVEL_WEIGHT = {"G": 4, "M": 3, "F": 3, "D": 2, "A": 1}

# Nombre de matchs en arrière utilisés pour mesurer la "dynamique du moment"
# (évolution de l'Elo sur ses N derniers matchs, distinct du simple taux de
# victoire "forme" : un joueur peut progresser en Elo même avec un bilan
# victoires/défaites moyen, s'il affronte des adversaires plus forts).
N_MOMENTUM_MATCHES = 8

# Fenêtre (en jours) sur laquelle on additionne les minutes jouées pour
# estimer la fatigue récente d'un joueur avant ce match.
FATIGUE_WINDOW_DAYS = 10


def fetch_csv(url):
    """Télécharge un CSV et renvoie une liste de dicts (csv.DictReader)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TennlyIA/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(raw)))


def try_fetch_year(year):
    url = f"{BASE_URL}/{year}.csv"
    try:
        rows = fetch_csv(url)
        print(f"  {year}.csv : {len(rows)} matchs récupérés depuis {url}")
        return rows
    except urllib.error.HTTPError as e:
        print(f"  pas de fichier pour {year} ({e.code}), on continue avec les autres années…")
        return None


def fetch_history(base_year, years_back):
    """Récupère base_year, base_year-1, …, base_year-years_back, en ignorant
    simplement les années manquantes (au lieu de s'arrêter à la première
    erreur) — plus on a d'historique, meilleur est le calcul d'Elo/forme."""
    all_rows = []
    for year in range(base_year, base_year - years_back - 1, -1):
        rows = try_fetch_year(year)
        if rows:
            all_rows.extend(rows)
    return all_rows


def parse_tourney_date(yyyymmdd, fallback_time="12:00:00"):
    """'20260113' -> '2026-01-13 12:00:00' (le CSV ne donne pas d'heure)."""
    if not yyyymmdd or len(str(yyyymmdd)) < 8:
        return None
    s = str(int(float(yyyymmdd)))
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {fallback_time}"


def sql_str(value):
    if value is None:
        return "NULL"
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def sql_json(obj):
    return sql_str(json.dumps(obj, ensure_ascii=False))


def bootstrap_elo(rank):
    """
    Estimation de départ de l'Elo à partir du seul classement ATP réel,
    utilisée UNIQUEMENT la toute première fois qu'un joueur apparaît dans
    l'historique récupéré. Ensuite, l'Elo évolue par la vraie simulation
    match après match (cf. simulate_history ci-dessous) — ce n'est donc plus
    une simple estimation figée comme dans la version précédente du script.
    """
    try:
        rank = int(float(rank))
    except (TypeError, ValueError):
        rank = 200
    return round(2200 - 220 * math.log10(max(rank, 1) + 1))


def elo_expected(a, b):
    return 1.0 / (1.0 + 10 ** ((b - a) / 400.0))


def apply_elo_update(elo_w, elo_l, k):
    """Mise à jour Elo classique, à somme nulle (ce que gagne le vainqueur,
    le perdant le perd)."""
    exp_w = elo_expected(elo_w, elo_l)
    delta = k * (1 - exp_w)
    return elo_w + delta, elo_l - delta


def elo_win_probability(elo_a, elo_b):
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def confidence_from_probability(p):
    if p >= 0.65:
        return "eleve"
    if p >= 0.55:
        return "moyen"
    return "faible"


def clamp(value, lo=1, hi=99):
    return max(lo, min(hi, round(value)))


def is_usable_match(m):
    """Filtre les lignes avec un id ou un nom de joueur manquant (trous
    connus dans ce jeu de données communautaire : certains qualifiés/wildcards
    n'ont pas d'id) — sans id fiable on ne peut pas construire les clés
    étrangères."""
    return bool(m.get("winner_id")) and bool(m.get("loser_id")) \
        and bool(m.get("winner_name")) and bool(m.get("loser_name"))


def to_num(value):
    """Convertit une valeur de cellule CSV en float, ou None si vide/invalide
    (certaines lignes, surtout les tournois Challenger, n'ont pas toutes les
    statistiques de jeu détaillées — on l'ignore proprement plutôt que de
    planter ou d'inventer un chiffre)."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def new_serve_running():
    return {"svpt": 0.0, "ace": 0.0, "first_in": 0.0, "first_won": 0.0,
            "second_won": 0.0, "bp_faced": 0.0, "bp_saved": 0.0, "matches": 0}


def new_return_running():
    return {"pts_total": 0.0, "pts_won": 0.0, "bp_total": 0.0, "bp_won": 0.0, "matches": 0}


def update_serve_running(running, m, side):
    """side = 'w' (vainqueur) ou 'l' (perdant) — préfixe des colonnes du CSV."""
    svpt = to_num(m.get(f"{side}_svpt"))
    if svpt is None or svpt <= 0:
        return
    running["svpt"] += svpt
    running["ace"] += to_num(m.get(f"{side}_ace")) or 0
    running["first_in"] += to_num(m.get(f"{side}_1stIn")) or 0
    running["first_won"] += to_num(m.get(f"{side}_1stWon")) or 0
    running["second_won"] += to_num(m.get(f"{side}_2ndWon")) or 0
    running["bp_faced"] += to_num(m.get(f"{side}_bpFaced")) or 0
    running["bp_saved"] += to_num(m.get(f"{side}_bpSaved")) or 0
    running["matches"] += 1


def update_return_running(running, m, opponent_side):
    """Le CSV ne donne que les stats de SERVICE de chaque joueur (w_*/l_*) —
    il n'y a pas de colonne "retour" séparée. On dérive donc la performance
    au retour d'un joueur à partir des stats de service de son ADVERSAIRE
    sur ce match précis : les points/balles de break que l'adversaire a
    perdus en servant sont, par définition, les points/balles de break que
    ce joueur a gagnés en retournant."""
    opp_svpt = to_num(m.get(f"{opponent_side}_svpt"))
    if opp_svpt is None or opp_svpt <= 0:
        return
    opp_first_won = to_num(m.get(f"{opponent_side}_1stWon")) or 0
    opp_second_won = to_num(m.get(f"{opponent_side}_2ndWon")) or 0
    opp_bp_faced = to_num(m.get(f"{opponent_side}_bpFaced")) or 0
    opp_bp_saved = to_num(m.get(f"{opponent_side}_bpSaved")) or 0
    running["pts_total"] += opp_svpt
    running["pts_won"] += max(opp_svpt - opp_first_won - opp_second_won, 0)
    running["bp_total"] += opp_bp_faced
    running["bp_won"] += max(opp_bp_faced - opp_bp_saved, 0)
    running["matches"] += 1


MIN_SAMPLE_POINTS = 20  # en dessous, on considère l'échantillon trop faible
DEFAULT_SERVE_RETURN_SCORE = 60  # neutre, documenté : pas assez d'historique


def serve_score(running):
    if running["svpt"] < MIN_SAMPLE_POINTS:
        return DEFAULT_SERVE_RETURN_SCORE
    first_in_pct = running["first_in"] / running["svpt"] if running["svpt"] else 0
    first_won_pct = running["first_won"] / running["first_in"] if running["first_in"] else 0
    second_serve_pts = running["svpt"] - running["first_in"]
    second_won_pct = running["second_won"] / second_serve_pts if second_serve_pts > 0 else 0
    bp_saved_pct = running["bp_saved"] / running["bp_faced"] if running["bp_faced"] else 1.0
    composite = (0.35 * first_won_pct + 0.30 * second_won_pct
                 + 0.20 * first_in_pct + 0.15 * bp_saved_pct)
    return clamp(composite * 100)


def return_score(running):
    if running["pts_total"] < MIN_SAMPLE_POINTS:
        return DEFAULT_SERVE_RETURN_SCORE
    pts_won_pct = running["pts_won"] / running["pts_total"] if running["pts_total"] else 0
    bp_won_pct = running["bp_won"] / running["bp_total"] if running["bp_total"] else 0
    composite = 0.6 * pts_won_pct + 0.4 * bp_won_pct
    return clamp(composite * 100)


def simulate_history(all_matches, relevant_ids):
    """Rejoue TOUT l'historique récupéré, dans l'ordre chronologique, pour
    calculer :
      - l'Elo de chaque joueur (global + par surface), qui évolue match après
        match (bootstrap uniquement à la toute première apparition) ;
      - ses stats réelles de service/retour cumulées.
    Pour chaque match dont l'id Python (id(m)) est dans `relevant_ids` (les
    matchs qu'on va effectivement afficher/pronostiquer), on capture un
    "instantané" de l'état AVANT ce match (donc sans fuite du résultat de ce
    match sur sa propre prédiction), pour le vainqueur et le perdant : Elo,
    stats service/retour, ET la dynamique Elo récente (momentum, cf.
    N_MOMENTUM_MATCHES) — variation de l'Elo global sur les N derniers matchs.
    Renvoie (elo_final, elo_snapshots, serve_return_snapshots, momentum_snapshots).
    """
    elo = {}
    serve_running = {}
    return_running = {}
    elo_history = {}  # pid -> liste de l'Elo global APRÈS chacun de ses matchs
    elo_snapshots = {}
    serve_return_snapshots = {}
    momentum_snapshots = {}

    def ensure_state(pid, rank_hint):
        if pid not in elo:
            e = bootstrap_elo(rank_hint)
            elo[pid] = {"overall": e, "hard": e, "clay": e, "grass": e}
            serve_running[pid] = new_serve_running()
            return_running[pid] = new_return_running()
            elo_history[pid] = []

    def momentum_for(pid):
        hist = elo_history.get(pid) or []
        if len(hist) < N_MOMENTUM_MATCHES:
            return None
        return elo[pid]["overall"] - hist[-N_MOMENTUM_MATCHES]

    ordered = sorted(
        all_matches,
        key=lambda m: (m.get("tourney_date", "0"), to_num(m.get("match_num")) or 0),
    )

    for m in ordered:
        wid, lid = m["winner_id"], m["loser_id"]
        ensure_state(wid, m.get("winner_rank"))
        ensure_state(lid, m.get("loser_rank"))

        if id(m) in relevant_ids:
            elo_snapshots[id(m)] = {"winner": dict(elo[wid]), "loser": dict(elo[lid])}
            serve_return_snapshots[id(m)] = {
                "winner": {"serve": serve_score(serve_running[wid]), "return": return_score(return_running[wid])},
                "loser": {"serve": serve_score(serve_running[lid]), "return": return_score(return_running[lid])},
            }
            momentum_snapshots[id(m)] = {"winner": momentum_for(wid), "loser": momentum_for(lid)}

        # -- Elo : global, puis par surface si connue --
        new_ow, new_ol = apply_elo_update(elo[wid]["overall"], elo[lid]["overall"], ELO_K_OVERALL)
        elo[wid]["overall"], elo[lid]["overall"] = new_ow, new_ol

        surf_key = SURFACE_ELO_KEY.get(m.get("surface", ""))
        if surf_key:
            new_sw, new_sl = apply_elo_update(elo[wid][surf_key], elo[lid][surf_key], ELO_K_SURFACE)
            elo[wid][surf_key], elo[lid][surf_key] = new_sw, new_sl

        # -- Stats service/retour cumulées --
        update_serve_running(serve_running[wid], m, "w")
        update_serve_running(serve_running[lid], m, "l")
        update_return_running(return_running[wid], m, "l")
        update_return_running(return_running[lid], m, "w")

        # -- Historique Elo (pour le momentum) : après mise à jour de ce match --
        elo_history[wid].append(elo[wid]["overall"])
        elo_history[lid].append(elo[lid]["overall"])

    return elo, elo_snapshots, serve_return_snapshots, momentum_snapshots


def main():
    print("1/4 — Téléchargement de l'historique (saison en cours + "
          f"{HIST_YEARS_BACK} années précédentes)…")
    this_year = date.today().year
    all_matches = fetch_history(this_year, HIST_YEARS_BACK)
    if not all_matches:
        raise SystemExit("Impossible de récupérer le moindre fichier de matchs, abandon.")

    all_matches = [m for m in all_matches if is_usable_match(m)]
    print(f"  {len(all_matches)} matchs exploitables au total (id + nom présents pour les deux joueurs)")

    print("2/4 — Détermination du classement le plus récent de chaque joueur…")
    # winner_rank / loser_rank donnent le classement AU MOMENT de CE match ;
    # on prend, pour chaque joueur, la valeur associée à sa toute dernière
    # apparition (date la plus récente) sur TOUTES les années récupérées.
    last_seen = {}  # pid -> (tourney_date, rank, name)
    for m in all_matches:
        for side in ("winner", "loser"):
            pid = m[f"{side}_id"]
            rank = m.get(f"{side}_rank")
            if not rank:
                continue
            d = m.get("tourney_date", "0")
            prev = last_seen.get(pid)
            if prev is None or d >= prev[0]:
                last_seen[pid] = (d, rank, m[f"{side}_name"])

    ranked = sorted(last_seen.items(), key=lambda kv: int(float(kv[1][1])))
    top_ids = {pid: {"rank": info[1], "name": info[2]} for pid, info in ranked[:TOP_N_PLAYERS]}
    print(f"  {len(top_ids)} joueurs retenus (top {TOP_N_PLAYERS} par classement le plus récent)")

    print("3/4 — Sélection des matchs entre joueurs du top classement…")
    candidates = [m for m in all_matches if m["winner_id"] in top_ids and m["loser_id"] in top_ids]
    # Priorité aux matchs les plus récents ("actualité"), et à date égale aux
    # plus grands tournois (donnée réelle tourney_level du CSV) — répond au
    # "matchs les plus attendus entre joueurs connus" sans rien inventer.
    candidates.sort(
        key=lambda m: (m.get("tourney_date", "0"), TOURNEY_LEVEL_WEIGHT.get(m.get("tourney_level", ""), 1)),
        reverse=True,
    )
    relevant = candidates[:MAX_MATCHES]
    print(f"  {len(relevant)} matchs retenus (sur {len(candidates)} entre joueurs du top classement)")

    if not relevant:
        raise SystemExit(
            "Aucun match trouvé entre joueurs du top classement sur les années récupérées — "
            "augmente TOP_N_PLAYERS ou HIST_YEARS_BACK en haut du script et relance."
        )

    print("4/4 — Simulation de l'historique (Elo par surface + stats service/retour) et génération du SQL…")
    relevant_ids = {id(m) for m in relevant}
    elo, elo_snapshots, sr_snapshots, momentum_snapshots = simulate_history(all_matches, relevant_ids)

    # -- Registre des joueurs réellement utilisés dans les matchs retenus --
    players = {}  # tml_id -> dict
    for m in relevant:
        for side in ("winner", "loser"):
            pid = m[f"{side}_id"]
            if pid in players:
                continue
            rank_row = top_ids.get(pid)
            rank = rank_row["rank"] if rank_row else m.get(f"{side}_rank") or 200
            players[pid] = {
                "full_name": m[f"{side}_name"],
                "country_code": (m.get(f"{side}_ioc") or "")[:3] or None,
                "atp_wta_rank": int(float(rank)) if rank else None,
                "hand": (m.get(f"{side}_hand") or "U")[:1] or "U",
                "external_ref": f"tml:{pid}",
            }

    # id local (1..N) attribué dans l'ordre d'insertion, pour construire les
    # clés étrangères des INSERT suivants sans dépendre des AUTO_INCREMENT
    # réels (inconnus à l'avance).
    local_id = {pid: i + 1 for i, pid in enumerate(players.keys())}

    # Forme récente / repos / face-à-face calculés sur TOUT l'historique
    # récupéré (plusieurs années), pas seulement les quelques matchs
    # finalement affichés — bien plus fiable que la version précédente.
    matches_by_player = {pid: [] for pid in players}
    for m in all_matches:
        wid, lid = m["winner_id"], m["loser_id"]
        if wid in matches_by_player:
            matches_by_player[wid].append(m)
        if lid in matches_by_player:
            matches_by_player[lid].append(m)

    def recent_form(pid, before_date):
        # Strictement AVANT ce match : sinon le résultat du match qu'on est en
        # train de "prédire" fuiterait dans son propre facteur de forme.
        played = [m for m in matches_by_player[pid] if m.get("tourney_date", "0") < before_date]
        if not played:
            return None
        wins = sum(1 for m in played if m["winner_id"] == pid)
        return wins / len(played)

    def days_rest(pid, before_date, this_match):
        prior = [
            m["tourney_date"] for m in matches_by_player[pid]
            if m.get("tourney_date", "0") < before_date and m is not this_match
        ]
        if not prior:
            return None
        try:
            last = max(prior)
            d1 = datetime.strptime(str(int(float(last))), "%Y%m%d")
            d2 = datetime.strptime(str(int(float(before_date))), "%Y%m%d")
            return max((d2 - d1).days, 0)
        except (ValueError, TypeError):
            return None

    def head_to_head(pid_a, pid_b, before_date):
        # Strictement AVANT ce match, même raison que recent_form : le match
        # en cours d'évaluation ne doit jamais compter dans son propre h2h.
        wins_a = wins_b = 0
        for m in matches_by_player[pid_a]:
            if m.get("tourney_date", "0") >= before_date:
                continue
            if {m["winner_id"], m["loser_id"]} == {pid_a, pid_b}:
                if m["winner_id"] == pid_a:
                    wins_a += 1
                else:
                    wins_b += 1
        return wins_a, wins_b

    def hand_matchup_rate(pid, opponent_hand, before_date):
        """Taux de victoire de pid, historiquement, spécifiquement contre des
        adversaires de la main `opponent_hand` (ex. contre des gauchers) —
        utile seulement quand les deux joueurs du match n'ont pas la même
        main. Toujours strictement avant ce match (même règle anti-fuite)."""
        wins = total = 0
        for m in matches_by_player[pid]:
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

    def recent_minutes_played(pid, before_date, window_days=FATIGUE_WINDOW_DAYS):
        """Somme des minutes jouées dans la fenêtre récente précédant ce
        match — un indicateur de fatigue réel basé sur la colonne `minutes`
        du CSV, pas une invention."""
        try:
            before_dt = datetime.strptime(str(int(float(before_date))), "%Y%m%d")
        except (ValueError, TypeError):
            return None
        cutoff = (before_dt - timedelta(days=window_days)).strftime("%Y%m%d")
        total = 0.0
        found = False
        for m in matches_by_player[pid]:
            d = m.get("tourney_date", "0")
            if cutoff <= d < before_date:
                minutes = to_num(m.get("minutes"))
                if minutes:
                    total += minutes
                    found = True
        return total if found else None

    def indoor_win_rate(pid, before_date):
        """Taux de victoire historique de pid spécifiquement en intérieur
        (colonne `indoor` du CSV) — pertinent uniquement quand CE match est
        lui-même en intérieur."""
        wins = total = 0
        for m in matches_by_player[pid]:
            if m.get("tourney_date", "0") >= before_date:
                continue
            if to_num(m.get("indoor")) != 1:
                continue
            total += 1
            wins += 1 if m["winner_id"] == pid else 0
        if total < 3:
            return None
        return wins / total

    def upset_rate(pid, before_date):
        """Parmi les matchs où pid était l'outsider au classement (moins
        bien classé que son adversaire à ce moment-là), le taux de victoires
        — une mesure réelle de la capacité à \"faire l'exploit\", dérivée
        des classements et résultats déjà présents dans le CSV."""
        wins = total = 0
        for m in matches_by_player[pid]:
            if m.get("tourney_date", "0") >= before_date:
                continue
            is_winner = m["winner_id"] == pid
            own_rank = to_num(m.get("winner_rank") if is_winner else m.get("loser_rank"))
            opp_rank = to_num(m.get("loser_rank") if is_winner else m.get("winner_rank"))
            if own_rank is None or opp_rank is None or own_rank <= opp_rank:
                continue  # pas un match où pid partait outsider
            total += 1
            wins += 1 if is_winner else 0
        if total < 3:
            return None
        return wins / total

    out = io.StringIO()
    out.write(
        "-- Import de vrais joueurs ATP + vrais matchs récents (source : "
        "github.com/Tennismylife/TML-Database, voir cahier des charges section 4.2).\n"
        "-- Généré par ml-service/import_real_data.py (v2, historique multi-annees) "
        "— NE PAS éditer à la main.\n"
        "--\n"
        "-- Limites assumées de cette version (voir en-tête du script Python) :\n"
        "--   * les matchs sont des résultats RÉCENTS RÉELLEMENT JOUÉS (status="
        "'finished'/'walkover'), pas un calendrier de matchs à venir ;\n"
        "--   * probability_favorite / radar_profile viennent d'un Elo par surface "
        "calcule sur plusieurs annees d'historique reel + vraies stats service/retour, "
        "pas encore un modèle entraîné (section 4.4.3 reste à construire, choix assume).\n\n"
        "-- DELETE (et non TRUNCATE) : TRUNCATE est bloqué par MySQL des qu'une\n"
        "-- table est referencee par une cle etrangere, meme table vide, et\n"
        "-- phpMyAdmin ne garanti pas que SET FOREIGN_KEY_CHECKS=0 reste actif\n"
        "-- pour toute la suite de l'import. DELETE fonctionne toujours tant que\n"
        "-- l'ordre enfant -> parent est respecte, ce qui est le cas ici.\n"
        "DELETE FROM prediction;\n"
        "DELETE FROM tennis_match;\n"
        "DELETE FROM player;\n\n"
    )

    out.write("INSERT INTO player (id, full_name, country_code, atp_wta_rank, "
               "elo_overall, elo_hard, elo_clay, elo_grass, dominant_hand, external_ref) VALUES\n")
    player_lines = []
    for pid, p in players.items():
        e = elo[pid]
        player_lines.append(
            f"  ({local_id[pid]}, {sql_str(p['full_name'])}, {sql_str(p['country_code'])}, "
            f"{p['atp_wta_rank'] or 'NULL'}, {round(e['overall'])}, {round(e['hard'])}, "
            f"{round(e['clay'])}, {round(e['grass'])}, "
            f"{sql_str(p['hand'])}, {sql_str(p['external_ref'])})"
        )
    out.write(",\n".join(player_lines) + ";\n\n")

    out.write("INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, "
               "tournament_name, round, surface, scheduled_at, status, score_text) VALUES\n")
    match_lines = []
    for i, m in enumerate(relevant, start=1):
        wid, lid = m["winner_id"], m["loser_id"]
        surface = SURFACE_MAP.get(m.get("surface", ""), "dur")
        round_label = ROUND_MAP.get(m.get("round", ""), m.get("round", "?"))
        scheduled_at = parse_tourney_date(m.get("tourney_date")) or "2026-01-01 12:00:00"
        score = (m.get("score") or "").strip()
        status = "walkover" if score.upper() in ("W/O", "WO", "") else "finished"
        match_lines.append(
            f"  ({i}, {local_id[wid]}, {local_id[lid]}, {local_id[wid]}, "
            f"{sql_str(m.get('tourney_name'))}, {sql_str(round_label)}, {sql_str(surface)}, "
            f"{sql_str(scheduled_at)}, {sql_str(status)}, {sql_str(score[:60])})"
        )
    out.write(",\n".join(match_lines) + ";\n\n")

    out.write("INSERT INTO prediction (id, match_id, favorite_player_id, "
               "probability_favorite, confidence_level, model_version, computed_at, "
               "explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES\n")
    pred_lines = []
    for i, m in enumerate(relevant, start=1):
        wid, lid = m["winner_id"], m["loser_id"]

        # Elo AVANT ce match (snapshot), sur la surface de CE match si on a
        # une colonne dédiée pour elle, sinon repli sur l'Elo global.
        surf_key = SURFACE_ELO_KEY.get(m.get("surface", ""))
        snap = elo_snapshots[id(m)]
        elo_w_match = snap["winner"][surf_key] if surf_key else snap["winner"]["overall"]
        elo_l_match = snap["loser"][surf_key] if surf_key else snap["loser"]["overall"]

        sr_snap = sr_snapshots[id(m)]
        serve_w, return_w = sr_snap["winner"]["serve"], sr_snap["winner"]["return"]
        serve_l, return_l = sr_snap["loser"]["serve"], sr_snap["loser"]["return"]

        # favori = celui des deux avec le meilleur Elo (sur la surface de ce
        # match précis) AVANT le match — pas forcément le vainqueur réel : un
        # pronostic peut se tromper, comme en vrai.
        if elo_w_match >= elo_l_match:
            fav_id, dog_id = wid, lid
            elo_fav, elo_dog = elo_w_match, elo_l_match
            serve_fav, serve_dog = serve_w, serve_l
            return_fav, return_dog = return_w, return_l
        else:
            fav_id, dog_id = lid, wid
            elo_fav, elo_dog = elo_l_match, elo_w_match
            serve_fav, serve_dog = serve_l, serve_w
            return_fav, return_dog = return_l, return_w

        proba = elo_win_probability(elo_fav, elo_dog)
        confidence = confidence_from_probability(proba)
        tourney_date = m.get("tourney_date", "0")

        form_fav = recent_form(fav_id, tourney_date)
        form_dog = recent_form(dog_id, tourney_date)
        rest_fav = days_rest(fav_id, tourney_date, m)
        rest_dog = days_rest(dog_id, tourney_date, m)
        h2h_fav, h2h_dog = head_to_head(fav_id, dog_id, tourney_date)

        # -- Signaux additionnels (toutes données réelles/dérivées du même CSV,
        # ajoutés uniquement quand il y a un échantillon suffisant ET un écart
        # notable, pour ne pas polluer la liste avec du bruit) --
        momentum_snap = momentum_snapshots[id(m)]
        momentum_w, momentum_l = momentum_snap["winner"], momentum_snap["loser"]
        momentum_fav = momentum_w if fav_id == wid else momentum_l
        momentum_dog = momentum_l if fav_id == wid else momentum_w

        hand_fav = players[fav_id]["hand"]
        hand_dog = players[dog_id]["hand"]
        hand_edge_fav = hand_edge_dog = None
        if hand_fav in ("L", "R") and hand_dog in ("L", "R") and hand_fav != hand_dog:
            hand_edge_fav = hand_matchup_rate(fav_id, hand_dog, tourney_date)
            hand_edge_dog = hand_matchup_rate(dog_id, hand_fav, tourney_date)

        fatigue_fav = recent_minutes_played(fav_id, tourney_date)
        fatigue_dog = recent_minutes_played(dog_id, tourney_date)

        is_indoor_match = to_num(m.get("indoor")) == 1
        indoor_fav = indoor_win_rate(fav_id, tourney_date) if is_indoor_match else None
        indoor_dog = indoor_win_rate(dog_id, tourney_date) if is_indoor_match else None

        upset_fav = upset_rate(fav_id, tourney_date)
        upset_dog = upset_rate(dog_id, tourney_date)

        factors = [{
            "label": "Classement ATP",
            "favors": "A" if fav_id == wid else "B",
            "impactPoints": round(abs(players[fav_id]["atp_wta_rank"] - players[dog_id]["atp_wta_rank"]) / 10, 1),
            "tone": "ok",
        }]
        if h2h_fav + h2h_dog > 0:
            factors.append({
                "label": "Face-à-face",
                "favors": "A" if (fav_id == wid) == (h2h_fav >= h2h_dog) else "B",
                "impactPoints": h2h_fav - h2h_dog,
                "tone": "ok" if h2h_fav >= h2h_dog else "warn",
            })
        if abs(serve_fav - serve_dog) >= 8:
            factors.append({
                "label": "Force au service",
                "favors": "A" if (fav_id == wid) == (serve_fav >= serve_dog) else "B",
                "impactPoints": round((serve_fav - serve_dog) / 10, 1),
                "tone": "ok" if serve_fav >= serve_dog else "warn",
            })
        if momentum_fav is not None and momentum_dog is not None and abs(momentum_fav - momentum_dog) >= 15:
            factors.append({
                "label": "Dynamique du moment (Elo sur les derniers matchs)",
                "favors": "A" if (fav_id == wid) == (momentum_fav >= momentum_dog) else "B",
                "impactPoints": round((momentum_fav - momentum_dog) / 10, 1),
                "tone": "ok" if momentum_fav >= momentum_dog else "warn",
            })
        if hand_edge_fav is not None and hand_edge_dog is not None and abs(hand_edge_fav - hand_edge_dog) >= 0.15:
            style = "gaucher" if hand_dog == "L" else "droitier"
            factors.append({
                "label": f"Habitude du jeu face à un {style}",
                "favors": "A" if (fav_id == wid) == (hand_edge_fav >= hand_edge_dog) else "B",
                "impactPoints": round((hand_edge_fav - hand_edge_dog) * 10, 1),
                "tone": "ok" if hand_edge_fav >= hand_edge_dog else "warn",
            })
        if fatigue_fav is not None and fatigue_dog is not None and abs(fatigue_fav - fatigue_dog) >= 60:
            more_rested = fav_id if fatigue_fav <= fatigue_dog else dog_id
            factors.append({
                "label": "Fatigue récente (minutes jouées sur les 10 derniers jours)",
                "favors": "A" if (more_rested == wid) else "B",
                "impactPoints": round((fatigue_dog - fatigue_fav) / 30, 1),
                "tone": "ok" if more_rested == fav_id else "warn",
            })
        if indoor_fav is not None and indoor_dog is not None and abs(indoor_fav - indoor_dog) >= 0.15:
            factors.append({
                "label": "Habitude du jeu en intérieur",
                "favors": "A" if (fav_id == wid) == (indoor_fav >= indoor_dog) else "B",
                "impactPoints": round((indoor_fav - indoor_dog) * 10, 1),
                "tone": "ok" if indoor_fav >= indoor_dog else "warn",
            })
        if upset_fav is not None and upset_dog is not None and abs(upset_fav - upset_dog) >= 0.15:
            factors.append({
                "label": "Capacité à créer l'exploit contre plus fort classé",
                "favors": "A" if (fav_id == wid) == (upset_fav >= upset_dog) else "B",
                "impactPoints": round((upset_fav - upset_dog) * 10, 1),
                "tone": "ok" if upset_fav >= upset_dog else "warn",
            })

        def pct(v, default=65):
            return clamp(v * 100) if v is not None else default

        radar = {
            "eloSurface": [clamp((elo_fav - 1500) / 8), clamp((elo_dog - 1500) / 8)] if fav_id == wid
                          else [clamp((elo_dog - 1500) / 8), clamp((elo_fav - 1500) / 8)],
            "forme": [pct(form_fav if fav_id == wid else form_dog), pct(form_dog if fav_id == wid else form_fav)],
            "service": [serve_w, serve_l] if fav_id == wid else [serve_l, serve_w],
            "retour": [return_w, return_l] if fav_id == wid else [return_l, return_w],
            "repos": [clamp((rest_fav or 3) * 10), clamp((rest_dog or 3) * 10)] if fav_id == wid
                     else [clamp((rest_dog or 3) * 10), clamp((rest_fav or 3) * 10)],
            "h2h": [clamp(50 + (h2h_fav - h2h_dog) * 10), clamp(50 - (h2h_fav - h2h_dog) * 10)] if fav_id == wid
                   else [clamp(50 - (h2h_fav - h2h_dog) * 10), clamp(50 + (h2h_fav - h2h_dog) * 10)],
        }
        # Les paires ci-dessus sont dans l'ordre [joueur_A, joueur_B] du match
        # (winner=A, loser=B) — on remet donc le tableau dans le bon ordre
        # A/B plutôt que favori/outsider :
        if fav_id != wid:
            for key in ("eloSurface", "forme", "repos", "h2h"):
                radar[key] = list(reversed(radar[key]))
        # "service"/"retour" sont déjà écrits directement en ordre [w, l] ci-dessus.

        pred_lines.append(
            f"  ({i}, {i}, {local_id[fav_id]}, {round(proba, 4)}, {sql_str(confidence)}, "
            f"'elo-surface-stats-2026.08', NOW(), {sql_json(factors)}, {sql_json(radar)}, NULL, NULL)"
        )
    out.write(",\n".join(pred_lines) + ";\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out.getvalue())

    print(f"\nTerminé : {len(players)} joueurs réels, {len(relevant)} matchs réels écrits dans {OUTPUT_FILE}")
    print(f"(Elo par surface + stats service/retour calculés sur {len(all_matches)} matchs d'historique.)")
    print("Étape suivante : phpMyAdmin -> ta base -> onglet Importer -> choisir ce fichier -> Importer.")
    print("(Ça REMPLACE les données existantes dans player / tennis_match / prediction, "
          "les tables plan / app_user / subscription ne sont pas touchées.)")


if __name__ == "__main__":
    main()
