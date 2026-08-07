#!/usr/bin/env bash
# Cron invitații Add USER:
# - 10:00 Europe/Bucharest — adăposturi (AM)
# - 16:00 Europe/Bucharest — colaboratori cabinet/magazin/grooming (PM)
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT_AM="${APP_DIR}/deploy/hetzner/run_invite_daily_wave.sh"
SCRIPT_PM="${APP_DIR}/deploy/hetzner/run_invite_daily_wave_pm.sh"
ENV_FILE="${APP_DIR}/.env"

chmod +x "${SCRIPT_AM}" "${SCRIPT_PM}" 2>/dev/null || true
touch /var/log/euadopt-invite-wave.log
chmod 644 /var/log/euadopt-invite-wave.log

if [[ -f "${ENV_FILE}" ]]; then
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_ENABLED=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_ENABLED=.*/EUADOPT_STAFF_INVITE_CRON_ENABLED=1/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_ENABLED=1' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_MAX_PER_DAY=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_MAX_PER_DAY=.*/EUADOPT_STAFF_INVITE_MAX_PER_DAY=55/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_MAX_PER_DAY=55' >> "${ENV_FILE}"
  fi
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=.*/EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=cabinet,magazin,grooming/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES=cabinet,magazin,grooming' >> "${ENV_FILE}"
  fi
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

CRON_AM='0 10 * * * TZ=Europe/Bucharest '"${SCRIPT_AM}"
CRON_PM='0 16 * * * TZ=Europe/Bucharest '"${SCRIPT_PM}"

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_invite_daily_wave.sh' \
  | grep -v 'run_invite_daily_wave_pm.sh' > "${TMP}" || true
echo "${CRON_AM}" >> "${TMP}"
echo "${CRON_PM}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron invitații instalat:"
crontab -l | grep run_invite_daily_wave || true
echo "Log: /var/log/euadopt-invite-wave.log"
