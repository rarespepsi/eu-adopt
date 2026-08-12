#!/usr/bin/env bash
# Scrie /var/lib/euadopt/EXPECTED_RELEASE.txt din HEAD curent (după deploy + smoke OK).
#   bash /opt/eu-adopt/deploy/hetzner/mark_expected_release.sh
#   bash .../mark_expected_release.sh "note opțională"
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
STATE_DIR="${EUADOPT_STATE_DIR:-/var/lib/euadopt}"
EXPECTED="${EUADOPT_EXPECTED_RELEASE:-${STATE_DIR}/EXPECTED_RELEASE.txt}"
NOTE="${1:-deploy OK}"

mkdir -p "${STATE_DIR}"
PREV=""
if [[ -f "${EXPECTED}" ]]; then
  PREV="$(grep -E '^SHA=' "${EXPECTED}" | head -1 | cut -d= -f2- | tr -d '\r' || true)"
fi

FULL="$(sudo -u euadopt git -C "${APP_DIR}" rev-parse HEAD)"
SHORT="$(sudo -u euadopt git -C "${APP_DIR}" rev-parse --short HEAD)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "${EXPECTED}" <<EOF
# Site funcțional — ultima versiune validată (deploy + smoke).
# Healthcheck revine aici la incident. Nu edita manual decât dacă știi ce faci.
SHA=${FULL}
SHORT=${SHORT}
PREV_SHA=${PREV}
UPDATED=${STAMP}
NOTE=${NOTE}
EOF

# Oglindă în repo (documentație) — pe server poate fi dirty; e OK dacă e doar acest fișier
REPO_COPY="${APP_DIR}/deploy/EXPECTED_RELEASE.txt"
cp -a "${EXPECTED}" "${REPO_COPY}" 2>/dev/null || true
chown euadopt:euadopt "${REPO_COPY}" 2>/dev/null || true

echo "EXPECTED_RELEASE updated: ${SHORT} (${FULL})"
echo "file=${EXPECTED}"
