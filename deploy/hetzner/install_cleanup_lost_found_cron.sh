#!/usr/bin/env bash
# Instalează cron zilnic cleanup LostFound soft-delete > 45 zile. Rulează ca root o singură dată.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_cleanup_lost_found.sh"
CRON_LINE="20 4 * * * sudo -u euadopt bash ${SCRIPT} >> /var/log/euadopt-cleanup-lost-found.log 2>&1"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-cleanup-lost-found.log
chmod 644 /var/log/euadopt-cleanup-lost-found.log

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'run_cleanup_lost_found' > "${TMP}" || true
if ! grep -q '^CRON_TZ=' "${TMP}" 2>/dev/null; then
  echo "CRON_TZ=Europe/Bucharest" >> "${TMP}"
fi
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron instalat:"
crontab -l | grep -E 'cleanup_lost_found|CRON_TZ' || true
