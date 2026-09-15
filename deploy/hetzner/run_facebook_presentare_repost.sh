#!/usr/bin/env bash
# Redistribuire video prezentare FB RO (luni / miercuri).
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-facebook-presentare.log"
LOCK="/var/lock/euadopt-facebook-presentare.lock"
WHICH="${1:-auto}"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: presentare repost deja în curs" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) facebook_presentare_repost which=${WHICH} START ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    echo "=== $(date -Iseconds) END exit=2 ==="
    exit 2
  fi
  export PYTHONUNBUFFERED=1
  sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
    "source venv/bin/activate && python -u manage.py facebook_presentare_repost --which ${WHICH}"
  ec=$?
  if [[ "${ec}" -ne 0 ]]; then
    echo "FAIL: exit=${ec}"
  fi
  echo "=== $(date -Iseconds) facebook_presentare_repost END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
