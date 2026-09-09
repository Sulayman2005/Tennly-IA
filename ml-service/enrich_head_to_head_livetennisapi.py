#!/usr/bin/env python3
"""
Enrichit player_head_to_head avec les VRAIS face-à-face historiques
(LiveTennisAPI, palier Basic, endpoint /h2h) pour tous les matchs
actuellement programmés ("scheduled") sur le site.

Pourquoi ce script et pas un import massif de tous les matchs archivés :
notre historique local (table tennis_match) ne compte qu'une trentaine de
matchs réels — beaucoup trop peu pour que le face-à-face calculé en interne
(compute_head_to_head_pairs dans import_upcoming_matches.py) reflète la
réalité. La table player_head_to_head alimente directement l'axe "H2H" du
radar de prédiction ET le comparateur de joueurs (voir
backend/src/Service/PlayerComparisonService.php) — la remplir avec les
vraies données LiveTennisAPI améliore donc directement ce que voient les
utilisateurs, sans les risques d'un import massif de matchs (doublons
possibles avec les matchs déjà importés depuis Tennismylife, gonflement de
la table player avec des adversaires historiques jamais revus).

Portée volontairement réduite : seulement les paires de joueurs qui
s'affrontent dans un match ACTUELLEMENT programmé (statut 'scheduled') —
c'est le seul moment où le H2H est réellement utilisé par le site. Se
relance sans risque à chaque fois que le calendrier des matchs à venir
change (par exemple juste après import_upcoming_matches.py).

Ce script :
  - Lit les paires depuis `tennis_match` (lecture seule sur cette table).
  - N'écrit QUE dans `player_head_to_head` (INSERT ... ON DUPLICATE KEY
    UPDATE, comme le fait déjà apply_snapshots_to_database() dans
    import_upcoming_matches.py).
  - Ne touche jamais `player` ni `tennis_match`.

Utilisation :
    cd ml-service
    python3 enrich_head_to_head_livetennisapi.py

Prérequis : LIVETENNIS_API_KEY et DATABASE_URL dans ml-service/.env.local
(le même fichier qu'utilisent déjà les autres scripts de ce dossier).
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import pymysql
except ImportError:
    sys.exit(
        "Le module 'pymysql' n'est pas installé. Lance : pip install pymysql "
        "(ou pip3 install pymysql --break-system-packages selon ton environnement)."
    )

SCRIPT_DIR = Path(__file__).resolve().parent
LIVETENNISAPI_BASE = "https://api.livetennisapi.com/api/public/v1"
DELAY_BETWEEN_CALLS_SECONDS = 1.0  # marge confortable sous la limite de débit du palier Basic


def load_env_local():
    """Même format que les autres scripts de ce dossier (voir
    import_upcoming_matches.py::load_env_local)."""
    path = SCRIPT_DIR / ".env.local"
    if not path.exists():
        raise SystemExit(
            f"Fichier manquant : {path}\n"
            "Doit déjà exister (utilisé par import_upcoming_matches.py) avec "
            "LIVETENNIS_API_KEY et DATABASE_URL."
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


def fetch_scheduled_pairs(conn):
    """Toutes les paires DISTINCTES de joueurs qui s'affrontent dans un match
    actuellement programmé — c'est là, et uniquement là, que le H2H compte."""
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            "SELECT DISTINCT m.player_a_id, pa.full_name AS name_a, "
            "m.player_b_id, pb.full_name AS name_b "
            "FROM tennis_match m "
            "JOIN player pa ON pa.id = m.player_a_id "
            "JOIN player pb ON pb.id = m.player_b_id "
            "WHERE m.status = 'scheduled'"
        )
        return cur.fetchall()


def fetch_h2h(api_key, name_a, name_b):
    params = {"p1": name_a, "p2": name_b}
    url = f"{LIVETENNISAPI_BASE}/h2h?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; TennlyIA/1.0)",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "data": payload}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": e.code, "error": detail}
    except urllib.error.URLError as e:
        return {"ok": False, "status": None, "error": str(e.reason)}


def upsert_h2h(conn, player_a_id, wins_a, player_b_id, wins_b):
    """player_head_to_head a pour clé primaire (player_low_id, player_high_id)
    — même convention que compute_head_to_head_pairs() dans
    import_upcoming_matches.py : le plus petit id en premier."""
    if player_a_id < player_b_id:
        low_id, wins_low, high_id, wins_high = player_a_id, wins_a, player_b_id, wins_b
    else:
        low_id, wins_low, high_id, wins_high = player_b_id, wins_b, player_a_id, wins_a

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO player_head_to_head (player_low_id, player_high_id, wins_low, wins_high, updated_at) "
            "VALUES (%s, %s, %s, %s, NOW()) "
            "ON DUPLICATE KEY UPDATE wins_low=VALUES(wins_low), wins_high=VALUES(wins_high), updated_at=NOW()",
            (low_id, high_id, wins_low, wins_high),
        )
    conn.commit()


def main():
    env = load_env_local()
    api_key = env["LIVETENNIS_API_KEY"]
    db_kwargs = parse_database_url(env["DATABASE_URL"])

    conn = pymysql.connect(**db_kwargs, charset="utf8mb4")
    try:
        pairs = fetch_scheduled_pairs(conn)
        print(f"{len(pairs)} paire(s) de joueurs à traiter (matchs actuellement programmés).\n")

        updated, skipped, failed = 0, 0, 0
        for i, p in enumerate(pairs, start=1):
            name_a, name_b = p["name_a"], p["name_b"]
            print(f"[{i}/{len(pairs)}] {name_a} vs {name_b}")

            result = fetch_h2h(api_key, name_a, name_b)
            if not result["ok"]:
                print(f"   ECHEC (HTTP {result['status']}) : {result['error'][:200]}")
                failed += 1
            else:
                totals = result["data"].get("totals") or {}
                wins_a = totals.get("p1_wins")
                wins_b = totals.get("p2_wins")
                if wins_a is None or wins_b is None:
                    print("   Pas de donnée H2H exploitable dans la réponse, ignoré.")
                    skipped += 1
                else:
                    upsert_h2h(conn, p["player_a_id"], wins_a, p["player_b_id"], wins_b)
                    print(f"   OK : {wins_a}-{wins_b} ({totals.get('meetings', wins_a + wins_b)} confrontation(s) au total)")
                    updated += 1

            if i < len(pairs):
                time.sleep(DELAY_BETWEEN_CALLS_SECONDS)

        print(f"\n=== Terminé : {updated} mis à jour, {skipped} ignoré(s), {failed} échec(s) sur {len(pairs)} paire(s) ===")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
