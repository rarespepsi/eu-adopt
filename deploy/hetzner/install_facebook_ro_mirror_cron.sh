#!/usr/bin/env bash
# Cron: la fiecare 15 min — poll RO + mirror (doar dacă mirror enabled în .env).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_facebook_ro_mirror_poll.sh"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-facebook-ro-mirror.log
chmod 644 /var/log/euadopt-facebook-ro-mirror.log

CRON_LINE='*/15 * * * * bash '"${SCRIPT}"

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_facebook_ro_mirror_poll.sh' \
  | grep -v 'euadopt-facebook-ro-mirror' \
  > "${TMP}" || true
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron Facebook RO mirror poll:"
crontab -l | grep -E 'facebook_ro_mirror|FACEBOOK_RO' || true
echo "Notă: EUADOPT_FACEBOOK_RO_MIRROR_ENABLED rămâne 0 până configurezi tokenurile DE/FR/ES/COM."
