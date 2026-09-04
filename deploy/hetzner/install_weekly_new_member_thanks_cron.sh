#!/usr/bin/env bash
# Instalează cron duminică ~18:00 Europe/Bucharest pentru mail mulțumire membri noi.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_weekly_new_member_thanks_at_ro_hour.sh"
ENV_FILE="${APP_DIR}/.env"
HOUR="${EUADOPT_WEEKLY_THANKS_CRON_HOUR:-18}"

chmod +x \
  "${APP_DIR}/deploy/hetzner/run_weekly_new_member_thanks.sh" \
  "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-weekly-thanks.log
chmod 644 /var/log/euadopt-weekly-thanks.log

_set_env() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s/^${key}=.*/${key}=${val}/" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

if [[ -f "${ENV_FILE}" ]]; then
  _set_env 'EUADOPT_WEEKLY_THANKS_CRON_ENABLED' '1'
  _set_env 'EUADOPT_WEEKLY_NEW_MEMBER_THANKS_EMAIL_ENABLED' '1'
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_weekly_new_member_thanks' \
  | grep -v 'euadopt-weekly-thanks' \
  > "${TMP}" || true

if ! grep -q '^CRON_TZ=Europe/Bucharest$' "${TMP}"; then
  {
    echo "CRON_TZ=Europe/Bucharest"
    cat "${TMP}"
  } > "${TMP}.2"
  mv "${TMP}.2" "${TMP}"
fi
awk 'BEGIN{seen=0} /^CRON_TZ=Europe\/Bucharest$/{if(seen++) next} {print}' "${TMP}" > "${TMP}.3"
mv "${TMP}.3" "${TMP}"

# Check hourly UTC; script filtrează duminică + ora RO
echo "0 * * * * bash ${SCRIPT} ${HOUR}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron weekly new-member thanks (duminică ora RO ${HOUR}:00):"
crontab -l | grep -E 'weekly_new_member_thanks|weekly-thanks|CRON_TZ' || true
echo "Log: /var/log/euadopt-weekly-thanks.log"
echo "Flag: EUADOPT_WEEKLY_THANKS_CRON_ENABLED=1"
echo "Restart app dacă tocmai ai schimbat .env: systemctl restart euadopt"
