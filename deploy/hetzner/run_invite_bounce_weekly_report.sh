#!/usr/bin/env bash
# Raport săptămânal bounce invitații (Luni 09:15 Europe/Bucharest).
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-invite-bounce-report.log"
LOCK="/var/lock/euadopt-invite-bounce-report.lock"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: bounce weekly report deja în curs" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) bounce weekly report START ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    exit 2
  fi
  sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
    'source venv/bin/activate && python -u manage.py staff_invite_bounce_weekly_report --days 7'
  ec=$?
  echo "=== $(date -Iseconds) bounce weekly report END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
