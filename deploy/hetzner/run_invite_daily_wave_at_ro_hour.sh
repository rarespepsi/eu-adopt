#!/usr/bin/env bash
# Rulează val AM/PM doar când ora Europe/Bucharest = TARGET_HOUR.
# Cron pe server UTC: 0 * * * * (fără CRON_TZ — nu e suportat peste tot).
set -euo pipefail

TARGET_HOUR="${1:?TARGET_HOUR required (ex. 10 sau 13)}"
SLOT="${2:?SLOT required (am sau pm)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_HOUR="$(TZ=Europe/Bucharest date +%H)"
TARGET_PADDED="$(printf '%02d' "${TARGET_HOUR}")"

if [[ "${CURRENT_HOUR}" != "${TARGET_PADDED}" ]]; then
  exit 0
fi

case "${SLOT}" in
  am) exec bash "${SCRIPT_DIR}/run_invite_daily_wave.sh" ;;
  pm) exec bash "${SCRIPT_DIR}/run_invite_daily_wave_pm.sh" ;;
  *)
    echo "run_invite_daily_wave_at_ro_hour: slot necunoscut: ${SLOT}" >&2
    exit 2
    ;;
esac
