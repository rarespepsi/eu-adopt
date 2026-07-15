#!/usr/bin/env bash
# Cron zilnic 09:00 (Europe/Bucharest) — raport invitații ziua anterioară.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_invite_daily_report.sh"
ENV_FILE="${APP_DIR}/.env"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-invite-report.log
chmod 644 /var/log/euadopt-invite-report.log

if [[ -f "${ENV_FILE}" ]]; then
  if grep -q '^EUADOPT_STAFF_INVITE_REPORT_ENABLED=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_REPORT_ENABLED=.*/EUADOPT_STAFF_INVITE_REPORT_ENABLED=1/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_REPORT_ENABLED=1' >> "${ENV_FILE}"
  fi
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

CRON_LINE='0 9 * * * TZ=Europe/Bucharest '"${SCRIPT}"

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'run_invite_daily_report.sh' > "${TMP}" || true
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron raport invitații instalat (09:00 Europe/Bucharest):"
crontab -l | grep run_invite_daily_report || true
echo "Log: /var/log/euadopt-invite-report.log"
