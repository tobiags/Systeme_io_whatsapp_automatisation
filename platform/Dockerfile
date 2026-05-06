FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy alembic "psycopg[binary]" \
    redis celery pydantic-settings httpx

COPY . .

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
