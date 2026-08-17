#!/usr/bin/env bash
# Instalează cron zilnic pentru backup DB (rotație 3). Rulează ca root o singură dată.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/backup_db_rotate.sh"
CRON_LINE="0 3 * * * EUADOPT_DB_BACKUP_KEEP=3 bash ${SCRIPT} >> /var/log/euadopt-db-backup.log 2>&1"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-db-backup.log
chmod 644 /var/log/euadopt-db-backup.log

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'backup_db_rotate.sh' > "${TMP}" || true
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron instalat:"
crontab -l | grep backup_db_rotate || true
