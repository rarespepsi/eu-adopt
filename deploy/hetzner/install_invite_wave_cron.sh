#!/usr/bin/env bash
# Cron invitații Add USER:
# - 10:00 Europe/Bucharest — val 1 (UAT sau adăpost, după .env)
# - 13:00 Europe/Bucharest — val 2
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT_AM="${APP_DIR}/deploy/hetzner/run_invite_daily_wave.sh"
SCRIPT_PM="${APP_DIR}/deploy/hetzner/run_invite_daily_wave_pm.sh"
SCRIPT_SCHED="${APP_DIR}/deploy/hetzner/run_invite_daily_wave_at_ro_hour.sh"
ENV_FILE="${APP_DIR}/.env"

chmod +x "${SCRIPT_AM}" "${SCRIPT_PM}" "${SCRIPT_SCHED}" 2>/dev/null || true
touch /var/log/euadopt-invite-wave.log
chmod 644 /var/log/euadopt-invite-wave.log

if [[ -f "${ENV_FILE}" ]]; then
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_ENABLED=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_ENABLED=.*/EUADOPT_STAFF_INVITE_CRON_ENABLED=1/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_ENABLED=1' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_MAX_PER_DAY=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_MAX_PER_DAY=.*/EUADOPT_STAFF_INVITE_MAX_PER_DAY=100/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_MAX_PER_DAY=100' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_WAVE_SIZE=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_WAVE_SIZE=.*/EUADOPT_STAFF_INVITE_CRON_WAVE_SIZE=50/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_WAVE_SIZE=50' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_PM_WAVE_SIZE=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_PM_WAVE_SIZE=.*/EUADOPT_STAFF_INVITE_CRON_PM_WAVE_SIZE=50/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_PM_WAVE_SIZE=50' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_UAT_ONLY=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_UAT_ONLY=.*/EUADOPT_STAFF_INVITE_CRON_UAT_ONLY=1/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_UAT_ONLY=1' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=.*/EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=cabinet,magazin,grooming/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=cabinet,magazin,grooming' >> "${ENV_FILE}"
  fi
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

# Server H = UTC; CRON_TZ nu e aplicat de cron pe acest host → verificăm ora RO în script.
CRON_AM='0 * * * * bash '"${SCRIPT_SCHED}"' 10 am'
CRON_PM='0 * * * * bash '"${SCRIPT_SCHED}"' 13 pm'

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_invite_daily_wave.sh' \
  | grep -v 'run_invite_daily_wave_pm.sh' \
  | grep -v 'run_invite_daily_wave_at_ro_hour.sh' \
  > "${TMP}" || true
echo "${CRON_AM}" >> "${TMP}"
echo "${CRON_PM}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron invitații instalat (10:00 + 13:00 Europe/Bucharest via hourly check):"
crontab -l | grep -E 'run_invite_daily_wave' || true
echo "Log: /var/log/euadopt-invite-wave.log"
