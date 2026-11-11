import os
import requests
import psycopg2

URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
KEY = os.environ["STEAM_API_KEY"]

conn = psycopg2.connect(
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
)
conn.autocommit = True

UPSERT_SQL = (
    "INSERT INTO games (app_id, name, tracked) VALUES (%s, %s, false) "
    "ON CONFLICT (app_id) DO UPDATE SET name = EXCLUDED.name"
)

last_appid = 0
total = 0
with conn.cursor() as cur:
    while True:
        r = requests.get(
            URL,
            params={"key": KEY, "max_results": 50000, "last_appid": last_appid},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()["response"]
        apps = data.get("apps", [])
        for a in apps:
            if a.get("name"):
                cur.execute(UPSERT_SQL, (a["appid"], a["name"]))
        total += len(apps)
        print(f"loaded {total}", flush=True)
        if not data.get("have_more_results"):
            break
        last_appid = data["last_appid"]
print("done")