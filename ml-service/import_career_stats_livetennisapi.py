#!/usr/bin/env python3
"""
Remplit player_career_stats avec le VRAI palmarès carrière de chaque joueur
suivi sur le site (LiveTennisAPI, palier Basic, endpoint
/history/archive/career) : victoires/défaites par surface, statistiques de
service (aces, doubles fautes, % premier/second service, % balles de break
sauvées), période couverte.

Portée : tous les joueurs actuellement dans la table `player` (les mêmes que
ceux affichés sur le site) — un appel API par joueur. Se relance sans risque
(UPSERT), par exemple après avoir ajouté de nouveaux joueurs via
import_upcoming_matches.py.

Ce script :
  - Lit la liste des joueurs depuis `player` (lecture seule).
  - N'écrit QUE dans `player_career_stats` (INSERT ... ON DUPLICATE KEY
    UPDATE).
  - Ne touche jamais `player` ni `tennis_match`.

Utilisation :
    cd ml-service
    python3 import_career_stats_livetennisapi.py

Prérequis : LIVETENNIS_API_KEY et DATABASE_URL dans ml-service/.env.local.
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
DELAY_BETWEEN_CALLS_SECONDS = 1.0


def load_env_local():
    path = SCRIPT_DIR / ".env.local"
    if not path.exists():
        raise SystemExit(f"Fichier manquant : {path}")
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


def fetch_all_players(conn):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("SELECT id, full_name FROM player ORDER BY id")
        return cur.fetchall()


def fetch_career(api_key, name):
    params = {"name": name}
    url = f"{LIVETENNISAPI_BASE}/history/archive/career?{urllib.parse.urlencode(params)}"
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


def surface_pair(by_surface, key):
    s = (by_surface or {}).get(key) or {}
    return s.get("wins"), s.get("losses")


def upsert_career_stats(conn, player_id, data):
    record = data.get("record") or {}
    by_surface = record.get("by_surface") or {}
    serve = data.get("serve") or {}
    span = data.get("span") or {}

    wins_hard, losses_hard = surface_pair(by_surface, "hard")
    wins_clay, losses_clay = surface_pair(by_surface, "clay")
    wins_grass, losses_grass = surface_pair(by_surface, "grass")
    wins_carpet, losses_carpet = surface_pair(by_surface, "carpet")

    values = (
        player_id,
        record.get("wins"), record.get("losses"), record.get("titles"),
        wins_hard, losses_hard, wins_clay, losses_clay,
        wins_grass, losses_grass, wins_carpet, losses_carpet,
        serve.get("aces"), serve.get("aces_per_match"), serve.get("double_faults"),
        serve.get("first_in_pct"), serve.get("first_won_pct"), serve.get("second_won_pct"),
        serve.get("bp_saved_pct"),
        span.get("first"), span.get("last"),
    )

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO player_career_stats (player_id, wins, losses, titles, "
            "wins_hard, losses_hard, wins_clay, losses_clay, wins_grass, losses_grass, "
            "wins_carpet, losses_carpet, aces, aces_per_match, double_faults, "
            "first_in_pct, first_won_pct, second_won_pct, bp_saved_pct, span_first, span_last, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) "
            "ON DUPLICATE KEY UPDATE "
            "wins=VALUES(wins), losses=VALUES(losses), titles=VALUES(titles), "
            "wins_hard=VALUES(wins_hard), losses_hard=VALUES(losses_hard), "
            "wins_clay=VALUES(wins_clay), losses_clay=VALUES(losses_clay), "
            "wins_grass=VALUES(wins_grass), losses_grass=VALUES(losses_grass), "
            "wins_carpet=VALUES(wins_carpet), losses_carpet=VALUES(losses_carpet), "
            "aces=VALUES(aces), aces_per_match=VALUES(aces_per_match), double_faults=VALUES(double_faults), "
            "first_in_pct=VALUES(first_in_pct), first_won_pct=VALUES(first_won_pct), "
            "second_won_pct=VALUES(second_won_pct), bp_saved_pct=VALUES(bp_saved_pct), "
            "span_first=VALUES(span_first), span_last=VALUES(span_last), updated_at=NOW()",
            values,
        )
    conn.commit()


def main():
    env = load_env_local()
    api_key = env["LIVETENNIS_API_KEY"]
    db_kwargs = parse_database_url(env["DATABASE_URL"])

    conn = pymysql.connect(**db_kwargs, charset="utf8mb4")
    try:
        players = fetch_all_players(conn)
        print(f"{len(players)} joueur(s) à traiter.\n")

        updated, failed = 0, 0
        for i, p in enumerate(players, start=1):
            print(f"[{i}/{len(players)}] {p['full_name']}")
            result = fetch_career(api_key, p["full_name"])
            if not result["ok"]:
                print(f"   ECHEC (HTTP {result['status']}) : {result['error'][:200]}")
                failed += 1
            else:
                upsert_career_stats(conn, p["id"], result["data"])
                record = result["data"].get("record") or {}
                print(f"   OK : {record.get('wins')}-{record.get('losses')}, {record.get('titles')} titre(s)")
                updated += 1

            if i < len(players):
                time.sleep(DELAY_BETWEEN_CALLS_SECONDS)

        print(f"\n=== Terminé : {updated} mis à jour, {failed} échec(s) sur {len(players)} joueur(s) ===")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
