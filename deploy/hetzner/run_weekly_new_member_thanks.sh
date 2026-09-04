#!/usr/bin/env bash
# Trimite mail mulțumire membri noi (manage.py weekly_new_member_thanks).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-weekly-thanks.log"
LOCK="/var/lock/euadopt-weekly-thanks.lock"
ENV_FILE="${APP_DIR}/.env"

mkdir -p "$(dirname "${LOG}")" "$(dirname "${LOCK}")"
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: weekly thanks deja în curs (flock)" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) weekly new-member thanks START ==="
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}" || true
    set +a
  fi
  if [[ "${EUADOPT_WEEKLY_THANKS_CRON_ENABLED:-1}" != "1" ]]; then
    echo "SKIP: EUADOPT_WEEKLY_THANKS_CRON_ENABLED!=1"
    echo "=== $(date -Iseconds) weekly thanks END exit=2 ==="
    exit 2
  fi
  sudo -u euadopt bash -lc \
    "cd '${APP_DIR}' && source venv/bin/activate && python -u manage.py weekly_new_member_thanks"
  ec=$?
  echo "=== $(date -Iseconds) weekly thanks END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
