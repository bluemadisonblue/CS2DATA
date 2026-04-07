# Deploy on DigitalOcean

The bot uses **long polling** (no public HTTP URL). Run it as a **worker**: App Platform **Worker** or a **Droplet** with Docker.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `FACEIT_API_KEY` | Yes | FACEIT Data API key |
| `DB_PATH` | No | SQLite file path. Default: `./bot_data.db`. On a **Droplet + Docker Compose**, use `/data/bot_data.db` with the compose volume (see below). |

`.env` is only for local runs; on DO set variables in the dashboard or App Spec (use **SECRETS** for tokens).

## SQLite and restarts

User data, FSM, and watch state live in SQLite.

- **DigitalOcean App Platform:** There is **no persistent disk** for workers. The [platform filesystem is ephemeral](https://docs.digitalocean.com/products/app-platform/how-to/store-data/) — **the DB is reset on redeploys**. You cannot add a Block Storage volume there. For durable SQLite, use a **Droplet + Docker** (below) or move to a **managed database** (requires code changes).
- **Droplet + Docker Compose:** `docker-compose.yml` sets `DB_PATH=/data/bot_data.db` and a **named Docker volume** — data survives restarts and deploys of the container.

## Option A — Droplet + Docker Compose

1. Create a Droplet (Ubuntu 22.04+), install [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) and Docker Compose plugin.
2. Clone the repo, copy `.env.example` → `.env`, fill `BOT_TOKEN` and `FACEIT_API_KEY`.
3. Run:

   ```bash
   docker compose up -d --build
   ```

4. Logs: `docker compose logs -f`

## Option B — App Platform (Worker)

1. Push the repo to GitHub (if it is not already).
2. DigitalOcean → **Apps** → **Create App** → GitHub → select repo.
3. Set **Resource type** to **Worker** (or import **`.do/app.yaml`** and adjust `github.repo` / `branch`).
4. Set **Run command** only if you override the image; the `Dockerfile` already runs `python bot.py`.
5. Add **Environment variables** (secrets): `BOT_TOKEN`, `FACEIT_API_KEY`. Mark them as **encrypted/secret**.
6. Optional: `PYTHONUNBUFFERED=1`. You can omit `DB_PATH` (default `bot_data.db` in the app dir) — it will still be **ephemeral** on App Platform.
7. Deploy. **Only one** instance (Telegram allows one `getUpdates` session per bot).

If you need **persistent registrations**, host the bot on a **Droplet** with `docker compose` instead of App Platform.

## Local Docker (smoke test)

```bash
docker build -t cs2-faceit-bot .
docker run --rm -e BOT_TOKEN=... -e FACEIT_API_KEY=... -e DB_PATH=/data/bot_data.db -v faceit_data:/data cs2-faceit-bot
```

## Build failed (DigitalOcean: “Non-Zero Exit”)

1. Open **Activity** → failed deployment → **View build logs** and scroll to the **first red error** (often a `pip` line or `COPY` failure).
2. **Source directory:** In the worker settings, **Source directory** must be the folder that contains `bot.py`, `requirements.txt`, and (if used) `Dockerfile`. If those files live in a subfolder of the repo, set it (e.g. `cs2_faceit_bot`).
3. **Dockerfile vs Buildpack:** Prefer **Dockerfile** (this repo root has one). If you use the **Python buildpack**, set **Run command** to `python bot.py` and rely on `requirements.txt` + optional `Procfile` / `runtime.txt` in the repo.
4. **Reproduce locally:**  
   `docker build -t cs2-test .` from the same directory as the Dockerfile (should finish with no errors).

## Development tests

```bash
pip install -r requirements-dev.txt
pytest
```
