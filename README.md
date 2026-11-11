# SteamCount

I needed a way to quickly check current steam players on a game before I buy it, especially a multiplayer one.
So i created this extension that collects Steam player counts into PostgreSQL and serves them through a small API
(for a browser extension that shows current players and 5 min / 1 hour / 1 day change). Bon appetite!


## For those who want to run it locally:
1. Copy `.env.example` to `.env` and fill in the values.
2. `docker compose up -d --build`
3. Load the game catalog: `docker compose run --rm poller python load_apps.py`
4. API docs: http://localhost:8000/docs

## For those who just want the browser extension:
Its coming!!