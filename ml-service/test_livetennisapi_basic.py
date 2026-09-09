#!/usr/bin/env python3
"""
Script de TEST pour l'abonnement LiveTennisAPI Basic (9,99€/mois).

Objectif : vérifier que la clé API a bien accès aux 3 endpoints "historique"
réservés au palier Basic (archives 1968-2022, carrière, head-to-head), et
regarder à quoi ressemblent les données renvoyées — AVANT de décider
comment (ou si) on les intègre au site.

Ce script :
  - NE se connecte à AUCUNE base de données (pas d'import pymysql).
  - NE modifie AUCUNE table `player` / `tennis_match` / etc.
  - Fait seulement 3 appels HTTP en lecture, avec des filtres réduits pour
    ne pas gaspiller de quota (l'abonnement Basic est limité en requêtes).
  - Enregistre les réponses brutes dans un fichier JSON local, pour qu'on
    puisse les relire ensemble et décider de la suite.

Utilisation :
    cd ml-service
    python3 test_livetennisapi_basic.py

Prérequis : LIVETENNIS_API_KEY doit être présent dans ml-service/.env.local
(le même fichier que import_upcoming_matches.py utilise déjà).
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LIVETENNISAPI_BASE = "https://api.livetennisapi.com/api/public/v1"

# Joueur bien connu, pour limiter le volume de données renvoyées par le test
# (on ne cherche pas à être exhaustif ici, juste à valider l'accès Basic).
TEST_PLAYER_NAME = "novak djokovic"
TEST_PLAYER_1 = "novak djokovic"
TEST_PLAYER_2 = "federer"


def load_api_key():
    """Reprend exactement le même format que import_upcoming_matches.py
    (ml-service/.env.local), mais ne réclame que LIVETENNIS_API_KEY : ce
    script n'a besoin d'aucun accès base de données."""
    path = SCRIPT_DIR / ".env.local"
    if not path.exists():
        raise SystemExit(
            f"Fichier manquant : {path}\n"
            "Ce script réutilise le même ml-service/.env.local que "
            "import_upcoming_matches.py — il doit déjà exister avec ta clé "
            "LIVETENNIS_API_KEY dedans."
        )
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    api_key = values.get("LIVETENNIS_API_KEY")
    if not api_key:
        raise SystemExit(f"LIVETENNIS_API_KEY est manquant ou vide dans {path}")
    return api_key


def call_api(path, api_key, params=None):
    """Un seul appel GET, authentifié par Bearer token — même pattern que
    fetch_upcoming_matches() dans import_upcoming_matches.py."""
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"{LIVETENNISAPI_BASE}{path}{query}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    })
    print(f"  -> GET {path}{query}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(f"     OK (HTTP {resp.status})")
            return {"ok": True, "status": resp.status, "data": body}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"     ERREUR HTTP {e.code} : {detail[:300]}")
        if e.code == 401:
            print("     -> clé API invalide ou manquante.")
        elif e.code == 403:
            print("     -> ton abonnement n'a pas accès à cet endpoint (vérifie le palier Basic sur ton compte).")
        elif e.code == 429:
            print("     -> quota dépassé (limite de requêtes atteinte).")
        return {"ok": False, "status": e.code, "error": detail}
    except urllib.error.URLError as e:
        print(f"     ERREUR réseau : {e.reason}")
        return {"ok": False, "status": None, "error": str(e.reason)}


def main():
    api_key = load_api_key()
    print("=== Test LiveTennisAPI — palier Basic (lecture seule, pas de BDD) ===\n")

    results = {}

    print(f"1) Historique des matchs archivés pour '{TEST_PLAYER_NAME}' (5 max)")
    results["archive_matches"] = call_api(
        "/history/archive/matches",
        api_key,
        {"tour": "atp", "name": TEST_PLAYER_NAME, "limit": 5},
    )

    print(f"\n2) Statistiques de carrière (archive) pour '{TEST_PLAYER_NAME}'")
    results["archive_career"] = call_api(
        "/history/archive/career",
        api_key,
        {"name": TEST_PLAYER_NAME},
    )

    print(f"\n3) Head-to-head : '{TEST_PLAYER_1}' vs '{TEST_PLAYER_2}'")
    results["h2h"] = call_api(
        "/h2h",
        api_key,
        {"p1": TEST_PLAYER_1, "p2": TEST_PLAYER_2},
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = SCRIPT_DIR / "logs"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"test_livetennisapi_basic_{timestamp}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== Terminé. Résultats enregistrés dans : {out_path} ===")
    all_ok = all(r["ok"] for r in results.values())
    if all_ok:
        print("Les 3 endpoints Basic ont répondu correctement — l'abonnement fonctionne.")
    else:
        failed = [name for name, r in results.items() if not r["ok"]]
        print(f"ATTENTION : ces endpoints ont échoué : {', '.join(failed)} (voir détails ci-dessus).")
        sys.exit(1)


if __name__ == "__main__":
    main()
