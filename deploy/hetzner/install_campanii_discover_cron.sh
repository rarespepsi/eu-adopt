#!/usr/bin/env bash
# Instalează cron zilnic 06:20 Europe/Bucharest — scriptul rulează efectiv la ≥3 zile.
# Rulează ca root o singură dată.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_campanii_discover_every_3d.sh"
CRON_LINE="20 6 * * * sudo -u euadopt bash ${SCRIPT} >> /var/log/euadopt-campanii-discover.log 2>&1"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-campanii-discover.log
chmod 644 /var/log/euadopt-campanii-discover.log
mkdir -p /var/lib/euadopt
chown euadopt:euadopt /var/lib/euadopt 2>/dev/null || true

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'run_campanii_discover_every_3d' | grep -v 'euadopt-campanii-discover' > "${TMP}" || true
if ! grep -q '^CRON_TZ=' "${TMP}" 2>/dev/null; then
  echo "CRON_TZ=Europe/Bucharest" >> "${TMP}"
fi
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Cron instalat (check zilnic; exec la ≥3 zile):"
crontab -l | grep -E 'campanii_discover|CRON_TZ' || true
