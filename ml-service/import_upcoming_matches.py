#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import du VRAI calendrier des matchs à venir (feature "Calendrier des matchs
à venir" du cahier des charges), ATP ET WTA, depuis LiveTennisAPI
(livetennisapi.com, formule gratuite, compte + clé API à créer sur leur
site).

Conçu pour tourner SEUL, sur une planification quotidienne (voir la section
"Automatisation" tout en bas) — donc sans intervention manuelle et sans
passer par phpMyAdmin. Ce que ce script fait, dans l'ordre, POUR CHAQUE
CIRCUIT (ATP puis WTA — traités indépendamment de bout en bout, un joueur
ATP et une joueuse WTA ne s'affrontant jamais, voir la même règle dans
import_real_data.py) :

  1. Se connecte à ta base MySQL locale (WAMP) pour savoir quels joueurs et
     quels matchs à venir existent déjà (id réel, external_ref, Elo actuel).
     Contrairement à import_real_data.py (qui repart de zéro à chaque
     exécution : DELETE + réinsertion complète), ce script n'écrit JAMAIS de
     DELETE — uniquement des INSERT (nouveaux joueurs/matchs/analyses) et
     des UPDATE ciblés sur l'Elo d'un joueur déjà connu.
  2. Retélécharge le même historique réel que import_real_data.py pour ce
     circuit (source Tennismylife/TML-Database pour l'ATP, stats.tennismylife.org
     pour la WTA — voir sa note de licence ambiguë MIT/non-commerciale dans
     import_real_data.py) et le rejoue entièrement pour connaître l'état
     ACTUEL (Elo par surface, stats service/retour, forme, repos,
     face-à-face, etc.) de chaque joueur — pas un instantané "avant tel
     match historique", mais l'état "à aujourd'hui".
  3. Interroge LiveTennisAPI pour les matchs "upcoming" (à venir) des
     prochains jours SUR CE CIRCUIT, filtre pour ne garder que des matchs
     simples GENUINEMENT à venir (voir is_genuinely_upcoming), puis écarte
     ceux déjà importés lors d'une exécution précédente (voir external_ref
     sur tennis_match).
  4. Pour chaque match VRAIMENT nouveau : fait correspondre chaque joueur à
     un joueur déjà connu (par nom — LiveTennisAPI a son propre espace
     d'identifiants, incompatible avec les id TML/Sackmann déjà utilisés
     dans player.external_ref), calcule une vraie probabilité/un vrai radar
     avec le modèle XGBoost combiné ATP+WTA si disponible (voir
     model_inference.py, tour_is_wta), sinon la même formule Elo+stats que
     import_real_data.py.
  5. Écrit directement en base (une seule transaction, tout ou rien, POUR
     LES DEUX CIRCUITS ENSEMBLE) ET garde une copie lisible de ce qui a été
     fait dans ml-service/logs/.
  6. Rafraîchit aussi, CHAQUE JOUR (même s'il n'y a aucun nouveau match à
     venir, sur AUCUN des deux circuits), un instantané du profil actuel de
     chaque joueur connu — table player_snapshot — et le face-à-face réel
     entre joueurs connus — table player_head_to_head — SÉPARÉMENT pour
     l'ATP et la WTA (même prudence anti-mélange que partout ailleurs).

Tables player_snapshot et player_head_to_head : à créer une fois via
phpMyAdmin (SQL fourni séparément) avant la première exécution de cette
version du script. La colonne player.tour (ATP/WTA) doit aussi déjà exister
(migration SQL fournie séparément avec le reste du support WTA) — sinon les
INSERT de nouveaux joueurs échoueront avec une erreur MySQL claire.

Limites assumées de cette version (honnêtes, pas cachées) :
  - Un joueur non retrouvé dans l'historique téléchargé (nouveau sur le
    circuit, ou nom qui ne correspond pas) est créé avec un Elo "bootstrap"
    (classement uniquement) et des facteurs de forme/repos/h2h non
    disponibles (valeurs neutres déjà utilisées ailleurs dans le projet).
  - Une fois qu'un match à venir a été importé, sa probabilité n'est plus
    recalculée aux exécutions suivantes — choix assumé pour que l'analyse
    affichée à un utilisateur ne change pas silencieusement d'un jour à
    l'autre.
  - Correspondance des surfaces avec l'Elo : LiveTennisAPI donne la surface
    réelle (hard/clay/grass) ET un booléen "indoor" séparés. Choix assumé :
    la catégorie affichée dans l'app devient "indoor" dès que indoor=true,
    mais LE CALCUL de probabilité utilise l'Elo de la surface physique
    réelle (hard->elo_hard, etc.), y compris en intérieur.
  - Le facteur "habitude du jeu en intérieur" fonctionne aussi bien pour un
    match WTA que pour un match ATP (colonne `indoor` présente dans les deux
    sources utilisées, voir import_real_data.py).
  - import_real_data.py N'EST PAS automatisé par ce script (et ne doit pas
    l'être tel quel) : il efface et reconstruit tous les joueurs/matchs/
    analyses à chaque exécution, ce qui supprimerait les matchs à venir
    ajoutés ici. Il reste un script à relancer manuellement, de temps en
    temps, pour rafraîchir les vrais résultats passés (ATP ET WTA).

Dépendance supplémentaire (contrairement à import_real_data.py qui n'utilise
que la bibliothèque standard) : PyMySQL, pour lire ET écrire dans la base.
    pip install pymysql

Configuration (fichier ml-service/.env.local, à créer toi-même — jamais
commité, voir ml-service/.gitignore) :
    LIVETENNIS_API_KEY=ta_vraie_cle_livetennisapi
    DATABASE_URL=mysql://root:@127.0.0.1:3306/tennly

Usage manuel :
    cd ml-service
    python import_upcoming_matches.py

