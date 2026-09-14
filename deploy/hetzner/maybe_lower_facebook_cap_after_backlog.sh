#!/usr/bin/env bash
# După golirea backlog-ului Facebook pe piețele Eu (de/fr/es/com),
# coboară EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY la TARGET (implicit 15).
# Până atunci lasă CLEARING_CAP (implicit 40) ca să se golească coada.
# Rulează ca root (scrie .env + restart). Fără secrete în stdout.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
ENV_FILE="${APP_DIR}/.env"
TARGET_CAP="${EUADOPT_FACEBOOK_TARGET_CAP_AFTER_BACKLOG:-15}"
CLEARING_CAP="${EUADOPT_FACEBOOK_CLEARING_CAP:-40}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "skip: missing ${ENV_FILE}"
  exit 0
fi

pending="$(
  sudo -u euadopt bash <<EOF
cd '${APP_DIR}'
source venv/bin/activate
python manage.py shell <<'PY'
from home.models import FacebookOutboundDelivery
n = FacebookOutboundDelivery.objects.filter(
    market__in=['de', 'fr', 'es', 'com'],
    status='pending',
).count()
print(n)
PY
EOF
)"

pending="$(echo "${pending}" | grep -E '^[0-9]+$' | tail -n1 | tr -d '[:space:]')"
if [[ ! "${pending}" =~ ^[0-9]+$ ]]; then
  echo "skip: could not read eu pending"
  exit 0
fi

cur="$(grep -E '^EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=' "${ENV_FILE}" | tail -n1 | cut -d= -f2- | tr -d '[:space:]')"
cur="${cur:-20}"

echo "eu_pending=${pending} current_cap=${cur} target=${TARGET_CAP} clearing=${CLEARING_CAP}"

if [[ "${pending}" -gt 0 ]]; then
  # Încă backlog Eu → asigură CLEARING_CAP (nu coborî prematur).
  if [[ "${cur}" != "${CLEARING_CAP}" ]]; then
    if grep -qE '^EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=' "${ENV_FILE}"; then
      sed -i "s/^EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=.*/EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=${CLEARING_CAP}/" "${ENV_FILE}"
    else
      echo "EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=${CLEARING_CAP}" >> "${ENV_FILE}"
    fi
    chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
    systemctl restart euadopt
    echo "kept/set clearing cap=${CLEARING_CAP} (backlog remains); restarted euadopt"
  else
    echo "keep clearing cap=${CLEARING_CAP} (backlog remains)"
  fi
  exit 0
fi

# Backlog Eu gol → coboară la TARGET dacă e nevoie
if [[ "${cur}" == "${TARGET_CAP}" ]]; then
  echo "already at target cap=${TARGET_CAP}"
  exit 0
fi

if grep -qE '^EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=' "${ENV_FILE}"; then
  sed -i "s/^EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=.*/EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=${TARGET_CAP}/" "${ENV_FILE}"
else
  echo "EUADOPT_FACEBOOK_MAX_POSTS_PER_DAY=${TARGET_CAP}" >> "${ENV_FILE}"
fi
chown euadopt:euadopt "${ENV_FILE}" 2>/dev/null || true
systemctl restart euadopt
echo "backlog clear → set cap=${TARGET_CAP}; restarted euadopt"
