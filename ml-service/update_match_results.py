#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clôture les matchs à venir une fois qu'ils ont réellement été joués.

Pourquoi ce script existe : import_upcoming_matches.py insère les matchs à
venir avec status='scheduled', winner_id=NULL, score_text=NULL — et rien
dans le projet ne les faisait jamais ressortir de cet état une fois le match
terminé. Conséquence concrète : passé leur scheduled_at, ces matchs
disparaissaient purement et simplement du site (MatchesView.vue ne les
affiche ni dans "à venir" — scheduled_at n'est plus strictement dans le
futur — ni dans "terminés" — status reste 'scheduled', jamais 'finished'/
'walkover'), et la page "Fiabilité du modèle" (ModelReliabilityView.vue,
GET /api/model-reliability) ne pouvait jamais s'enrichir de nouvelles
comparaisons prédiction/résultat réel depuis le lancement.

Ce script :
  - Lit `tennis_match` (lecture seule sur les joueurs) pour trouver les
    matchs status='scheduled', scheduled_at déjà passé, importés depuis
    LiveTennisAPI (external_ref LIKE 'livetennisapi:%' — le seul cas où
    external_ref est renseigné sur tennis_match, voir import_upcoming_
    matches.py ; les matchs historiques d'import_real_data.py sont déjà
    insérés directement en 'finished'/'walkover').
  - Interroge LiveTennisAPI (endpoint /matches, status=completed) sur une
    fenêtre de dates couvrant ces matchs, SÉPARÉMENT pour l'ATP et la WTA
    (même prudence anti-mélange que partout ailleurs dans ce dossier), et
    fait correspondre chaque match trouvé à une ligne en base via l'id
    LiveTennisAPI encodé dans external_ref.
  - N'écrit JAMAIS de DELETE ni de INSERT ici : uniquement des UPDATE
    ciblés (status, winner_id, score_text) sur des lignes déjà existantes,
    identifiées par leur id — même philosophie que import_upcoming_
    matches.py. Un match non retrouvé dans la réponse de l'API est laissé
    tel quel (il sera retenté à la prochaine exécution).
  - Garde une copie lisible de ce qui a été fait dans ml-service/logs/,
    comme les autres scripts de ce dossier.

Mapping des champs LiveTennisAPI -> tennis_match (vérifié sur un vrai match
terminé, Ben Shelton vs Carlos Alcaraz, US Open QF, id LiveTennisAPI
187552) :
  - `winner` (1 ou 2, POSITIONNEL — pas un id de joueur) : 1 -> player_a_id,
    2 -> player_b_id. Vérifié en relisant process_tour_upcoming() dans
    import_upcoming_matches.py : p1/p2 sont résolus dans CET ORDRE en
    id_a/id_b, eux-mêmes écrits tels quels dans player_a_id/player_b_id.
  - `score.games` (deux tableaux parallèles, un par joueur, jeux gagnés par
    set) -> score_text lisible ("6-7, 6-1, 6-3, 1-6, 7-6"), en associant les
    deux tableaux position par position.
  - `event_status` -> status : seule la valeur "Finished" a été observée en
    pratique à ce jour (pas encore de cas walkover/abandon confirmé). Choix
    assumé et défensif, pas garanti à 100% : tout `event_status` contenant
    "walkover" (insensible à la casse) devient notre statut 'walkover',
    tout le reste (y compris un abandon/retired — il y a bien un
    gagnant et un score partiel) devient 'finished'. À ajuster si un
    exemple réel de walkover apparaît un jour avec une valeur différente.
  - Un match dont le `winner` n'est ni 1 ni 2 (annulé, résultat non encore
    connu de l'API malgré status=completed, etc.) est explicitement IGNORÉ
    plutôt que deviné — il sera retenté à la prochaine exécution.

Dépendance : PyMySQL (déjà requise par import_upcoming_matches.py).
    pip install pymysql

Configuration : le même ml-service/.env.local que les autres scripts
(LIVETENNIS_API_KEY, DATABASE_URL) — jamais commité.

Usage manuel :
    cd ml-service
    python3 update_match_results.py

