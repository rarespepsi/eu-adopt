#!/usr/bin/env bash
# Instalează cron val radio zilnic (ora RO configurabilă, default 10:00).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_media_outreach_daily_wave_at_ro_hour.sh"
ENV_FILE="${APP_DIR}/.env"
HOUR="${EUADOPT_MEDIA_OUTREACH_CRON_HOUR:-10}"

chmod +x \
  "${APP_DIR}/deploy/hetzner/run_media_outreach_daily_wave.sh" \
  "${SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-media-radio-wave.log
chmod 644 /var/log/euadopt-media-radio-wave.log

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
  _set_env 'EUADOPT_MEDIA_OUTREACH_CRON_ENABLED' '1'
  _set_env 'EUADOPT_MEDIA_OUTREACH_MAX_PER_DAY' '30'
  _set_env 'EUADOPT_MEDIA_OUTREACH_CRON_WAVE_SIZE' '30'
  # Pauză SMTP (moștenește și STAFF_INVITE_SEND_DELAY_SEC dacă lipsește)
  _set_env 'EUADOPT_MEDIA_OUTREACH_SEND_DELAY_SEC' '60'
  _set_env 'EUADOPT_MEDIA_RADIO_WAVE_TIMEOUT' '2100'
  chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
fi

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_media_outreach_daily_wave' \
  | grep -v 'euadopt-media-radio' \
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

# Oră RO: verificare în script (cron UTC hourly)
echo "0 * * * * bash ${SCRIPT} ${HOUR}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron media radio wave (ora RO ${HOUR}:00, check hourly UTC):"
crontab -l | grep -E 'media_outreach|media-radio|CRON_TZ' || true
echo "Log: /var/log/euadopt-media-radio-wave.log"
echo "Flag: EUADOPT_MEDIA_OUTREACH_CRON_ENABLED=1 în .env (setat de acest script)"
echo "Restart app dacă tocmai ai schimbat .env: systemctl restart euadopt"
