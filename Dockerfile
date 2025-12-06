FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r campbot && useradd -r -g campbot campbot

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src/alembic.ini ./alembic.ini
COPY src/alembic ./alembic

COPY . .

RUN mkdir -p /app/data /app/logs \
    && chown -R campbot:campbot /app

USER campbot

ENV CAMPBOT_SERVER__RELOAD=false \
    CAMPBOT_SERVER__LOG_LEVEL=info

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["sh", "-c", "python -m src.migrate && python -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000"]