Automatisation (Windows, planification quotidienne) : voir le fichier
AUTOMATISATION.md à côté de ce script pour la marche à suivre complète
(création d'une tâche planifiée Windows qui lance ce script tout seul).
"""

import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    raise SystemExit(
        "Le module 'pymysql' est requis pour lire ET écrire dans ta base.\n"
        "Installe-le avec : pip install pymysql\n"
        "(voir l'en-tête de ce script pour le pourquoi.)"
    )

# On réutilise les fonctions PURES (Elo, stats service/retour, téléchargement
# de l'historique ATP et WTA) de import_real_data.py directement, plutôt que
# de les recopier : ce sont des fonctions sans effet de bord, le risque de
# les réutiliser est faible, et ça garantit qu'on calcule une probabilité
# EXACTEMENT selon la même méthode que pour les matchs déjà joués.
import import_real_data as hist

# Charge le modèle XGBoost entraîné par train_model.py s'il est disponible
# (voir model_inference.py — ne plante jamais, même si xgboost n'est pas
# installé ou si le modèle n'a pas encore été entraîné : dans ce cas
# model_inference.MODEL_AVAILABLE reste False et on retombe sur la formule
# Elo de repli, voir plus bas dans la boucle principale).
import model_inference

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"

LIVETENNISAPI_BASE = "https://api.livetennisapi.com/api/public/v1"
LOOKAHEAD_DAYS = 14  # fenêtre du calendrier : matchs entre maintenant et +14 jours

# Élo : à quelle clé du dict elo{overall,hard,clay,grass} correspond chaque
# valeur de surface renvoyée par LiveTennisAPI (toujours en minuscules) —
# voir la note sur le choix indoor/surface physique dans le docstring
# ci-dessus. Commun aux deux circuits.
SURFACE_ELO_KEY = {"hard": "hard", "clay": "clay", "grass": "grass"}

# Catégorie affichée dans l'app (colonne tennis_match.surface, 4 valeurs
# possibles : dur/terre_battue/gazon/indoor).
SURFACE_APP_LABEL = {"hard": "dur", "clay": "terre_battue", "grass": "gazon"}

ELO_K_OVERALL = hist.ELO_K_OVERALL
ELO_K_SURFACE = hist.ELO_K_SURFACE
N_MOMENTUM_MATCHES = hist.N_MOMENTUM_MATCHES
FATIGUE_WINDOW_DAYS = hist.FATIGUE_WINDOW_DAYS

# Même identifiant que import_real_data.py : c'est littéralement la même
# méthode (Elo + stats réelles), seulement appliquée à un match qui n'a pas
# encore eu lieu plutôt qu'en rétrospective sur un match déjà joué. Garder le
# même nom évite d'afficher deux "versions du modèle" différentes sur la
# page /fiabilite pour une méthode qui est en réalité identique.
MODEL_VERSION = "elo-surface-stats-2026.08"

OUTPUT_FILE = SCRIPT_DIR / "import_upcoming_matches.sql"

# Préfixe external_ref et libellé du facteur "classement" par circuit — voir
# la même convention dans import_real_data.py (external_ref = "tml:<id>"
# pour l'ATP, "wta:<id>" pour la WTA).
TOUR_EXTERNAL_REF_PREFIX = {"atp": "tml", "wta": "wta"}
TOUR_RANK_LABEL = {"atp": "Classement ATP", "wta": "Classement WTA"}


# ---------------------------------------------------------------------------
# Configuration (.env.local)
# ---------------------------------------------------------------------------

def load_env_local():
    """Parseur minimal type .env — volontairement sans dépendance
    supplémentaire (python-dotenv) pour un fichier aussi simple."""
    path = SCRIPT_DIR / ".env.local"
    if not path.exists():
        raise SystemExit(
            f"Fichier manquant : {path}\n"
            "Crée-le avec deux lignes :\n"
            "  LIVETENNIS_API_KEY=ta_vraie_cle\n"
            "  DATABASE_URL=mysql://root:@127.0.0.1:3306/tennly\n"
            "(copie DATABASE_URL depuis backend/.env — ne mets JAMAIS ce "
            "fichier dans git, voir ml-service/.gitignore.)"
        )
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    missing = [k for k in ("LIVETENNIS_API_KEY", "DATABASE_URL") if not values.get(k)]
    if missing:
        raise SystemExit(f"Il manque {', '.join(missing)} dans {path}")
    return values


def parse_database_url(database_url):
    """'mysql://root:@127.0.0.1:3306/tennly?...' -> kwargs pour pymysql.connect."""
    parsed = urllib.parse.urlparse(database_url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/").split("?")[0],
    }


def connect_db(db_kwargs):
    try:
        return pymysql.connect(**db_kwargs, charset="utf8mb4")
    except pymysql.err.OperationalError as e:
        raise SystemExit(
            "Impossible de se connecter à MySQL — vérifie que WAMP est bien démarré "
            f"(icône WAMP verte dans la barre des tâches) et que DATABASE_URL dans "
            f".env.local est correct.\nErreur détaillée : {e}"
        )


# ---------------------------------------------------------------------------
# Lecture de l'état actuel (avant tout calcul) — commun aux deux circuits,
# la table `player` les contient tous les deux (voir colonne `tour`).
# ---------------------------------------------------------------------------

def load_existing_players(conn):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            "SELECT id, full_name, external_ref, elo_overall, elo_hard, "
            "elo_clay, elo_grass, atp_wta_rank, dominant_hand, country_code, tour "
            "FROM player"
        )
        rows = cur.fetchall()
    by_external_ref = {r["external_ref"]: r for r in rows if r["external_ref"]}
    by_name_key = {}
    for r in rows:
        by_name_key.setdefault(normalize_name_key(r["full_name"]), r)
    max_id = max((r["id"] for r in rows), default=0)
    return by_external_ref, by_name_key, max_id


def load_max_id(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
        (value,) = cur.fetchone()
    return value


def load_existing_match_refs(conn):
    """Les matchs à venir déjà importés lors d'une exécution précédente —
    indispensable pour ne jamais créer de doublon quand ce script tourne
    chaque jour tant qu'un match n'a pas encore eu lieu."""
    with conn.cursor() as cur:
        cur.execute("SELECT external_ref FROM tennis_match WHERE external_ref IS NOT NULL")
        return {row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Nom des joueurs : LiveTennisAPI a son propre espace d'identifiants,
# incompatible avec les id TML/Sackmann déjà utilisés dans
# player.external_ref (colonne unique) — la seule correspondance fiable sans
# base d'identifiants partagée est le nom, normalisé pour ignorer accents,
# casse, ponctuation ET l'ordre des mots.
# ---------------------------------------------------------------------------

def normalize_name_key(name):
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    tokens = re.findall(r"[a-z0-9]+", ascii_only.lower())
    return " ".join(sorted(tokens))


# ---------------------------------------------------------------------------
# Rejeu de l'historique jusqu'à l'état ACTUEL — identique pour ATP et WTA,
# appelé une fois par circuit avec les matchs de CE circuit uniquement (voir
# replay_tour_history plus bas).
# ---------------------------------------------------------------------------

def build_matches_by_player(all_matches):
    idx = {}
    for m in all_matches:
        idx.setdefault(m["winner_id"], []).append(m)
        idx.setdefault(m["loser_id"], []).append(m)
    return idx


def simulate_to_present(all_matches):
    elo, serve_running, return_running, elo_history = {}, {}, {}, {}

    def ensure(pid, rank_hint):
        if pid not in elo:
            e = hist.bootstrap_elo(rank_hint)
            elo[pid] = {"overall": e, "hard": e, "clay": e, "grass": e}
            serve_running[pid] = hist.new_serve_running()
            return_running[pid] = hist.new_return_running()
            elo_history[pid] = []

    ordered = sorted(
        all_matches,
        key=lambda m: (m.get("tourney_date", "0"), hist.to_num(m.get("match_num")) or 0),
    )
    for m in ordered:
        wid, lid = m["winner_id"], m["loser_id"]
        ensure(wid, m.get("winner_rank"))
        ensure(lid, m.get("loser_rank"))

        new_ow, new_ol = hist.apply_elo_update(elo[wid]["overall"], elo[lid]["overall"], ELO_K_OVERALL)
        elo[wid]["overall"], elo[lid]["overall"] = new_ow, new_ol

        surf_key = {"Hard": "hard", "Clay": "clay", "Grass": "grass"}.get(m.get("surface", ""))
        if surf_key:
            new_sw, new_sl = hist.apply_elo_update(elo[wid][surf_key], elo[lid][surf_key], ELO_K_SURFACE)
            elo[wid][surf_key], elo[lid][surf_key] = new_sw, new_sl

        hist.update_serve_running(serve_running[wid], m, "w")
        hist.update_serve_running(serve_running[lid], m, "l")
        hist.update_return_running(return_running[wid], m, "l")
        hist.update_return_running(return_running[lid], m, "w")

        elo_history[wid].append(elo[wid]["overall"])
        elo_history[lid].append(elo[lid]["overall"])

    return elo, serve_running, return_running, elo_history


def replay_tour_history(fetch_fn, this_year, hist_years_back):
    """Télécharge et rejoue l'historique d'UN SEUL circuit jusqu'à l'état
    actuel. `fetch_fn` est hist.fetch_history (ATP) ou hist.fetch_wta_history
    (WTA). Tout l'état renvoyé ici (elo, matches_by_player, name_to_pid...)
    est local à CE circuit — aucun risque de mélange avec l'autre circuit
    tant qu'on ne combine pas deux appels différents dans le même dict."""
    all_matches = fetch_fn(this_year, hist.HIST_YEARS_BACK if hist_years_back is None else hist_years_back)
    all_matches = [m for m in all_matches if hist.is_usable_match(m)]

    elo, serve_running, return_running, elo_history = simulate_to_present(all_matches)
    matches_by_player = build_matches_by_player(all_matches)

    # Registre nom normalisé -> id source, à partir du classement le plus
    # récent connu pour chaque joueur (sans limiter à un top N).
    name_to_pid = {}
    ambiguous_names = set()
    for pid, rows in matches_by_player.items():
        name, latest_date = None, "0"
        for m in rows:
            for side in ("winner", "loser"):
                if m.get(f"{side}_id") == pid:
                    d = m.get("tourney_date", "0")
                    if d >= latest_date:
                        latest_date, name = d, m.get(f"{side}_name")
        if not name:
            continue
        key = normalize_name_key(name)
        if key in name_to_pid and name_to_pid[key] != pid:
            ambiguous_names.add(key)
        else:
            name_to_pid[key] = pid

    return {
        "all_matches": all_matches,
        "elo": elo,
        "serve_running": serve_running,
        "return_running": return_running,
        "elo_history": elo_history,
        "matches_by_player": matches_by_player,
        "name_to_pid": name_to_pid,
        "ambiguous_names": ambiguous_names,
    }


# -- Mêmes calculs que import_real_data.py (recopiés car ce script doit
#    pouvoir tourner seul, sans dépendre d'un autre module qui a lui-même
#    une dépendance — pymysql — sans rapport), prenant matches_by_player/
#    before_date en paramètres explicites. --

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
# LiveTennisAPI
# ---------------------------------------------------------------------------

def fetch_upcoming_matches(api_key, tour, date_from, date_to):
    matches, offset, limit = [], 0, 200
    while True:
        params = {
            "status": "upcoming",
            "tour": tour,
            "from": date_from,
            "to": date_to,
            "limit": str(limit),
            "offset": str(offset),
        }
        url = f"{LIVETENNISAPI_BASE}/matches?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (compatible; TennlyIA/1.0)",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"LiveTennisAPI a renvoyé une erreur {e.code} (tour={tour}) : {body}")
        except urllib.error.URLError as e:
            raise SystemExit(f"Impossible de joindre LiveTennisAPI (pas de réseau ?) : {e}")

        data = payload.get("data", [])
        matches.extend(data)
        meta = payload.get("meta", {})
        if not meta.get("has_more") or not data:
            break
        offset += limit
    return matches


