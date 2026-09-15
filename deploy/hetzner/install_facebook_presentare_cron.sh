#!/usr/bin/env bash
# Cron: Luni + Miercuri 10:00 Europe/Bucharest — redistribuire video prezentare FB RO.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_facebook_presentare_repost.sh"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-facebook-presentare.log
chmod 644 /var/log/euadopt-facebook-presentare.log

# 10:00 RO — luni (1) și miercuri (3); CRON_TZ pe linie e suportat de cronie/vixie pe Ubuntu.
CRON_MON='0 10 * * 1 CRON_TZ=Europe/Bucharest bash '"${SCRIPT}"' lun'
CRON_WED='0 10 * * 3 CRON_TZ=Europe/Bucharest bash '"${SCRIPT}"' mie'

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_facebook_presentare_repost.sh' \
  | grep -v 'euadopt-facebook-presentare' \
  > "${TMP}" || true
echo "${CRON_MON}" >> "${TMP}"
echo "${CRON_WED}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron Facebook prezentare (Luni/Mie 10:00 RO):"
crontab -l | grep -E 'presentare|PRESENTARE' || true
