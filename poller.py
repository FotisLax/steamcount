import os
import time
import requests
import psycopg2

RUN_ONCE = os.environ.get("RUN_ONCE", "false").lower() == "true"
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "300"))

URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

SELECT_SQL = (
    "SELECT app_id FROM games "
    "WHERE tracked "
    "AND (last_polled IS NULL "
    "OR last_polled + poll_every - interval '1 minute' <= now()) "
    "ORDER BY last_polled NULLS FIRST LIMIT 1000"
)

INSERT_SQL = (
    "INSERT INTO player_counts (app_id, ts, players) "
    "VALUES (%s, date_bin('5 minutes', now(), '2000-01-01'), %s) "
    "ON CONFLICT DO NOTHING"
)

TOUCH_SQL = "UPDATE games SET last_polled = now() WHERE app_id = %s"
ERROR_SQL = "INSERT INTO poll_errors (app_id, error) VALUES (%s, %s)"


def connect():
    while True:
        try:
            conn = psycopg2.connect(
                dbname=os.environ["DB_NAME"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"],
                host=os.environ["DB_HOST"],
                port=int(os.environ.get("DB_PORT", "5432")),
            )
            conn.autocommit = True
            return conn
        except psycopg2.OperationalError as e:
            print(f"DB not ready, retrying in 5s: {e}")
            time.sleep(5)


def poll_once(conn):
    with conn.cursor() as cur:
        cur.execute(SELECT_SQL)
        app_ids = [row[0] for row in cur.fetchall()]

        for app_id in app_ids:
            try:
                r = requests.get(URL, params={"appid": app_id}, timeout=10)
                r.raise_for_status()
                players = r.json()["response"].get("player_count")
                if players is None:
                    raise ValueError(f"no player_count in response for app_id {app_id}")
                cur.execute(INSERT_SQL, (app_id, players))
            except Exception as e:
                cur.execute(ERROR_SQL, (app_id, str(e)[:500]))
            cur.execute(TOUCH_SQL, (app_id,))
            time.sleep(0.1)
    return len(app_ids)


if __name__ == "__main__":
    conn = connect()
    if RUN_ONCE:
        print(f"done, polled {poll_once(conn)} games")
    else:
        while True:
            started = time.time()
            try:
                n = poll_once(conn)
                print(f"pass complete, polled {n} games", flush=True)
            except psycopg2.Error as e:
                print(f"DB error, reconnecting: {e}", flush=True)
                conn = connect()
            time.sleep(max(0, POLL_INTERVAL - (time.time() - started)))