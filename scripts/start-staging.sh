#!/usr/bin/env bash
set -euo pipefail
python staging.py
exec gunicorn --workers 2 --threads 4 --bind "0.0.0.0:${PORT:?}" \
  --access-logfile - --access-logformat 'method=%(m)s status=%(s)s duration_us=%(D)s' \
  --error-logfile - app:app
