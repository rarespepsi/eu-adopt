#!/usr/bin/env bash
# Cron: la fiecare 20 min — coadă Facebook (plafon zilnic + retry).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_facebook_outbound_flush.sh"
ENV_FILE="${APP_DIR}/.env"

chmod +x "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-facebook-outbound.log
chmod 644 /var/log/euadopt-facebook-outbound.log

if [[ -f "${ENV_FILE}" ]]; then
  if grep -q '^EUADOPT_FACEBOOK_AUTO_POST=' "${ENV_FILE}"; then
    sed -i 's/^EUADOPT_FACEBOOK_AUTO_POST=.*/EUADOPT_FACEBOOK_AUTO_POST=1/' "${ENV_FILE}"
  else
    echo 'EUADOPT_FACEBOOK_AUTO_POST=1' >> "${ENV_FILE}"
  fi
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

CRON_LINE='*/20 * * * * bash '"${SCRIPT}"

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_facebook_outbound_flush.sh' \
  | grep -v 'euadopt-facebook-outbound' \
  > "${TMP}" || true
echo "${CRON_LINE}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron Facebook outbound:"
crontab -l | grep -E 'facebook_outbound|FACEBOOK' || true
