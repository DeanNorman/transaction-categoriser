#!/bin/sh
# Wait for the database, migrate, import the sample once (the import is idempotent, so "once" costs nothing on a
# restart), then run whatever the command is: gunicorn by default, pytest or a management command when asked.
set -e

tries=0
until python manage.py migrate --noinput >/tmp/migrate.log 2>&1; do
  tries=$((tries + 1))
  if [ "$tries" -ge 30 ]; then echo "database not ready after 30 tries"; cat /tmp/migrate.log; exit 1; fi
  echo "waiting for the database ($tries)"; sleep 2
done
cat /tmp/migrate.log

if [ -n "$SEED_CSV" ] && [ "$1" = "gunicorn" ]; then
  echo "importing $SEED_CSV (existing IDs are skipped)"
  python manage.py import_csv "$SEED_CSV"
fi

exec "$@"