def is_genuinely_upcoming(m, now_utc):
    """Filtre défensif : on a constaté que LiveTennisAPI renvoie parfois,
    même sous status=upcoming, des matchs qui ne le sont plus vraiment
    (retirés/annulés/W.O./reportés, ou déjà commencés). On ne fait jamais
    confiance au seul filtre `status=upcoming` de la requête : on revérifie
    chaque match individuellement."""
    if m.get("status") != "upcoming":
        return False
    if m.get("event_status") is not None:
        return False
    if m.get("winner") is not None:
        return False
    if m.get("is_doubles"):
        return False
    scheduled = m.get("scheduled_time")
    if not scheduled:
        return False
    try:
        dt = datetime.fromisoformat(str(scheduled).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt > now_utc


def map_app_surface(m):
    if m.get("indoor"):
        return "indoor"
    return SURFACE_APP_LABEL.get((m.get("surface") or "").lower(), "dur")


def elo_key_for_match(m):
    return SURFACE_ELO_KEY.get((m.get("surface") or "").lower())


# ---------------------------------------------------------------------------
# Instantané quotidien par joueur + face-à-face (comparateur de joueurs,
# frontend/src/views/ComparateurView.vue + backend ComparateurController) —
# calculé à CHAQUE exécution de ce script, même les jours sans nouveau match
# à venir, pour CHAQUE circuit séparément (voir replay_tour_history). Le
# comparateur compare deux joueurs QUELCONQUES de la base, pas seulement
# ceux d'un match précis : ces deux tables existent pour ça.
# ---------------------------------------------------------------------------

def app_players_with_history(existing_by_external_ref, prefix):
    """{id joueur app: id source} — uniquement les joueurs dont l'historique
    de CE circuit est connu (external_ref = '<prefix>:<id>', prefix='tml'
    pour l'ATP, 'wta' pour la WTA). Un joueur découvert seulement via
    LiveTennisAPI (external_ref = 'livetennisapi:<id>', pas d'historique)
    n'a pas d'instantané calculable ici, comme partout ailleurs dans ce
    fichier pour un joueur sans historique."""
    result = {}
    for ref, row in existing_by_external_ref.items():
        if ref.startswith(f"{prefix}:"):
            try:
                result[row["id"]] = int(ref.split(":", 1)[1])
            except ValueError:
                continue
    return result


def compute_player_snapshots(existing_by_external_ref, matches_by_player, serve_running,
                              return_running, elo_history, today_str, prefix):
    mapping = app_players_with_history(existing_by_external_ref, prefix)
    snapshots = []
    for app_id, source_pid in mapping.items():
        snapshots.append({
            "player_id": app_id,
            "serve_score": hist.serve_score(serve_running[source_pid]),
            "return_score": hist.return_score(return_running[source_pid]),
            "momentum": momentum_for(elo_history, source_pid),
            "recent_form": recent_form(matches_by_player, source_pid, today_str),
            "days_rest": days_rest(matches_by_player, source_pid, today_str),
            "fatigue_minutes": recent_minutes_played(matches_by_player, source_pid, today_str),
            "upset_rate": upset_rate(matches_by_player, source_pid, today_str),
            # Taux de victoire face à un gaucher / un droitier — précalculés
            # séparément (indépendamment de l'adversaire du jour) pour que le
            # comparateur puisse piocher la bonne valeur selon la main de
            # l'adversaire réellement choisi, sans avoir à rejouer tout
            # l'historique à la demande (voir hand_matchup_rate ci-dessus).
            "winrate_vs_left": hand_matchup_rate(matches_by_player, source_pid, "L", today_str),
            "winrate_vs_right": hand_matchup_rate(matches_by_player, source_pid, "R", today_str),
        })
    return snapshots


def compute_head_to_head_pairs(existing_by_external_ref, all_matches, prefix):
    """Face-à-face réel entre joueurs actuellement connus de l'app, POUR CE
    CIRCUIT, déduit de TOUT l'historique téléchargé pour ce circuit (pas
    seulement les quelques matchs affichés dans /matchs). Convention :
    toujours stocké avec player_low_id < player_high_id — voir
    ComparateurController côté backend, qui respecte la même convention à la
    lecture."""
    source_to_app = {}
    for ref, row in existing_by_external_ref.items():
        if ref.startswith(f"{prefix}:"):
            try:
                source_to_app[int(ref.split(":", 1)[1])] = row["id"]
            except ValueError:
                continue

    pairs = {}
    for m in all_matches:
        app_w = source_to_app.get(m["winner_id"])
        app_l = source_to_app.get(m["loser_id"])
        if app_w is None or app_l is None or app_w == app_l:
            continue
        low, high = (app_w, app_l) if app_w < app_l else (app_l, app_w)
        key = (low, high)
        if key not in pairs:
            pairs[key] = {"player_low_id": low, "player_high_id": high, "wins_low": 0, "wins_high": 0}
        if app_w == low:
            pairs[key]["wins_low"] += 1
        else:
            pairs[key]["wins_high"] += 1
    return list(pairs.values())


def apply_snapshots_to_database(conn, snapshots, h2h_pairs):
    """Comme apply_to_database() plus bas : requêtes paramétrées, jamais de
    concaténation de chaînes SQL. INSERT ... ON DUPLICATE KEY UPDATE, puisque
    ces deux tables se rafraîchissent en place chaque jour (pas d'historique
    de versions à garder ici, contrairement aux matchs/analyses)."""
    with conn.cursor() as cur:
        for s in snapshots:
            cur.execute(
                "INSERT INTO player_snapshot (player_id, serve_score, return_score, momentum, "
                "recent_form, days_rest, fatigue_minutes, upset_rate, winrate_vs_left, "
                "winrate_vs_right, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) "
                "ON DUPLICATE KEY UPDATE serve_score=VALUES(serve_score), return_score=VALUES(return_score), "
                "momentum=VALUES(momentum), recent_form=VALUES(recent_form), days_rest=VALUES(days_rest), "
                "fatigue_minutes=VALUES(fatigue_minutes), upset_rate=VALUES(upset_rate), "
                "winrate_vs_left=VALUES(winrate_vs_left), winrate_vs_right=VALUES(winrate_vs_right), "
                "updated_at=NOW()",
                (s["player_id"], round(s["serve_score"]), round(s["return_score"]), s["momentum"],
                 s["recent_form"], s["days_rest"], s["fatigue_minutes"], s["upset_rate"],
                 s["winrate_vs_left"], s["winrate_vs_right"]),
            )
        for p in h2h_pairs:
            cur.execute(
                "INSERT INTO player_head_to_head (player_low_id, player_high_id, wins_low, wins_high, updated_at) "
                "VALUES (%s, %s, %s, %s, NOW()) "
                "ON DUPLICATE KEY UPDATE wins_low=VALUES(wins_low), wins_high=VALUES(wins_high), updated_at=NOW()",
                (p["player_low_id"], p["player_high_id"], p["wins_low"], p["wins_high"]),
            )


# ---------------------------------------------------------------------------
# Correspondance joueur (par nom) + traitement des matchs à venir d'UN
# circuit — regroupé en fonctions explicites (plutôt que des closures dans
# main()) pour pouvoir être appelé une fois par circuit sans dupliquer tout
# le corps de la boucle.
# ---------------------------------------------------------------------------

def resolve_player(tour, prefix, api_player, tour_state, existing_by_name_key,
                    existing_by_external_ref, next_player_id, new_players, updated_players):
    """Fait correspondre un joueur renvoyé par LiveTennisAPI à un joueur déjà
    connu (par nom), ou en crée un nouveau. Mute `new_players`/`updated_players`
    (listes) et `existing_by_name_key` (dict) en place ; renvoie
    (app_id, source_pid_ou_None, next_player_id_mis_a_jour) — next_player_id
    doit être ré-affecté par l'appelant (entier, donc pas mutable en place)."""
    name = api_player.get("name") or "Joueur inconnu"
    name_key = normalize_name_key(name)

    source_pid = tour_state["name_to_pid"].get(name_key) if name_key not in tour_state["ambiguous_names"] else None
    source_elo = tour_state["elo"].get(source_pid) if source_pid else None

    existing_row = existing_by_name_key.get(name_key)
    if source_pid:
        existing_row = existing_row or existing_by_external_ref.get(f"{prefix}:{source_pid}")

    rank = api_player.get("ranking")
    hand = (api_player.get("hand") or "").strip()[:1] or None
    country = (api_player.get("country") or "").strip()[:3] or None

    if existing_row:
        app_id = existing_row["id"]
        # Corrige aussi `tour` s'il est incorrect (voir bug corrigé le
        # 27/08/2026 : une exécution de ce script AVANT le support WTA — donc
        # sans jamais renseigner `tour` — a inséré certaines joueuses WTA
        # récupérées via LiveTennisAPI avec la valeur par défaut 'atp' de la
        # colonne. Ce joueur/cette joueuse est alors resté(e) mal étiqueté(e)
        # indéfiniment, car ce bloc ne touchait avant que l'Elo/le classement,
        # jamais `tour`, sur un joueur déjà connu). On corrige systématiquement
        # ici, même si `tour` est déjà bon (coût négligeable), plutôt que de
        # ne réparer qu'au prochain import_real_data.py (qui, lui, reconstruit
        # tout depuis les vraies sources et aurait fini par corriger ça).
        if source_elo is not None or existing_row.get("tour") != tour:
            updated_players.append({
                "id": app_id,
                "elo_overall": source_elo["overall"] if source_elo is not None else existing_row["elo_overall"],
                "elo_hard": source_elo["hard"] if source_elo is not None else existing_row["elo_hard"],
                "elo_clay": source_elo["clay"] if source_elo is not None else existing_row["elo_clay"],
                "elo_grass": source_elo["grass"] if source_elo is not None else existing_row["elo_grass"],
                "atp_wta_rank": rank if rank is not None else existing_row["atp_wta_rank"],
                "tour": tour,
            })
        return app_id, source_pid, next_player_id

    next_player_id += 1
    app_id = next_player_id
    if source_elo is not None:
        e, external_ref = source_elo, f"{prefix}:{source_pid}"
    else:
        base = hist.bootstrap_elo(rank)
        e = {"overall": base, "hard": base, "clay": base, "grass": base}
        external_ref = f"livetennisapi:{api_player.get('id')}"
    new_players.append({
        "id": app_id, "full_name": name, "country_code": country, "atp_wta_rank": rank,
        "elo_overall": e["overall"], "elo_hard": e["hard"], "elo_clay": e["clay"], "elo_grass": e["grass"],
        "hand": hand, "external_ref": external_ref, "tour": tour,
    })
    # ajouté tout de suite au registre "existant" : si un autre match de ce
    # même lot implique le même joueur, pas de doublon.
    existing_by_name_key[name_key] = {
        "id": app_id, "full_name": name, "external_ref": external_ref,
        "elo_overall": e["overall"], "elo_hard": e["hard"], "elo_clay": e["clay"],
        "elo_grass": e["grass"], "atp_wta_rank": rank, "dominant_hand": hand, "country_code": country,
        "tour": tour,
    }
    return app_id, source_pid, next_player_id


def process_tour_upcoming(tour, api_key, date_from, date_to, now_utc, tour_state,
                           existing_by_name_key, existing_by_external_ref, existing_match_refs,
                           next_player_id, next_match_id, next_prediction_id):
    """Traite le calendrier des matchs à venir d'UN circuit : fetch
    LiveTennisAPI, filtre/dédoublonne, résout les joueurs, calcule
    probabilité/facteurs/radar. Renvoie (new_players, updated_players,
    new_matches, new_predictions, next_player_id, next_match_id,
    next_prediction_id, stats) où stats est un dict de compteurs pour
    l'affichage console."""
    prefix = TOUR_EXTERNAL_REF_PREFIX[tour]
    rank_label = TOUR_RANK_LABEL[tour]
    tour_is_wta = 1 if tour == "wta" else 0

    raw_matches = fetch_upcoming_matches(api_key, tour, date_from, date_to)
    upcoming = [m for m in raw_matches if is_genuinely_upcoming(m, now_utc)]

    seen_ids, deduped = set(), []
    for m in upcoming:
        if m.get("id") in seen_ids:
            continue
        seen_ids.add(m.get("id"))
        deduped.append(m)
    already_imported = sum(1 for m in deduped if f"livetennisapi:{m.get('id')}" in existing_match_refs)
    upcoming = [m for m in deduped if f"livetennisapi:{m.get('id')}" not in existing_match_refs]
    dropped = len(raw_matches) - len(deduped)

    stats = {
        "raw": len(raw_matches), "genuinely_upcoming": len(deduped), "dropped": dropped,
        "already_imported": already_imported, "truly_new": len(upcoming),
    }

    new_players, updated_players, new_matches, new_predictions = [], [], [], []

    for m in upcoming:
        p1, p2 = m["players"]["p1"], m["players"]["p2"]
        id_a, tour_a, next_player_id = resolve_player(
            tour, prefix, p1, tour_state, existing_by_name_key,
            existing_by_external_ref, next_player_id, new_players, updated_players,
        )
        id_b, tour_b, next_player_id = resolve_player(
            tour, prefix, p2, tour_state, existing_by_name_key,
            existing_by_external_ref, next_player_id, new_players, updated_players,
        )

        elo_a = tour_state["elo"].get(tour_a) if tour_a else None
        elo_b = tour_state["elo"].get(tour_b) if tour_b else None
        surf_key = elo_key_for_match(m)

        def elo_value(elo_dict, fallback_row):
            if elo_dict is not None:
                return elo_dict[surf_key] if surf_key and surf_key in elo_dict else elo_dict["overall"]
            if surf_key == "hard":
                return fallback_row["elo_hard"]
            if surf_key == "clay":
                return fallback_row["elo_clay"]
            if surf_key == "grass":
                return fallback_row["elo_grass"]
            return fallback_row["elo_overall"]

        row_a = existing_by_name_key.get(normalize_name_key(p1.get("name") or ""))
        row_b = existing_by_name_key.get(normalize_name_key(p2.get("name") or ""))
        elo_val_a = elo_value(elo_a, row_a)
        elo_val_b = elo_value(elo_b, row_b)
        elo_overall_a = elo_a["overall"] if elo_a is not None else row_a["elo_overall"]
        elo_overall_b = elo_b["overall"] if elo_b is not None else row_b["elo_overall"]

        rank_a, rank_b = p1.get("ranking"), p2.get("ranking")
        matches_by_player = tour_state["matches_by_player"]
        serve_running, return_running = tour_state["serve_running"], tour_state["return_running"]
        elo_history = tour_state["elo_history"]
        today_str = date_from.replace("-", "")

        serve_a = hist.serve_score(serve_running[tour_a]) if tour_a else hist.DEFAULT_SERVE_RETURN_SCORE
        serve_b = hist.serve_score(serve_running[tour_b]) if tour_b else hist.DEFAULT_SERVE_RETURN_SCORE
        return_a = hist.return_score(return_running[tour_a]) if tour_a else hist.DEFAULT_SERVE_RETURN_SCORE
        return_b = hist.return_score(return_running[tour_b]) if tour_b else hist.DEFAULT_SERVE_RETURN_SCORE

        form_a = recent_form(matches_by_player, tour_a, today_str) if tour_a else None
        form_b = recent_form(matches_by_player, tour_b, today_str) if tour_b else None
        rest_a = days_rest(matches_by_player, tour_a, today_str) if tour_a else None
        rest_b = days_rest(matches_by_player, tour_b, today_str) if tour_b else None
        h2h_a, h2h_b = head_to_head(matches_by_player, tour_a, tour_b, today_str) if (tour_a and tour_b) else (0, 0)
        momentum_a = momentum_for(elo_history, tour_a) if tour_a else None
        momentum_b = momentum_for(elo_history, tour_b) if tour_b else None

        hand_a, hand_b = (p1.get("hand") or None), (p2.get("hand") or None)
        hand_edge_a = hand_edge_b = None
        if hand_a in ("L", "R") and hand_b in ("L", "R") and hand_a != hand_b:
            hand_edge_a = hand_matchup_rate(matches_by_player, tour_a, hand_b, today_str) if tour_a else None
            hand_edge_b = hand_matchup_rate(matches_by_player, tour_b, hand_a, today_str) if tour_b else None

        fatigue_a = recent_minutes_played(matches_by_player, tour_a, today_str) if tour_a else None
        fatigue_b = recent_minutes_played(matches_by_player, tour_b, today_str) if tour_b else None

        is_indoor_match = bool(m.get("indoor"))
        indoor_a = indoor_win_rate(matches_by_player, tour_a, today_str) if (is_indoor_match and tour_a) else None
        indoor_b = indoor_win_rate(matches_by_player, tour_b, today_str) if (is_indoor_match and tour_b) else None

        upset_a = upset_rate(matches_by_player, tour_a, today_str) if tour_a else None
        upset_b = upset_rate(matches_by_player, tour_b, today_str) if tour_b else None

        if model_inference.MODEL_AVAILABLE:
            feature_dict = model_inference.build_feature_row(
                rank_a, rank_b, elo_overall_a, elo_overall_b, elo_val_a, elo_val_b,
                serve_a, serve_b, return_a, return_b, momentum_a, momentum_b,
                form_a, form_b, rest_a, rest_b, h2h_a, h2h_b, hand_edge_a, hand_edge_b,
                fatigue_a, fatigue_b, indoor_a, indoor_b, upset_a, upset_b, tour_is_wta,
            )
            proba_a_wins = model_inference.predict_probability(feature_dict)
            model_version_used = model_inference.MODEL_VERSION
        else:
            proba_a_wins = hist.elo_win_probability(elo_val_a, elo_val_b)
            model_version_used = MODEL_VERSION

        is_a_fav = proba_a_wins >= 0.5
        fav_id = id_a if is_a_fav else id_b
        proba = proba_a_wins if is_a_fav else 1 - proba_a_wins
        confidence = hist.confidence_from_probability(proba)

        elo_fav, elo_dog = (elo_val_a, elo_val_b) if is_a_fav else (elo_val_b, elo_val_a)
        rank_fav, rank_dog = (rank_a, rank_b) if is_a_fav else (rank_b, rank_a)
        serve_fav, serve_dog = (serve_a, serve_b) if is_a_fav else (serve_b, serve_a)
        h2h_fav, h2h_dog = (h2h_a, h2h_b) if is_a_fav else (h2h_b, h2h_a)
        momentum_fav, momentum_dog = (momentum_a, momentum_b) if is_a_fav else (momentum_b, momentum_a)
        hand_dog = hand_b if is_a_fav else hand_a
        hand_edge_fav, hand_edge_dog = (hand_edge_a, hand_edge_b) if is_a_fav else (hand_edge_b, hand_edge_a)
        fatigue_fav, fatigue_dog = (fatigue_a, fatigue_b) if is_a_fav else (fatigue_b, fatigue_a)
        indoor_fav, indoor_dog = (indoor_a, indoor_b) if is_a_fav else (indoor_b, indoor_a)
        upset_fav, upset_dog = (upset_a, upset_b) if is_a_fav else (upset_b, upset_a)

        factors = []
        if rank_fav is not None and rank_dog is not None:
            factors.append({"label": rank_label, "favors": "A" if is_a_fav else "B",
                             "impactPoints": round(abs(float(rank_fav) - float(rank_dog)) / 10, 1), "tone": "ok"})
        if h2h_fav + h2h_dog > 0:
            factors.append({"label": "Face-à-face", "favors": "A" if is_a_fav == (h2h_fav >= h2h_dog) else "B",
                             "impactPoints": h2h_fav - h2h_dog, "tone": "ok" if h2h_fav >= h2h_dog else "warn"})
        if abs(serve_fav - serve_dog) >= 8:
            factors.append({"label": "Force au service", "favors": "A" if is_a_fav == (serve_fav >= serve_dog) else "B",
                             "impactPoints": round((serve_fav - serve_dog) / 10, 1), "tone": "ok" if serve_fav >= serve_dog else "warn"})
        if momentum_fav is not None and momentum_dog is not None and abs(momentum_fav - momentum_dog) >= 15:
            factors.append({"label": "Dynamique du moment (Elo sur les derniers matchs)",
                             "favors": "A" if is_a_fav == (momentum_fav >= momentum_dog) else "B",
                             "impactPoints": round((momentum_fav - momentum_dog) / 10, 1),
                             "tone": "ok" if momentum_fav >= momentum_dog else "warn"})
        if hand_edge_fav is not None and hand_edge_dog is not None and abs(hand_edge_fav - hand_edge_dog) >= 0.15:
            style = "gaucher" if hand_dog == "L" else "droitier"
            factors.append({"label": f"Habitude du jeu face à un {style}",
                             "favors": "A" if is_a_fav == (hand_edge_fav >= hand_edge_dog) else "B",
                             "impactPoints": round((hand_edge_fav - hand_edge_dog) * 10, 1),
                             "tone": "ok" if hand_edge_fav >= hand_edge_dog else "warn"})
        if fatigue_fav is not None and fatigue_dog is not None and abs(fatigue_fav - fatigue_dog) >= 60:
            more_rested_is_fav = fatigue_fav <= fatigue_dog
            factors.append({"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)",
                             "favors": "A" if (is_a_fav == more_rested_is_fav) else "B",
                             "impactPoints": round((fatigue_dog - fatigue_fav) / 30, 1),
                             "tone": "ok" if more_rested_is_fav else "warn"})
        if indoor_fav is not None and indoor_dog is not None and abs(indoor_fav - indoor_dog) >= 0.15:
            factors.append({"label": "Habitude du jeu en intérieur",
                             "favors": "A" if is_a_fav == (indoor_fav >= indoor_dog) else "B",
                             "impactPoints": round((indoor_fav - indoor_dog) * 10, 1),
                             "tone": "ok" if indoor_fav >= indoor_dog else "warn"})
        if upset_fav is not None and upset_dog is not None and abs(upset_fav - upset_dog) >= 0.15:
            factors.append({"label": "Capacité à créer l'exploit contre plus fort classé",
                             "favors": "A" if is_a_fav == (upset_fav >= upset_dog) else "B",
                             "impactPoints": round((upset_fav - upset_dog) * 10, 1),
                             "tone": "ok" if upset_fav >= upset_dog else "warn"})
        if not factors:
            factors.append({"label": "Estimation Elo (historique insuffisant pour affiner)",
                             "favors": "A" if is_a_fav else "B",
                             "impactPoints": round(abs(elo_fav - elo_dog) / 20, 1), "tone": "ok"})

        def pct(v, default=65):
            return hist.clamp(v * 100) if v is not None else default

        radar = {
            "eloSurface": [hist.clamp((elo_val_a - 1500) / 8), hist.clamp((elo_val_b - 1500) / 8)],
            "forme": [pct(form_a), pct(form_b)],
            "service": [hist.clamp(serve_a), hist.clamp(serve_b)],
            "retour": [hist.clamp(return_a), hist.clamp(return_b)],
            "repos": [hist.clamp((rest_a or 3) * 10), hist.clamp((rest_b or 3) * 10)],
            "h2h": [hist.clamp(50 + (h2h_a - h2h_b) * 10), hist.clamp(50 - (h2h_a - h2h_b) * 10)],
        }

        next_match_id += 1
        match_id = next_match_id
        tournament_name = m.get("tournament") or ("Tournoi WTA" if tour == "wta" else "Tournoi ATP")
        round_code = m.get("round_code") or ""
        round_label = hist.ROUND_MAP.get(round_code, m.get("round") or round_code or "?")
        app_surface = map_app_surface(m)
        scheduled_at = datetime.fromisoformat(str(m["scheduled_time"]).replace("Z", "+00:00")) \
            .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        new_matches.append({
            "id": match_id, "player_a_id": id_a, "player_b_id": id_b,
            "tournament_name": tournament_name, "round": round_label, "surface": app_surface,
            "scheduled_at": scheduled_at, "external_ref": f"livetennisapi:{m.get('id')}",
        })

        next_prediction_id += 1
        new_predictions.append({
            "id": next_prediction_id, "match_id": match_id, "favorite_player_id": fav_id,
            "probability_favorite": round(proba, 4), "confidence_level": confidence,
            "factors": factors, "radar": radar, "model_version": model_version_used,
        })

    return (new_players, updated_players, new_matches, new_predictions,
            next_player_id, next_match_id, next_prediction_id, stats)


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main():
    env = load_env_local()
    api_key = env["LIVETENNIS_API_KEY"]
    db_kwargs = parse_database_url(env["DATABASE_URL"])

    print("1/5 — Lecture de l'état actuel de ta base…")
    conn = connect_db(db_kwargs)
    try:
        existing_by_external_ref, existing_by_name_key, max_player_id = load_existing_players(conn)
        max_match_id = load_max_id(conn, "tennis_match")
        max_prediction_id = load_max_id(conn, "prediction")
        existing_match_refs = load_existing_match_refs(conn)
        print(f"  {len(existing_by_name_key)} joueurs déjà en base, {len(existing_match_refs)} matchs à venir "
              f"déjà importés précédemment (id max joueur={max_player_id}, match={max_match_id}, "
              f"analyse={max_prediction_id})")

        this_year = datetime.now().year
        today_str = datetime.now().strftime("%Y%m%d")
        now_utc = datetime.now(timezone.utc)
        date_from = now_utc.strftime("%Y-%m-%d")
        date_to = (now_utc + timedelta(days=LOOKAHEAD_DAYS)).strftime("%Y-%m-%d")

        print("2/5 — Retéléchargement et rejeu de l'historique réel, ATP puis WTA "
              "(deux circuits totalement indépendants)…")
        tour_states = {}
        print(" Circuit ATP (source : Tennismylife/TML-Database)…")
        tour_states["atp"] = replay_tour_history(hist.fetch_history, this_year, hist.HIST_YEARS_BACK)
        print(f"  {len(tour_states['atp']['all_matches'])} matchs ATP exploitables")
        print(" Circuit WTA (source : stats.tennismylife.org)…")
        tour_states["wta"] = replay_tour_history(hist.fetch_wta_history, this_year, hist.HIST_YEARS_BACK)
        print(f"  {len(tour_states['wta']['all_matches'])} matchs WTA exploitables")

        # -- Instantané quotidien des joueurs + face-à-face (comparateur) --
        # Fait ICI, avant de savoir s'il y a de nouveaux matchs à venir : ce
        # rafraîchissement doit avoir lieu TOUS LES JOURS, même un jour sans
        # aucun nouveau match, sur LES DEUX circuits.
        print("Mise à jour de l'instantané quotidien des joueurs (comparateur de joueurs), "
              "ATP + WTA…")
        all_snapshots, all_h2h_pairs = [], []
        for tour, prefix in TOUR_EXTERNAL_REF_PREFIX.items():
            state = tour_states[tour]
            snapshots = compute_player_snapshots(
                existing_by_external_ref, state["matches_by_player"], state["serve_running"],
                state["return_running"], state["elo_history"], today_str, prefix,
            )
            h2h_pairs = compute_head_to_head_pairs(existing_by_external_ref, state["all_matches"], prefix)
            all_snapshots.extend(snapshots)
            all_h2h_pairs.extend(h2h_pairs)
        apply_snapshots_to_database(conn, all_snapshots, all_h2h_pairs)
        conn.commit()
        print(f"  {len(all_snapshots)} joueur(s)/joueuse(s) et {len(all_h2h_pairs)} paire(s) "
              f"face-à-face mis à jour (ATP + WTA).")

        print(f"3/5 — Récupération des matchs simple à venir sur LiveTennisAPI, ATP + WTA "
              f"({date_from} -> {date_to})…")

        next_player_id, next_match_id, next_prediction_id = max_player_id, max_match_id, max_prediction_id
        all_new_players, all_updated_players, all_new_matches, all_new_predictions = [], [], [], []

        for tour in ("atp", "wta"):
            (new_players, updated_players, new_matches, new_predictions,
             next_player_id, next_match_id, next_prediction_id, stats) = process_tour_upcoming(
                tour, api_key, date_from, date_to, now_utc, tour_states[tour],
                existing_by_name_key, existing_by_external_ref, existing_match_refs,
                next_player_id, next_match_id, next_prediction_id,
            )
            print(f"  {tour.upper()} : {stats['raw']} matchs renvoyés par l'API, "
                  f"{stats['genuinely_upcoming']} genuinement à venir ({stats['dropped']} écartés), "
                  f"dont {stats['already_imported']} déjà importés précédemment -> "
                  f"{stats['truly_new']} VRAIMENT nouveau(x)")
            all_new_players.extend(new_players)
            all_updated_players.extend(updated_players)
            all_new_matches.extend(new_matches)
            all_new_predictions.extend(new_predictions)

        if not all_new_matches:
            print("\nRien de nouveau aujourd'hui (ATP ET WTA) — la base est déjà à jour, "
                  "aucune écriture de match nécessaire.")
            return

        print("4/5 — Écriture en base…")
        log_path = write_log(all_new_players, all_updated_players, all_new_matches, all_new_predictions)
        apply_to_database(conn, all_new_players, all_updated_players, all_new_matches, all_new_predictions)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\n5/5 — Terminé : {len(all_new_players)} nouveaux joueurs/joueuses, "
          f"{len(all_updated_players)} joueurs existants avec Elo et/ou circuit (tour) rafraîchi, "
          f"{len(all_new_matches)} matchs à venir écrits DIRECTEMENT en base (ATP + WTA).")
    print(f"Journal de cette exécution : {log_path}")


