#!/usr/bin/env python3
"""
Remplit player.photo_url avec la photo officielle de chaque joueur suivi sur
le site, quand elle existe sous licence libre sur Wikipedia/Wikimedia
Commons (voir Player::$photoUrl côté backend, dont le commentaire précisait
déjà "une fois les droits obtenus" — Wikipedia impose une licence libre pour
toute image d'infobox d'une personne vivante, donc une image trouvée ici est
utilisable légalement, contrairement à une photo de presse quelconque
récupérée au hasard sur le web).

Démarche pour chaque joueur, en deux temps :
  1. Recherche Wikipedia (action=query&list=search) sur "<nom> tennis" pour
     retrouver le bon titre de page, y compris quand le nom seul est ambigu
     (ex. un homonyme non-sportif).
  2. Résumé REST de cette page (extraits + thumbnail) pour en extraire la
     photo — on vérifie que l'extrait mentionne bien "tennis" avant de
     retenir quoi que ce soit, pour ne jamais accrocher la photo d'un
     homonyme sans rapport.

Portée : tous les joueurs actuellement dans la table `player` (les mêmes que
ceux affichés sur le site). Se relance sans risque (idempotent, ne touche
que photo_url) — utile après l'ajout de nouveaux joueurs via
import_upcoming_matches.py. Un joueur pour qui aucune photo fiable n'est
trouvée garde photo_url à NULL : le frontend affiche alors l'avatar
générique (initiales + dégradé), jamais une image inventée.

Ce script :
  - Lit la liste des joueurs depuis `player` (lecture seule, sauf photo_url).
  - N'écrit QUE la colonne `player.photo_url`.
  - Ne touche jamais les autres colonnes de `player`, ni `tennis_match`.

Utilisation :
    cd ml-service
    python3 import_player_photos_wikipedia.py

Prérequis : DATABASE_URL dans ml-service/.env.local (pas de clé API : les
API Wikipedia/Wikimedia publiques ne demandent pas d'authentification), et
la migration Version20260909140000 appliquée (player.photo_url élargi à
VARCHAR(500) — les URLs Wikimedia dépassent souvent 255 caractères).
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
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_REST_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"
DELAY_BETWEEN_CALLS_SECONDS = 0.6
USER_AGENT = "Mozilla/5.0 (compatible; TennlyIA/1.0; +https://tennly.fr)"


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
    if not values.get("DATABASE_URL"):
        raise SystemExit(f"Il manque DATABASE_URL dans {path}")
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


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_wikipedia_title(name):
    """Titre de la page Wikipedia la plus probable pour ce joueur, ou None."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{name} tennis",
        "srlimit": "1",
        "format": "json",
    }
    url = f"{WIKI_API}?{urllib.parse.urlencode(params)}"
    data = http_get_json(url)
    results = (data.get("query") or {}).get("search") or []
    if not results:
        return None
    return results[0].get("title")


def fetch_summary(title):
    url = f"{WIKI_REST_SUMMARY}/{urllib.parse.quote(title.replace(' ', '_'))}"
    return http_get_json(url)


# player.photo_url est VARCHAR(500) (voir migration Version20260909140000,
# initialement 255 — trop court, incident réel en prod sur "Ben Shelton").
# Marge de sécurité malgré l'élargissement de colonne et le nettoyage des
# paramètres de tracking ci-dessous (clean_thumbnail_url) : coupe plutôt que
# de laisser l'UPDATE échouer une deuxième fois pour un nom encore plus long.
PHOTO_URL_MAX_LENGTH = 500


def clean_thumbnail_url(source):
    """
    Retire les paramètres de tracking Wikimedia (?utm_source=...&utm_campaign=
    api&utm_content=thumbnail) : inutiles pour charger l'image, mais à eux
    seuls ~70 caractères qui ont fait dépasser l'ancienne colonne VARCHAR(255)
    sur les noms les plus longs (voir Version20260909140000).
    """
    parts = urllib.parse.urlsplit(source)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def fetch_player_photo(name):
    """
    Retourne (photo_url, raison_echec). photo_url est None si rien de fiable
    n'a été trouvé — jamais une exception pour ce cas normal (joueur sans
    page Wikipedia, ou page sans photo), seules les vraies pannes réseau/API
    remontent une exception à l'appelant.
    """
    title = find_wikipedia_title(name)
    if not title:
        return None, "aucune page Wikipedia trouvée"

    summary = fetch_summary(title)

    if summary.get("type") == "disambiguation":
        return None, "page d'homonymie, non résolue"

    extract = (summary.get("extract") or "").lower()
    description = (summary.get("description") or "").lower()
    if "tennis" not in extract and "tennis" not in description:
        return None, f"page trouvée ({title}) mais ne semble pas être le/la joueur·se de tennis"

    thumbnail = summary.get("thumbnail") or {}
    source = thumbnail.get("source")
    if not source:
        return None, f"page trouvée ({title}) mais sans photo"

    source = clean_thumbnail_url(source)
    if len(source) > PHOTO_URL_MAX_LENGTH:
        return None, f"page trouvée ({title}) mais URL de photo trop longue ({len(source)} caractères)"

    return source, None


def update_photo_url(conn, player_id, photo_url):
    with conn.cursor() as cur:
        cur.execute("UPDATE player SET photo_url = %s WHERE id = %s", (photo_url, player_id))
    conn.commit()


def main():
    env = load_env_local()
    db_kwargs = parse_database_url(env["DATABASE_URL"])

    conn = pymysql.connect(**db_kwargs, charset="utf8mb4")
    try:
        players = fetch_all_players(conn)
        print(f"{len(players)} joueur(s) à traiter.\n")

        found, not_found, errors = 0, 0, 0
        for i, p in enumerate(players, start=1):
            print(f"[{i}/{len(players)}] {p['full_name']}", end=" ")
            try:
                photo_url, reason = fetch_player_photo(p["full_name"])
                if photo_url:
                    update_photo_url(conn, p["id"], photo_url)
                    print(f"OK : {photo_url}")
                    found += 1
                else:
                    print(f"— {reason}")
                    not_found += 1
            except urllib.error.HTTPError as e:
                print(f"ERREUR (HTTP {e.code})")
                errors += 1
            except urllib.error.URLError as e:
                print(f"ERREUR ({e.reason})")
                errors += 1
            except Exception as e:
                # Filet de sécurité : une erreur inattendue pour CE joueur
                # précis (colonne encore trop courte malgré la marge,
                # connexion DB momentanément coupée, JSON inattendu...) ne
                # doit jamais interrompre tout le lot — voir l'incident du
                # 09/09/2026 où une seule DataError (Ben Shelton, joueur 5
                # sur 56) a arrêté le script avant les 51 joueurs suivants.
                print(f"ERREUR inattendue ({e})")
                errors += 1

            if i < len(players):
                time.sleep(DELAY_BETWEEN_CALLS_SECONDS)

        print(
            f"\n=== Terminé : {found} photo(s) trouvée(s), {not_found} sans photo fiable, "
            f"{errors} erreur(s) sur {len(players)} joueur(s) ==="
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
