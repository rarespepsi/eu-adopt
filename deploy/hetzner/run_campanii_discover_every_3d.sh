#!/usr/bin/env bash
# Căutare campanii sterilizare pe toate județele + refresh DB + auto-publish (hartă + FB enqueue).
# Rulează doar dacă au trecut ≥3 zile de la ultima rulare reușită.
set -euo pipefail
APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
STAMP_DIR="${EUADOPT_STATE_DIR:-/var/lib/euadopt}"
STAMP_FILE="${STAMP_DIR}/campanii_discover_last_run.txt"
MIN_HOURS="${EUADOPT_CAMPANII_DISCOVER_EVERY_HOURS:-72}"
LOG="${EUADOPT_CAMPANII_DISCOVER_LOG:-/var/log/euadopt-campanii-discover.log}"

mkdir -p "${STAMP_DIR}"
cd "${APP_DIR}"
# shellcheck disable=SC1091
source venv/bin/activate

now_epoch="$(date +%s)"
if [[ -f "${STAMP_FILE}" ]]; then
  last="$(tr -d '[:space:]' < "${STAMP_FILE}" || true)"
  if [[ "${last}" =~ ^[0-9]+$ ]]; then
    age=$(( now_epoch - last ))
    need=$(( MIN_HOURS * 3600 ))
    if (( age < need )); then
      echo "[$(date -Is)] skip: last run ${age}s ago (< ${need}s / ${MIN_HOURS}h)" | tee -a "${LOG}"
      exit 0
    fi
  fi
fi

echo "[$(date -Is)] START discover --all-judete --refresh-db --auto-publish" | tee -a "${LOG}"
set +e
python manage.py discover_campanii_sterilizare \
  --all-judete \
  --refresh-db \
  --auto-publish \
  --publish-limit "${EUADOPT_CAMPANII_PUBLISH_LIMIT:-8}" \
  --max-per-query "${EUADOPT_CAMPANII_MAX_PER_QUERY:-6}" \
  --sleep "${EUADOPT_CAMPANII_SLEEP:-1.0}" \
  --out "database/exports/campanii_discover_cron_$(date +%Y%m%d).csv" \
  >>"${LOG}" 2>&1
rc=$?
set -e

if [[ "${rc}" -eq 0 ]]; then
  echo "${now_epoch}" > "${STAMP_FILE}"
  chown euadopt:euadopt "${STAMP_FILE}" 2>/dev/null || true
  echo "[$(date -Is)] DONE ok" | tee -a "${LOG}"
else
  echo "[$(date -Is)] FAIL rc=${rc}" | tee -a "${LOG}"
  exit "${rc}"
fi
