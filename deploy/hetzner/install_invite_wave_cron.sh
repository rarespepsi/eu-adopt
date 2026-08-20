#!/usr/bin/env bash
# Cron invitații Add USER — 4×25 / zi, Europe/Bucharest:
# 09:00, 11:00, 13:00, 15:00 (anti-blocaj Zoho + pauză SMTP din .env).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT_AM="${APP_DIR}/deploy/hetzner/run_invite_daily_wave.sh"
SCRIPT_PM="${APP_DIR}/deploy/hetzner/run_invite_daily_wave_pm.sh"
SCRIPT_SCHED="${APP_DIR}/deploy/hetzner/run_invite_daily_wave_at_ro_hour.sh"
ENV_FILE="${APP_DIR}/.env"

chmod +x "${SCRIPT_AM}" "${SCRIPT_PM}" "${SCRIPT_SCHED}" 2>/dev/null || true
touch /var/log/euadopt-invite-wave.log
chmod 644 /var/log/euadopt-invite-wave.log

_set_env() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s/^${key}=.*/${key}=${val}/" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

if [[ -f "${ENV_FILE}" ]]; then
  _set_env 'EUADOPT_STAFF_INVITE_CRON_ENABLED' '1'
  _set_env 'EUADOPT_STAFF_INVITE_MAX_PER_DAY' '100'
  _set_env 'EUADOPT_STAFF_INVITE_CRON_WAVE_SIZE' '25'
  _set_env 'EUADOPT_STAFF_INVITE_CRON_PM_WAVE_SIZE' '25'
  _set_env 'EUADOPT_STAFF_INVITE_SEND_DELAY_SEC' '60'
  _set_env 'EUADOPT_STAFF_INVITE_CRON_UAT_ONLY' '1'
  _set_env 'EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES' 'cabinet,magazin,grooming'
  # 25 mailuri × 60s ≈ 24 min + overhead
  _set_env 'EUADOPT_INVITE_WAVE_TIMEOUT' '2100'
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

# Server H = UTC; verificăm ora RO în script. Toate pe slot morning (= UAT când UAT_ONLY=1).
CRON_H9='0 * * * * bash '"${SCRIPT_SCHED}"' 9 am'
CRON_H11='0 * * * * bash '"${SCRIPT_SCHED}"' 11 am'
CRON_H13='0 * * * * bash '"${SCRIPT_SCHED}"' 13 am'
CRON_H15='0 * * * * bash '"${SCRIPT_SCHED}"' 15 am'

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_invite_daily_wave.sh' \
  | grep -v 'run_invite_daily_wave_pm.sh' \
  | grep -v 'run_invite_daily_wave_at_ro_hour.sh' \
  > "${TMP}" || true
echo "${CRON_H9}" >> "${TMP}"
echo "${CRON_H11}" >> "${TMP}"
echo "${CRON_H13}" >> "${TMP}"
echo "${CRON_H15}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron invitații instalat (09/11/13/15 Europe/Bucharest, wave 25, delay 60s):"
crontab -l | grep -E 'run_invite_daily_wave' || true
echo "Log: /var/log/euadopt-invite-wave.log"
