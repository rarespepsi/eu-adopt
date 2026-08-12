#!/usr/bin/env bash
# Update standard pe Hetzner: backup DB (rotație 3) → pull → migrate → collectstatic → restart
# → smoke post-deploy → mark EXPECTED_RELEASE (sau rollback la PREV dacă smoke eșuează).
# Rulează pe server ca root:
#   bash /opt/eu-adopt/deploy/hetzner/deploy_update.sh

set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
BACKUP_SCRIPT="${APP_DIR}/deploy/hetzner/backup_db_rotate.sh"
STATE_DIR="${EUADOPT_STATE_DIR:-/var/lib/euadopt}"
EXPECTED="${EUADOPT_EXPECTED_RELEASE:-${STATE_DIR}/EXPECTED_RELEASE.txt}"
PY="${APP_DIR}/deploy/hetzner/site_healthcheck.py"

echo "[$(date -Is)] === EU-Adopt deploy update ==="

if [[ -x "${BACKUP_SCRIPT}" ]] || [[ -f "${BACKUP_SCRIPT}" ]]; then
  bash "${BACKUP_SCRIPT}"
else
  echo "WARN: ${BACKUP_SCRIPT} lipsește — deploy fără backup DB."
fi

mkdir -p "${STATE_DIR}"
PREV_GOOD=""
if [[ -f "${EXPECTED}" ]]; then
  PREV_GOOD="$(grep -E '^SHA=' "${EXPECTED}" | head -1 | cut -d= -f2- | tr -d '\r' || true)"
fi

cd "${APP_DIR}"
BEFORE_SHA="$(sudo -u euadopt git rev-parse --short HEAD 2>/dev/null || echo '?')"
echo "[$(date -Is)] Git înainte: ${BEFORE_SHA}"

sudo -u euadopt bash -c '
  set -e
  source venv/bin/activate
  git fetch origin
  git checkout -B main --track origin/main 2>/dev/null || git checkout main || git checkout -B main
  git reset --hard origin/main
  pip install -q -r requirements.txt
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
'

AFTER_SHA="$(sudo -u euadopt git rev-parse --short HEAD 2>/dev/null || echo '?')"
AFTER_FULL="$(sudo -u euadopt git rev-parse HEAD 2>/dev/null || echo '')"
echo "[$(date -Is)] Git după: ${AFTER_SHA}"

systemctl restart euadopt
sleep 2
systemctl is-active --quiet euadopt
echo "[$(date -Is)] euadopt: active"

echo "[$(date -Is)] Post-deploy smoke + Maps…"
export EUADOPT_APP_DIR="${APP_DIR}"
export EUADOPT_EXPECTED_RELEASE="${EXPECTED}"
export EUADOPT_HEALTHCHECK_LAST_JSON="${STATE_DIR}/last_healthcheck.json"
export EUADOPT_HEALTHCHECK_BASE_URL="${EUADOPT_HEALTHCHECK_BASE_URL:-https://eu-adopt.ro}"

if sudo -u euadopt env \
  EUADOPT_APP_DIR="${APP_DIR}" \
  EUADOPT_EXPECTED_RELEASE="${EXPECTED}" \
  EUADOPT_HEALTHCHECK_LAST_JSON="${STATE_DIR}/last_healthcheck.json" \
  EUADOPT_HEALTHCHECK_BASE_URL="${EUADOPT_HEALTHCHECK_BASE_URL:-https://eu-adopt.ro}" \
  bash -lc "cd '${APP_DIR}' && source venv/bin/activate && python '${PY}' smoke"
then
  bash "${APP_DIR}/deploy/hetzner/mark_expected_release.sh" "deploy_update ${AFTER_SHA}"
  echo "[$(date -Is)] EXPECTED_RELEASE = ${AFTER_SHA} (smoke OK)"
else
  echo "[$(date -Is)] FAIL post-deploy smoke — rollback la PREV_GOOD=${PREV_GOOD:-none}"
  if [[ -n "${PREV_GOOD}" ]]; then
    sudo -u euadopt bash -lc "
      set -e
      cd '${APP_DIR}'
      git fetch --quiet origin || true
      git checkout -B main --track origin/main 2>/dev/null || git checkout -B main
      git reset --hard '${PREV_GOOD}'
      source venv/bin/activate
      python manage.py collectstatic --noinput
    "
    systemctl restart euadopt
    sleep 2
    systemctl is-active --quiet euadopt
    echo "[$(date -Is)] Rollback post-deploy done → $(sudo -u euadopt git rev-parse --short HEAD)"
  fi
  exit 1
fi

echo "[$(date -Is)] === Deploy update DONE ==="
