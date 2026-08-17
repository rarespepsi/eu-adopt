#!/usr/bin/env bash
# Instalează cron healthcheck 3×/zi (06:00, 14:00, 22:00 Europe/Bucharest).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_site_healthcheck.sh"
STATE_DIR="${EUADOPT_STATE_DIR:-/var/lib/euadopt}"

chmod +x "${SCRIPT}" \
  "${APP_DIR}/deploy/hetzner/undo_last_auto_repair.sh" \
  "${APP_DIR}/deploy/hetzner/mark_expected_release.sh" \
  "${APP_DIR}/deploy/hetzner/site_healthcheck.py" 2>/dev/null || true

mkdir -p "${STATE_DIR}"
chgrp euadopt "${STATE_DIR}" 2>/dev/null || true
chmod 775 "${STATE_DIR}" 2>/dev/null || true
touch /var/log/euadopt-healthcheck.log
chmod 644 /var/log/euadopt-healthcheck.log

# Seed EXPECTED dacă lipsește
if [[ ! -f "${STATE_DIR}/EXPECTED_RELEASE.txt" ]]; then
  bash "${APP_DIR}/deploy/hetzner/mark_expected_release.sh" "initial seed at cron install"
fi

# CRON_TZ pe crontab (Debian/Ubuntu)
CRON_BLOCK=$(cat <<EOF
CRON_TZ=Europe/Bucharest
0 6 * * * bash ${SCRIPT}
0 14 * * * bash ${SCRIPT}
0 22 * * * bash ${SCRIPT}
EOF
)

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_site_healthcheck.sh' \
  | grep -v 'euadopt-healthcheck' \
  | grep -v '^CRON_TZ=Europe/Bucharest$' \
  > "${TMP}" || true

# Păstrează un singur CRON_TZ=Europe/Bucharest la început dacă mai e folosit de alte joburi
if ! grep -q '^CRON_TZ=Europe/Bucharest$' "${TMP}"; then
  # inserăm TZ doar dacă nu există; altfel liniile healthcheck folosesc TZ deja setat
  {
    echo "CRON_TZ=Europe/Bucharest"
    cat "${TMP}"
  } > "${TMP}.2"
  mv "${TMP}.2" "${TMP}"
fi

# Elimină duplicate CRON_TZ
awk 'BEGIN{seen=0} /^CRON_TZ=Europe\/Bucharest$/{if(seen++) next} {print}' "${TMP}" > "${TMP}.3"
mv "${TMP}.3" "${TMP}"

echo "0 6 * * * bash ${SCRIPT}" >> "${TMP}"
echo "0 14 * * * bash ${SCRIPT}" >> "${TMP}"
echo "0 22 * * * bash ${SCRIPT}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron site healthcheck (06/14/22 Europe/Bucharest):"
crontab -l | grep -E 'healthcheck|CRON_TZ' || true
echo "Alert email: ${EUADOPT_HEALTHCHECK_EMAIL:-rarespepsi@gmail.com}"
echo "Auto-repair (rollback): ${EUADOPT_HEALTHCHECK_AUTO_REPAIR:-1}"
