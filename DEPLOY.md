# Deploy notes: SQLite persistence and backups

## Docker Compose (recommended for a VPS)

The bundled `docker-compose.yml` stores the database on a **named volume** so it survives container rebuilds and image updates:

- **Volume:** `faceit_bot_data` → mounted at `/data` in the container  
- **Database file:** `DB_PATH=/data/bot_data.db`

Do not remove the volume unless you intend to wipe user data.

### Backup the database

**1. Copy the file out of a running container**

```bash
docker compose cp bot:/data/bot_data.db ./bot_data.backup.db
```

**2. Copy from the volume (one-off container)**

```bash
docker run --rm -v cs2_faceit_bot_faceit_bot_data:/data -v "$(pwd)":/backup alpine \
  cp /data/bot_data.db /backup/bot_data.backup.db
```

Adjust the volume name if your Compose project name differs (`docker volume ls`).

**3. SQLite online backup (consistent snapshot)**

```bash
docker compose exec bot sh -c 'sqlite3 /data/bot_data.db ".backup /data/bot_data.backup.db"'
docker compose cp bot:/data/bot_data.backup.db ./bot_data.backup.db
```

Restore by stopping the bot, replacing `/data/bot_data.db` with your backup (or copying the backup file over it), then starting again.

### Observability

- **Request logs:** logger `bot.requests` — one line per update with `kind`, `user_id`, and command/callback/query snippet. Disable with `LOG_UPDATES=0` if logs are too noisy.
- **Errors:** set `SENTRY_DSN` to send uncaught handler exceptions to Sentry. Optional: `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` (0–1, default `0`).
