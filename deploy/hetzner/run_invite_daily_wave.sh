#!/usr/bin/env bash
# Val zilnic invitații Add USER (manage.py staff_invite_daily_wave).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="/var/log/euadopt-invite-wave.log"

touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

{
  echo "=== $(date -Iseconds) invite daily wave ==="
  cd "${APP_DIR}"
  sudo -u euadopt bash -c 'source venv/bin/activate && python manage.py staff_invite_daily_wave'
} >> "${LOG}" 2>&1
