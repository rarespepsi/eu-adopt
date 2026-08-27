#!/usr/bin/env bash
# Val zilnic email Radio (spot audio) — manage.py media_outreach_daily_wave
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-media-radio-wave.log"
LOCK="/var/lock/euadopt-media-radio-wave.lock"
# 20×60s delay ≈ 20 min; buffer 35 min
TIMEOUT_SEC="${EUADOPT_MEDIA_RADIO_WAVE_TIMEOUT:-2100}"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: media radio wave deja în curs (flock)" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) media radio wave START ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    echo "=== $(date -Iseconds) media radio wave END exit=2 ==="
    exit 2
  fi
  export PYTHONUNBUFFERED=1
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=30 "${TIMEOUT_SEC}" \
      sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
      'source venv/bin/activate && python -u manage.py media_outreach_daily_wave'
    ec=$?
  else
    sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c \
      'source venv/bin/activate && python -u manage.py media_outreach_daily_wave'
    ec=$?
  fi
  if [[ "${ec}" -eq 124 ]]; then
    echo "FAIL: timeout ${TIMEOUT_SEC}s"
  elif [[ "${ec}" -ne 0 ]]; then
    echo "FAIL: exit=${ec}"
  fi
  echo "=== $(date -Iseconds) media radio wave END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
