#!/bin/sh
set -e

# Only the web service (CMD gunicorn ...) runs migrate/collectstatic — celery_worker
# and celery_beat override `command:` to `celery ...` and share this same image/
# entrypoint, so without this guard all three would race to migrate the same fresh
# database concurrently and collide (seen as "relation ... already exists").
if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