def apply_to_database(conn, new_players, updated_players, new_matches, new_predictions):
    """Écrit directement en base, en une seule transaction (tout ou rien —
    voir le try/except autour de l'appel dans main()). Requêtes paramétrées,
    jamais de concaténation de chaînes SQL."""
    with conn.cursor() as cur:
        for p in new_players:
            cur.execute(
                "INSERT INTO player (id, full_name, country_code, atp_wta_rank, elo_overall, "
                "elo_hard, elo_clay, elo_grass, dominant_hand, external_ref, tour) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (p["id"], p["full_name"], p["country_code"], p["atp_wta_rank"],
                 round(p["elo_overall"]), round(p["elo_hard"]), round(p["elo_clay"]), round(p["elo_grass"]),
                 p["hand"], p["external_ref"], p["tour"]),
            )
        for p in updated_players:
            cur.execute(
                "UPDATE player SET elo_overall=%s, elo_hard=%s, elo_clay=%s, elo_grass=%s, atp_wta_rank=%s, "
                "tour=%s WHERE id=%s",
                (round(p["elo_overall"]), round(p["elo_hard"]), round(p["elo_clay"]), round(p["elo_grass"]),
                 p["atp_wta_rank"], p["tour"], p["id"]),
            )
        for m in new_matches:
            cur.execute(
                "INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, "
                "round, surface, scheduled_at, status, score_text, external_ref) "
                "VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, 'scheduled', NULL, %s)",
                (m["id"], m["player_a_id"], m["player_b_id"], m["tournament_name"], m["round"],
                 m["surface"], m["scheduled_at"], m["external_ref"]),
            )
        for p in new_predictions:
            cur.execute(
                "INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, "
                "confidence_level, model_version, computed_at, explanation_factors, radar_profile, "
                "market_odds_favorite, value_edge) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, NULL, NULL)",
                (p["id"], p["match_id"], p["favorite_player_id"], p["probability_favorite"],
                 p["confidence_level"], p["model_version"],
                 json.dumps(p["factors"], ensure_ascii=False), json.dumps(p["radar"], ensure_ascii=False)),
            )


