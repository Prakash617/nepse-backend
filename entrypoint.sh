#!/usr/bin/env bash
set -e

# Wait for PostgreSQL
if [ -n "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
        sleep 0.5
    done
    echo "PostgreSQL is ready!"
fi

if [ "$1" = "web" ]; then
    echo "Running database migrations..."
    python manage.py migrate --no-input

    echo "Collecting static files..."
    python manage.py collectstatic --no-input

    echo "Ensuring demo user exists..."
    python manage.py create_demo_user || true

    echo "Starting Daphne ASGI server on 0.0.0.0:8000..."
    exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
fi

exec "$@"
