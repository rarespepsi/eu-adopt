#!/usr/bin/env bash
# Raport zilnic invitații Add USER — ziua anterioară (manage.py staff_invite_daily_report).
# Rulează pe Hetzner (cron) — NU depinde de PC-ul local.
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-invite-report.log"
LOCK="/var/lock/euadopt-invite-report.lock"
TIMEOUT_SEC="${EUADOPT_INVITE_REPORT_TIMEOUT:-300}"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: report deja în curs (flock)" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) invite daily report START ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    echo "=== $(date -Iseconds) invite daily report END exit=2 ==="
    exit 2
  fi
  export PYTHONUNBUFFERED=1
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=20 "${TIMEOUT_SEC}" \
      sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
      'source venv/bin/activate && python -u manage.py staff_invite_daily_report'
    ec=$?
  else
    sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
      'source venv/bin/activate && python -u manage.py staff_invite_daily_report'
    ec=$?
  fi
  if [[ "${ec}" -eq 124 ]]; then
    echo "FAIL: timeout ${TIMEOUT_SEC}s"
  elif [[ "${ec}" -ne 0 ]]; then
    echo "FAIL: exit=${ec}"
  fi
  echo "=== $(date -Iseconds) invite daily report END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