Automatisation : à ajouter au cron existant (voir AUTOMATISATION.md),
après l'import des matchs à venir — l'ordre importe peu en pratique (les
deux scripts touchent des matchs à des stades différents) mais autant
garder une chronologie logique : import des nouveaux matchs à venir, puis
clôture des matchs déjà joués.
"""

import json
import sys
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
    )

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"

LIVETENNISAPI_BASE = "https://api.livetennisapi.com/api/public/v1"

# Marge de sécurité de part et d'autre de la fenêtre [plus ancien match
# encore "scheduled" en retard ; aujourd'hui] : les fuseaux horaires et les
# éventuels décalages d'horaire côté API font qu'un match joué "hier soir"
# peut techniquement apparaître daté de la veille ou du lendemain selon la
# source. Un jour de marge de chaque côté suffit très largement.
DATE_MARGIN_DAYS = 1

# Filet de sécurité : si un match "scheduled" traîne depuis plus longtemps
# que ça sans qu'on retrouve son résultat (tournoi non couvert par l'API,
# id introuvable, etc.), on ne l'inclut plus dans la fenêtre de requête pour
# ne pas faire grossir indéfiniment l'intervalle interrogé — il reste en
# base tel quel, sans erreur, simplement plus jamais retenté automatiquement
# au-delà de cette ancienneté.
MAX_LOOKBACK_DAYS = 45


# ---------------------------------------------------------------------------
# Configuration (.env.local) — identique à import_upcoming_matches.py
# ---------------------------------------------------------------------------

def load_env_local():
    path = SCRIPT_DIR / ".env.local"
    if not path.exists():
        raise SystemExit(
            f"Fichier manquant : {path}\n"
            "Crée-le avec deux lignes :\n"
            "  LIVETENNIS_API_KEY=ta_vraie_cle\n"
            "  DATABASE_URL=mysql://root:@127.0.0.1:3306/tennly\n"
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
            "Impossible de se connecter à MySQL — vérifie DATABASE_URL dans .env.local.\n"
            f"Erreur détaillée : {e}"
        )


# ---------------------------------------------------------------------------
# Lecture des matchs "scheduled" en retard
# ---------------------------------------------------------------------------

def load_pending_matches(conn):
    """Matchs encore 'scheduled' dont l'heure prévue est déjà passée, avec
    le circuit (tour) déduit du joueur A (les deux joueurs d'un même match
    sont toujours du même circuit, voir la règle anti-mélange ATP/WTA
    partout ailleurs dans ce dossier)."""
    now_utc = datetime.now(timezone.utc)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            "SELECT m.id, m.player_a_id, m.player_b_id, m.external_ref, m.scheduled_at, "
            "pa.tour AS tour "
            "FROM tennis_match m "
            "JOIN player pa ON pa.id = m.player_a_id "
            "WHERE m.status = 'scheduled' "
            "AND m.scheduled_at < %s "
            "AND m.external_ref LIKE 'livetennisapi:%%'",
            (now_utc.strftime("%Y-%m-%d %H:%M:%S"),),
        )
        rows = cur.fetchall()

    oldest_allowed = now_utc - timedelta(days=MAX_LOOKBACK_DAYS)
    kept, too_old = [], 0
    for row in rows:
        scheduled_at = row["scheduled_at"]
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at < oldest_allowed:
            too_old += 1
            continue
        api_id = row["external_ref"].split(":", 1)[1] if ":" in row["external_ref"] else None
        if not api_id:
            continue
        row["api_id"] = api_id
        kept.append(row)

    if too_old:
        print(f"  ({too_old} match(s) 'scheduled' en retard de plus de {MAX_LOOKBACK_DAYS} jours, "
              f"ignoré(s) — probablement introuvable(s) côté API, à vérifier à la main si besoin.)")
    return kept


# ---------------------------------------------------------------------------
# LiveTennisAPI — matchs terminés sur une fenêtre de dates
# ---------------------------------------------------------------------------

def fetch_completed_matches(api_key, tour, date_from, date_to):
    matches, offset, limit = [], 0, 200
    while True:
        params = {
            "status": "completed",
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


def build_score_text(m):
    """'6-7, 6-1, 6-3, 1-6, 7-6' à partir de score.games (deux tableaux
    parallèles, un par joueur, jeux gagnés par set). Repli sur score.sets
    (juste le nombre de sets gagnés par joueur, ex. '3-2') si games est
    absent/mal formé — mieux que rien plutôt qu'un score_text NULL. None si
    ni l'un ni l'autre n'est exploitable."""
    score = m.get("score") or {}
    games = score.get("games")
    if isinstance(games, list) and len(games) == 2 and isinstance(games[0], list) and isinstance(games[1], list):
        g1, g2 = games[0], games[1]
        n = min(len(g1), len(g2))
        if n > 0:
            return ", ".join(f"{g1[i]}-{g2[i]}" for i in range(n))
    sets = score.get("sets")
    if isinstance(sets, list) and len(sets) == 2:
        return f"{sets[0]}-{sets[1]}"
    return None


def resolve_status(m):
    event_status = (m.get("event_status") or "").lower()
    if "walkover" in event_status:
        return "walkover"
    return "finished"


def match_updates_for_tour(rows_by_api_id, api_matches):
    """Croise les lignes en base (indexées par id LiveTennisAPI) avec les
    matchs terminés renvoyés par l'API pour CE circuit, et prépare les
    UPDATE à appliquer. Ignore explicitement (avec un message) tout match
    dont le gagnant n'est pas clairement 1 ou 2."""
    updates, skipped = [], []
    for m in api_matches:
        api_id = str(m.get("id"))
        row = rows_by_api_id.get(api_id)
        if row is None:
            continue  # pas un des matchs qu'on attendait sur ce circuit

        winner = m.get("winner")
        if winner == 1:
            winner_id = row["player_a_id"]
        elif winner == 2:
            winner_id = row["player_b_id"]
        else:
            skipped.append((row["id"], api_id, f"winner={winner!r} inattendu"))
            continue

        updates.append({
            "id": row["id"],
            "status": resolve_status(m),
            "winner_id": winner_id,
            "score_text": build_score_text(m),
        })
    return updates, skipped


