#!/usr/bin/env bash
# Cron zilnic 10:00 (Europe/Bucharest) — val invitații Add USER.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_invite_daily_wave.sh"
ENV_FILE="${APP_DIR}/.env"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-invite-wave.log
chmod 644 /var/log/euadopt-invite-wave.log

if [[ -f "${ENV_FILE}" ]]; then
  if grep -q '^EUADOPT_STAFF_INVITE_CRON_ENABLED=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_STAFF_INVITE_CRON_ENABLED=.*/EUADOPT_STAFF_INVITE_CRON_ENABLED=1/' "${ENV_FILE}"
  else
    echo 'EUADOPT_STAFF_INVITE_CRON_ENABLED=1' >> "${ENV_FILE}"
  fi
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

CRON_LINE='0 10 * * * TZ=Europe/Bucharest '"${SCRIPT}"

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'run_invite_daily_wave.sh' > "${TMP}" || true
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron invitații instalat (10:00 Europe/Bucharest):"
crontab -l | grep run_invite_daily_wave || true

echo "Inițializare cache Grupa B (ultima trimisă manual azi)..."
cd "${APP_DIR}"
sudo -u euadopt bash -c 'source venv/bin/activate && python manage.py staff_invite_daily_wave --init-last-group b'

echo "Gata. Următorul cron: Grupa A. Log: /var/log/euadopt-invite-wave.log"
