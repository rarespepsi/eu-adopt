#!/usr/bin/env bash
# Hard-delete anunțuri pierdut/găsit soft-șterse de peste 45 zile.
set -euo pipefail
APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
cd "${APP_DIR}"
# shellcheck disable=SC1091
source venv/bin/activate
exec python manage.py cleanup_lost_found_deleted --days 45
