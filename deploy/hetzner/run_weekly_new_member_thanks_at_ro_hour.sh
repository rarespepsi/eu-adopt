#!/usr/bin/env bash
# Mail mulțumire membri noi — rulează doar duminică, la ora RO țintă (default 18).
# Cron UTC hourly: 0 * * * * bash .../run_weekly_new_member_thanks_at_ro_hour.sh 18
set -euo pipefail

TARGET_HOUR="${1:?TARGET_HOUR required (ex. 18)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_DOW="$(TZ=Europe/Bucharest date +%u)"   # 1=Mon … 7=Sun
CURRENT_HOUR="$(TZ=Europe/Bucharest date +%H)"
TARGET_PADDED="$(printf '%02d' "${TARGET_HOUR}")"

# Doar duminică
if [[ "${CURRENT_DOW}" != "7" ]]; then
  exit 0
fi
if [[ "${CURRENT_HOUR}" != "${TARGET_PADDED}" ]]; then
  exit 0
fi

exec bash "${SCRIPT_DIR}/run_weekly_new_member_thanks.sh"
