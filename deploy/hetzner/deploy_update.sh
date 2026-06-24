#!/usr/bin/env bash
# Update standard pe Hetzner: backup DB (rotație 3) → pull → migrate → collectstatic → restart.
# Rulează pe server ca root:
#   bash /opt/eu-adopt/deploy/hetzner/deploy_update.sh

set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
BACKUP_SCRIPT="${APP_DIR}/deploy/hetzner/backup_db_rotate.sh"

echo "[$(date -Is)] === EU-Adopt deploy update ==="

if [[ -x "${BACKUP_SCRIPT}" ]] || [[ -f "${BACKUP_SCRIPT}" ]]; then
  bash "${BACKUP_SCRIPT}"
else
  echo "WARN: ${BACKUP_SCRIPT} lipsește — deploy fără backup DB."
fi

cd "${APP_DIR}"
BEFORE_SHA="$(sudo -u euadopt git rev-parse --short HEAD 2>/dev/null || echo '?')"
echo "[$(date -Is)] Git înainte: ${BEFORE_SHA}"

sudo -u euadopt bash -c '
  set -e
  source venv/bin/activate
  git pull
  pip install -q -r requirements.txt
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
'

AFTER_SHA="$(sudo -u euadopt git rev-parse --short HEAD 2>/dev/null || echo '?')"
echo "[$(date -Is)] Git după: ${AFTER_SHA}"

systemctl restart euadopt
systemctl is-active --quiet euadopt
echo "[$(date -Is)] euadopt: active"