def write_log(new_players, updated_players, new_matches, new_predictions):
    """Copie lisible (texte SQL, jamais exécutée telle quelle) de ce que
    apply_to_database() vient d'écrire en base — un fichier par exécution
    dans logs/, pour pouvoir vérifier après coup ce que l'automatisation a
    fait sans avoir eu besoin de le relire avant."""
    out = [
        f"-- Journal de l'exécution du {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "-- (déjà appliqué directement en base — ce fichier est juste une trace lisible, "
        "ne pas le réimporter.)\n\n"
    ]

    if new_players:
        out.append("-- Nouveaux joueurs/joueuses (ATP + WTA) :\n")
        out.extend(
            f"INSERT INTO player (id, full_name, country_code, atp_wta_rank, elo_overall, elo_hard, "
            f"elo_clay, elo_grass, dominant_hand, external_ref, tour) VALUES "
            f"({p['id']}, {hist.sql_str(p['full_name'])}, {hist.sql_str(p['country_code'])}, "
            f"{p['atp_wta_rank'] if p['atp_wta_rank'] is not None else 'NULL'}, {round(p['elo_overall'])}, "
            f"{round(p['elo_hard'])}, {round(p['elo_clay'])}, {round(p['elo_grass'])}, "
            f"{hist.sql_str(p['hand'])}, {hist.sql_str(p['external_ref'])}, {hist.sql_str(p['tour'])});\n"
            for p in new_players
        )
        out.append("\n")

    if updated_players:
        out.append("-- Joueurs existants dont l'Elo (et/ou le circuit, voir resolve_player) a été rafraîchi :\n")
        out.extend(
            f"UPDATE player SET elo_overall={round(p['elo_overall'])}, elo_hard={round(p['elo_hard'])}, "
            f"elo_clay={round(p['elo_clay'])}, elo_grass={round(p['elo_grass'])}, "
            f"atp_wta_rank={p['atp_wta_rank'] if p['atp_wta_rank'] is not None else 'NULL'}, "
            f"tour={hist.sql_str(p['tour'])} WHERE id={p['id']};\n"
            for p in updated_players
        )
        out.append("\n")

    if new_matches:
        out.append("-- Nouveaux matchs à venir (ATP + WTA) :\n")
        out.extend(
            f"INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, "
            f"surface, scheduled_at, status, score_text, external_ref) VALUES "
            f"({m['id']}, {m['player_a_id']}, {m['player_b_id']}, NULL, {hist.sql_str(m['tournament_name'])}, "
            f"{hist.sql_str(m['round'])}, {hist.sql_str(m['surface'])}, {hist.sql_str(m['scheduled_at'])}, "
            f"'scheduled', NULL, {hist.sql_str(m['external_ref'])});\n"
            for m in new_matches
        )
        out.append("\n")

    if new_predictions:
        out.append("-- Nouvelles analyses :\n")
        out.extend(
            f"INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, "
            f"confidence_level, model_version, computed_at, explanation_factors, radar_profile, "
            f"market_odds_favorite, value_edge) VALUES ({p['id']}, {p['match_id']}, {p['favorite_player_id']}, "
            f"{p['probability_favorite']}, {hist.sql_str(p['confidence_level'])}, {hist.sql_str(p['model_version'])}, "
            f"NOW(), {hist.sql_json(p['factors'])}, {hist.sql_json(p['radar'])}, NULL, NULL);\n"
            for p in new_predictions
        )

    text = "".join(out)
    OUTPUT_FILE.write_text(text, encoding="utf-8")  # copie "dernière exécution", écrasée à chaque fois
    LOG_DIR.mkdir(exist_ok=True)
    timestamped = LOG_DIR / f"import_upcoming_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    timestamped.write_text(text, encoding="utf-8")
    return timestamped


if __name__ == "__main__":
    main()


