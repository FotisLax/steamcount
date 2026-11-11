import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

STEAM_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

pool = ThreadedConnectionPool(
    1, 10,
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=int(os.environ.get("DB_PORT", "5432")),
)

app = FastAPI(title="SteamCount API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

SEARCH_SQL = (
    "SELECT app_id, name, tracked FROM games "
    "WHERE name ILIKE %(pat)s OR name %% %(q)s "
    "ORDER BY (lower(name) = lower(%(q)s)) DESC, "
    "similarity(name, %(q)s) DESC, tracked DESC, name "
    "LIMIT 10"
)

FRESH_SQL = (
    "SELECT ts > now() - interval '10 minutes' AS fresh "
    "FROM player_counts WHERE app_id = %s ORDER BY ts DESC LIMIT 1"
)

INSERT_SQL = (
    "INSERT INTO player_counts (app_id, ts, players) "
    "VALUES (%s, date_bin('5 minutes', now(), '2000-01-01'), %s) "
    "ON CONFLICT DO NOTHING"
)

PROMOTE_SQL = (
    "UPDATE games SET tracked = true, poll_every = '5 minutes', "
    "last_polled = now() WHERE app_id = %s"
)

STATS_SQL = """
SELECT
    l.players AS current_players,
    l.ts      AS as_of,
    round((l.players - p5.players)  * 100.0 / NULLIF(p5.players, 0), 1)  AS change_5m,
    round((l.players - p60.players) * 100.0 / NULLIF(p60.players, 0), 1) AS change_1h,
    round((l.players - p1d.players) * 100.0 / NULLIF(p1d.players, 0), 1) AS change_1d
FROM (
    SELECT players, ts FROM player_counts
    WHERE app_id = %(id)s ORDER BY ts DESC LIMIT 1
) l
LEFT JOIN LATERAL (
    SELECT players FROM player_counts
    WHERE app_id = %(id)s
      AND ts <= l.ts - interval '5 minutes'
      AND ts >= l.ts - interval '7 minutes'
    ORDER BY ts DESC LIMIT 1
) p5 ON true
LEFT JOIN LATERAL (
    SELECT players FROM player_counts
    WHERE app_id = %(id)s
      AND ts <= l.ts - interval '1 hour'
      AND ts >= l.ts - interval '70 minutes'
    ORDER BY ts DESC LIMIT 1
) p60 ON true
LEFT JOIN LATERAL (
    SELECT players FROM player_counts
    WHERE app_id = %(id)s
      AND ts <= l.ts - interval '1 day'
      AND ts >= l.ts - interval '25 hours'
    ORDER BY ts DESC LIMIT 1
) p1d ON true
"""


def run(sql, params=None, fetch=None):
    conn = pool.getconn()
    try:
        conn.autocommit = True
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
    finally:
        pool.putconn(conn)


def live_count(app_id):
    try:
        r = requests.get(STEAM_URL, params={"appid": app_id}, timeout=8)
        r.raise_for_status()
        return r.json()["response"].get("player_count")
    except Exception:
        return None


def num(x):
    return float(x) if x is not None else None


@app.get("/search")
def search(q: str = Query(..., min_length=2, max_length=100)):
    cleaned = q.replace("%", "").replace("_", "").strip()
    if len(cleaned) < 2:
        return []
    return run(SEARCH_SQL, {"pat": f"%{cleaned}%", "q": cleaned}, "all")


@app.get("/game/{app_id}")
def game(app_id: int):
    g = run("SELECT app_id, name FROM games WHERE app_id = %s", (app_id,), "one")
    if not g:
        raise HTTPException(404, "Unknown game")

    row = run(FRESH_SQL, (app_id,), "one")
    if row is None or not row["fresh"]:
        players = live_count(app_id)
        if players is not None:
            run(INSERT_SQL, (app_id, players))
            run(PROMOTE_SQL, (app_id,))
        elif row is None:
            raise HTTPException(502, "Steam did not return a player count")

    s = run(STATS_SQL, {"id": app_id}, "one")
    if s is None:
        raise HTTPException(502, "No data available yet")

    changes = {"5m": num(s["change_5m"]), "1h": num(s["change_1h"]), "1d": num(s["change_1d"])}
    note = None
    if all(v is None for v in changes.values()):
        note = "Tracking just started. Changes appear after 5 minutes, 1 hour and 1 day of data."

    return {
        "app_id": g["app_id"],
        "name": g["name"],
        "current_players": s["current_players"],
        "as_of": s["as_of"],
        "change_pct": changes,
        "note": note,
    }