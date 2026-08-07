#!/usr/bin/env bash
# Val zilnic invitații Add USER (manage.py staff_invite_daily_wave).
# Rulează pe Hetzner (cron) — NU depinde de PC-ul local.
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-invite-wave.log"
LOCK="/var/lock/euadopt-invite-wave.lock"
# Max 15 min — evită procese blocate pe SMTP fără log
TIMEOUT_SEC="${EUADOPT_INVITE_WAVE_TIMEOUT:-900}"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: wave deja în curs (flock)" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) invite daily wave START ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    echo "=== $(date -Iseconds) invite daily wave END exit=2 ==="
    exit 2
  fi
  export PYTHONUNBUFFERED=1
  # timeout: dacă lipsește, rulează fără (rare pe Ubuntu)
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=30 "${TIMEOUT_SEC}" \
      sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
      'source venv/bin/activate && python -u manage.py staff_invite_daily_wave'
    ec=$?
  else
    sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
      'source venv/bin/activate && python -u manage.py staff_invite_daily_wave'
    ec=$?
  fi
  if [[ "${ec}" -eq 124 ]]; then
    echo "FAIL: timeout ${TIMEOUT_SEC}s (SMTP/blocaj)"
  elif [[ "${ec}" -ne 0 ]]; then
    echo "FAIL: exit=${ec}"
  fi
  echo "=== $(date -Iseconds) invite daily wave END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
