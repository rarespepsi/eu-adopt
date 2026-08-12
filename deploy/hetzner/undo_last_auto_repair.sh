#!/usr/bin/env bash
# Revine la sha_before din ultimul auto-repair (dacă repararea a stricat altceva).
#   bash /opt/eu-adopt/deploy/hetzner/undo_last_auto_repair.sh
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
STATE_DIR="${EUADOPT_STATE_DIR:-/var/lib/euadopt}"
STATE_JSON="${STATE_DIR}/AUTO_REPAIR_STATE.json"

if [[ ! -f "${STATE_JSON}" ]]; then
  echo "Nu există ${STATE_JSON} — nimic de anulat."
  exit 1
fi

BEFORE="$(python3 - <<PY
import json
from pathlib import Path
d=json.loads(Path("${STATE_JSON}").read_text(encoding="utf-8"))
print((d.get("sha_before") or "").strip())
PY
)"

if [[ -z "${BEFORE}" || "${BEFORE}" == "unknown" ]]; then
  echo "sha_before lipsă în state."
  exit 2
fi

NOW="$(sudo -u euadopt git -C "${APP_DIR}" rev-parse HEAD)"
echo "Undo auto-repair: ${NOW} → ${BEFORE}"
sudo -u euadopt bash -lc "
  set -e
  cd '${APP_DIR}'
  git fetch --quiet origin || true
  git checkout --force '${BEFORE}'
  source venv/bin/activate
  python manage.py collectstatic --noinput
"
systemctl restart euadopt
sleep 2
systemctl is-active euadopt
echo "Undo OK. SHA acum: $(sudo -u euadopt git -C "${APP_DIR}" rev-parse --short HEAD)"
echo "State păstrat în ${STATE_JSON} (istoric)."
