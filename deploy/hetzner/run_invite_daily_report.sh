#!/usr/bin/env bash
# Raport zilnic invitații Add USER — ziua anterioară (manage.py staff_invite_daily_report).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-invite-report.log"

touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

{
  echo "=== $(date -Iseconds) invite daily report ==="
  cd "${APP_DIR}"
  sudo -u euadopt bash -c 'source venv/bin/activate && python manage.py staff_invite_daily_report'
} >> "${LOG}" 2>&1
