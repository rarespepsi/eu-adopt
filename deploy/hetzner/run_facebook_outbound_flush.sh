#!/usr/bin/env bash
# Flush coadă postări Facebook (manage.py facebook_outbound_flush).
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-facebook-outbound.log"
LOCK="/var/lock/euadopt-facebook-outbound.lock"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: facebook flush deja în curs" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) facebook_outbound_flush START ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    echo "=== $(date -Iseconds) facebook_outbound_flush END exit=2 ==="
    exit 2
  fi
  export PYTHONUNBUFFERED=1
  sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
    'source venv/bin/activate && python -u manage.py facebook_outbound_flush'
  ec=$?
  if [[ "${ec}" -ne 0 ]]; then
    echo "FAIL: exit=${ec}"
  fi
  echo "=== $(date -Iseconds) facebook_outbound_flush END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
