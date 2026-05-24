#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

if [ "$#" -gt 0 ]; then
  echo "Starting custom process: $*"
  exec "$@"
fi

echo "Starting API server..."
exec uvicorn services.api_gateway.app.main:app --host 0.0.0.0 --port 8000
