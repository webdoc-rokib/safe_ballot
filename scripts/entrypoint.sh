#!/usr/bin/env bash
set -e

# If SEED_DEMO is true, run the seed_demo management command
if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "Seeding demo data..."
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  python manage.py seed_demo
fi

# Run the passed command (default: gunicorn)
exec "$@"
