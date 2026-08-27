#!/usr/bin/env bash
# Rulează val radio doar când ora Europe/Bucharest = TARGET_HOUR.
# Cron UTC: 0 * * * * bash .../run_media_outreach_daily_wave_at_ro_hour.sh 10
set -euo pipefail

TARGET_HOUR="${1:?TARGET_HOUR required (ex. 10)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_HOUR="$(TZ=Europe/Bucharest date +%H)"
TARGET_PADDED="$(printf '%02d' "${TARGET_HOUR}")"

if [[ "${CURRENT_HOUR}" != "${TARGET_PADDED}" ]]; then
  exit 0
fi

exec bash "${SCRIPT_DIR}/run_media_outreach_daily_wave.sh"
