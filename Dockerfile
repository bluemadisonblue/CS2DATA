# CS2 FACEIT Telegram bot — polling worker (no HTTP port)
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Reliable HTTPS for pip on some build hosts
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite + FSM: use DB_PATH=/data/bot_data.db with a mounted volume in production
RUN mkdir -p /data

CMD ["python", "bot.py"]
