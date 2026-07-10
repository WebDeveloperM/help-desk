#!/bin/sh
set -e
cd /app
echo "Running database migrations..."
python -m alembic upgrade head
echo "Starting application..."
exec "$@"