# ---------------------------------------------------------------------------
# Écriture en base — uniquement des UPDATE ciblés, jamais de DELETE/INSERT
# ---------------------------------------------------------------------------

def apply_updates(conn, updates):
    with conn.cursor() as cur:
        for u in updates:
            cur.execute(
                "UPDATE tennis_match SET status=%s, winner_id=%s, score_text=%s WHERE id=%s",
                (u["status"], u["winner_id"], u["score_text"], u["id"]),
            )


def write_log(updates, skipped):
    out = [
        f"-- Journal de l'exécution du {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "-- (déjà appliqué directement en base — ce fichier est juste une trace lisible, "
        "ne pas le réimporter.)\n\n"
    ]
    if updates:
        out.append("-- Matchs clôturés (résultat réel appliqué) :\n")
        out.extend(
            f"UPDATE tennis_match SET status={hist_sql_str(u['status'])}, "
            f"winner_id={u['winner_id']}, score_text={hist_sql_str(u['score_text'])} "
            f"WHERE id={u['id']};\n"
            for u in updates
        )
        out.append("\n")
    if skipped:
        out.append("-- Matchs trouvés côté API mais ignorés (résultat pas clairement exploitable) :\n")
        out.extend(f"-- match id={mid} (LiveTennisAPI id={api_id}) : {reason}\n" for mid, api_id, reason in skipped)
        out.append("\n")

    LOG_DIR.mkdir(exist_ok=True)
    timestamped = LOG_DIR / f"update_match_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    timestamped.write_text("".join(out), encoding="utf-8")
    return timestamped


def hist_sql_str(value):
    """Petit équivalent local de import_real_data.hist.sql_str (échappement
    SQL minimal pour le fichier de log lisible uniquement — jamais exécuté
    tel quel, voir apply_updates() qui utilise des requêtes paramétrées)."""
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main():
    env = load_env_local()
    api_key = env["LIVETENNIS_API_KEY"]
    db_kwargs = parse_database_url(env["DATABASE_URL"])

    print("1/3 — Recherche des matchs 'scheduled' dont l'heure prévue est déjà passée…")
    conn = connect_db(db_kwargs)
    try:
        pending = load_pending_matches(conn)
        if not pending:
            print("  Aucun match en attente de clôture — rien à faire.")
            return
        print(f"  {len(pending)} match(s) en attente de clôture.")

        by_tour = {"atp": {}, "wta": {}}
        oldest = {"atp": None, "wta": None}
        for row in pending:
            tour = row["tour"] if row["tour"] in by_tour else "atp"
            by_tour[tour][row["api_id"]] = row
            scheduled_at = row["scheduled_at"]
            if oldest[tour] is None or scheduled_at < oldest[tour]:
                oldest[tour] = scheduled_at

        now_utc = datetime.now(timezone.utc)
        all_updates, all_skipped = [], []

        print("2/3 — Interrogation de LiveTennisAPI (matchs terminés), ATP puis WTA…")
        for tour in ("atp", "wta"):
            rows_by_api_id = by_tour[tour]
            if not rows_by_api_id:
                continue
            date_from = (oldest[tour] - timedelta(days=DATE_MARGIN_DAYS)).strftime("%Y-%m-%d")
            date_to = (now_utc + timedelta(days=DATE_MARGIN_DAYS)).strftime("%Y-%m-%d")
            print(f"  {tour.upper()} : {len(rows_by_api_id)} match(s) attendu(s), fenêtre {date_from} -> {date_to}…")
            api_matches = fetch_completed_matches(api_key, tour, date_from, date_to)
            updates, skipped = match_updates_for_tour(rows_by_api_id, api_matches)
            print(f"    {len(api_matches)} match(s) terminé(s) renvoyé(s) par l'API sur cette fenêtre -> "
                  f"{len(updates)} correspondance(s) exploitable(s)"
                  + (f", {len(skipped)} ignoré(s)" if skipped else ""))
            all_updates.extend(updates)
            all_skipped.extend(skipped)

        if not all_updates:
            print("\nAucun résultat exploitable trouvé cette fois — les matchs en attente seront "
                  "retentés à la prochaine exécution.")
            return

        print("3/3 — Écriture en base (UPDATE ciblés uniquement)…")
        log_path = write_log(all_updates, all_skipped)
        apply_updates(conn, all_updates)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\nTerminé : {len(all_updates)} match(s) clôturé(s) avec leur résultat réel.")
    print(f"Journal de cette exécution : {log_path}")


if __name__ == "__main__":
    main()
